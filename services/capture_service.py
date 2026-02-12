"""截图服务 - 实现ICaptureService接口"""
import os
import threading
from typing import Any

from PIL import Image
import win32gui

from services.interfaces import ICaptureService, CaptureResult
from services.overlay.target_window import get_client_rect_in_screen


class CaptureService(ICaptureService):
    """
    截图服务实现

    策略：
    1. capture_window: 按窗口句柄截取整窗
    2. capture_client: 截取client区域（推荐用于OCR/Overlay对齐）
    3. capture_region: 截取client区域内的指定子区域
    """

    def capture_window(
        self,
        hwnd: int,
        out_path: str,
        timeout_sec: float = 2.5
    ) -> CaptureResult:
        """截取整个窗口

        Args:
            hwnd: 窗口句柄
            out_path: 输出路径
            timeout_sec: 超时时间

        Returns:
            截图结果
        """
        if not hwnd or not win32gui.IsWindow(hwnd):
            return CaptureResult(ok=False, error="无效的目标窗口句柄(hwnd)")

        title = win32gui.GetWindowText(hwnd) or ""
        if not title.strip():
            return CaptureResult(ok=False, error="目标窗口标题为空，无法按标题截图")

        return self._capture_by_title(title, out_path, timeout_sec)

    def capture_region(
        self,
        hwnd: int,
        out_path: str,
        region: dict[str, Any],
        timeout_sec: float = 2.5,
        preprocess: bool = False
    ) -> CaptureResult:
        """截取指定区域

        Args:
            hwnd: 窗口句柄
            out_path: 输出路径
            region: 区域定义 {x, y, width, height}
            timeout_sec: 超时时间
            preprocess: 是否预处理

        Returns:
            截图结果
        """
        if not hwnd or not win32gui.IsWindow(hwnd):
            return CaptureResult(ok=False, error="无效的目标窗口句柄(hwnd)")

        # 检查窗口是否可见
        if not win32gui.IsWindowVisible(hwnd):
            return CaptureResult(ok=False, error="目标窗口不可见")

        # 检查窗口是否最小化
        if win32gui.IsIconic(hwnd):
            return CaptureResult(ok=False, error="目标窗口已最小化")

        out_path = os.path.abspath(out_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        tmp_client = out_path + ".tmp_client.png"

        # 1) 先截取整个 client 区域
        client = self.capture_client(hwnd, tmp_client, timeout_sec)
        if not client.ok or not client.path:
            return client

        # 2) 从 client 截图中裁剪出指定区域
        try:
            x = int(region['x'])
            y = int(region['y'])
            width = int(region['width'])
            height = int(region['height'])

            im = Image.open(tmp_client).convert("RGBA")
            img_w, img_h = im.size

            # 检查区域是否在图像范围内
            if x < 0 or y < 0 or x + width > img_w or y + height > img_h:
                return CaptureResult(
                    ok=False,
                    error=f"区域超出图像范围: image={img_w}x{img_h}, region={x},{y},{width},{height}"
                )

            # 裁剪区域
            cropped = im.crop((x, y, x + width, y + height))

            # 如果需要预处理，可以在这里添加（当前未实现）
            if preprocess:
                # 可以添加图像增强、去噪等预处理逻辑
                pass

            cropped.save(out_path)

            # 清理临时文件
            try:
                os.remove(tmp_client)
            except Exception:
                pass

            return CaptureResult(ok=True, path=out_path)

        except Exception as e:
            return CaptureResult(ok=False, error=f"裁剪区域失败：{e}")

    def capture_client(
        self,
        hwnd: int,
        out_path: str,
        timeout_sec: float = 2.5
    ) -> CaptureResult:
        """截取client区域

        Args:
            hwnd: 窗口句柄
            out_path: 输出路径
            timeout_sec: 超时时间

        Returns:
            截图结果
        """
        if not hwnd or not win32gui.IsWindow(hwnd):
            return CaptureResult(ok=False, error="无效的目标窗口句柄(hwnd)")

        title = win32gui.GetWindowText(hwnd) or ""
        if not title.strip():
            return CaptureResult(ok=False, error="目标窗口标题为空，无法按标题截图")

        out_path = os.path.abspath(out_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        tmp_full = out_path + ".tmp_full.png"

        # 1) 先截整窗
        full = self._capture_by_title(title, tmp_full, timeout_sec)
        if not full.ok or not full.path:
            return full

        # 2) 计算 client 相对整窗的偏移（都用屏幕坐标系）
        try:
            wx1, wy1, wx2, wy2 = win32gui.GetWindowRect(hwnd)    # window rect in screen coords
            cx, cy, cw, ch = get_client_rect_in_screen(hwnd)     # client rect in screen coords

            ox = int(cx - wx1)
            oy = int(cy - wy1)

            # 3) 裁剪出 client 区域
            im = Image.open(tmp_full).convert("RGBA")
            cropped = im.crop((ox, oy, ox + int(cw), oy + int(ch)))
            cropped.save(out_path)

            # 清理临时文件
            try:
                os.remove(tmp_full)
            except Exception:
                pass

            return CaptureResult(ok=True, path=out_path)

        except Exception as e:
            return CaptureResult(ok=False, error=f"裁剪 client 失败：{e}")

    def _capture_by_title(
        self,
        window_title: str,
        out_path: str,
        timeout_sec: float = 2.0,
        cursor_capture=None,
        draw_border=None,
    ) -> CaptureResult:
        """按窗口标题截图

        Args:
            window_title: 窗口标题
            out_path: 输出路径
            timeout_sec: 超时时间
            cursor_capture: 是否捕获光标
            draw_border: 是否绘制边框

        Returns:
            截图结果
        """
        try:
            from windows_capture import WindowsCapture, Frame, InternalCaptureControl
        except Exception as e:
            return CaptureResult(ok=False, error=f"未安装或无法加载 windows_capture：{e}")

        out_path = os.path.abspath(out_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        done = threading.Event()
        result = CaptureResult(ok=False)

        capture = WindowsCapture(
            cursor_capture=cursor_capture,
            draw_border=draw_border,
            monitor_index=None,
            window_name=window_title,
        )

        @capture.event
        def on_frame_arrived(frame: Frame, capture_control: InternalCaptureControl):
            nonlocal result
            try:
                frame.save_as_image(out_path)
                result = CaptureResult(ok=True, path=out_path)
            except Exception as e:
                result = CaptureResult(ok=False, error=f"save_as_image失败：{e}")
            finally:
                try:
                    capture_control.stop()
                finally:
                    done.set()

        @capture.event
        def on_closed():
            if not done.is_set():
                done.set()

        capture.start()

        if not done.wait(timeout=timeout_sec):
            return CaptureResult(ok=False, error=f"截图超时（{timeout_sec}s），可能未找到窗口或无法捕获")

        return result
