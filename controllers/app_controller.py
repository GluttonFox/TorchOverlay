from core.config import AppConfig
from services.game_binder import GameBinder
from services.ocr.base_ocr import IOcrEngine
from services.process_watcher import ProcessWatcher
from services.capture_service import CaptureService
import time
import os

class AppController:
    """控制器：业务流程与 UI 交互的中枢。"""

    def __init__(self, cfg: AppConfig, binder: GameBinder, watcher: ProcessWatcher, capture: CaptureService, ocr: IOcrEngine):
        self._cfg = cfg
        self._binder = binder
        self._watcher = watcher
        self._capture = capture
        self._ocr = ocr
        self._ui = None

    def attach_ui(self, ui):
        self._ui = ui

    def on_window_shown(self):
        self._ensure_bound_or_exit()
        self._schedule_watch()

    def _ensure_bound_or_exit(self):
        while True:
            if self._binder.try_bind():
                self._ui.set_bind_state(self._binder.bound)
                return

            retry = self._ui.ask_bind_retry_or_exit()
            if not retry:
                self._ui.close()
                return

    def _schedule_watch(self):
        def tick():
            bound = self._binder.bound
            if bound:
                # 句柄失效或进程退出 -> 关闭程序
                if not self._binder.is_bound_hwnd_valid():
                    self._ui.close()
                    return
                if not self._watcher.is_alive(bound):
                    self._ui.close()
                    return

            self._ui.schedule(self._watcher.interval_ms, tick)

        self._ui.schedule(self._watcher.interval_ms, tick)

    def on_detect_click(self):
        bound = self._binder.bound
        if not bound:
            self._ui.show_info("未绑定游戏窗口，无法识别。")
            return

        out_path = os.path.join(os.getcwd(), "captures", "last_capture.png")
        cap = self._capture.capture_window_once(bound.title, out_path, timeout_sec=2.5)
        if not cap.ok:
            self._ui.show_info(f"截图失败：{cap.error}")
            return

        r = self._ocr.recognize(cap.path)
        if not r.ok:
            self._ui.show_info(f"OCR失败：{r.error}")
            return

        self._ui.show_info(r.text if r.text else "未识别到文字")