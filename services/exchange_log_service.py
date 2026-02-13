"""兑换日志服务 - 管理exchange_log.json文件"""
import os
import json
from datetime import datetime
from typing import List, Optional
import threading

from core.logger import get_logger
from domain.models.exchange_record import ExchangeRecord

logger = get_logger(__name__)


class ExchangeLogService:
    """兑换日志服务"""

    def __init__(self, exchange_log_path: str | None = None):
        """初始化兑换日志服务

        Args:
            exchange_log_path: 兑换日志文件路径
        """
        self.exchange_log_path = exchange_log_path or self._get_default_path()
        self._lock = threading.Lock()

        # 确保日志目录存在
        self._ensure_log_directory()

    def _get_default_path(self) -> str:
        """获取默认的兑换日志路径"""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(base_dir, 'exchange_log.json')

    def _ensure_log_directory(self) -> None:
        """确保日志目录存在"""
        log_dir = os.path.dirname(self.exchange_log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            logger.info(f"创建日志目录: {log_dir}")

    def load_records(self) -> List[ExchangeRecord]:
        """加载所有兑换记录

        Returns:
            兑换记录列表
        """
        if not os.path.exists(self.exchange_log_path):
            logger.info("兑换日志文件不存在，返回空列表")
            return []

        try:
            with open(self.exchange_log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                records = [ExchangeRecord.from_dict(record_data) for record_data in data]
                logger.info(f"加载了 {len(records)} 条兑换记录")
                return records
        except Exception as e:
            logger.error(f"加载兑换记录失败: {e}", exc_info=True)
            return []

    def save_records(self, records: List[ExchangeRecord]) -> bool:
        """保存兑换记录

        Args:
            records: 兑换记录列表

        Returns:
            True表示保存成功
        """
        try:
            data = [record.to_dict() for record in records]
            with open(self.exchange_log_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"保存了 {len(records)} 条兑换记录")
            return True
        except Exception as e:
            logger.error(f"保存兑换记录失败: {e}", exc_info=True)
            return False

    def add_record(self, record: ExchangeRecord) -> bool:
        """添加一条兑换记录

        Args:
            record: 兑换记录

        Returns:
            True表示添加成功
        """
        with self._lock:
            records = self.load_records()
            records.append(record)
            return self.save_records(records)

    def add_records(self, records: List[ExchangeRecord]) -> bool:
        """批量添加兑换记录

        Args:
            records: 兑换记录列表

        Returns:
            True表示添加成功
        """
        with self._lock:
            if not records:
                return True

            existing_records = self.load_records()
            existing_records.extend(records)

            # 按时间戳排序
            existing_records.sort(key=lambda r: r.timestamp)

            result = self.save_records(existing_records)
            if result:
                print(f"[兑换日志] 成功保存 {len(records)} 条验证通过的记录")
            return result

    def get_records_by_date_range(self, start_date: datetime,
                                 end_date: datetime) -> List[ExchangeRecord]:
        """获取指定日期范围内的兑换记录

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            兑换记录列表
        """
        records = self.load_records()
        return [
            record for record in records
            if start_date <= record.timestamp <= end_date
        ]

    def get_records_by_item_name(self, item_name: str) -> List[ExchangeRecord]:
        """获取指定物品的兑换记录

        Args:
            item_name: 物品名称

        Returns:
            兑换记录列表
        """
        records = self.load_records()
        return [
            record for record in records
            if record.item_name == item_name
        ]

    def get_latest_records(self, limit: int = 10) -> List[ExchangeRecord]:
        """获取最新的N条兑换记录

        Args:
            limit: 记录数量

        Returns:
            兑换记录列表
        """
        records = self.load_records()
        # 按时间戳降序排序
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]

    def get_statistics(self) -> dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        records = self.load_records()

        if not records:
            return {
                'total_records': 0,
                'total_profit': 0.0,
                'total_gem_cost': 0,
                'items_count': {},
                'by_date': {}
            }

        total_profit = sum(record.profit for record in records)
        total_gem_cost = sum(record.gem_cost for record in records)

        # 按物品统计
        items_count = {}
        for record in records:
            if record.item_name not in items_count:
                items_count[record.item_name] = {
                    'count': 0,
                    'total_profit': 0.0,
                    'total_gem_cost': 0
                }
            items_count[record.item_name]['count'] += 1
            items_count[record.item_name]['total_profit'] += record.profit
            items_count[record.item_name]['total_gem_cost'] += record.gem_cost

        # 按日期统计
        by_date = {}
        for record in records:
            date_str = record.timestamp.strftime('%Y-%m-%d')
            if date_str not in by_date:
                by_date[date_str] = {
                    'count': 0,
                    'total_profit': 0.0,
                    'total_gem_cost': 0
                }
            by_date[date_str]['count'] += 1
            by_date[date_str]['total_profit'] += record.profit
            by_date[date_str]['total_gem_cost'] += record.gem_cost

        return {
            'total_records': len(records),
            'total_profit': total_profit,
            'total_gem_cost': total_gem_cost,
            'items_count': items_count,
            'by_date': by_date
        }

    def clear_records(self) -> bool:
        """清空所有兑换记录

        Returns:
            True表示清空成功
        """
        try:
            with open(self.exchange_log_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            logger.info("已清空所有兑换记录")
            return True
        except Exception as e:
            logger.error(f"清空兑换记录失败: {e}", exc_info=True)
            return False

    def delete_record_by_timestamp(self, timestamp: datetime) -> bool:
        """根据时间戳删除兑换记录

        Args:
            timestamp: 时间戳

        Returns:
            True表示删除成功
        """
        with self._lock:
            records = self.load_records()
            original_count = len(records)

            records = [
                record for record in records
                if record.timestamp != timestamp
            ]

            if len(records) == original_count:
                logger.warning(f"未找到时间戳为 {timestamp} 的记录")
                return False

            return self.save_records(records)

    def backup(self) -> Optional[str]:
        """备份兑换日志

        Returns:
            备份文件路径，如果备份失败返回None
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{self.exchange_log_path}.backup_{timestamp}"

            with open(self.exchange_log_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())

            logger.info(f"兑换日志已备份到: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"备份兑换日志失败: {e}", exc_info=True)
            return None
