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
from services.price_calculator_service import PriceCalculatorService
from services.recognition_flow_service import RecognitionFlowService
from services.ui_update_service import UIUpdateService
from services.config_manager import ConfigManager
from domain.services import TextParserService, RegionCalculatorService
from core.logger import get_logger
from core.event_bus import get_event_bus, EventBus
from core.state_manager import get_state_manager, StateManager

logger = get_logger(__name__)


class AppFactory:
    """集中装配依赖：后续加截图/云OCR只需在这里注入。"""

    def __init__(self, enable_config_hot_reload: bool = False, enable_config_encryption: bool = False) -> None:
        # 使用ConfigManager加载配置（如果需要热更新或加密）
        if enable_config_hot_reload or enable_config_encryption:
            self._config_manager = ConfigManager(
                enable_hot_reload=enable_config_hot_reload,
                enable_encryption=enable_config_encryption
            )
            self._cfg = self._config_manager.load_config()
        else:
            self._config_manager = None
            self._cfg = AppConfig.load()

        self._debug_print("[AppFactory] 配置已加载:")
        self._debug_print(f"  API Key: {self._cfg.ocr.api_key[:10] if self._cfg.ocr.api_key else '空'}...")
        self._debug_print(f"  Secret Key: {self._cfg.ocr.secret_key[:10] if self._cfg.ocr.secret_key else '空'}...")
        self._debug_print(f"  API Name: {self._cfg.ocr.api_name}")
        self._debug_print(f"  Debug Mode: {self._cfg.ocr.debug_mode}")

    def _debug_print(self, *args, **kwargs) -> None:
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
        price_calculator = self.create_price_calculator_service(item_price_service)
        recognition_flow = self.create_recognition_flow_service(capture, ocr, text_parser, region_calculator)
        ui_update_service = self.create_ui_update_service(text_parser, price_calculator, item_price_service)
        state_manager = self.create_state_manager()
        event_bus = self.create_event_bus()
        return AppController(cfg=self._cfg, binder=binder, watcher=watcher, capture=capture, ocr=ocr, overlay=overlay, text_parser=text_parser, region_calculator=region_calculator, item_price_service=item_price_service, price_update_service=price_update_service, price_calculator=price_calculator, recognition_flow=recognition_flow, state_manager=state_manager, event_bus=event_bus, ui_update_service=ui_update_service)

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

    def create_price_calculator_service(self, item_price_service: ItemPriceService) -> PriceCalculatorService:
        """创建价格计算服务"""
        return PriceCalculatorService(item_price_service=item_price_service, gem_price_key="神威辉石")

    def create_recognition_flow_service(
        self,
        capture_service: CaptureService,
        ocr_engine: BaiduOcrEngine,
        text_parser: TextParserService,
        region_calculator: RegionCalculatorService
    ) -> RecognitionFlowService:
        """创建识别流程服务"""
        return RecognitionFlowService(
            capture_service=capture_service,
            ocr_service=ocr_engine,
            text_parser=text_parser,
            region_calculator=region_calculator,
            debug_callback=self._debug_print
        )

    def create_ui_update_service(
        self,
        text_parser: TextParserService,
        price_calculator: PriceCalculatorService,
        item_price_service: ItemPriceService
    ) -> UIUpdateService:
        """创建UI更新服务"""
        service = UIUpdateService(
            text_parser=text_parser,
            price_calculator=price_calculator,
            item_price_service=item_price_service
        )
        service.set_config(self._cfg)
        return service

    def create_event_bus(self) -> EventBus:
        """创建事件总线（单例）"""
        return get_event_bus()

    def create_state_manager(self) -> StateManager:
        """创建状态管理器（单例）"""
        return get_state_manager()

    def create_config_manager(self) -> ConfigManager | None:
        """创建配置管理器"""
        return self._config_manager

    def create_overlay_service(self) -> OverlayService:
        return OverlayService()

    def create_main_window(self, controller: AppController) -> MainWindow:
        return MainWindow(cfg=self._cfg, controller=controller)

    def create_capture_service(self) -> CaptureService:
        return CaptureService()

    def create_ocr_engine(self) -> BaiduOcrEngine:
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

    def recreate_ocr_engine(self) -> BaiduOcrEngine:
        """重新创建OCR引擎（用于配置更新后）"""
        return self.create_ocr_engine()




