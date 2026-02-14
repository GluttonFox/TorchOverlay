"""线程池管理器 - 统一管理所有异步任务"""
import threading
import time
from typing import Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    future: Future
    submitted_at: float
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    exception: Optional[Exception] = None


class ThreadPoolManager:
    """统一的线程池管理器

    管理应用中所有的异步任务，提供统一的接口。
    """

    _instance: Optional['ThreadPoolManager'] = None
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
        max_workers: int = 4,
        task_timeout: float = 300.0
    ):
        """初始化线程池管理器

        Args:
            max_workers: 最大工作线程数
            task_timeout: 默认任务超时时间（秒）
        """
        if self._initialized:
            return

        self._max_workers = max_workers
        self._task_timeout = task_timeout

        # 创建线程池
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="TorchWorker"
        )

        # 任务追踪
        self._tasks: dict[str, TaskInfo] = {}
        self._tasks_lock = threading.Lock()

        # 统计信息
        self._stats = {
            'total_submitted': 0,
            'total_completed': 0,
            'total_failed': 0,
            'total_cancelled': 0,
            'active_tasks': 0
        }

        # 关闭标志
        self._is_shutdown = False

        self._initialized = True
        logger.info(f"线程池管理器已初始化，最大工作线程数: {max_workers}")

    @classmethod
    def get_instance(cls) -> 'ThreadPoolManager':
        """获取线程池管理器单例

        Returns:
            ThreadPoolManager 实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def submit_task(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        timeout: Optional[float] = None,
        callback: Optional[Callable[[Any], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
        **kwargs
    ) -> str:
        """提交任务到线程池

        Args:
            func: 要执行的函数
            *args: 函数位置参数
            task_id: 任务ID（如果为None，自动生成）
            timeout: 超时时间（秒），None使用默认值
            callback: 成功回调
            error_callback: 失败回调
            **kwargs: 函数关键字参数

        Returns:
            任务ID
        """
        if self._is_shutdown:
            raise RuntimeError("线程池已关闭，无法提交新任务")

        # 生成任务ID
        if task_id is None:
            task_id = f"task_{time.time()}_{id(func)}"

        # 创建任务包装器
        def task_wrapper():
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"任务执行失败 [task_id={task_id}]: {e}", exc_info=True)
                raise

        # 提交任务
        future = self._executor.submit(task_wrapper)

        # 追踪任务
        task_info = TaskInfo(
            task_id=task_id,
            future=future,
            submitted_at=time.time()
        )

        with self._tasks_lock:
            self._tasks[task_id] = task_info
            self._stats['total_submitted'] += 1
            self._stats['active_tasks'] = len(self._tasks)

        # 添加回调
        def on_complete(f: Future):
            with self._tasks_lock:
                if task_id in self._tasks:
                    task_info = self._tasks[task_id]
                    task_info.completed_at = time.time()

            try:
                result = f.result(timeout=timeout if timeout else self._task_timeout)
                task_info.result = result

                self._stats['total_completed'] += 1
                self._stats['active_tasks'] -= 1

                logger.debug(f"任务完成 [task_id={task_id}]: 耗时 {task_info.completed_at - task_info.submitted_at:.2f}s")

                if callback:
                    try:
                        callback(result)
                    except Exception as e:
                        logger.error(f"任务回调执行失败 [task_id={task_id}]: {e}", exc_info=True)

            except Exception as e:
                task_info.exception = e

                self._stats['total_failed'] += 1
                self._stats['active_tasks'] -= 1

                logger.error(f"任务异常 [task_id={task_id}]: {e}")

                if error_callback:
                    try:
                        error_callback(e)
                    except Exception as callback_e:
                        logger.error(f"错误回调执行失败 [task_id={task_id}]: {callback_e}")

        future.add_done_callback(on_complete)

        return task_id

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态字典，如果任务不存在则返回None
        """
        with self._tasks_lock:
            if task_id not in self._tasks:
                return None

            task_info = self._tasks[task_id]

            return {
                'task_id': task_id,
                'status': self._get_future_status(task_info.future),
                'submitted_at': task_info.submitted_at,
                'completed_at': task_info.completed_at,
                'elapsed': time.time() - task_info.submitted_time,
                'result': task_info.result,
                'exception': str(task_info.exception) if task_info.exception else None
            }

    def cancel_task(self, task_id: str) -> bool:
        """取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        with self._tasks_lock:
            if task_id not in self._tasks:
                return False

            task_info = self._tasks[task_id]

        cancelled = task_info.future.cancel()

        if cancelled:
            with self._tasks_lock:
                if task_id in self._tasks:
                    del self._tasks[task_id]
                    self._stats['total_cancelled'] += 1
                    self._stats['active_tasks'] -= 1

            logger.info(f"任务已取消 [task_id={task_id}]")

        return cancelled

    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """等待任务完成

        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）

        Returns:
            任务结果

        Raises:
            TimeoutError: 超时
            Exception: 任务执行异常
        """
        with self._tasks_lock:
            if task_id not in self._tasks:
                raise ValueError(f"任务不存在: {task_id}")

            task_info = self._tasks[task_id]

        return task_info.future.result(timeout=timeout if timeout else self._task_timeout)

    def cleanup_completed_tasks(self, max_age_seconds: float = 300.0) -> int:
        """清理已完成的任务记录

        Args:
            max_age_seconds: 最大保留时间（秒）

        Returns:
            清理的任务数
        """
        with self._tasks_lock:
            current_time = time.time()
            completed_task_ids = []

            for task_id, task_info in self._tasks.items():
                if task_info.future.done():
                    # 任务已完成
                    age = current_time - (task_info.completed_at or task_info.submitted_at)
                    if age > max_age_seconds:
                        completed_task_ids.append(task_id)

            for task_id in completed_task_ids:
                del self._tasks[task_id]

            if completed_task_ids:
                logger.debug(f"清理了 {len(completed_task_ids)} 个已完成任务记录")

            return len(completed_task_ids)

    def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        with self._tasks_lock:
            return {
                **self._stats,
                'pending_tasks': self._stats['active_tasks'],
                'max_workers': self._max_workers,
                'success_rate': (
                    self._stats['total_completed'] / self._stats['total_submitted'] * 100
                    if self._stats['total_submitted'] > 0 else 0.0
                )
            }

    def reset_stats(self) -> None:
        """重置统计信息"""
        with self._tasks_lock:
            self._stats = {
                'total_submitted': 0,
                'total_completed': 0,
                'total_failed': 0,
                'total_cancelled': 0,
                'active_tasks': len(self._tasks)
            }

    def shutdown(self, wait: bool = True, timeout: float = 5.0) -> None:
        """关闭线程池

        Args:
            wait: 是否等待所有任务完成
            timeout: 等待超时时间（秒）
        """
        if self._is_shutdown:
            return

        logger.info("正在关闭线程池管理器...")

        self._is_shutdown = True

        # 等待所有任务完成
        if wait:
            with self._tasks_lock:
                active_count = len(self._tasks)

            if active_count > 0:
                logger.info(f"等待 {active_count} 个活动任务完成...")

            self._executor.shutdown(wait=True, timeout=timeout)
        else:
            self._executor.shutdown(wait=False)

        # 清理任务记录
        with self._tasks_lock:
            self._tasks.clear()
            self._stats['active_tasks'] = 0

        logger.info("线程池管理器已关闭")

    def _get_future_status(self, future: Future) -> str:
        """获取Future状态

        Args:
            future: Future对象

        Returns:
            状态字符串
        """
        if future.cancelled():
            return "cancelled"
        elif future.done():
            if future.exception():
                return "failed"
            else:
                return "completed"
        else:
            return "running"


def get_thread_pool() -> ThreadPoolManager:
    """获取线程池管理器实例（便捷函数）

    Returns:
        ThreadPoolManager 实例
    """
    return ThreadPoolManager.get_instance()


def submit_to_pool(
    func: Callable,
    *args,
    task_id: Optional[str] = None,
    timeout: Optional[float] = None,
    callback: Optional[Callable[[Any], None]] = None,
    error_callback: Optional[Callable[[Exception], None]] = None,
    **kwargs
) -> str:
    """提交任务到线程池（便捷函数）

    Args:
        func: 要执行的函数
        *args: 函数位置参数
        task_id: 任务ID
        timeout: 超时时间
        callback: 成功回调
        error_callback: 失败回调
        **kwargs: 函数关键字参数

    Returns:
        任务ID
    """
    pool = get_thread_pool()
    return pool.submit_task(
        func, *args,
        task_id=task_id,
        timeout=timeout,
        callback=callback,
        error_callback=error_callback,
        **kwargs
    )
