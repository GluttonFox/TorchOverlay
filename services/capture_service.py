"""截图服务 - 实现ICaptureService接口，集成内存优化"""
import os
import threading
import gc
from typing import Any

from PIL import Image
import win32gui

from services.interfaces import ICaptureService, CaptureResult
from services.overlay.target_window import get_client_rect_in_screen
from core.logger import get_logger

logger = get_logger(__name__)


class CaptureService(ICaptureService):
    """
    截图服务实现（带内存优化）

    策略：
    1. capture_window: 按窗口句柄截取整窗
    2. capture_client: 截取client区域（推荐用于OCR/Overlay对齐）
    3. capture_region: 截取client区域内的指定子区域

    优化特性：
    - 自动释放图像资源
    - 可选的图片格式优化
    - 可选的临时文件自动清理
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
        self._stats['total_captures'] += 1

        if not hwnd or not win32gui.IsWindow(hwnd):
            return CaptureResult(ok=False, error="无效的目标窗口句柄(hwnd)")

        title = win32gui.GetWindowText(hwnd) or ""
        if not title.strip():
            return CaptureResult(ok=False, error="目标窗口标题为空，无法按标题截图")

        result = self._capture_by_title(title, out_path, timeout_sec)

        # 优化和清理
        if result.ok and result.path:
            self._post_process_capture(result.path)

        return result

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
        im = None
        cropped = None
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
        finally:
            # 确保图像对象被正确关闭
            if cropped:
                cropped.close()
            if im:
                im.close()

            # 优化和清理
            self._post_process_capture(out_path)

            # 优化和清理
            self._post_process_capture(out_path)

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

        self._stats['total_captures'] += 1

        out_path = os.path.abspath(out_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        tmp_full = out_path + ".tmp_full.png"

        # 1) 先截整窗
        full = self._capture_by_title(title, tmp_full, timeout_sec)
        if not full.ok or not full.path:
            return full

        # 2) 计算 client 相对整窗的偏移（都用屏幕坐标系）
        im = None
        cropped = None
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
        finally:
            # 确保图像对象被正确关闭
            if cropped:
                cropped.close()
            if im:
                im.close()

    def _post_process_capture(self, image_path: str) -> None:
        """截图后处理：优化图片和清理临时文件

        Args:
            image_path: 图片路径
        """
        try:
            # 优化图片
            if self._enable_optimization:
                self._optimize_image(image_path)

            # 清理临时文件
            if self._auto_cleanup_temp:
                self._cleanup_temp_files(os.path.dirname(image_path))
        except Exception as e:
            logger.warning(f"截图后处理失败: {e}")

    def _optimize_image(self, image_path: str) -> bool:
        """优化图片以减少内存使用

        Args:
            image_path: 图片路径

        Returns:
            是否优化成功
        """
        try:
            original_size = os.path.getsize(image_path)
            img = Image.open(image_path)

            # 转换为RGB模式（如果需要）
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background

            # 保存为优化格式
            if self._optimize_format == 'JPEG':
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                optimized_path = image_path.replace('.png', '.jpg')
                img.save(
                    optimized_path,
                    'JPEG',
                    quality=self._optimize_quality,
                    optimize=True
                )

                # 删除原始PNG
                os.remove(image_path)
                os.rename(optimized_path, image_path)
            else:  # PNG
                img.save(
                    image_path,
                    'PNG',
                    optimize=True,
                    compress_level=9
                )

            optimized_size = os.path.getsize(image_path)
            savings = original_size - optimized_size

            if savings > 0:
                self._stats['optimized_captures'] += 1

            # 显式释放内存
            img.close()
            del img
            gc.collect()

            return True

        except Exception as e:
            logger.error(f"优化图片失败: {e}")
            return False

    def _cleanup_temp_files(self, temp_dir: str) -> int:
        """清理临时文件

        Args:
            temp_dir: 临时文件目录

        Returns:
            清理的文件数
        """
        try:
            temp_files = []
            for ext in ('*.png', '*.jpg', '*.jpeg'):
                import glob
                temp_files.extend(glob.glob(os.path.join(temp_dir, ext)))

            # 按修改时间排序
            temp_files.sort(key=lambda f: os.path.getmtime(f))

            cleanup_count = 0
            if len(temp_files) > self._max_temp_files:
                files_to_delete = len(temp_files) - self._max_temp_files

                for i in range(files_to_delete):
                    try:
                        os.remove(temp_files[i])
                        cleanup_count += 1
                    except Exception as e:
                        logger.error(f"删除临时文件失败: {e}")

                self._stats['cleanup_count'] += cleanup_count

            return cleanup_count

        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
            return 0

    def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            'total_captures': 0,
            'optimized_captures': 0,
            'cleanup_count': 0
        }

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
