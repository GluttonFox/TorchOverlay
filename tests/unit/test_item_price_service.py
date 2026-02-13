"""物品价格服务测试"""
import pytest
import os
import json
import tempfile

from services.item_price_service import ItemPriceService


class TestItemPriceService:
    """物品价格服务测试类"""

    @pytest.fixture
    def temp_item_json(self, tmp_path):
        """创建临时item.json文件"""
        item_data = {
            "10001": {
                "Name": "神威辉石",
                "Price": 50.0
            },
            "10002": {
                "Name": "初火源质",
                "Price": 1.0
            },
            "10003": {
                "Name": "神秘物品",
                "Price": 100.0
            },
            "10004": {
                "Name": "null价格物品",
                "Price": None
            },
            "10005": {
                "Name": "字符串价格物品",
                "Price": "invalid"
            }
        }

        temp_file = tmp_path / "item.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(item_data, f, ensure_ascii=False, indent=2)

        return temp_file

    @pytest.fixture
    def service_with_temp_file(self, temp_item_json, monkeypatch):
        """使用临时文件创建服务"""
        # 修改工作目录到临时目录
        monkeypatch.chdir(temp_item_json.parent)
        return ItemPriceService()

    def test_get_price_by_name_found(self, service_with_temp_file):
        """测试获取存在的物品价格"""
        price = service_with_temp_file.get_price_by_name("神威辉石")
        assert price == 50.0

    def test_get_price_by_name_not_found(self, service_with_temp_file):
        """测试获取不存在的物品价格"""
        price = service_with_temp_file.get_price_by_name("不存在的物品")
        assert price is None

    def test_get_price_by_name_double_dash(self, service_with_temp_file):
        """测试获取--物品价格"""
        price = service_with_temp_file.get_price_by_name("--")
        assert price is None

    def test_get_price_by_name_second_item(self, service_with_temp_file):
        """测试获取第二个物品价格"""
        price = service_with_temp_file.get_price_by_name("初火源质")
        assert price == 1.0

    def test_get_price_by_name_third_item(self, service_with_temp_file):
        """测试获取第三个物品价格"""
        price = service_with_temp_file.get_price_by_name("神秘物品")
        assert price == 100.0

    def test_load_invalid_price_none(self, service_with_temp_file):
        """测试加载None价格物品"""
        price = service_with_temp_file.get_price_by_name("null价格物品")
        # None值应该被跳过，返回None
        assert price is None

    def test_load_invalid_price_string(self, service_with_temp_file):
        """测试加载无效字符串价格物品"""
        price = service_with_temp_file.get_price_by_name("字符串价格物品")
        # 无效价格应该被跳过，返回None
        assert price is None

    def test_initialization(self, service_with_temp_file):
        """测试服务初始化"""
        assert service_with_temp_file._item_prices is not None
        assert isinstance(service_with_temp_file._item_prices, dict)
        assert len(service_with_temp_file._item_prices) > 0

    def test_prices_loaded_correctly(self, service_with_temp_file):
        """测试价格是否正确加载"""
        prices = service_with_temp_file._item_prices
        assert "神威辉石" in prices
        assert prices["神威辉石"] == 50.0
        assert "初火源质" in prices
        assert prices["初火源质"] == 1.0
        assert "神秘物品" in prices
        assert prices["神秘物品"] == 100.0

    def test_empty_item_json(self, tmp_path, monkeypatch):
        """测试空的item.json文件"""
        # 创建空的item.json
        temp_file = tmp_path / "item.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump({}, f)

        monkeypatch.chdir(temp_path)
        service = ItemPriceService()

        # 应该创建空的价格字典
        assert len(service._item_prices) == 0

    def test_malformed_item_json(self, tmp_path, monkeypatch):
        """测试格式错误的item.json文件"""
        # 创建格式错误的item.json
        temp_file = tmp_path / "item.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write("{invalid json")

        monkeypatch.chdir(tmp_path)
        service = ItemPriceService()

        # 应该创建空的价格字典（不会抛出异常）
        assert isinstance(service._item_prices, dict)

    def test_item_without_name(self, tmp_path, monkeypatch):
        """测试没有Name字段的物品"""
        item_data = {
            "10001": {
                "Price": 50.0
            }
        }

        temp_file = tmp_path / "item.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(item_data, f, ensure_ascii=False, indent=2)

        monkeypatch.chdir(tmp_path)
        service = ItemPriceService()

        # 没有Name字段的物品应该被跳过
        assert len(service._item_prices) == 0

    def test_item_without_price(self, tmp_path, monkeypatch):
        """测试没有Price字段的物品"""
        item_data = {
            "10001": {
                "Name": "测试物品"
            }
        }

        temp_file = tmp_path / "item.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(item_data, f, ensure_ascii=False, indent=2)

        monkeypatch.chdir(tmp_path)
        service = ItemPriceService()

        # 没有Price字段的物品应该被跳过
        assert len(service._item_prices) == 0

    def test_float_price_conversion(self, tmp_path, monkeypatch):
        """测试浮点数价格转换"""
        item_data = {
            "10001": {
                "Name": "浮点价格物品",
                "Price": 99.99
            }
        }

        temp_file = tmp_path / "item.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(item_data, f, ensure_ascii=False, indent=2)

        monkeypatch.chdir(tmp_path)
        service = ItemPriceService()

        price = service.get_price_by_name("浮点价格物品")
        assert price == 99.99
