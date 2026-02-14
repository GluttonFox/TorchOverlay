"""兑换验证服务 - 将OCR识别结果与游戏日志交叉验证"""
import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import threading

from core.logger import get_logger
from domain.models.buy_event import BuyEvent
from domain.models.refresh_event import RefreshEvent
from domain.models.exchange_record import OcrRecognitionRecord, ExchangeRecord
from services.item_price_service import ItemPriceService

logger = get_logger(__name__)


class ExchangeVerificationService:
    """兑换验证服务"""

    # OCR结果缓存过期时间（秒）
    DEFAULT_CACHE_EXPIRE_TIME = 60

    def __init__(self, ocr_log_path: str | None = None, cache_expire: int = 60):
        """初始化验证服务

        Args:
            ocr_log_path: OCR识别记录日志路径
            cache_expire: OCR结果缓存过期时间（秒）
        """
        self.ocr_log_path = ocr_log_path or self._get_default_ocr_log_path()
        self._cache_expire = cache_expire

        # OCR结果缓存 {id: OcrRecognitionRecord}
        self._ocr_cache: Dict[str, OcrRecognitionRecord] = {}

        # 购买事件缓存 {id: BuyEvent}
        self._buy_event_cache: Dict[str, BuyEvent] = {}

        # 刷新事件列表
        self._refresh_events: List[RefreshEvent] = []

        # 线程锁
        self._lock = threading.Lock()

        # 加载已有的OCR记录
        self._load_ocr_records()

    def _get_default_ocr_log_path(self) -> str:
        """获取默认的OCR日志路径"""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(base_dir, 'ocr_recognition_log.json')

    def _load_ocr_records(self) -> None:
        """加载已有的OCR识别记录"""
        if not os.path.exists(self.ocr_log_path):
            logger.info("OCR识别记录文件不存在，将创建新文件")
            return

        try:
            with open(self.ocr_log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for record_data in data:
                    record = OcrRecognitionRecord.from_dict(record_data)
                    # 只加载未过期且未验证的记录
                    if not record.verified and self._is_record_valid(record):
                        self._ocr_cache[record.timestamp.isoformat()] = record
            logger.info(f"加载了 {len(self._ocr_cache)} 条未验证的OCR记录")
        except Exception as e:
            logger.error(f"加载OCR记录失败: {e}", exc_info=True)

    def _save_ocr_records(self) -> None:
        """保存OCR识别记录"""
        try:
            # 加载所有记录
            all_records = []
            if os.path.exists(self.ocr_log_path):
                with open(self.ocr_log_path, 'r', encoding='utf-8') as f:
                    all_records = json.load(f)

            # 更新缓存中的记录
            cache_records = {record.timestamp.isoformat(): record.to_dict()
                           for record in self._ocr_cache.values()}

            # 合并记录（去重，以缓存为准）
            existing_timestamps = {r['timestamp'] for r in all_records}
            for timestamp, record_dict in cache_records.items():
                if timestamp in existing_timestamps:
                    # 更新已存在的记录
                    index = next(i for i, r in enumerate(all_records) if r['timestamp'] == timestamp)
                    all_records[index] = record_dict
                else:
                    # 添加新记录
                    all_records.append(record_dict)

            # 保存
            with open(self.ocr_log_path, 'w', encoding='utf-8') as f:
                json.dump(all_records, f, ensure_ascii=False, indent=2)

            # logger.debug(f"保存了 {len(all_records)} 条OCR记录")
        except Exception as e:
            logger.error(f"保存OCR记录失败: {e}", exc_info=True)

    def _is_record_valid(self, record: OcrRecognitionRecord) -> bool:
        """检查记录是否有效（未过期）

        Args:
            record: OCR识别记录

        Returns:
            True表示记录有效
        """
        now = datetime.now()
        if record.expire_time and now > record.expire_time:
            return False
        return True

    def _generate_event_id(self, event: BuyEvent | OcrRecognitionRecord) -> str:
        """生成事件唯一ID

        Args:
            event: 事件对象

        Returns:
            事件ID字符串
        """
        if isinstance(event, BuyEvent):
            return f"buy_{event.timestamp.isoformat()}_{event.item_id}_{event.gem_cost}"
        else:
            return f"ocr_{event.timestamp.isoformat()}_{event.item_name}_{event.gem_cost}"

    def add_ocr_result(self, item_name: str, item_quantity: str,
                      original_price: float, converted_price: float,
                      profit: float, gem_cost: str) -> None:
        """添加OCR识别结果

        Args:
            item_name: 物品名称
            item_quantity: 物品数量（如"x5"）
            original_price: 原价
            converted_price: 折后价
            profit: 利润
            gem_cost: 游戏内显示的神威辉石价格（字符串）
        """
        timestamp = datetime.now()
        expire_time = timestamp + timedelta(seconds=self._cache_expire)

        # 提取中文名称（去除前缀英文、数字、符号）
        clean_item_name = self._extract_chinese_name(item_name) or item_name

        # 通过物品名称查询物品ID
        item_id = self._find_item_id_by_name(item_name)

        record = OcrRecognitionRecord(
            timestamp=timestamp,
            item_name=clean_item_name,  # 保存清理后的名称
            item_id=item_id,
            item_quantity=item_quantity,
            original_price=original_price,
            converted_price=converted_price,
            profit=profit,
            gem_cost=gem_cost,
            verified=False,
            expire_time=expire_time
        )

        with self._lock:
            self._ocr_cache[timestamp.isoformat()] = record
            self._save_ocr_records()

        item_id_str = f"(ID:{item_id})" if item_id else "(ID:未找到)"
        # print(f"[验证服务] 添加OCR识别结果: {item_name} {item_id_str} {item_quantity}, 价格: {gem_cost}, 利润: {profit:.4f}")
        # logger.info(f"添加OCR识别结果: {item_name} {item_quantity}, 价格: {gem_cost}")

    def _find_item_id_by_name(self, item_name: str) -> int | None:
        """通过物品名称查找物品ID

        Args:
            item_name: OCR识别的物品名称

        Returns:
            物品ID，如果未找到返回None
        """
        try:
            import json
            import os

            # 提取中文名称（去除前缀英文、数字、符号）
            clean_name = self._extract_chinese_name(item_name) or item_name

            # 从item.json中查找
            item_json_path = os.path.join(os.path.dirname(__file__), '..', 'item.json')
            if not os.path.exists(item_json_path):
                logger.warning(f"item.json 不存在: {item_json_path}")
                return None

            with open(item_json_path, 'r', encoding='utf-8') as f:
                item_data = json.load(f)

                # 精确匹配：直接比较名称（先尝试清理后的名称）
                for item_id, item_info in item_data.items():
                    if item_info.get('Name') == clean_name:
                        return int(item_id)

                # 如果清理后的名称没找到，尝试原始名称
                if clean_name != item_name:
                    for item_id, item_info in item_data.items():
                        if item_info.get('Name') == item_name:
                            return int(item_id)

                # 模糊匹配：对OCR识别的名称与item.json中的名称进行模糊匹配
                price_service = ItemPriceService()
                ocr_price = price_service.get_price_by_name(item_name)

                if ocr_price is not None:
                    # 找到价格相同的item.json物品
                    for item_id, item_info in item_data.items():
                        if item_info.get('Name'):
                            info_price = price_service.get_price_by_name(item_info['Name'])
                            if info_price is not None and abs(ocr_price - info_price) < 0.01:
                                # logger.debug(f"物品名称模糊匹配[价格匹配]: '{item_name}' -> '{item_info['Name']}' (价格: {ocr_price})")
                                return int(item_id)

                # logger.debug(f"未找到匹配的物品ID: {item_name}")
                return None
        except Exception as e:
            logger.error(f"查找物品ID失败: {e}", exc_info=True)
            return None

    def _extract_chinese_name(self, name: str) -> Optional[str]:
        """提取中文名称部分

        Args:
            name: 原始物品名称

        Returns:
            提取的中文名称，如果没有中文则返回None
        """
        import re
        # 提取所有中文字符、数字、括号等
        chinese_part = re.sub(r'[^\u4e00-\u9fa5（）\(\)0-9]', '', name)
        return chinese_part.strip() if chinese_part else None

    def add_buy_event(self, buy_event: BuyEvent) -> None:
        """添加购买事件

        Args:
            buy_event: 购买事件
        """
        logger.info(f"[DEBUG] add_buy_event 被调用: {buy_event.item_name}, 时间: {buy_event.timestamp.strftime('%H:%M:%S')}")

        # 直接添加到缓存，不做时间过滤
        # 因为GameLogParserService已经确保只读取新日志
        with self._lock:
            event_id = self._generate_event_id(buy_event)
            self._buy_event_cache[event_id] = buy_event

        # print(f"[验证服务] 添加购买事件: {buy_event.item_name}, 消耗神威辉石: {buy_event.gem_cost}")
        logger.info(f"添加购买事件: {buy_event.item_name}, 消耗: {buy_event.gem_cost}")

    def add_refresh_event(self, refresh_event: RefreshEvent) -> None:
        """添加刷新商店事件

        Args:
            refresh_event: 刷新商店事件
        """
        with self._lock:
            self._refresh_events.append(refresh_event)

        # print(f"[验证服务] 添加刷新事件: 消耗 {refresh_event.gem_cost} 神威辉石, 时间: {refresh_event.timestamp.strftime('%H:%M:%S')}")
        # logger.debug(f"添加刷新事件: 消耗 {refresh_event.gem_cost} 神威辉石")

    def verify_purchases(self) -> List[ExchangeRecord]:
        """验证购买事件，返回已验证的兑换记录

        Returns:
            已验证的兑换记录列表
        """
        verified_records = []

        with self._lock:
            # 先收集需要删除的过期记录ID
            expired_ids = []

            # 遍历所有OCR记录
            for ocr_id, ocr_record in self._ocr_cache.items():
                if ocr_record.verified:
                    continue

                if not self._is_record_valid(ocr_record):
                    # 标记为需要删除的过期记录
                    expired_ids.append(ocr_id)
                    continue

                # 尝试匹配购买事件
                matched_event = self._find_matching_buy_event(ocr_record)
                if matched_event:
                    # 验证通过，创建兑换记录
                    exchange_record = self._create_exchange_record(ocr_record, matched_event)
                    verified_records.append(exchange_record)

                    # 标记为已验证
                    ocr_record.verified = True
                    ocr_record.verified_by_event_id = self._generate_event_id(matched_event)

                    # print(f"[验证服务] ✓ 验证通过: {ocr_record.item_name} {ocr_record.item_quantity}, "
                    #       f"利润: {ocr_record.profit:.2f}")
                    logger.info(f"验证通过: {ocr_record.item_name} {ocr_record.item_quantity}, "
                               f"利润: {ocr_record.profit:.2f}")

            # 删除过期记录
            for expired_id in expired_ids:
                if expired_id in self._ocr_cache:
                    del self._ocr_cache[expired_id]

            # 保存更新后的OCR记录
            if verified_records or expired_ids:
                self._save_ocr_records()

        return verified_records

    def _find_matching_buy_event(self, ocr_record: OcrRecognitionRecord) -> Optional[BuyEvent]:
        """查找匹配的购买事件

        匹配条件：
        1. 神威辉石消耗量匹配
        2. 物品ID匹配（优先）或物品名称匹配（备用）
        3. 物品增加的数量与OCR识别的物品数量匹配

        Args:
            ocr_record: OCR识别记录

        Returns:
            匹配的购买事件，如果没有匹配返回None
        """
        # 提取OCR识别的价格（可能是"x 50"或"50"等格式）
        ocr_gem_cost = self._extract_gem_cost_from_ocr(ocr_record.gem_cost)
        if ocr_gem_cost is None:
            logger.warning(f"无法从OCR结果中提取神威辉石数量: {ocr_record.gem_cost}")
            return None

        # 提取OCR识别的物品数量
        ocr_item_quantity = self._extract_item_quantity_from_ocr(ocr_record.item_quantity)

        # 输出当前缓存的购买事件（调试）
        # print(f"[验证服务] 当前缓存的购买事件数: {len(self._buy_event_cache)}")
        # for event_id, buy_event in self._buy_event_cache.items():
        #     time_diff = abs((buy_event.timestamp - ocr_record.timestamp).total_seconds())
        #     print(f"[验证服务]   缓存事件: 物品={buy_event.item_name}, ID={buy_event.item_id}, 消耗={buy_event.gem_cost}, 数量={buy_event.item_quantity}, 时间={buy_event.timestamp.strftime('%H:%M:%S')}")
        # print(f"[验证服务] OCR记录: 物品={ocr_record.item_name}, ID={ocr_record.item_id}, 消耗={ocr_gem_cost}, 数量={ocr_item_quantity}, 时间={ocr_record.timestamp.strftime('%H:%M:%S')}")

        # 遍历所有购买事件
        for event_id, buy_event in self._buy_event_cache.items():
            # 检查神威辉石消耗量
            if buy_event.gem_cost != ocr_gem_cost:
                continue

            # 优先使用物品ID匹配
            if ocr_record.item_id is not None and ocr_record.item_id == buy_event.item_id:
                # 检查物品数量是否匹配
                if ocr_item_quantity is not None and buy_event.item_quantity != ocr_item_quantity:
                    # print(f"[验证服务] ✗ 神威辉石和物品ID匹配，但数量不匹配: OCR={ocr_item_quantity}, 日志={buy_event.item_quantity}")
                    continue

                # print(f"[验证服务] ✓ 找到匹配事件(ID): 物品={buy_event.item_name}, ID={buy_event.item_id}, 消耗={buy_event.gem_cost}, 数量={buy_event.item_quantity}")
                # logger.debug(f"找到匹配事件: 物品={buy_event.item_name}, ID={buy_event.item_id}, 消耗={buy_event.gem_cost}, 数量={buy_event.item_quantity}")
                return buy_event

            # 备用：物品名称匹配
            if self._match_item_name(ocr_record.item_name, buy_event.item_name):
                # 检查物品数量是否匹配
                if ocr_item_quantity is not None and buy_event.item_quantity != ocr_item_quantity:
                    # print(f"[验证服务] ✗ 神威辉石和物品名称匹配，但数量不匹配: OCR={ocr_item_quantity}, 日志={buy_event.item_quantity}")
                    continue

                # print(f"[验证服务] ✓ 找到匹配事件(名称): 物品={buy_event.item_name}, 消耗={buy_event.gem_cost}, 数量={buy_event.item_quantity}")
                # logger.debug(f"找到匹配事件: 物品={buy_event.item_name}, 消耗={buy_event.gem_cost}, 数量={buy_event.item_quantity}")
                return buy_event

        return None

    def _extract_gem_cost_from_ocr(self, gem_cost_str: str) -> Optional[int]:
        """从OCR识别的价格字符串中提取神威辉石数量

        Args:
            gem_cost_str: OCR识别的价格字符串（如"x 50", "50", "x50"等）

        Returns:
            神威辉石数量，如果提取失败返回None
        """
        import re

        # 提取数字
        match = re.search(r'\d+', gem_cost_str)
        if match:
            return int(match.group(0))

        return None

    def _extract_item_quantity_from_ocr(self, item_quantity_str: str) -> Optional[int]:
        """从OCR识别的物品数量字符串中提取数量

        Args:
            item_quantity_str: OCR识别的物品数量字符串（如"x1", "1", "x 1"等）

        Returns:
            物品数量，如果提取失败返回None
        """
        import re

        # 提取数字
        match = re.search(r'\d+', item_quantity_str)
        if match:
            return int(match.group(0))

        return None

    def _match_item_name(self, ocr_name: str, log_name: str) -> bool:
        """匹配物品名称

        Args:
            ocr_name: OCR识别的物品名称
            log_name: 日志中的物品名称

        Returns:
            True表示名称匹配
        """
        # 精确匹配
        if ocr_name == log_name:
            return True

        # 使用ItemPriceService的模糊匹配逻辑
        price_service = ItemPriceService()
        ocr_price = price_service.get_price_by_name(ocr_name)
        log_price = price_service.get_price_by_name(log_name)

        # 如果两个名称对应的价格相同，则认为是同一个物品
        if ocr_price is not None and log_price is not None:
            if abs(ocr_price - log_price) < 0.01:  # 价格相同（允许浮点误差）
                return True

        return False

    def _create_exchange_record(self, ocr_record: OcrRecognitionRecord,
                               buy_event: BuyEvent) -> ExchangeRecord:
        """创建兑换记录

        Args:
            ocr_record: OCR识别记录
            buy_event: 购买事件

        Returns:
            兑换记录
        """
        # 取较早的时间作为购买时间
        purchase_time = min(ocr_record.timestamp, buy_event.timestamp)

        return ExchangeRecord(
            timestamp=purchase_time,
            item_name=ocr_record.item_name,
            item_id=buy_event.item_id,
            item_quantity=ocr_record.item_quantity,
            original_price=ocr_record.original_price,
            converted_price=ocr_record.converted_price,
            profit=ocr_record.profit,
            gem_cost=buy_event.gem_cost,
            ocr_timestamp=ocr_record.timestamp,
            log_timestamp=buy_event.timestamp,
            verified=True
        )

    def get_refresh_events(self) -> List[RefreshEvent]:
        """获取刷新事件列表并清空缓存

        Returns:
            刷新事件列表
        """
        with self._lock:
            # 获取所有刷新事件并清空列表
            events = self._refresh_events.copy()
            self._refresh_events.clear()
            return events

    def clean_expired_records(self) -> int:
        """清理过期的OCR记录

        Returns:
            清理的记录数量
        """
        cleaned_count = 0

        with self._lock:
            expired_ids = []
            for ocr_id, record in self._ocr_cache.items():
                if not self._is_record_valid(record):
                    expired_ids.append(ocr_id)

            for ocr_id in expired_ids:
                del self._ocr_cache[ocr_id]
                cleaned_count += 1

            if cleaned_count > 0:
                self._save_ocr_records()

        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 条过期OCR记录")

        return cleaned_count

    def clear_cache(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._ocr_cache.clear()
            self._buy_event_cache.clear()
            self._refresh_events.clear()
        logger.info("验证服务缓存已清空")
