"""应用控制器 - 重构版，使用接口抽象和领域服务"""
from typing import Any

from core.config import AppConfig
from core.paths import ProjectPaths
from core.logger import get_logger
from core.event_bus import Events, EventBus
from core.state_manager import StateManager
from services.interfaces import (
    IGameBinder,
    IProcessWatcher,
    ICaptureService,
    IOcrService,
    IOverlayService,
)
from services.overlay.target_window import get_client_rect_in_screen
from services.price_calculator_service import PriceCalculatorService
from services.recognition_flow_service import RecognitionFlowService
from services.ui_update_service import UIUpdateService
from domain.services import TextParserService, RegionCalculatorService
from domain.models import Region

logger = get_logger(__name__)


class AppController:
    """控制器：业务流程与 UI 交互的中枢。

    遵循依赖倒置原则（DIP），通过接口依赖服务，不依赖具体实现。
    遵循单一职责原则（SRP），只负责协调业务流程。
    """

    def __init__(
        self,
        cfg: AppConfig,
        binder: IGameBinder,
        watcher: IProcessWatcher,
        capture: ICaptureService,
        ocr: IOcrService,
        overlay: IOverlayService,
        text_parser: TextParserService,
        region_calculator: RegionCalculatorService,
        item_price_service,
        price_service,
        price_calculator: PriceCalculatorService,
        recognition_flow: RecognitionFlowService,
        state_manager: StateManager,
        event_bus: EventBus,
        ui_update_service: UIUpdateService,
        game_log_watcher=None,
        verification_service=None,
        exchange_monitor=None,
    ):
        """初始化控制器

        Args:
            cfg: 应用配置
            binder: 游戏绑定器接口
            watcher: 进程监视器接口
            capture: 截图服务接口
            ocr: OCR服务接口
            overlay: Overlay服务接口
            text_parser: 文本解析领域服务
            region_calculator: 区域计算领域服务
            item_price_service: 物品价格服务
            price_service: 统一价格服务（同步/异步）
            price_calculator: 价格计算服务
            recognition_flow: 识别流程服务
            state_manager: 状态管理器
            event_bus: 事件总线
            ui_update_service: UI更新服务
        """
        self._cfg = cfg
        self._binder = binder
        self._watcher = watcher
        self._capture = capture
        self._ocr = ocr
        self._overlay = overlay
        self._text_parser = text_parser
        self._region_calculator = region_calculator
        self._item_price_service = item_price_service
        self._price_service = price_service
        self._price_calculator = price_calculator
        self._recognition_flow = recognition_flow
        self._state_manager = state_manager
        self._event_bus = event_bus
        self._ui_update_service = ui_update_service
        self._ui_update_service.set_config(cfg)
        self._game_log_watcher = game_log_watcher
        self._verification_service = verification_service
        self._exchange_monitor = exchange_monitor
        self._ui = None

    def attach_ui(self, ui) -> None:
        """附加UI到控制器

        Args:
            ui: UI实例
        """
        self._ui = ui
        # 更新UI窗口状态
        self._state_manager.set_ui_window_visible(True)

    def _debug_log(self, *args, **kwargs) -> None:
        """调试日志（仅在debug模式下输出）

        Args:
            *args: 打印参数
            **kwargs: 打印关键字参数
        """
        if self._cfg.ocr.debug_mode:
            # logger.debug(*args, **kwargs)
            pass

    def on_window_shown(self) -> None:
        """窗口显示后的初始化"""
        self._ensure_bound_or_exit()
        self._schedule_watch()

    def _ensure_bound_or_exit(self) -> None:
        """确保绑定游戏或退出"""
        while True:
            if self._binder.try_bind():
                self._ui.set_bind_state(self._binder.bound)

                # 初始化游戏日志监控（基于绑定的进程路径）
                self._initialize_game_log_watcher()

                return

            retry = self._ui.ask_bind_retry_or_exit()
            if not retry:
                self._overlay.close()
                self._ui.close()
                return

    def _initialize_game_log_watcher(self) -> None:
        """初始化游戏日志监控服务

        根据绑定的游戏进程路径动态设置游戏日志路径
        """
        if not self._game_log_watcher:
            logger.info("游戏日志监控服务未初始化")
            return

        try:
            # 获取进程路径
            process_path = self._binder._finder.get_process_path(self._binder.bound.process_id)
            if not process_path:
                logger.warning("无法获取游戏进程路径，使用默认日志路径")
                process_path = r"D:\TapTap\PC Games\172664\UE_game\Torchlight\Saved\Logs\UE_game.log"

            # 构建游戏日志路径
            # 游戏进程在 UE_game\Binaries\Win64\ 下，需要向上找到 UE_game 目录
            # 然后拼接: UE_game\Torchlight\Saved\Logs\UE_game.log
            import os
            process_dir = os.path.dirname(process_path)

            # 从进程目录向上查找 UE_game 目录
            current_dir = process_dir
            ue_game_dir = None

            # 最多向上查找3层
            for _ in range(3):
                parent_dir = os.path.dirname(current_dir)
                if os.path.basename(parent_dir) == "UE_game":
                    ue_game_dir = parent_dir
                    break
                current_dir = parent_dir

            # 如果找到 UE_game 目录，构建日志路径
            if ue_game_dir:
                game_log_path = os.path.join(ue_game_dir, "Torchlight", "Saved", "Logs", "UE_game.log")
            else:
                # 如果没找到，使用默认路径
                logger.warning("未找到 UE_game 目录，使用默认日志路径")
                game_log_path = r"D:\TapTap\PC Games\172664\UE_game\Torchlight\Saved\Logs\UE_game.log"

            # 控制台输出路径信息（用于测试）
            print("=" * 60)
            print("游戏日志监控初始化")
            print("=" * 60)
            print(f"游戏进程路径: {process_path}")
            print(f"游戏进程目录: {process_dir}")
            if ue_game_dir:
                print(f"UE_game目录: {ue_game_dir}")
            print(f"游戏日志路径: {game_log_path}")
            print("=" * 60)

            logger.info(f"游戏进程路径: {process_path}")
            logger.info(f"游戏进程目录: {process_dir}")
            if ue_game_dir:
                logger.info(f"UE_game目录: {ue_game_dir}")
            logger.info(f"游戏日志路径: {game_log_path}")

            # 检查日志文件是否存在
            if os.path.exists(game_log_path):
                file_size = os.path.getsize(game_log_path)
                print(f"✓ 日志文件存在 (大小: {file_size} 字节)")
                logger.info(f"日志文件存在 (大小: {file_size} 字节)")
            else:
                print(f"✗ 警告: 日志文件不存在!")
                logger.warning(f"日志文件不存在: {game_log_path}")
            print("=" * 60)

            # 设置游戏日志路径
            self._game_log_watcher._parser.game_log_path = game_log_path

            # 启动监控
            self._game_log_watcher.start()

            print("✓ 游戏日志监控已启动")
            logger.info("游戏日志监控已启动")

        except Exception as e:
            print(f"✗ 初始化游戏日志监控失败: {e}")
            logger.error(f"初始化游戏日志监控失败: {e}", exc_info=True)

    def _schedule_watch(self) -> None:
        """安排窗口监视任务"""
        def tick():
            bound = self._binder.bound
            if bound:
                if not self._binder.is_bound_hwnd_valid():
                    self._overlay.close()
                    self._ui.close()
                    return
                if not self._watcher.is_alive(bound):
                    self._overlay.close()
                    self._ui.close()
                    return
            self._ui.schedule(self._watcher.interval_ms, tick)

        self._ui.schedule(self._watcher.interval_ms, tick)

    def on_detect_click(self) -> None:
        """处理识别点击事件

        流程：
        1. 验证绑定状态
        2. 执行识别流程
        3. 更新UI
        """
        bound = self._binder.bound
        if not bound:
            self._ui.show_info("未绑定游戏窗口，无法识别。")
            return

        # 发布识别开始事件
        self._event_bus.publish(Events.RECOGNITION_STARTED, hwnd=bound.hwnd)

        # 开始识别状态
        self._state_manager.start_recognition()

        # 获取窗口client区域大小
        client_x, client_y, client_width, client_height = get_client_rect_in_screen(bound.hwnd)

        # 执行识别流程
        result = self._recognition_flow.execute_recognition_flow(
            hwnd=bound.hwnd,
            client_width=client_width,
            client_height=client_height
        )

        if not result['success']:
            self._state_manager.complete_recognition(success=False, error=result['error'])
            self._event_bus.publish(Events.RECOGNITION_FAILED, error=result['error'])
            self._ui.show_info(result['error'])
            return

        balance_value = result['balance_value']
        item_results = result['item_results']

        # 更新UI余额
        self._ui.update_balance(balance_value)

        if balance_value == '--':
            self._debug_log("[识别流程] 余额识别失败")

        # 创建overlay显示区域边框
        if not self._overlay.is_visible():
            self._debug_log("[Overlay] 创建Overlay窗口")
            self._overlay.create_overlay(bound.hwnd)
        else:
            self._debug_log("[Overlay] Overlay窗口已存在")

        # 在overlay上显示物品识别结果
        # 获取物品区域（从识别流程服务返回或重新计算）
        balance_region, item_regions = self._region_calculator.calculate_for_resolution(
            client_width, client_height
        )

        self._debug_log(f"[Overlay] 物品区域数量: {len(item_regions)}, 识别结果数量: {len(item_results)}")

        # 添加物品结果到表格（如果UI支持）
        self._add_item_results_batch(item_results, item_regions)

        # 在overlay上显示物品识别结果
        self._display_item_results_on_overlay(item_results, item_regions)

        # 完成识别状态
        self._state_manager.complete_recognition(success=True)
        # 发布识别完成事件
        self._event_bus.publish(Events.RECOGNITION_COMPLETED, balance=balance_value, items_count=len(item_results))

    def on_update_price_click(self) -> None:
        """处理更新物价按钮点击事件"""
        if not self._price_service.can_update():
            last_update = self._price_service.get_last_update_time()
            if last_update:
                time_str = last_update.strftime("%Y-%m-%d %H:%M:%S")
                self._ui.show_info(f"距离上次更新不到1小时。\n上次更新时间：{time_str}")
            else:
                self._ui.show_info("距离上次更新不到1小时。")
            return

        # 发布价格更新开始事件
        self._event_bus.publish(Events.PRICE_UPDATE_STARTED)

        # 开始价格更新状态
        self._state_manager.start_price_update()

        # 禁用按钮，防止重复点击
        self._ui.btn_update_price.config(state="disabled", text="更新中...")

        # 在UI线程中异步执行更新
        def do_update():
            success, message = self._price_service.update_prices()

            # 完成价格更新状态
            self._state_manager.complete_price_update(success=success, message=message)

            # 发布价格更新完成事件
            if success:
                self._event_bus.publish(Events.PRICE_UPDATE_COMPLETED, message=message)
            else:
                self._event_bus.publish(Events.PRICE_UPDATE_FAILED, message=message)

            # 重新启用按钮
            self._ui.btn_update_price.config(state="normal", text="更新物价")

            # 重新加载价格数据到内存
            if success:
                self._reload_item_prices()
                # 从config.json重新加载上次更新时间
                self._ui._load_last_update_time()
                # 重新加载初火源质价格
                self._ui._load_source_price()

            # 显示结果
            self._ui.show_info(message)

        self._ui.schedule(0, do_update)

    def _reload_item_prices(self) -> None:
        """重新加载物品价格数据"""
        try:
            import importlib
            import services.item_price_service

            # 重新加载模块
            importlib.reload(services.item_price_service)

            # 创建新的服务实例
            from services.item_price_service import ItemPriceService
            new_service = ItemPriceService()

            # 更新控制器的价格服务引用
            self._item_price_service = new_service

            self._debug_log("物品价格数据已重新加载")
        except Exception as e:
            self._debug_log(f"重新加载物品价格失败: {e}")

    def _add_item_results_batch(self, item_results: list[dict], item_regions: list[Region]) -> None:
        """批量添加物品识别结果到表格

        Args:
            item_results: 文字块结果列表 [{'index', 'text', 'region_name'}, ...]
            item_regions: 物品区域列表
        """
        # 使用UI更新服务准备表格结果
        table_results = self._ui_update_service.prepare_table_results(
            item_results, item_regions
        )

        # 添加结果到UI
        for result in table_results:
            self._debug_log(
                f"[物品识别] 区域 {result['index']} ({result['region_name']}): "
                f"物品={result['item_name']}, 数量={result['item_quantity']}"
            )

            self._ui.add_item_result(
                result['index'],
                result['region_name'],
                result['item_name'],
                result['item_quantity'],
                result['item_price'],
                result['original_price'],
                result['converted_price'],
                result['profit_ratio']
            )

    def _display_item_results_on_overlay(self, item_results: list[dict], item_regions: list[Region]) -> None:
        """在overlay上显示物品识别结果

        Args:
            item_results: 物品识别结果列表
            item_regions: 物品区域列表
        """
        self._debug_log(f"[Overlay] 开始准备显示文本，物品结果数: {len(item_results)}, 区域数: {len(item_regions)}")

        # 使用UI更新服务准备overlay文本项
        text_items = self._ui_update_service.prepare_overlay_text_items(
            item_results, item_regions
        )

        self._debug_log(f"[Overlay] 准备了 {len(text_items)} 个文本项")

        # 在overlay上显示文本
        if text_items:
            self._debug_log(f"[Overlay] 调用 overlay.show_texts 显示文本")
            self._overlay.show_texts(text_items)
        else:
            self._debug_log("[Overlay] 没有文本项可显示")

    def update_config(self, ocr_config, watch_interval_ms: int, enable_tax_calculation: bool = False, mystery_gem_mode: str = "min") -> bool:
        """更新配置

        Args:
            ocr_config: 新的OCR配置
            watch_interval_ms: 新的监视间隔
            enable_tax_calculation: 是否开启税率计算
            mystery_gem_mode: 奥秘辉石处理模式

        Returns:
            是否更新成功
        """
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
                last_price_update=self._cfg.last_price_update,
                enable_tax_calculation=enable_tax_calculation,
                mystery_gem_mode=mystery_gem_mode,
            )

            # 保存配置文件
            if not self._cfg.save():
                raise Exception("保存配置文件失败")

            # 更新监控间隔
            self._watcher.interval_ms = watch_interval_ms

            # 重新创建OCR引擎（确保新配置生效，包括debug_mode）
            ocr_cfg = BaiduOcrConfig(
                api_key=ocr_config.api_key,
                secret_key=ocr_config.secret_key,
                api_name=ocr_config.api_name,
                timeout_sec=ocr_config.timeout_sec,
                max_retries=ocr_config.max_retries,
                debug_mode=ocr_config.debug_mode,
            )
            self._ocr = BaiduOcrEngine(ocr_cfg)

            # 更新状态管理器中的配置
            self._state_manager.update_config({
                'watch_interval_ms': watch_interval_ms,
                'debug_mode': ocr_config.debug_mode,
                'mystery_gem_mode': mystery_gem_mode,
                'enable_tax_calculation': enable_tax_calculation,
            })

            # 更新UI更新服务的配置
            self._ui_update_service.set_config(self._cfg)

            return True
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False

    def get_config(self) -> AppConfig:
        """获取当前配置

        Returns:
            当前配置对象
        """
        return self._cfg

    def add_exchange_log(self, item_name: str, quantity: str, original_price: float,
                         converted_price: float, profit: float, status: str = "完成"):
        """添加兑换记录到日志

        Args:
            item_name: 物品名称
            quantity: 数量
            original_price: 原价
            converted_price: 转换价
            profit: 盈亏
            status: 状态
        """
        try:
            import json
            import os

            log_data = {
                'item_name': item_name,
                'quantity': quantity,
                'original_price': original_price,
                'converted_price': converted_price,
                'profit': profit,
                'status': status
            }

            log_file = os.path.join(os.path.dirname(__file__), '..', 'exchange_log.json')

            # 加载现有日志
            logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)

            # 添加新日志
            logs.append(log_data)

            # 保存到文件
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

            logger.info(f"添加兑换记录: {item_name} x{quantity}, 盈亏={profit:.4f}")
        except Exception as e:
            logger.error(f"添加兑换记录失败: {e}")
