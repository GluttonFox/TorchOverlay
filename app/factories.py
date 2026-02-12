from core.config import AppConfig
from controllers.app_controller import AppController
from services.admin_service import AdminService
from services.window_finder import WindowFinder
from services.game_binder import GameBinder
from services.process_watcher import ProcessWatcher
from ui.main_window import MainWindow
from services.capture_service import CaptureService
from services.ocr.baidu_ocr import BaiduOcrEngine, BaiduOcrConfig


class AppFactory:
    """集中装配依赖：后续加截图/云OCR只需在这里注入。"""

    def __init__(self):
        self._cfg = AppConfig.load()
        self._debug_print("[AppFactory] 配置已加载:")
        self._debug_print(f"  API Key: {self._cfg.ocr.api_key[:10] if self._cfg.ocr.api_key else '空'}...")
        self._debug_print(f"  Secret Key: {self._cfg.ocr.secret_key[:10] if self._cfg.ocr.secret_key else '空'}...")
        self._debug_print(f"  API Name: {self._cfg.ocr.api_name}")
        self._debug_print(f"  Debug Mode: {self._cfg.ocr.debug_mode}")

    def _debug_print(self, *args, **kwargs):
        """调试输出，仅在调试模式下打印"""
        if self._cfg.ocr.debug_mode:
            print(*args, **kwargs)

    def create_config(self) -> AppConfig:
        return self._cfg

    def create_admin_service(self) -> AdminService:
        return AdminService()

    def create_window_finder(self) -> WindowFinder:
        return WindowFinder(self._cfg.keywords)

    def create_game_binder(self) -> GameBinder:
        finder = self.create_window_finder()
        return GameBinder(finder)

    def create_process_watcher(self) -> ProcessWatcher:
        return ProcessWatcher(interval_ms=self._cfg.watch_interval_ms)

    def create_controller(self) -> AppController:
        binder = self.create_game_binder()
        watcher = self.create_process_watcher()
        return AppController(cfg=self._cfg, binder=binder, watcher=watcher)

    def create_main_window(self, controller: AppController) -> MainWindow:
        return MainWindow(cfg=self._cfg, controller=controller)

    def create_capture_service(self) -> CaptureService:
        return CaptureService()

    def create_ocr_engine(self):
        cfg = BaiduOcrConfig(
            api_key=self._cfg.ocr.api_key,
            secret_key=self._cfg.ocr.secret_key,
            api_name=self._cfg.ocr.api_name,
            timeout_sec=self._cfg.ocr.timeout_sec,
            max_retries=self._cfg.ocr.max_retries,
            debug_mode=self._cfg.ocr.debug_mode,
        )
        self._debug_print("[AppFactory] 创建 OCR 引擎:")
        self._debug_print(f"  API Key 长度: {len(cfg.api_key)}")
        self._debug_print(f"  Secret Key 长度: {len(cfg.secret_key)}")
        self._debug_print(f"  Debug Mode: {cfg.debug_mode}")
        return BaiduOcrEngine(cfg)

    def recreate_ocr_engine(self):
        """重新创建OCR引擎（用于配置更新后）"""
        return self.create_ocr_engine()




