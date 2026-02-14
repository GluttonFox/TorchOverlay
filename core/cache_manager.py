"""缓存管理工具 - 提供带大小限制和TTL的缓存"""
import time
from typing import TypeVar, Optional, Callable, Any
from collections import OrderedDict
from threading import Lock

from core.logger import get_logger

logger = get_logger(__name__)

K = TypeVar('K')
V = TypeVar('V')


class CacheEntry:
    """缓存条目"""

    def __init__(self, value: V, ttl: Optional[float] = None):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl  # 过期时间（秒），None表示永不过期

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl


class LRUCache:
    """带TTL的LRU缓存"""

    def __init__(
        self,
        max_size: int = 128,
        default_ttl: Optional[float] = None,
        auto_cleanup: bool = True
    ):
        """初始化LRU缓存

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认TTL（秒），None表示永不过期
            auto_cleanup: 是否自动清理过期条目
        """
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._auto_cleanup = auto_cleanup

        # 使用OrderedDict实现LRU
        self._cache: OrderedDict[K, CacheEntry] = OrderedDict()
        self._lock = Lock()

        # 统计信息
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0
        }

    def get(self, key: K) -> Optional[V]:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或已过期则返回None
        """
        with self._lock:
            # 自动清理过期条目
            if self._auto_cleanup:
                self._cleanup_expired()

            # 查找键
            if key not in self._cache:
                self._stats['misses'] += 1
                return None

            entry = self._cache[key]

            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                self._stats['expirations'] += 1
                self._stats['misses'] += 1
                return None

            # 命中，移动到末尾（最近使用）
            self._cache.move_to_end(key)
            self._stats['hits'] += 1

            return entry.value

    def set(self, key: K, value: V, ttl: Optional[float] = None) -> None:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None使用默认TTL
        """
        with self._lock:
            # 自动清理过期条目
            if self._auto_cleanup:
                self._cleanup_expired()

            # 使用指定的TTL或默认TTL
            actual_ttl = ttl if ttl is not None else self._default_ttl

            # 检查容量
            if len(self._cache) >= self._max_size and key not in self._cache:
                # 删除最旧的条目
                oldest_key, _ = self._cache.popitem(last=False)
                self._stats['evictions'] += 1
                logger.debug(f"缓存已满，驱逐最旧的条目: {oldest_key}")

            # 添加或更新条目
            self._cache[key] = CacheEntry(value, actual_ttl)
            self._cache.move_to_end(key)  # 移动到末尾

    def delete(self, key: K) -> bool:
        """删除缓存值

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            logger.debug("缓存已清空")

    def _cleanup_expired(self) -> int:
        """清理过期条目

        Returns:
            清理的条目数
        """
        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]
            self._stats['expirations'] += 1

        if expired_keys:
            logger.debug(f"清理了 {len(expired_keys)} 个过期缓存条目")

        return len(expired_keys)

    def get_stats(self) -> dict:
        """获取缓存统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (
                self._stats['hits'] / total_requests * 100
                if total_requests > 0 else 0.0
            )

            return {
                **self._stats,
                'size': len(self._cache),
                'max_size': self._max_size,
                'hit_rate': f"{hit_rate:.2f}%"
            }

    def reset_stats(self) -> None:
        """重置统计信息"""
        with self._lock:
            self._stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'expirations': 0
            }


class TimedCache:
    """基于时间的简单缓存（适用于时间序列数据）"""

    def __init__(
        self,
        max_size: int = 1000,
        max_age_seconds: float = 3600
    ):
        """初始化时间缓存

        Args:
            max_size: 最大缓存条目数
            max_age_seconds: 最大保留时间（秒）
        """
        self._max_size = max_size
        self._max_age_seconds = max_age_seconds
        self._cache: OrderedDict[Any, Any] = OrderedDict()
        self._timestamps: OrderedDict[Any, float] = OrderedDict()
        self._lock = Lock()

    def add(self, key: Any, value: Any, timestamp: Optional[float] = None) -> None:
        """添加缓存条目

        Args:
            key: 缓存键
            value: 缓存值
            timestamp: 时间戳（None使用当前时间）
        """
        if timestamp is None:
            timestamp = time.time()

        with self._lock:
            # 检查容量
            if len(self._cache) >= self._max_size:
                # 删除最旧的条目
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]

            # 添加条目
            self._cache[key] = value
            self._timestamps[key] = timestamp

    def get_recent(self, count: int = 10) -> list[tuple[Any, Any, float]]:
        """获取最近的N个条目

        Args:
            count: 要获取的条目数

        Returns:
            [(key, value, timestamp), ...] 按时间从新到旧排序
        """
        with self._lock:
            # 按时间戳排序
            sorted_items = sorted(
                self._timestamps.items(),
                key=lambda x: x[1],
                reverse=True
            )
            # 获取最近的N个
            recent_items = sorted_items[:count]
            # 返回 (key, value, timestamp)
            return [
                (key, self._cache[key], timestamp)
                for key, timestamp in recent_items
            ]

    def cleanup_old(self, max_age_seconds: Optional[float] = None) -> int:
        """清理旧的条目

        Args:
            max_age_seconds: 最大年龄（秒），None使用默认值

        Returns:
            清理的条目数
        """
        if max_age_seconds is None:
            max_age_seconds = self._max_age_seconds

        with self._lock:
            current_time = time.time()
            expired_keys = []

            for key, timestamp in self._timestamps.items():
                if current_time - timestamp > max_age_seconds:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]
                del self._timestamps[key]

            if expired_keys:
                logger.debug(f"清理了 {len(expired_keys)} 个过期条目")

            return len(expired_keys)

    def get_size(self) -> int:
        """获取当前缓存大小"""
        with self._lock:
            return len(self._cache)

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
