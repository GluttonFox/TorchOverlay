"""应用控制器 - 重构版，使用接口抽象和领域服务"""
from typing import Any

from core.config import AppConfig
from core.paths import ProjectPaths
from core.logger import get_logger
from services.interfaces import (
    IGameBinder,
    IProcessWatcher,
    ICaptureService,
    IOcrService,
    IOverlayService,
)
from services.overlay.target_window import get_client_rect_in_screen
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
        price_update_service,
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
            price_update_service: 物价更新服务
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
        self._price_update_service = price_update_service
        self._ui = None

    def attach_ui(self, ui):
        """附加UI到控制器

        Args:
            ui: UI实例
        """
        self._ui = ui

    def _debug_log(self, *args, **kwargs) -> None:
        """调试日志（仅在debug模式下输出）

        Args:
            *args: 打印参数
            **kwargs: 打印关键字参数
        """
        if self._cfg.ocr.debug_mode:
            logger.debug(*args, **kwargs)

    def on_window_shown(self):
        """窗口显示后的初始化"""
        self._ensure_bound_or_exit()
        self._schedule_watch()

    def _ensure_bound_or_exit(self):
        """确保绑定游戏或退出"""
        while True:
            if self._binder.try_bind():
                self._ui.set_bind_state(self._binder.bound)
                return

            retry = self._ui.ask_bind_retry_or_exit()
            if not retry:
                self._overlay.close()
                self._ui.close()
                return

    def _schedule_watch(self):
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

    def on_detect_click(self):
        """处理识别点击事件

        流程：
        1. 验证绑定状态
        2. 计算识别区域
        3. 截取合并区域
        4. OCR识别
        5. 解析结果
        6. 更新UI
        """
        bound = self._binder.bound
        if not bound:
            self._ui.show_info("未绑定游戏窗口，无法识别。")
            return

        # 获取窗口client区域大小
        client_x, client_y, client_width, client_height = get_client_rect_in_screen(bound.hwnd)

        # 根据分辨率自适应计算识别区域（使用领域服务）
        balance_region, item_regions = self._region_calculator.calculate_for_resolution(
            client_width, client_height
        )

        # 计算包含所有区域的合并区域（使用领域服务）
        combined_region = self._region_calculator.calculate_combined_region(
            balance_region, *item_regions
        )

        self._debug_log(f"\n[OCR优化] 合并区域: x={combined_region.x}, y={combined_region.y}, "
                        f"width={combined_region.width}, height={combined_region.height}")
        self._debug_log(f"[OCR优化] 窗口分辨率: {client_width}x{client_height}")
        self._debug_log(f"[OCR优化] 包含区域: 余额区域({balance_region.name}) + {len(item_regions)}个物品区域")

        # 截取合并区域（1次截图）
        combined_out_path = ProjectPaths.get_capture_path("last_combined.png")
        cap = self._capture.capture_region(
            bound.hwnd,
            combined_out_path,
            combined_region.get_bounding_box(),
            timeout_sec=2.5,
            preprocess=False
        )

        if not cap.ok or not cap.path:
            self._ui.show_info("截图失败，无法识别。")
            return

        self._debug_log(f"[OCR优化] 截图已保存到: {combined_out_path}")

        # OCR识别（1次调用）
        r = self._ocr.recognize(cap.path)
        if not r.ok:
            self._ui.show_info(f"OCR识别失败: {r.error}")
            return

        self._debug_log(f"[OCR优化] 原始识别文本: {repr(r.text)}")
        if r.words:
            self._debug_log(f"[OCR优化] 识别到 {len(r.words)} 个文字块")

        # 根据位置信息分配结果
        balance_value = "--"
        item_results = []

        if r.words:
            # 遍历所有识别到的文字块
            for word in r.words:
                # 计算文字块在合并区域中的绝对位置
                word_x = word.x + combined_region.x
                word_y = word.y + combined_region.y

                # 检查是否在余额区域内
                if balance_region.contains_center(word_x, word_y, word.width, word.height):
                    balance_text = word.text
                    balance_value = self._text_parser.extract_balance(balance_text)

                    self._debug_log(f"[OCR优化] 文字块归属余额: {repr(balance_text)} -> 余额: {balance_value}")
                else:
                    # 检查是否在某个物品区域内
                    for item_idx, item_region in enumerate(item_regions):
                        if item_region.contains_center(word_x, word_y, word.width, word.height):
                            # 收集该物品区域的所有文字块
                            item_results.append({
                                'index': item_idx,
                                'text': word.text,
                                'region_name': item_region.name
                            })

                            self._debug_log(f"[OCR优化] 文字块归属物品区域{item_idx + 1}({item_region.name}): {repr(word.text)}")
                            break

        # 更新UI余额
        self._ui.update_balance(balance_value)

        if balance_value == "--":
            self._debug_log(f"\n[OCR优化] 余额识别失败")

        # 创建overlay显示区域边框
        if not self._overlay.is_visible():
            self._overlay.create_overlay(bound.hwnd)

        # 在overlay上显示物品识别结果
        self._display_item_results_on_overlay(item_results, item_regions)

    def on_update_price_click(self):
        """处理更新物价按钮点击事件"""
        if not self._price_update_service.can_update():
            last_update = self._price_update_service.get_last_update_time()
            if last_update:
                time_str = last_update.strftime("%Y-%m-%d %H:%M:%S")
                self._ui.show_info(f"距离上次更新不到1小时。\n上次更新时间：{time_str}")
            else:
                self._ui.show_info("距离上次更新不到1小时。")
            return

        # 禁用按钮，防止重复点击
        self._ui.btn_update_price.config(state="disabled", text="更新中...")

        # 在UI线程中异步执行更新
        def do_update():
            success, message = self._price_update_service.update_prices()

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

    def _reload_item_prices(self):
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

    def _add_item_results_batch(self, item_results: list[dict], item_regions: list[Region]):
        """批量添加物品识别结果到表格

        Args:
            item_results: 文字块结果列表 [{'index', 'text', 'region_name'}, ...]
            item_regions: 物品区域列表
        """
        # 按区域索引分组文字块
        grouped = {}
        for result in item_results:
            idx = result['index']
            if idx not in grouped:
                grouped[idx] = []
            grouped[idx].append(result['text'])

        # 为每个区域生成结果
        for idx, region in enumerate(item_regions):
            if idx in grouped:
                # 合并该区域的所有文字块
                combined_text = ' '.join(grouped[idx])
            else:
                combined_text = "--"

            self._debug_log(f"[物品识别] 区域 {idx + 1} ({region.name}): 合并文本 = {repr(combined_text)}")

            # 解析物品信息（使用领域服务）
            item_name, item_quantity, item_price = self._text_parser.parse_item_info(combined_text)

            # 计算价格相关信息
            original_price = "--"
            converted_price = "--"
            profit_ratio = "--"

            if item_name != "--" and item_name != "已售罄":
                # 获取神威辉石单价
                gem_price = self._item_price_service.get_price_by_name("神威辉石")

                # 特殊处理奥秘辉石
                if "奥秘辉石" in item_name:
                    self._debug_log(f"[奥秘辉石] 检测到奥秘辉石: {item_name}, 当前模式: {self._cfg.mystery_gem_mode}")
                    try:
                        quantity_int = int(item_quantity)

                        if gem_price is not None and gem_price > 0:
                            import random

                            # 判断是小奥秘还是大奥秘
                            if "小" in item_name:
                                # 小奥秘辉石：50-100神威辉石
                                if self._cfg.mystery_gem_mode == "min":
                                    gem_count = 50
                                elif self._cfg.mystery_gem_mode == "max":
                                    gem_count = 100
                                else:  # random
                                    gem_count = random.randint(50, 100)
                            else:
                                # 大奥秘辉石：100-900神威辉石
                                if self._cfg.mystery_gem_mode == "min":
                                    gem_count = 100
                                elif self._cfg.mystery_gem_mode == "max":
                                    gem_count = 900
                                else:  # random
                                    gem_count = random.randint(100, 900)

                            self._debug_log(f"[奥秘辉石] 计算方式: gem_count={gem_count}, quantity={quantity_int}, gem_price={gem_price}")

                            # 计算原始价格（神威辉石数量 × 数量 × 神威辉石单价）
                            original_price_value = gem_count * quantity_int * gem_price
                            original_price = f"{original_price_value:.2f}"
                            self._debug_log(f"[奥秘辉石] 原始价格: {original_price}")

                            # 计算转换价格（物品价格 × 神威辉石单价）
                            if item_price != "--":
                                try:
                                    price_int = int(item_price)
                                    if price_int > 0:
                                        converted_price_value = price_int * gem_price
                                        converted_price = f"{converted_price_value:.2f}"
                                        self._debug_log(f"[奥秘辉石] 转换价格: {converted_price}")

                                        # 计算盈亏量（原始价格 - 转换价格）
                                        profit_ratio_value = original_price_value - converted_price_value
                                        profit_ratio = f"{profit_ratio_value:.2f}"
                                        self._debug_log(f"[奥秘辉石] 盈亏量: {profit_ratio}")
                                except ValueError:
                                    pass
                    except ValueError:
                        pass
                else:
                    # 获取物品单价
                    unit_price = self._item_price_service.get_price_by_name(item_name)
                    if unit_price is not None:
                        # 计算原始价格（单价 × 数量）
                        try:
                            quantity_int = int(item_quantity)
                            original_price_value = quantity_int * unit_price
                            original_price = f"{original_price_value:.2f}"

                            # 计算转换价格（物品价格 × 神威辉石单价）
                            if gem_price is not None and gem_price > 0:
                                if item_price != "--":
                                    try:
                                        price_int = int(item_price)
                                        if price_int > 0:
                                            converted_price_value = price_int * gem_price
                                            converted_price = f"{converted_price_value:.2f}"

                                            # 计算盈亏量（原始价格 - 转换价格）
                                            profit_ratio_value = original_price_value - converted_price_value
                                            profit_ratio = f"{profit_ratio_value:.2f}"
                                    except ValueError:
                                        pass
                        except ValueError:
                            pass

            self._ui.add_item_result(
                idx + 1, region.name, item_name, item_quantity, item_price,
                original_price, converted_price, profit_ratio
            )

    def _display_item_results_on_overlay(self, item_results: list[dict], item_regions: list[Region]):
        """在overlay上显示物品识别结果

        Args:
            item_results: 物品识别结果列表
            item_regions: 物品区域列表
        """
        # 按区域索引分组文字块
        grouped = {}
        for result in item_results:
            idx = result['index']
            if idx not in grouped:
                grouped[idx] = []
            grouped[idx].append(result['text'])

        # 准备要在overlay上显示的文本项
        from services.overlay.overlay_service import OverlayTextItem
        text_items = []

        # 为每个区域生成显示文本
        for idx, region in enumerate(item_regions):
            if idx in grouped:
                # 合并该区域的所有文字块
                combined_text = ' '.join(grouped[idx])
            else:
                combined_text = "--"

            # 解析物品信息
            item_name, item_quantity, item_price = self._text_parser.parse_item_info(combined_text)

            display_text = ""
            color = "#00FF00"  # 默认绿色

            if item_name != "--" and item_name != "已售罄":
                # 计算价格信息（简化的显示文本）
                gem_price = self._item_price_service.get_price_by_name("神威辉石")

                # 特殊处理奥秘辉石
                if "奥秘辉石" in item_name:
                    try:
                        quantity_int = int(item_quantity)

                        if gem_price is not None and gem_price > 0:
                            import random

                            # 判断是小奥秘还是大奥秘
                            if "小" in item_name:
                                if self._cfg.mystery_gem_mode == "min":
                                    gem_count = 50
                                elif self._cfg.mystery_gem_mode == "max":
                                    gem_count = 100
                                else:
                                    gem_count = random.randint(50, 100)
                            else:
                                if self._cfg.mystery_gem_mode == "min":
                                    gem_count = 100
                                elif self._cfg.mystery_gem_mode == "max":
                                    gem_count = 900
                                else:
                                    gem_count = random.randint(100, 900)

                            # 计算盈亏量
                            original_price_value = gem_count * quantity_int * gem_price
                            # 奥秘辉石的获取到的价格就是总神威辉石数量
                            gem_total = gem_count * quantity_int
                            if item_price != "--":
                                try:
                                    price_int = int(item_price)
                                    if price_int > 0:
                                        converted_price_value = price_int * gem_price
                                        total_price = quantity_int * price_int
                                        profit_value = original_price_value - converted_price_value
                                        if profit_value > 0:
                                            display_text = f"{item_name}\n{item_quantity}X{gem_total:.4f}={original_price_value:.4f}({converted_price_value:.4f})\n盈利：{profit_value:.4f}火"
                                            color = "#00FF00"  # 绿色（盈利）
                                        elif profit_value < 0:
                                            display_text = f"{item_name}\n{item_quantity}X{gem_total:.4f}={original_price_value:.4f}({converted_price_value:.4f})\n亏损：{abs(profit_value):.4f}火"
                                            color = "#FF0000"  # 红色（亏损）
                                        else:
                                            display_text = f"{item_name}\n{item_quantity}X{gem_total:.4f}={original_price_value:.4f}({converted_price_value:.4f})\n持平"
                                            color = "#FFFF00"  # 黄色（平衡）
                                except ValueError:
                                    pass
                    except ValueError:
                        pass
                else:
                    # 普通物品
                    unit_price = self._item_price_service.get_price_by_name(item_name)
                    if unit_price is not None:
                        try:
                            quantity_int = int(item_quantity)
                            original_price_value = quantity_int * unit_price
                            if gem_price is not None and gem_price > 0:
                                if item_price != "--":
                                    try:
                                        price_int = int(item_price)
                                        if price_int > 0:
                                            converted_price_value = price_int * gem_price
                                            total_price = quantity_int * price_int
                                            profit_value = original_price_value - converted_price_value
                                            if profit_value > 0:
                                                display_text = f"{item_name}\n{item_quantity}X{unit_price:.4f}={original_price_value:.4f}({converted_price_value:.4f})\n盈利：{profit_value:.4f}火"
                                                color = "#00FF00"  # 绿色（盈利）
                                            elif profit_value < 0:
                                                display_text = f"{item_name}\n{item_quantity}X{unit_price:.4f}={original_price_value:.4f}({converted_price_value:.4f})\n亏损：{abs(profit_value):.4f}火"
                                                color = "#FF0000"  # 红色（亏损）
                                            else:
                                                display_text = f"{item_name}\n{item_quantity}X{unit_price:.4f}={original_price_value:.4f}({converted_price_value:.4f})\n持平"
                                                color = "#FFFF00"  # 黄色（平衡）
                                    except ValueError:
                                        pass
                        except ValueError:
                            pass

            # 创建文本项
            if display_text:
                # 获取区域的坐标
                bbox = region.get_bounding_box()

                # 创建文本项（显示在识别区域内）
                text_item = OverlayTextItem(
                    text=display_text,
                    x=bbox['x'],
                    y=bbox['y'],
                    width=bbox['width'],
                    height=bbox['height'],
                    color=color,
                    font_size=12,
                    background=""
                )
                text_items.append(text_item)

        # 在overlay上显示文本
        if text_items:
            self._overlay.show_texts(text_items)

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

            return True
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False

    def get_config(self):
        """获取当前配置

        Returns:
            当前配置对象
        """
        return self._cfg
