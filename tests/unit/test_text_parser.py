"""文本解析服务测试"""
import pytest

from domain.services.text_parser_service import TextParserService


class TestTextParserService:
    """文本解析服务测试类"""

    @pytest.fixture
    def parser(self):
        return TextParserService()

    def test_extract_balance_valid_number(self, parser):
        """测试提取有效余额"""
        text = "1,234,567"
        result = parser.extract_balance(text)
        assert result == "1,234,567"

    def test_extract_balance_with_multiple_numbers(self, parser):
        """测试提取多个数字时的最长匹配"""
        text = "余额：12345 其他：678"
        result = parser.extract_balance(text)
        assert result == "12,345"  # 取最长的数字串

    def test_extract_balance_invalid(self, parser):
        """测试无效文本"""
        text = "无法识别"
        result = parser.extract_balance(text)
        assert result == "--"

    def test_parse_item_info_standard(self, parser):
        """测试标准物品信息解析"""
        text = "物品名称X10 100"
        name, quantity, price = parser.parse_item_info(text)
        assert name == "物品名称"
        assert quantity == "10"
        assert price == "100"

    def test_parse_item_info_sold_out(self, parser):
        """测试已售罄物品"""
        text = "物品名称已售罄"
        name, quantity, price = parser.parse_item_info(text)
        assert name == "物品名称"
        assert quantity == "已售罄"
        assert price == "0"

    def test_parse_item_info_with_interference(self, parser):
        """测试带干扰文本的解析"""
        text = "TUFF 物品名称X10 100"
        name, quantity, price = parser.parse_item_info(text)
        assert name == "物品名称"
        assert quantity == "10"
        assert price == "100"

    def test_parse_item_info_various_x_symbols(self, parser):
        """测试各种X符号"""
        test_cases = [
            "物品名称×10 100",
            "物品名称x10 100",
            "物品名称Ⅹ10 100",
            "物品名称✕10 100",
        ]
        for text in test_cases:
            name, quantity, price = parser.parse_item_info(text)
            assert name == "物品名称"
            assert quantity == "10"
            assert price == "100"

    def test_parse_item_info_default_quantity(self, parser):
        """测试默认数量"""
        text = "物品名称 100"
        name, quantity, price = parser.parse_item_info(text)
        assert name == "物品名称"
        assert quantity == "1"  # 默认为1
        assert price == "100"

    def test_parse_item_info_invalid(self, parser):
        """测试无效文本"""
        text = "--"
        name, quantity, price = parser.parse_item_info(text)
        assert name == "--"
        assert quantity == "--"
        assert price == "--"
