"""刷新日志服务 - 管理商店刷新记录"""
import os
import json
from datetime import datetime
from typing import List, Optional
import threading

from core.logger import get_logger
from domain.models.refresh_event import RefreshEvent

logger = get_logger(__name__)


class RefreshLogService:
    """刷新日志服务"""

    def __init__(self, refresh_log_path: str | None = None):
        """初始化刷新日志服务

        Args:
            refresh_log_path: 刷新日志文件路径
        """
        self.refresh_log_path = refresh_log_path or self._get_default_path()
        self._lock = threading.Lock()

        # 确保日志目录存在
        self._ensure_log_directory()

    def _get_default_path(self) -> str:
        """获取默认的刷新日志路径"""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(base_dir, 'refresh_log.json')

    def _ensure_log_directory(self) -> None:
        """确保日志目录存在"""
        log_dir = os.path.dirname(self.refresh_log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            logger.info(f"创建日志目录: {log_dir}")

    def load_records(self) -> List[RefreshEvent]:
        """加载所有刷新记录

        Returns:
            刷新记录列表
        """
        if not os.path.exists(self.refresh_log_path):
            logger.info("刷新日志文件不存在，返回空列表")
            return []

        try:
            with open(self.refresh_log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                records = []
                for record_data in data:
                    # 兼容旧格式（dict）和新格式（RefreshEvent）
                    if isinstance(record_data, dict):
                        records.append(RefreshEvent(
                            timestamp=datetime.fromisoformat(record_data['timestamp']),
                            gem_cost=record_data['gem_cost'],
                            log_context=record_data.get('log_context')
                        ))
                    else:
                        records.append(record_data)
                logger.info(f"加载了 {len(records)} 条刷新记录")
                return records
        except Exception as e:
            logger.error(f"加载刷新记录失败: {e}", exc_info=True)
            return []

    def save_records(self, records: List[RefreshEvent]) -> bool:
        """保存刷新记录

        Args:
            records: 刷新记录列表

        Returns:
            True表示保存成功
        """
        try:
            data = []
            for record in records:
                if isinstance(record, RefreshEvent):
                    data.append({
                        'timestamp': record.timestamp.isoformat(),
                        'gem_cost': record.gem_cost,
                        'log_context': record.log_context
                    })
                else:
                    data.append(record)

            with open(self.refresh_log_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"保存了 {len(records)} 条刷新记录")
            return True
        except Exception as e:
            logger.error(f"保存刷新记录失败: {e}", exc_info=True)
            return False

    def add_record(self, record: RefreshEvent) -> bool:
        """添加一条刷新记录

        Args:
            record: 刷新记录

        Returns:
            True表示添加成功
        """
        with self._lock:
            records = self.load_records()
            records.append(record)
            # 按时间戳排序
            records.sort(key=lambda r: r.timestamp)
            return self.save_records(records)

    def add_records(self, records: List[RefreshEvent]) -> bool:
        """批量添加刷新记录

        Args:
            records: 刷新记录列表

        Returns:
            True表示添加成功
        """
        with self._lock:
            if not records:
                return True

            existing_records = self.load_records()
            existing_timestamps = {rec.timestamp.isoformat() for rec in existing_records}

            # 只添加不存在的记录（去重）
            new_records = [rec for rec in records if rec.timestamp.isoformat() not in existing_timestamps]

            if not new_records:
                # logger.debug("没有新的刷新记录需要添加")
                return True

            existing_records.extend(new_records)

            # 按时间戳排序
            existing_records.sort(key=lambda r: r.timestamp)

            return self.save_records(existing_records)

    def get_records_by_date_range(self, start_date: datetime,
                                 end_date: datetime) -> List[RefreshEvent]:
        """获取指定日期范围内的刷新记录

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            刷新记录列表
        """
        records = self.load_records()
        return [
            record for record in records
            if start_date <= record.timestamp <= end_date
        ]

    def get_latest_records(self, limit: int = 10) -> List[RefreshEvent]:
        """获取最新的N条刷新记录

        Args:
            limit: 记录数量

        Returns:
            刷新记录列表
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
                'total_gem_cost': 0,
                'by_date': {}
            }

        total_gem_cost = sum(record.gem_cost for record in records)

        # 按日期统计
        by_date = {}
        for record in records:
            date_str = record.timestamp.strftime('%Y-%m-%d')
            if date_str not in by_date:
                by_date[date_str] = {
                    'count': 0,
                    'total_gem_cost': 0
                }
            by_date[date_str]['count'] += 1
            by_date[date_str]['total_gem_cost'] += record.gem_cost

        return {
            'total_records': len(records),
            'total_gem_cost': total_gem_cost,
            'by_date': by_date
        }

    def clear_records(self) -> bool:
        """清空所有刷新记录

        Returns:
            True表示清空成功
        """
        try:
            with open(self.refresh_log_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            logger.info("已清空所有刷新记录")
            return True
        except Exception as e:
            logger.error(f"清空刷新记录失败: {e}", exc_info=True)
            return False

    def backup(self) -> Optional[str]:
        """备份刷新日志

        Returns:
            备份文件路径，如果备份失败返回None
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{self.refresh_log_path}.backup_{timestamp}"

            with open(self.refresh_log_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())

            logger.info(f"刷新日志已备份到: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"备份刷新日志失败: {e}", exc_info=True)
            return None
