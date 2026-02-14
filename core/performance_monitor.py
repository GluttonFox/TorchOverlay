"""性能监控工具 - 收集和分析性能指标"""
import time
import threading
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass, field
from collections import deque
from functools import wraps

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    value: float
    unit: str
    timestamp: float
    metadata: Dict = field(default_factory=dict)


class PerformanceMonitor:
    """性能监控器

    收集和分析应用性能指标。
    """

    _instance: Optional['PerformanceMonitor'] = None
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
        max_history: int = 1000,
        auto_cleanup: bool = True
    ):
        """初始化性能监控器

        Args:
            max_history: 最大历史记录数
            auto_cleanup: 是否自动清理旧记录
        """
        if self._initialized:
            return

        self._max_history = max_history
        self._auto_cleanup = auto_cleanup

        # 指标存储（按类别）
        self._metrics: Dict[str, deque] = {}
        self._metrics_lock = threading.Lock()

        # 活跃的计时器
        self._timers: Dict[str, float] = {}

        # 统计信息
        self._stats = {
            'total_metrics': 0,
            'categories': 0
        }

        self._initialized = True
        logger.info("性能监控器已初始化")

    @classmethod
    def get_instance(cls) -> 'PerformanceMonitor':
        """获取性能监控器单例

        Returns:
            PerformanceMonitor 实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        category: str = "default",
        metadata: Optional[Dict] = None
    ) -> None:
        """记录性能指标

        Args:
            name: 指标名称
            value: 指标值
            unit: 单位（如"ms", "MB", "count"）
            category: 类别
            metadata: 附加元数据

        Example:
            >>> monitor.record_metric("capture_time", 125.5, "ms", "capture")
            >>> monitor.record_metric("memory_usage", 256.3, "MB", "memory")
        """
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=time.time(),
            metadata=metadata or {}
        )

        with self._metrics_lock:
            # 获取或创建类别的deque
            if category not in self._metrics:
                self._metrics[category] = deque(maxlen=self._max_history)

            # 添加指标
            self._metrics[category].append(metric)
            self._stats['total_metrics'] += 1

        logger.debug(f"记录性能指标: {category}.{name} = {value}{unit}")

    def start_timer(self, name: str) -> str:
        """开始计时

        Args:
            name: 计时器名称

        Returns:
            计时器ID

        Example:
            >>> timer_id = monitor.start_timer("ocr_recognition")
            >>> # 执行操作
            >>> monitor.end_timer(timer_id)
        """
        timer_id = f"{name}_{time.time()}"
        self._timers[timer_id] = time.time()
        return timer_id

    def end_timer(
        self,
        timer_id: str,
        category: str = "timing",
        record: bool = True
    ) -> float:
        """结束计时

        Args:
            timer_id: 计时器ID
            category: 类别
            record: 是否记录指标

        Returns:
            耗时（秒）

        Example:
            >>> timer_id = monitor.start_timer("ocr_recognition")
            >>> # 执行操作
            >>> elapsed = monitor.end_timer(timer_id)
            >>> print(f"耗时: {elapsed:.3f}秒")
        """
        if timer_id not in self._timers:
            logger.warning(f"计时器不存在: {timer_id}")
            return 0.0

        start_time = self._timers.pop(timer_id)
        elapsed = time.time() - start_time

        if record:
            name = timer_id.rsplit('_', 1)[0]
            self.record_metric(
                name=f"{name}_duration",
                value=elapsed * 1000,  # 转换为毫秒
                unit="ms",
                category=category
            )

        return elapsed

    def get_metrics(
        self,
        category: str,
        name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[PerformanceMetric]:
        """获取性能指标

        Args:
            category: 类别
            name: 指标名称（None表示所有）
            limit: 最大返回数量（None表示全部）

        Returns:
            指标列表

        Example:
            >>> # 获取所有capture类别指标
            >>> metrics = monitor.get_metrics("capture")
            >>>
            >>> # 获取特定指标
            >>> metrics = monitor.get_metrics("capture", "capture_time")
            >>>
            >>> # 获取最近10个指标
            >>> metrics = monitor.get_metrics("capture", limit=10)
        """
        with self._metrics_lock:
            if category not in self._metrics:
                return []

            metrics_list = list(self._metrics[category])

            # 按名称过滤
            if name is not None:
                metrics_list = [m for m in metrics_list if m.name == name]

            # 按时间排序（最新的在前）
            metrics_list.sort(key=lambda m: m.timestamp, reverse=True)

            # 限制数量
            if limit is not None:
                metrics_list = metrics_list[:limit]

            return metrics_list

    def get_stats(
        self,
        category: str,
        name: Optional[str] = None
    ) -> Dict:
        """获取统计信息

        Args:
            category: 类别
            name: 指标名称（None表示所有）

        Returns:
            统计信息字典

        Returns:
            {
                'count': 数量,
                'min': 最小值,
                'max': 最大值,
                'avg': 平均值,
                'p50': 中位数,
                'p95': 95分位数,
                'p99': 99分位数
            }

        Example:
            >>> stats = monitor.get_stats("capture", "capture_time")
            >>> print(f"平均耗时: {stats['avg']:.2f}ms")
            >>> print(f"P95: {stats['p95']:.2f}ms")
        """
        metrics = self.get_metrics(category, name)

        if not metrics:
            return {
                'count': 0,
                'min': 0,
                'max': 0,
                'avg': 0,
                'p50': 0,
                'p95': 0,
                'p99': 0
            }

        values = [m.value for m in metrics]
        count = len(values)

        # 计算统计值
        stats = {
            'count': count,
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / count,
            'p50': self._percentile(values, 50),
            'p95': self._percentile(values, 95),
            'p99': self._percentile(values, 99)
        }

        return stats

    @staticmethod
    def _percentile(values: List[float], p: int) -> float:
        """计算百分位数

        Args:
            values: 值列表
            p: 百分位数（0-100）

        Returns:
            百分位数值
        """
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = (p / 100) * (len(sorted_values) - 1)
        return sorted_values[int(index)]

    def cleanup_old_metrics(
        self,
        max_age_seconds: float = 3600.0
    ) -> int:
        """清理旧的性能指标

        Args:
            max_age_seconds: 最大保留时间（秒）

        Returns:
            清理的指标数
        """
        with self._metrics_lock:
            current_time = time.time()
            total_cleaned = 0

            for category in list(self._metrics.keys()):
                metrics = self._metrics[category]
                # 移除旧指标
                new_metrics = deque([
                    m for m in metrics
                    if current_time - m.timestamp <= max_age_seconds
                ], maxlen=self._max_history)

                cleaned_count = len(metrics) - len(new_metrics)
                total_cleaned += cleaned_count

                if cleaned_count > 0:
                    self._metrics[category] = new_metrics
                    logger.debug(f"清理类别 '{category}' 的 {cleaned_count} 个旧指标")

            return total_cleaned

    def clear_category(self, category: str) -> None:
        """清空类别的所有指标

        Args:
            category: 类别名称
        """
        with self._metrics_lock:
            if category in self._metrics:
                count = len(self._metrics[category])
                del self._metrics[category]
                logger.debug(f"清空类别 '{category}' 的 {count} 个指标")

    def clear_all(self) -> None:
        """清空所有指标"""
        with self._metrics_lock:
            total_count = sum(len(v) for v in self._metrics.values())
            self._metrics.clear()
            self._timers.clear()
            logger.info(f"清空所有指标，共 {total_count} 个")

    def get_summary(self) -> Dict:
        """获取所有类别的摘要

        Returns:
            摘要字典

        Example:
            >>> summary = monitor.get_summary()
            >>> for category, info in summary.items():
            >>>     print(f"{category}: {info['count']} 个指标")
        """
        with self._metrics_lock:
            summary = {}
            for category, metrics in self._metrics.items():
                if metrics:
                    summary[category] = {
                        'count': len(metrics),
                        'latest': metrics[-1].timestamp if metrics else 0,
                        'oldest': metrics[0].timestamp if metrics else 0
                    }
            return summary


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器实例（便捷函数）

    Returns:
        PerformanceMonitor 实例
    """
    return PerformanceMonitor.get_instance()


