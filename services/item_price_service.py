"""物品价格服务 - 负责从item.json中查询物品价格"""
import json
import os
import re
import difflib
from typing import Optional, Tuple

from core.logger import get_logger

logger = get_logger(__name__)


class ItemPriceService:
    """物品价格查询服务"""

    def __init__(self) -> None:
        self._item_prices = {}  # {名称: 价格} 的映射
        self._item_names = []  # 物品名称列表（用于模糊匹配）
        self._load_item_prices()

    def _load_item_prices(self) -> None:
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
                                self._item_names.append(item_info['Name'])
                            except (ValueError, TypeError):
                                # 价格格式错误，跳过
                                logger.warning(f"物品 {item_info['Name']} 的价格格式错误: {price}")
        except Exception as e:
            logger.error(f"加载物品价格失败: {e}")

    def get_price_by_name(self, name: str) -> Optional[float]:
        """根据物品名称获取价格（使用智能模糊匹配）

        Args:
            name: 物品名称

        Returns:
            物品价格（辉石单价），如果未找到返回None
        """
        if name == "--":
            return None

        # 策略1: 精确匹配
        if name in self._item_prices:
            return self._item_prices[name]

        # 策略2: 提取中文名称部分（去除所有前缀、后缀的英文、数字、符号）
        chinese_name = self._extract_chinese_name(name)
        if chinese_name and chinese_name != name and chinese_name in self._item_prices:
            logger.info(f"物品名称匹配[中文提取]: '{name}' -> '{chinese_name}'")
            return self._item_prices[chinese_name]

        # 策略3: 模糊匹配（使用 difflib 计算相似度）
        matched_name = self._fuzzy_match_name(name)
        if matched_name:
            logger.info(f"物品名称匹配[模糊匹配]: '{name}' -> '{matched_name}' (相似度: {self._calculate_similarity(name, matched_name):.2%})")
            return self._item_prices[matched_name]

        # 策略4: 对中文名称进行模糊匹配
        if chinese_name:
            matched_name = self._fuzzy_match_name(chinese_name)
            if matched_name:
                logger.info(f"物品名称匹配[中文模糊]: '{name}' -> '{matched_name}' (相似度: {self._calculate_similarity(chinese_name, matched_name):.2%})")
                return self._item_prices[matched_name]

        logger.warning(f"物品价格未找到: {name}")
        return None

    def _extract_chinese_name(self, name: str) -> Optional[str]:
        """提取中文名称部分

        Args:
            name: 原始物品名称

        Returns:
            提取的中文名称，如果没有中文则返回None
        """
        # 提取所有中文字符、数字、括号等
        chinese_part = re.sub(r'[^\u4e00-\u9fa5（）\(\)0-9]', '', name)
        return chinese_part.strip() if chinese_part else None

    def _fuzzy_match_name(self, name: str, min_similarity: float = 0.6) -> Optional[str]:
        """使用模糊匹配查找相似的物品名称

        Args:
            name: 要匹配的物品名称
            min_similarity: 最小相似度阈值

        Returns:
            匹配到的物品名称，如果没有足够相似的则返回None
        """
        # 使用 difflib 获取最相似的匹配
        matches = difflib.get_close_matches(name, self._item_names, n=1, cutoff=min_similarity)
        if matches:
            return matches[0]
        return None

    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """计算两个名称的相似度

        Args:
            name1: 第一个名称
            name2: 第二个名称

        Returns:
            相似度（0-1之间）
        """
        return difflib.SequenceMatcher(None, name1, name2).ratio()
