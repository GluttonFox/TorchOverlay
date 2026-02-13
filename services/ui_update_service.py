"""UI更新服务 - 统一处理UI更新逻辑"""
from typing import List, Dict, Optional
from core.logger import get_logger
from domain.models import Region
from services.exchange_verification_service import ExchangeVerificationService

logger = get_logger(__name__)


class UIUpdateService:
    """UI更新服务 - 封装UI更新逻辑"""

    def __init__(self, text_parser, price_calculator, item_price_service, controller=None,
                 verification_service: Optional[ExchangeVerificationService] = None):
        """初始化UI更新服务

        Args:
            text_parser: 文本解析服务
            price_calculator: 价格计算服务
            item_price_service: 物品价格服务
            controller: 控制器（可选，用于记录兑换日志）
            verification_service: 兑换验证服务（可选，用于交叉验证）
        """
        self._text_parser = text_parser
        self._price_calculator = price_calculator
        self._item_price_service = item_price_service
        self._controller = controller
        self._verification_service = verification_service
        self._cfg = None

    def set_config(self, cfg):
        """设置配置

        Args:
            cfg: 应用配置
        """
        self._cfg = cfg

    def set_verification_service(self, verification_service: ExchangeVerificationService) -> None:
        """设置验证服务

        Args:
            verification_service: 兑换验证服务
        """
        self._verification_service = verification_service
        logger.info("验证服务已设置")

    def prepare_overlay_text_items(
        self,
        item_results: List[Dict],
        item_regions: List[Region]
    ) -> List:
        """准备要显示在overlay上的文本项

        Args:
            item_results: 物品识别结果列表
            item_regions: 物品区域列表

        Returns:
            文本项列表
        """
        # 导入OverlayTextItem
        from services.overlay.overlay_service import OverlayTextItem

        # 按区域索引分组文字块
        grouped = {}
        for result in item_results:
            idx = result['index']
            if idx not in grouped:
                grouped[idx] = []
            grouped[idx].append(result['text'])

        # 准备文本项
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

            logger.info(f"[Overlay准备] 区域{idx} ({region.name}): 名称={item_name}, 数量={item_quantity}, 价格={item_price}")

            # 准备显示文本
            display_text, color = self._prepare_display_text(
                item_name, item_quantity, item_price, self._cfg.enable_tax_calculation
            )

            if not display_text:
                logger.warning(f"[Overlay准备] 区域{idx} ({region.name}) 未生成显示文本")

            # 创建文本项
            if display_text:
                bbox = region.get_bounding_box()
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

        return text_items

    def prepare_table_results(
        self,
        item_results: List[Dict],
        item_regions: List[Region]
    ) -> List[Dict]:
        """准备要添加到表格的结果

        Args:
            item_results: 物品识别结果列表
            item_regions: 物品区域列表

        Returns:
            表格结果列表
        """
        # 按区域索引分组文字块
        grouped = {}
        for result in item_results:
            idx = result['index']
            if idx not in grouped:
                grouped[idx] = []
            grouped[idx].append(result['text'])

        # 为每个区域生成结果
        table_results = []

        for idx, region in enumerate(item_regions):
            if idx in grouped:
                combined_text = ' '.join(grouped[idx])
            else:
                combined_text = "--"

            # 解析物品信息
            item_name, item_quantity, item_price = self._text_parser.parse_item_info(combined_text)

            # 计算价格
            original_price = "--"
            converted_price = "--"
            profit_ratio = "--"

            try:
                result = self._price_calculator.calculate_item_price(
                    item_name=item_name,
                    item_quantity=item_quantity,
                    item_price=item_price,
                    mystery_gem_mode=self._cfg.mystery_gem_mode,
                    enable_tax_calculation=self._cfg.enable_tax_calculation
                )
                if result.original_price is not None:
                    original_price = f"{result.original_price:.2f}"
                if result.converted_price is not None:
                    # 根据是否开启税率计算显示对应的价格
                    display_price = result.taxed_converted_price if self._cfg.enable_tax_calculation else result.converted_price
                    converted_price = f"{display_price:.2f}"
                if result.profit_value is not None:
                    profit_ratio = f"{result.profit_value:.2f}"
            except Exception as e:
                # logger.debug(f"价格计算失败: {e}")

            table_results.append({
                'index': idx + 1,
                'region_name': region.name,
                'item_name': item_name,
                'item_quantity': item_quantity,
                'item_price': item_price,
                'original_price': original_price,
                'converted_price': converted_price,
                'profit_ratio': profit_ratio
            })

        return table_results

    def _prepare_display_text(self, item_name, item_quantity, item_price, enable_tax_calculation=False):
        """准备显示文本

        Args:
            item_name: 物品名称
            item_quantity: 数量
            item_price: 价格
            enable_tax_calculation: 是否开启税率计算

        Returns:
            (显示文本, 颜色)
        """
        display_text = ""
        color = "#00FF00"  # 默认绿色

        if item_name != "--" and item_name != "已售罄":
            try:
                result = self._price_calculator.calculate_item_price(
                    item_name=item_name,
                    item_quantity=item_quantity,
                    item_price=item_price,
                    mystery_gem_mode=self._cfg.mystery_gem_mode,
                    enable_tax_calculation=self._cfg.enable_tax_calculation
                )

                # 如果价格计算失败（original_price为None），至少显示物品信息
                if result.original_price is None:
                    # 无法计算价格，显示基本信息
                    if item_price != "--":
                        display_text = f"{item_name}\n{item_quantity} x {item_price}火"
                    else:
                        display_text = f"{item_name}\n数量: {item_quantity}"
                    color = "#FFFFFF"  # 白色（未知）
                    logger.info(f"价格计算失败（原价为None）: {item_name}, 数量={item_quantity}, 价格={item_price}")
                elif result.converted_price is None:
                    # 无法计算转换价格，显示原始价格
                    display_text = f"{item_name}\n{item_quantity} x {item_price}火\n原价: {result.original_price:.4f}火"
                    color = "#FFFF00"  # 黄色（警告）
                    logger.info(f"价格计算失败（转换价为None）: {item_name}, 数量={item_quantity}, 价格={item_price}")
                else:
                    # 完整的价格信息
                    # 获取单价（用于显示）
                    if "奥秘辉石" in item_name:
                        # 奥秘辉石：显示总神威辉石数量
                        import random
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
                        quantity_int = int(item_quantity)
                        unit_price_display = gem_count * quantity_int
                    else:
                        # 普通物品：显示物品单价
                        unit_price = self._item_price_service.get_price_by_name(item_name)
                        unit_price_display = unit_price if unit_price else 0

                    if result.profit_value is not None:
                        profit_value = result.profit_value
                        # 决定显示的价格：如果开启税率计算，显示税后价格；否则显示原始转换价
                        display_price = result.taxed_converted_price if enable_tax_calculation else result.converted_price

                        # 添加OCR识别结果到验证服务（如果可用）
                        if self._verification_service:
                            try:
                                self._verification_service.add_ocr_result(
                                    item_name=item_name,
                                    item_quantity=item_quantity,
                                    original_price=result.original_price,
                                    converted_price=display_price,
                                    profit=profit_value,
                                    gem_cost=item_price
                                )
                                # logger.debug(f"添加OCR识别结果到验证服务: {item_name}")
                            except Exception as e:
                                logger.error(f"添加OCR识别结果到验证服务失败: {e}")

                        # 兼容旧版本：添加兑换记录（仅在控制器可用且没有验证服务时）
                        elif self._controller:
                            try:
                                self._controller.add_exchange_log(
                                    item_name=item_name,
                                    quantity=item_quantity,
                                    original_price=result.original_price,
                                    converted_price=display_price,
                                    profit=profit_value,
                                    status="完成"
                                )
                            except Exception as e:
                                logger.error(f"添加兑换记录失败: {e}")

                        if profit_value > 0:
                            display_text = f"{item_name}\n{item_quantity}X{unit_price_display:.4f}={result.original_price:.4f}({display_price:.4f})\n盈利：{profit_value:.4f}火"
                            color = "#00FF00"  # 绿色（盈利）
                        elif profit_value < 0:
                            display_text = f"{item_name}\n{item_quantity}X{unit_price_display:.4f}={result.original_price:.4f}({display_price:.4f})\n亏损：{abs(profit_value):.4f}火"
                            color = "#FF0000"  # 红色（亏损）
                        else:
                            display_text = f"{item_name}\n{item_quantity}X{unit_price_display:.4f}={result.original_price:.4f}({display_price:.4f})\n持平"
                            color = "#FFFF00"  # 黄色（平衡）
            except Exception as e:
                # 计算失败，至少显示基本信息
                logger.error(f"价格计算异常: {e}, item={item_name}, quantity={item_quantity}, price={item_price}", exc_info=True)
                if item_price != "--":
                    display_text = f"{item_name}\n{item_quantity} x {item_price}火"
                else:
                    display_text = f"{item_name}\n数量: {item_quantity}"
                color = "#FFFFFF"  # 白色（错误）

        return display_text, color
