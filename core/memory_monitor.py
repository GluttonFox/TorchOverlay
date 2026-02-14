"""内存监控器 - 监控内存使用情况，预警内存溢出"""
import gc
import time
import threading
from typing import Callable, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from core.logger import get_logger

logger = get_logger(__name__)


class MemoryMonitor:
    """内存监控器

    监控进程内存使用情况，提供预警和自动清理功能。
    """

    _instance: Optional['MemoryMonitor'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

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
        if self._initialized:
            return

        self._warning_threshold = warning_threshold_mb
        self._critical_threshold = critical_threshold_mb
        self._check_interval = check_interval
        self._auto_cleanup_on_warning = auto_cleanup_on_warning

        # 监控状态
        self._is_monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 当前状态
        self._current_usage_mb = 0.0
        self._peak_usage_mb = 0.0
        self._last_check_time = 0.0

        # 回调函数
        self._on_warning: Optional[Callable[[float], None]] = None
        self._on_critical: Optional[Callable[[float], None]] = None
        self._on_recovery: Optional[Callable[[float], None]] = None

        # 统计信息
        self._stats = {
            'warning_count': 0,
            'critical_count': 0,
            'recovery_count': 0,
            'cleanup_count': 0
        }

        self._initialized = True
        logger.info(
            f"内存监控器已初始化，"
            f"警告阈值: {warning_threshold_mb}MB, "
            f"严重阈值: {critical_threshold_mb}MB"
        )

    @classmethod
    def get_instance(cls) -> 'MemoryMonitor':
        """获取内存监控器单例

        Returns:
            MemoryMonitor 实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start(self) -> None:
        """启动内存监控"""
        if self._is_monitoring:
            logger.warning("内存监控已在运行")
            return

        self._is_monitoring = True
        self._stop_event.clear()

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self._monitor_thread.start()

        logger.info("内存监控已启动")

    def stop(self) -> None:
        """停止内存监控"""
        if not self._is_monitoring:
            return

        self._is_monitoring = False
        self._stop_event.set()

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)

        logger.info("内存监控已停止")

    def _monitor_loop(self) -> None:
        """监控循环（在独立线程中运行）"""
        while self._is_monitoring:
            try:
                # 检查内存使用
                self._check_memory()

                # 等待下一次检查
                self._stop_event.wait(self._check_interval)

            except Exception as e:
                logger.error(f"内存监控循环出错: {e}", exc_info=True)
                # 出错后等待一段时间再继续
                self._stop_event.wait(self._check_interval)

    def _check_memory(self) -> None:
        """检查内存使用情况"""
        # 获取当前内存使用
        memory_info = self._get_memory_info()

        if memory_info is None:
            return

        self._current_usage_mb = memory_info['rss_mb']
        self._last_check_time = time.time()

        # 更新峰值
        if self._current_usage_mb > self._peak_usage_mb:
            self._peak_usage_mb = self._current_usage_mb
            logger.debug(f"内存使用峰值更新: {self._peak_usage_mb:.2f}MB")

        # 检查阈值
        if self._current_usage_mb >= self._critical_threshold:
            self._handle_critical()
        elif self._current_usage_mb >= self._warning_threshold:
            self._handle_warning()
        else:
            # 恢复正常
            if (self._stats['warning_count'] > 0 or
                self._stats['critical_count'] > 0):
                self._handle_recovery()

    def _get_memory_info(self) -> Optional[dict]:
        """获取内存信息

        Returns:
            内存信息字典，如果获取失败则返回None
        """
        if not PSUTIL_AVAILABLE:
            return None

        try:
            process = psutil.Process()
            mem_info = process.memory_info()

            return {
                'rss': mem_info.rss,
                'rss_mb': mem_info.rss / 1024 / 1024,
                'vms': mem_info.vms,
                'vms_mb': mem_info.vms / 1024 / 1024,
                'available': psutil.virtual_memory().available
            }
        except Exception as e:
            logger.warning(f"获取内存信息失败: {e}")
            return None

    def _handle_warning(self) -> None:
        """处理警告级别"""
        if self._stats['warning_count'] == 0:
            # 第一次警告
            logger.warning(
                f"内存使用超过警告阈值: {self._current_usage_mb:.2f}MB / {self._warning_threshold:.2f}MB"
            )

            # 调用警告回调
            if self._on_warning:
                try:
                    self._on_warning(self._current_usage_mb)
                except Exception as e:
                    logger.error(f"警告回调执行失败: {e}")

            # 自动清理
            if self._auto_cleanup_on_warning:
                self._cleanup_memory()
                self._stats['cleanup_count'] += 1

        self._stats['warning_count'] += 1

    def _handle_critical(self) -> None:
        """处理严重级别"""
        if self._stats['critical_count'] == 0:
            # 第一次严重警告
            logger.error(
                f"内存使用超过严重阈值: {self._current_usage_mb:.2f}MB / {self._critical_threshold:.2f}MB"
            )

            # 调用严重回调
            if self._on_critical:
                try:
                    self._on_critical(self._current_usage_mb)
                except Exception as e:
                    logger.error(f"严重回调执行失败: {e}")

            # 强制清理
            self._cleanup_memory(force=True)
            self._stats['cleanup_count'] += 1

        self._stats['critical_count'] += 1

    def _handle_recovery(self) -> None:
        """处理恢复到正常水平"""
        logger.info(
            f"内存使用恢复到正常水平: {self._current_usage_mb:.2f}MB"
        )

        # 调用恢复回调
        if self._on_recovery:
            try:
                self._on_recovery(self._current_usage_mb)
            except Exception as e:
                logger.error(f"恢复回调执行失败: {e}")

        self._stats['recovery_count'] += 1

        # 重置警告计数
        self._stats['warning_count'] = 0
        self._stats['critical_count'] = 0

    def _cleanup_memory(self, force: bool = False) -> None:
        """清理内存

        Args:
            force: 是否强制清理
        """
        logger.info(f"执行内存清理 (force={force})")

        # 垃圾回收
        gc.collect()

        # 清理资源管理器中的资源
        try:
            from core.resource_manager import ResourceManager
            rm = ResourceManager.get_instance()
            released_count = rm.cleanup_old_resources(
                max_age_seconds=60.0 if not force else 0.0
            )
            if released_count > 0:
                logger.info(f"清理了 {released_count} 个资源")
        except Exception as e:
            logger.error(f"清理资源失败: {e}")

        # 获取清理后的内存使用
        memory_info = self._get_memory_info()
        if memory_info:
            saved_mb = self._current_usage_mb - memory_info['rss_mb']
            logger.info(f"内存清理完成，释放: {saved_mb:.2f}MB")

    def set_callbacks(
        self,
        on_warning: Optional[Callable[[float], None]] = None,
        on_critical: Optional[Callable[[float], None]] = None,
        on_recovery: Optional[Callable[[float], None]] = None
    ) -> None:
        """设置回调函数

        Args:
            on_warning: 警告回调，参数为当前内存使用（MB）
            on_critical: 严重回调，参数为当前内存使用（MB）
            on_recovery: 恢复回调，参数为当前内存使用（MB）
        """
        self._on_warning = on_warning
        self._on_critical = on_critical
        self._on_recovery = on_recovery

    def get_current_usage(self) -> float:
        """获取当前内存使用（MB）

        Returns:
            当前内存使用（MB）
        """
        return self._current_usage_mb

    def get_peak_usage(self) -> float:
        """获取峰值内存使用（MB）

        Returns:
            峰值内存使用（MB）
        """
        return self._peak_usage_mb

    def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        memory_info = self._get_memory_info()

        return {
            **self._stats,
            'current_usage_mb': self._current_usage_mb,
            'peak_usage_mb': self._peak_usage_mb,
            'warning_threshold_mb': self._warning_threshold,
            'critical_threshold_mb': self._critical_threshold,
            'is_monitoring': self._is_monitoring,
            'psutil_available': PSUTIL_AVAILABLE,
            'detailed_memory': memory_info
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            'warning_count': 0,
            'critical_count': 0,
            'recovery_count': 0,
            'cleanup_count': 0
        }

    def trigger_manual_cleanup(self) -> None:
        """手动触发内存清理"""
        logger.info("手动触发内存清理")
        self._cleanup_memory(force=True)
        self._stats['cleanup_count'] += 1


def get_memory_monitor() -> MemoryMonitor:
    """获取内存监控器实例（便捷函数）

    Returns:
        MemoryMonitor 实例
    """
    return MemoryMonitor.get_instance()


def check_memory_now() -> Optional[dict]:
    """立即检查内存使用（便捷函数）

    Returns:
        内存信息字典
    """
    monitor = get_memory_monitor()
    monitor._check_memory()
    return monitor._get_memory_info()
