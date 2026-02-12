"""价格计算服务测试"""
import pytest
from unittest.mock import Mock

from services.price_calculator_service import (
    PriceCalculatorService,
    PriceCalculationResult
)


class TestPriceCalculatorService:
    """价格计算服务测试类"""

    @pytest.fixture
    def item_price_service(self):
        """模拟物品价格服务"""
        mock_service = Mock()
        mock_service.get_price_by_name.return_value = 100.0
        return mock_service

    @pytest.fixture
    def calculator(self, item_price_service):
        """价格计算服务fixture"""
        return PriceCalculatorService(item_price_service)

    def test_calculate_normal_item(self, calculator):
        """测试普通物品价格计算"""
        result = calculator.calculate_item_price(
            item_name="测试物品",
            item_quantity="5",
            item_price="10",
            mystery_gem_mode="min"
        )

        assert result.item_name == "测试物品"
        assert result.item_quantity == "5"
        assert result.item_price == "10"
        assert result.original_price == 500.0  # 5 * 100
        assert result.converted_price == 1000.0  # 10 * 100
        assert result.profit_value == -500.0  # 500 - 1000
        assert result.profit_symbol == "↓"

    def test_calculate_mystery_gem_small(self, calculator):
        """测试小奥秘辉石价格计算（min模式）"""
        calculator._item_price_service.get_price_by_name.side_effect = lambda name: 50.0 if name == "神威辉石" else None

        result = calculator.calculate_item_price(
            item_name="小奥秘辉石",
            item_quantity="2",
            item_price="100",
            mystery_gem_mode="min"
        )

        assert result.item_name == "小奥秘辉石"
        assert result.item_quantity == "2"
        assert result.item_price == "100"
        # 小奥秘min模式：50神威辉石
        assert result.original_price == 20000.0  # 50 * 2 * 200 (gem_price)
        assert result.converted_price == 5000.0  # 100 * 50
        assert result.profit_value == 15000.0
        assert result.profit_symbol == "↑"

    def test_calculate_mystery_gem_large_max(self, calculator):
        """测试大奥秘辉石价格计算（max模式）"""
        calculator._item_price_service.get_price_by_name.side_effect = lambda name: 50.0 if name == "神威辉石" else None

        result = calculator.calculate_item_price(
            item_name="大奥秘辉石",
            item_quantity="1",
            item_price="500",
            mystery_gem_mode="max"
        )

        # 大奥秘max模式：900神威辉石
        assert result.original_price == 45000.0  # 900 * 1 * 50 (gem_price)
        assert result.converted_price == 25000.0  # 500 * 50
        assert result.profit_value == 20000.0
        assert result.profit_symbol == "↑"

    def test_calculate_profit_neutral(self, calculator):
        """测试持平情况"""
        result = calculator.calculate_item_price(
            item_name="测试物品",
            item_quantity="10",
            item_price="100",  # 与单价相同
            mystery_gem_mode="min"
        )

        assert result.original_price == 1000.0
        assert result.converted_price == 10000.0
        assert result.profit_value == -9000.0
        assert result.profit_symbol == "↓"

    def test_calculate_sold_out_item(self, calculator):
        """测试已售罄物品"""
        result = calculator.calculate_item_price(
            item_name="已售罄",
            item_quantity="已售罄",
            item_price="0",
            mystery_gem_mode="min"
        )

        assert result.item_name == "已售罄"
        assert result.item_quantity == "已售罄"
        assert result.original_price is None
        assert result.converted_price is None
        assert result.profit_value is None

    def test_calculate_invalid_quantity(self, calculator):
        """测试无效数量"""
        with pytest.raises(Exception):
            calculator.calculate_item_price(
                item_name="测试物品",
                item_quantity="abc",  # 无效数量
                item_price="100",
                mystery_gem_mode="min"
            )

    def test_calculate_item_not_found(self, item_price_service):
        """测试物品价格未找到"""
        item_price_service.get_price_by_name.return_value = None
        calculator = PriceCalculatorService(item_price_service)

        with pytest.raises(Exception):
            calculator.calculate_item_price(
                item_name="不存在的物品",
                item_quantity="1",
                item_price="100",
                mystery_gem_mode="min"
            )
