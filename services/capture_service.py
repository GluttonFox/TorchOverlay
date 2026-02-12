import os
import threading
from dataclasses import dataclass

from PIL import Image, ImageEnhance, ImageFilter
import win32gui

from services.overlay.target_window import get_client_rect_in_screen


@dataclass
class CaptureResult:
    ok: bool
    path: str | None = None
    error: str | None = None


class CaptureService:
    """
    截图服务：
    - capture_window_once: 你当前可用的整窗截图（B）
    - capture_client_once: 推荐用于OCR/Overlay对齐的client截图（A）
        实现策略：先用B方式截一张，再按 client rect 从整窗图中裁剪出 A
    """

    def capture_window_once(
        self,
        window_title: str,
        out_path: str,
        timeout_sec: float = 2.0,
        cursor_capture=None,
        draw_border=None,
    ) -> CaptureResult:
        """
        B：整窗截图（按窗口标题 window_name 捕获）
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

    def capture_client_once(
        self,
        target_hwnd: int,
        out_path: str,
        timeout_sec: float = 2.5,
    ) -> CaptureResult:
        """
        A：只截 client 区域（推荐）
        实现：先用 B 截整窗到临时文件，再裁剪出 client 区域保存到 out_path
        """
        if not target_hwnd or not win32gui.IsWindow(target_hwnd):
            return CaptureResult(ok=False, error="无效的目标窗口句柄(hwnd)")

        title = win32gui.GetWindowText(target_hwnd) or ""
        if not title.strip():
            return CaptureResult(ok=False, error="目标窗口标题为空，无法按标题截图")

        out_path = os.path.abspath(out_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        tmp_full = out_path + ".tmp_full.png"

        # 1) 先按 B 截整窗
        full = self.capture_window_once(title, tmp_full, timeout_sec=timeout_sec)
        if not full.ok or not full.path:
            return full

        # 2) 计算 client 相对整窗的偏移（都用屏幕坐标系）
        try:
            wx1, wy1, wx2, wy2 = win32gui.GetWindowRect(target_hwnd)    # window rect in screen coords
            cx, cy, cw, ch = get_client_rect_in_screen(target_hwnd)     # client rect in screen coords

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

    @staticmethod
    def _preprocess_image(image_path: str, output_path: str) -> str:
        """
        预处理图片以提高OCR识别准确率
        1. 放大图片
        2. 增强对比度
        3. 增强锐度
        """
        try:
            img = Image.open(image_path).convert('RGB')

            # 放大图片 - 提高小文字的识别率
            scale_factor = 3  # 放大3倍
            new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

            # 增强对比度 - 使文字更清晰
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)  # 对比度增强2倍

            # 增强锐度 - 使文字边缘更清晰
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(2.0)  # 锐度增强2倍

            # 保存预处理后的图片
            img.save(output_path, quality=95)
            return output_path

        except Exception as e:
            print(f"[CaptureService] 图片预处理失败: {e}")
            # 如果预处理失败，返回原始图片路径
            return image_path

    def capture_region_once(
        self,
        target_hwnd: int,
        out_path: str,
        region: dict,
        timeout_sec: float = 2.5,
        preprocess: bool = True,  # 是否预处理图片
    ) -> CaptureResult:
        """
        截取client区域中的指定区域
        region格式: {'x': int, 'y': int, 'width': int, 'height': int}
        preprocess: 是否预处理图片以提高识别准确率
        """
        if not target_hwnd or not win32gui.IsWindow(target_hwnd):
            return CaptureResult(ok=False, error="无效的目标窗口句柄(hwnd)")

        out_path = os.path.abspath(out_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # 先截取整个client区域
        tmp_full = out_path + ".tmp_full.png"
        full_cap = self.capture_client_once(target_hwnd, tmp_full, timeout_sec=timeout_sec)
        if not full_cap.ok or not full_cap.path:
            return full_cap

        try:
            # 裁剪出指定区域
            im = Image.open(tmp_full).convert("RGBA")
            cropped = im.crop((
                region['x'],
                region['y'],
                region['x'] + region['width'],
                region['y'] + region['height']
            ))

            # 如果需要预处理，应用预处理
            if preprocess:
                tmp_cropped = out_path + ".tmp_cropped.png"
                cropped.save(tmp_cropped)
                processed_path = self._preprocess_image(tmp_cropped, out_path)
                # 清理临时文件
                try:
                    os.remove(tmp_cropped)
                except Exception:
                    pass
                result_path = processed_path
            else:
                cropped.save(out_path)
                result_path = out_path

            # 清理临时文件
            try:
                os.remove(tmp_full)
            except Exception:
                pass

            return CaptureResult(ok=True, path=result_path)

        except Exception as e:
            return CaptureResult(ok=False, error=f"裁剪区域失败：{e}")
