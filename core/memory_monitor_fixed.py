"""简化版内存监控器 - 移除复杂的初始化逻辑"""
import time
from typing import Optional, Callable

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from core.logger import get_logger

logger = get_logger(__name__)


class SimpleMemoryMonitor:
    """简化的内存监控器

    去除单例模式，简化初始化，避免卡死问题。
    """

    def __init__(
        self,
        warning_threshold_mb: float = 500.0,
        critical_threshold_mb: float = 1000.0,
        check_interval: float = 10.0,
        auto_cleanup_on_warning: bool = True
    ):
        """初始化内存监控器

        Args:
            warning_threshold_mb: 警告阈值（MB）
            critical_threshold_mb: 严重阈值（MB）
            check_interval: 检查间隔（秒）
            auto_cleanup_on_warning: 警告时是否自动清理
        """
        self._warning_threshold = warning_threshold_mb
        self._critical_threshold = critical_threshold_mb
        self._check_interval = check_interval
        self._auto_cleanup_on_warning = auto_cleanup_on_warning

        # 监控状态
        self._is_monitoring = False
        self._stop_requested = False

        # 当前状态
        self._current_usage_mb = 0.0
        self._peak_usage_mb = 0.0

        # 统计信息
        self._stats = {
            'warning_count': 0,
            'critical_count': 0,
            'recovery_count': 0,
            'cleanup_count': 0
        }

        logger.info(
            f"内存监控器已初始化，"
            f"警告阈值: {warning_threshold_mb}MB, "
            f"严重阈值: {critical_threshold_mb}MB"
        )

    def start(self) -> None:
        """启动内存监控（简化版，不使用线程）"""
        if self._is_monitoring:
            logger.warning("内存监控已在运行")
            return

        self._is_monitoring = True
        self._stop_requested = False
        logger.info("内存监控已启动（简化版）")

    def stop(self) -> None:
        """停止内存监控"""
        if not self._is_monitoring:
            return

        self._is_monitoring = False
        self._stop_requested = True
        logger.info("内存监控已停止")

    def check_memory(self) -> None:
        """手动检查内存使用一次

        Returns:
            当前内存使用（MB），如果获取失败返回None
        """
        if not PSUTIL_AVAILABLE:
            return None

        try:
            import psutil
            process = psutil.Process()
            mem_info = process.memory_info()
            usage_mb = mem_info.rss / 1024 / 1024

            self._current_usage_mb = usage_mb

            # 更新峰值
            if usage_mb > self._peak_usage_mb:
                self._peak_usage_mb = usage_mb

            # 检查阈值
            if usage_mb >= self._critical_threshold:
                if self._stats['critical_count'] == 0:
                    logger.error(
                        f"内存使用超过严重阈值: {usage_mb:.2f}MB / {self._critical_threshold:.2f}MB"
                    )
                self._stats['critical_count'] += 1
            elif usage_mb >= self._warning_threshold:
                if self._stats['warning_count'] == 0:
                    logger.warning(
                        f"内存使用超过警告阈值: {usage_mb:.2f}MB / {self._warning_threshold:.2f}MB"
                    )
                self._stats['warning_count'] += 1
                if self._auto_cleanup_on_warning:
                    self._cleanup_memory()
            else:
                if (self._stats['warning_count'] > 0 or
                    self._stats['critical_count'] > 0):
                    self._stats['recovery_count'] += 1

            return usage_mb

        except Exception as e:
            logger.warning(f"获取内存信息失败: {e}")
            return None

    def _cleanup_memory(self) -> None:
        """执行内存清理"""
        try:
            import gc
            gc.collect()
            self._stats['cleanup_count'] += 1
            logger.debug("执行了垃圾回收")
        except Exception as e:
            logger.warning(f"内存清理失败: {e}")

    def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            'current_usage_mb': self._current_usage_mb,
            'peak_usage_mb': self._peak_usage_mb,
            'warning_count': self._stats['warning_count'],
            'critical_count': self._stats['critical_count'],
            'recovery_count': self._stats['recovery_count'],
            'cleanup_count': self._stats['cleanup_count']
        }


# 全局实例
_memory_monitor: Optional[SimpleMemoryMonitor] = None


def get_memory_monitor() -> SimpleMemoryMonitor:
    """获取内存监控器实例

    Returns:
        SimpleMemoryMonitor 实例
    """
    global _memory_monitor

    if _memory_monitor is None:
        _memory_monitor = SimpleMemoryMonitor()

    return _memory_monitor
