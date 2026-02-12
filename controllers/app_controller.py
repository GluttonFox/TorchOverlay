import os
import time

from core.config import AppConfig
from services.game_binder import GameBinder
from services.process_watcher import ProcessWatcher
from services.capture_service import CaptureService
from services.ocr.base_ocr import IOcrEngine


class AppController:
    """控制器：业务流程与 UI 交互的中枢。"""

    def __init__(
        self,
        cfg: AppConfig,
        binder: GameBinder,
        watcher: ProcessWatcher,
        capture: CaptureService,
        ocr: IOcrEngine,
    ):
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

        # A：截 client 区域（用于OCR/Overlay对齐）
        out_path = os.path.join(os.getcwd(), "captures", "last_client.png")
        cap = self._capture.capture_client_once(bound.hwnd, out_path, timeout_sec=2.5)

        if not cap.ok or not cap.path:
            self._ui.show_info(f"截图失败：{cap.error}")
            return

        # 云OCR
        r = self._ocr.recognize(cap.path)
        if not r.ok:
            self._ui.show_info(f"OCR失败：{r.error}")
            return

        self._ui.show_info(r.text if r.text else "未识别到文字")

    def update_config(self, ocr_config, watch_interval_ms: int) -> bool:
        """更新配置"""
        try:
            from core.config import AppConfig, OcrConfig
            from services.ocr.baidu_ocr import BaiduOcrEngine, BaiduOcrConfig

            # 更新配置对象
            self._cfg = AppConfig(
                app_title_prefix=self._cfg.app_title_prefix,
                keywords=self._cfg.keywords,
                watch_interval_ms=watch_interval_ms,
                elevated_marker=self._cfg.elevated_marker,
                ocr=ocr_config,
            )

            # 保存到文件
            if not self._cfg.save():
                raise Exception("保存配置文件失败")

            # 更新监控间隔
            self._watcher.interval_ms = watch_interval_ms

            # 重新创建OCR引擎（重要：确保新配置生效，包括debug_mode）
            ocr_cfg = BaiduOcrConfig(
                api_key=ocr_config.api_key,
                secret_key=ocr_config.secret_key,
                api_name=ocr_config.api_name,
                timeout_sec=ocr_config.timeout_sec,
                max_retries=ocr_config.max_retries,
                debug_mode=ocr_config.debug_mode,
            )
            self._ocr = BaiduOcrEngine(ocr_cfg)

            return True
        except Exception as e:
            print(f"更新配置失败: {e}")
            return False

    def get_config(self):
        """获取当前配置"""
        return self._cfg
