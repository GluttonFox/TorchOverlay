import os
import threading
from dataclasses import dataclass

from windows_capture import WindowsCapture, Frame, InternalCaptureControl  # windows-capture 包

@dataclass
class CaptureResult:
    ok: bool
    path: str | None = None
    error: str | None = None


class CaptureService:
    """
    使用 windows-capture 截一帧并保存为 PNG。
    设计目标：一次点击 -> 一次截图 -> 返回结果（可接云OCR）
    """

    def capture_window_once(
        self,
        window_title: str,
        out_path: str,
        timeout_sec: float = 2.0,
        cursor_capture=None,
        draw_border=None,
    ) -> CaptureResult:
        if not window_title:
            return CaptureResult(ok=False, error="window_title 为空")

        out_path = os.path.abspath(out_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        done = threading.Event()
        result = CaptureResult(ok=False)

        # 按库的示例参数：monitor_index / window_name 二选一，这里用 window_name
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
                frame.save_as_image(out_path)  # 库示例：直接保存 PNG :contentReference[oaicite:2]{index=2}
                result = CaptureResult(ok=True, path=out_path)
            except Exception as e:
                result = CaptureResult(ok=False, error=f"save_as_image 失败：{e}")
            finally:
                # 只截一帧：保存后立即停止
                try:
                    capture_control.stop()  # 库示例：优雅停止 :contentReference[oaicite:3]{index=3}
                finally:
                    done.set()

        @capture.event
        def on_closed():
            # 窗口关闭/会话结束也要退出等待
            if not done.is_set():
                done.set()

        # start() 会启动捕获（库示例就是 capture.start()） :contentReference[oaicite:4]{index=4}
        capture.start()

        if not done.wait(timeout=timeout_sec):
            # 超时：可能没找到窗口/没有权限/系统不支持
            return CaptureResult(ok=False, error=f"截图超时（{timeout_sec}s），可能未找到窗口或无法捕获")

        return result
