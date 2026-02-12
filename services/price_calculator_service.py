"""价格计算服务 - 消除重复代码"""
from dataclasses import dataclass
from typing import Optional
from core.exceptions import PriceError


@dataclass
class PriceCalculationResult:
    """价格计算结果"""
    item_name: str
    item_quantity: str
    item_price: str
    original_price: Optional[float] = None
    converted_price: Optional[float] = None
    profit_value: Optional[float] = None
    profit_symbol: Optional[str] = None


class PriceCalculatorService:
    """价格计算服务 - 统一的价格计算逻辑"""

    def __init__(self, item_price_service, gem_price_key="神威辉石"):
        """初始化价格计算服务

        Args:
            item_price_service: 物品价格服务
            gem_price_key: 神威辉石的名称
        """
        self._item_price_service = item_price_service
        self._gem_price_key = gem_price_key

    def calculate_item_price(
        self,
        item_name: str,
        item_quantity: str,
        item_price: str,
        mystery_gem_mode: str = "min"
    ) -> PriceCalculationResult:
        """计算物品价格（统一逻辑）

        Args:
            item_name: 物品名称
            item_quantity: 数量
            item_price: 价格（游戏内显示的价格）
            mystery_gem_mode: 奥秘辉石模式（min/max/random）

        Returns:
            价格计算结果

        Raises:
            PriceError: 价格计算失败时
        """
        # 验证输入
        if item_name == "--" or item_name == "已售罄":
            return PriceCalculationResult(
                item_name=item_name,
                item_quantity=item_quantity,
                item_price=item_price
            )

        try:
            quantity_int = int(item_quantity)
        except ValueError as e:
            raise PriceError(f"数量格式错误: {item_quantity}") from e

        # 获取神威辉石单价
        gem_price = self._item_price_service.get_price_by_name(self._gem_price_key)
        if gem_price is None or gem_price <= 0:
            raise PriceError(f"神威辉石价格无效: {gem_price}")

        # 特殊处理奥秘辉石
        if "奥秘辉石" in item_name:
            return self._calculate_mystery_gem_price(
                item_name=item_name,
                quantity_int=quantity_int,
                gem_price=gem_price,
                mystery_gem_mode=mystery_gem_mode,
                item_price=item_price
            )
        else:
            return self._calculate_normal_item_price(
                item_name=item_name,
                quantity_int=quantity_int,
                gem_price=gem_price,
                item_price=item_price
            )

    def _calculate_mystery_gem_price(
        self,
        item_name: str,
        quantity_int: int,
        gem_price: float,
        mystery_gem_mode: str,
        item_price: str
    ) -> PriceCalculationResult:
        """计算奥秘辉石价格

        Args:
            item_name: 物品名称
            quantity_int: 数量
            gem_price: 神威辉石单价
            mystery_gem_mode: 奥秘辉石模式
            item_price: 游戏内价格

        Returns:
            价格计算结果
        """
        import random

        # 判断是小奥秘还是大奥秘
        if "小" in item_name:
            if mystery_gem_mode == "min":
                gem_count = 50
            elif mystery_gem_mode == "max":
                gem_count = 100
            else:  # random
                gem_count = random.randint(50, 100)
        else:
            if mystery_gem_mode == "min":
                gem_count = 100
            elif mystery_gem_mode == "max":
                gem_count = 900
            else:  # random
                gem_count = random.randint(100, 900)

        # 计算原始价格（神威辉石数量 × 数量 × 神威辉石单价）
        original_price_value = gem_count * quantity_int * gem_price

        # 计算转换价格
        converted_price_value = None
        profit_value = None
        profit_symbol = None

        if item_price != "--":
            try:
                price_int = int(item_price)
                if price_int > 0:
                    converted_price_value = price_int * gem_price
                    profit_value = original_price_value - converted_price_value

                    # 计算盈亏符号
                    if profit_value > 0:
                        profit_symbol = "↑"
                    elif profit_value < 0:
                        profit_symbol = "↓"
                    else:
                        profit_symbol = "→"
            except ValueError as e:
                raise PriceError(f"价格格式错误: {item_price}") from e

        # 计算获取到的价格（总神威辉石数量）
        gem_total = gem_count * quantity_int

        return PriceCalculationResult(
            item_name=item_name,
            item_quantity=item_quantity,
            item_price=item_price,
            original_price=original_price_value,
            converted_price=converted_price_value,
            profit_value=profit_value,
            profit_symbol=profit_symbol
        )

    def _calculate_normal_item_price(
        self,
        item_name: str,
        quantity_int: int,
        gem_price: float,
        item_price: str
    ) -> PriceCalculationResult:
        """计算普通物品价格

        Args:
            item_name: 物品名称
            quantity_int: 数量
            gem_price: 神威辉石单价
            item_price: 游戏内价格

        Returns:
            价格计算结果
        """
        # 获取物品单价
        unit_price = self._item_price_service.get_price_by_name(item_name)
        if unit_price is None:
            raise PriceError(f"物品价格未找到: {item_name}")

        # 计算原始价格（单价 × 数量）
        original_price_value = quantity_int * unit_price

        # 计算转换价格
        converted_price_value = None
        profit_value = None
        profit_symbol = None

        if item_price != "--":
            try:
                price_int = int(item_price)
                if price_int > 0:
                    converted_price_value = price_int * gem_price
                    profit_value = original_price_value - converted_price_value

                    # 计算盈亏符号
                    if profit_value > 0:
                        profit_symbol = "↑"
                    elif profit_value < 0:
                        profit_symbol = "↓"
                    else:
                        profit_symbol = "→"
            except ValueError as e:
                raise PriceError(f"价格格式错误: {item_price}") from e

        return PriceCalculationResult(
            item_name=item_name,
            item_quantity=item_quantity,
            item_price=item_price,
            original_price=original_price_value,
            converted_price=converted_price_value,
            profit_value=profit_value,
            profit_symbol=profit_symbol
        )
