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
        self._cfg = AppConfig()

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

    def create_controller(self) -> AppController:
        binder = self.create_game_binder()
        watcher = self.create_process_watcher()
        capture = self.create_capture_service()
        ocr = self.create_ocr_engine()
        return AppController(cfg=self._cfg, binder=binder, watcher=watcher, capture=capture, ocr=ocr)

    def create_ocr_engine(self):
        cfg = BaiduOcrConfig(
            api_key="ZWkIofSWD0NLUaVOv9haUv6v",
            secret_key="0QXmsJTj5egvRPnIn78DKPh0JehRiN2B",
            api_name="accurate",  # 先用标准版；需要更强再换 accurate_basic
        )
        return BaiduOcrEngine(cfg)




