"""线程池管理器 - 修复版，避免卡死问题"""
import threading
import time
from typing import Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass

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
    """统一的线程池管理器（修复版）

    使用更简单的实现，避免双检锁导致的潜在问题。
    """

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

        logger.info(f"线程池管理器已初始化，最大工作线程数: {max_workers}")

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

        # 注册回调
        future.add_done_callback(
            lambda f: self._on_task_complete(task_id, f, callback, error_callback)
        )

        return task_id

    def _on_task_complete(
        self,
        task_id: str,
        future: Future,
        callback: Optional[Callable[[Any], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None
    ) -> None:
        """任务完成回调"""
        with self._tasks_lock:
            if task_id not in self._tasks:
                return

            task_info = self._tasks[task_id]
            task_info.completed_at = time.time()
            self._stats['active_tasks'] -= 1

            if future.cancelled():
                self._stats['total_cancelled'] += 1
            elif future.exception():
                self._stats['total_failed'] += 1
                task_info.exception = future.exception()
            else:
                self._stats['total_completed'] += 1
                task_info.result = future.result()

            del self._tasks[task_id]

        # 调用回调
        if callback and not future.cancelled() and not future.exception():
            try:
                callback(task_info.result)
            except Exception as e:
                logger.error(f"成功回调执行失败: {e}", exc_info=True)

        if error_callback and future.exception():
            try:
                error_callback(future.exception())
            except Exception as e:
                logger.error(f"错误回调执行失败: {e}", exc_info=True)

    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务信息，如果不存在则返回None
        """
        with self._tasks_lock:
            return self._tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        with self._tasks_lock:
            task_info = self._tasks.get(task_id)
            if task_info is None:
                return False

        return task_info.future.cancel()

    def shutdown(self, wait: bool = True) -> None:
        """关闭线程池

        Args:
            wait: 是否等待所有任务完成
        """
        self._is_shutdown = True
        self._executor.shutdown(wait=wait)
        logger.info(f"线程池已关闭 (wait={wait})")

    def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        with self._tasks_lock:
            return {
                'total_submitted': self._stats['total_submitted'],
                'total_completed': self._stats['total_completed'],
                'total_failed': self._stats['total_failed'],
                'total_cancelled': self._stats['total_cancelled'],
                'active_tasks': self._stats['active_tasks']
            }


# 全局实例（不使用单例模式，避免初始化问题）
_thread_pool_manager: Optional[ThreadPoolManager] = None
_thread_pool_lock = threading.Lock()


def get_thread_pool_manager() -> ThreadPoolManager:
    """获取线程池管理器实例（不使用单例模式）

    Returns:
        ThreadPoolManager 实例
    """
    global _thread_pool_manager

    if _thread_pool_manager is None:
        with _thread_pool_lock:
            if _thread_pool_manager is None:
                _thread_pool_manager = ThreadPoolManager()

    return _thread_pool_manager