def monitor_performance(
    name: str,
    category: str = "default"
):
    """性能监控装饰器

    Args:
        name: 操作名称
        category: 类别

    Example:
        >>> @monitor_performance("ocr_recognition", "ocr")
        >>> def recognize_image(image):
        >>>     # OCR识别逻辑
        >>>     return result
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            timer_id = monitor.start_timer(name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = monitor.end_timer(timer_id, category=category)
                logger.debug(f"{name} 耗时: {elapsed * 1000:.2f}ms")
        return wrapper
    return decorator


def record_counter(name: str, value: int = 1, category: str = "counter") -> None:
    """记录计数器指标（便捷函数）

    Args:
        name: 计数器名称
        value: 增加的值
        category: 类别

    Example:
        >>> record_counter("capture_success")
        >>> record_counter("capture_failed", category="errors")
    """
    monitor = get_performance_monitor()
    current = monitor.get_metrics(category, name)
    count = current[0].value if current else 0
    monitor.record_metric(name, count + value, "count", category)


def time_operation(name: str):
    """操作计时上下文管理器

    Args:
        name: 操作名称

    Example:
        >>> with time_operation("screenshot_capture"):
        >>>     result = capture_screenshot()
        >>> # 自动记录耗时
    """
    class TimerContext:
        def __init__(self, name, category):
            self.name = name
            self.category = category
            self.timer_id = None
            self.monitor = get_performance_monitor()

        def __enter__(self):
            self.timer_id = self.monitor.start_timer(self.name)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.monitor.end_timer(self.timer_id, self.category)

    return TimerContext(name, "timing")
