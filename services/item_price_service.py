"""物品价格服务 - 负责从item.json中查询物品价格"""
import json
import os
from typing import Optional


class ItemPriceService:
    """物品价格查询服务"""

    def __init__(self):
        self._item_prices = {}  # {名称: 价格} 的映射
        self._load_item_prices()

    def _load_item_prices(self):
        """从item.json加载物品价格"""
        try:
            item_path = os.path.join(os.path.dirname(__file__), '..', 'item.json')
            with open(item_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 创建名称到价格的映射
                for item_id, item_info in data.items():
                    if 'Name' in item_info and 'Price' in item_info:
                        price = item_info['Price']
                        # 处理 None 或 null 值
                        if price is not None and price != 'null':
                            try:
                                self._item_prices[item_info['Name']] = float(price)
                            except (ValueError, TypeError):
                                # 价格格式错误，跳过
                                print(f"警告: 物品 {item_info['Name']} 的价格格式错误: {price}")
        except Exception as e:
            print(f"加载物品价格失败: {e}")

    def get_price_by_name(self, name: str) -> Optional[float]:
        """根据物品名称获取价格

        Args:
            name: 物品名称

        Returns:
            物品价格（辉石单价），如果未找到返回None
        """
        if name == "--":
            return None
        return self._item_prices.get(name)
