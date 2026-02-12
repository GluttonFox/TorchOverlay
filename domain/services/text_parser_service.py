"""文本解析领域服务 - 负责OCR文本的业务解析"""
import re
from typing import Tuple


class TextParserService:
    """文本解析服务 - 从 Controller 拆分出来"""

    # 预编译正则表达式
    _STUFF_PATTERN = re.compile(r'^(TUFF|STUFF)\s*', re.IGNORECASE)
    _QUANTITY_PATTERN = re.compile(r'[×XxⅩ✕✖☓✗]\s*(\d+)')  # 匹配各种X/乘号后面跟的数字
    _PRICE_PATTERN = re.compile(r'(\d+)\s*$')
    _NUMBERS_PATTERN = re.compile(r'\d+')

    def parse_item_info(self, text: str) -> Tuple[str, str, str]:
        """解析物品信息，返回 (名称, 数量, 价格)

        Args:
            text: 识别的文本

        Returns:
            (名称, 数量, 价格)
        """
        if text == "--":
            return "--", "--", "--"

        # 将换行符替换为空格，并压缩连续空格
        text = ' '.join(text.split())

        # 去掉开头的 TUFF 或 STUFF 标记（使用预编译正则）
        text = self._STUFF_PATTERN.sub('', text)

        # 检查是否已售罄
        if '已售罄' in text:
            # 提取物品名称（已售罄之前的部分）
            name = text.replace('已售罄', '').strip()
            return name, '已售罄', '0'

        # 查找 "X" 后面的数字作为数量（使用预编译正则）
        quantity_match = self._QUANTITY_PATTERN.search(text)
        if quantity_match:
            quantity = quantity_match.group(1)
            # 去掉数量部分，获取物品名称和价格
            remaining = self._QUANTITY_PATTERN.sub('', text).strip()
        else:
            # 没有显式数量，默认为1
            quantity = '1'
            remaining = text

        # 从剩余文本中提取最后一个数字作为价格（使用预编译正则）
        price_match = self._PRICE_PATTERN.search(remaining)
        if price_match:
            price = price_match.group(1)
            # 去掉价格，获取物品名称
            name = self._PRICE_PATTERN.sub('', remaining).strip()
        else:
            # 没有找到价格
            price = '--'
            name = remaining.strip()

        return name, quantity, price

    def extract_balance(self, text: str) -> str:
        """从识别的文本中提取余额数字

        Args:
            text: 识别的文本

        Returns:
            格式化后的余额（带千分位分隔符）
        """
        # 匹配连续的数字（使用预编译正则）
        numbers = self._NUMBERS_PATTERN.findall(text)
        if numbers:
            # 取最长的数字串（最可能是余额）
            balance = max(numbers, key=len)
            # 格式化余额（添加千分位分隔符）
            try:
                num = int(balance)
                return f"{num:,}"
            except ValueError:
                return balance
        return "--"
