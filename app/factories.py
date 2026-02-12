from core.config import AppConfig
from controllers.app_controller import AppController
from services.admin_service import AdminService
from services.window_finder import WindowFinder
from services.game_binder import GameBinder
from services.process_watcher import ProcessWatcher
from ui.main_window import MainWindow
from services.capture_service import CaptureService
from services.ocr.baidu_ocr import BaiduOcrEngine, BaiduOcrConfig
from services.overlay.overlay_service import OverlayService
from services.item_price_service import ItemPriceService
from services.price_update_service import PriceUpdateService
from domain.services import TextParserService, RegionCalculatorService
from core.logger import get_logger

logger = get_logger(__name__)


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
            logger.debug(*args, **kwargs)

    def create_config(self) -> AppConfig:
        return self._cfg

    def create_admin_service(self) -> AdminService:
        return AdminService(self._cfg)

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
        capture = self.create_capture_service()
        ocr = self.create_ocr_engine()
        overlay = self.create_overlay_service()
        text_parser = self.create_text_parser_service()
        region_calculator = self.create_region_calculator_service()
        item_price_service = self.create_item_price_service()
        price_update_service = self.create_price_update_service()
        return AppController(cfg=self._cfg, binder=binder, watcher=watcher, capture=capture, ocr=ocr, overlay=overlay, text_parser=text_parser, region_calculator=region_calculator, item_price_service=item_price_service, price_update_service=price_update_service)

    def create_text_parser_service(self) -> TextParserService:
        """创建文本解析服务"""
        return TextParserService()

    def create_region_calculator_service(self) -> RegionCalculatorService:
        """创建区域计算服务"""
        return RegionCalculatorService()

    def create_item_price_service(self) -> ItemPriceService:
        """创建物品价格服务"""
        return ItemPriceService()

    def create_price_update_service(self) -> PriceUpdateService:
        """创建物价更新服务"""
        return PriceUpdateService(self._cfg)

    def create_overlay_service(self) -> OverlayService:
        return OverlayService()

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
        logger.debug("[AppFactory] 创建 OCR 引擎:")
        logger.debug(f"  API Key 长度: {len(cfg.api_key)}")
        logger.debug(f"  Secret Key 长度: {len(cfg.secret_key)}")
        logger.debug(f"  Debug Mode: {cfg.debug_mode}")
        return BaiduOcrEngine(cfg)

    def recreate_ocr_engine(self):
        """重新创建OCR引擎（用于配置更新后）"""
        return self.create_ocr_engine()




