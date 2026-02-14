"""资源管理器 - 统一管理各种系统资源"""
import gc
import threading
import time
from typing import TypeVar, Generic, Optional, ContextManager
from contextlib import contextmanager

from PIL import Image
from core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class ResourceManager:
    """资源管理器

    统一管理图像、文件等系统资源，确保正确释放。
    提供上下文管理器和自动清理机制。
    """

    _instance: Optional['ResourceManager'] = None
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
        auto_gc: bool = True,
        gc_interval: float = 30.0
    ):
        """初始化资源管理器

        Args:
            auto_gc: 是否自动触发垃圾回收
            gc_interval: 垃圾回收间隔（秒）
        """
        if self._initialized:
            return

        self._auto_gc = auto_gc
        self._gc_interval = gc_interval
        self._last_gc_time = time.time()

        # 资源追踪
        self._resources: dict[str, any] = {}
        self._resources_lock = threading.Lock()

        # 统计信息
        self._stats = {
            'total_acquired': 0,
            'total_released': 0,
            'gc_triggered': 0,
            'active_resources': 0
        }

        self._initialized = True
        logger.info("资源管理器已初始化")

    @classmethod
    def get_instance(cls) -> 'ResourceManager':
        """获取资源管理器单例

        Returns:
            ResourceManager 实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def acquire_image(
        self,
        image_path: str,
        resource_id: Optional[str] = None
    ) -> Optional[Image.Image]:
        """获取图像资源

        Args:
            image_path: 图像路径
            resource_id: 资源ID（如果为None，自动生成）

        Returns:
            PIL Image 对象，如果加载失败则返回None
        """
        if resource_id is None:
            resource_id = f"image_{image_path}_{time.time()}"

        try:
            img = Image.open(image_path)

            with self._resources_lock:
                self._resources[resource_id] = {
                    'type': 'image',
                    'resource': img,
                    'path': image_path,
                    'acquired_at': time.time()
                }
                self._stats['total_acquired'] += 1
                self._stats['active_resources'] = len(self._resources)

            logger.debug(f"图像资源已获取 [resource_id={resource_id}]: {image_path}")
            return img

        except Exception as e:
            logger.error(f"加载图像失败 [path={image_path}]: {e}")
            return None

    def release_image(
        self,
        image: Image.Image,
        resource_id: Optional[str] = None
    ) -> bool:
        """释放图像资源

        Args:
            image: PIL Image 对象
            resource_id: 资源ID

        Returns:
            是否成功释放
        """
        try:
            # 关闭图像
            image.close()

            # 从追踪中移除
            if resource_id:
                with self._resources_lock:
                    if resource_id in self._resources:
                        del self._resources[resource_id]
                        self._stats['total_released'] += 1
                        self._stats['active_resources'] = len(self._resources)

            logger.debug(f"图像资源已释放 [resource_id={resource_id}]")

            # 触发垃圾回收（如果启用）
            if self._auto_gc:
                self._maybe_trigger_gc()

            return True

        except Exception as e:
            logger.error(f"释放图像资源失败 [resource_id={resource_id}]: {e}")
            return False

    def release_resource(self, resource_id: str) -> bool:
        """释放资源

        Args:
            resource_id: 资源ID

        Returns:
            是否成功释放
        """
        with self._resources_lock:
            if resource_id not in self._resources:
                return False

            resource_info = self._resources[resource_id]

        # 根据类型释放
        if resource_info['type'] == 'image':
            self.release_image(resource_info['resource'], resource_id)
            return True
        else:
            logger.warning(f"未知的资源类型 [resource_id={resource_id}]: {resource_info['type']}")
            return False

    def release_all_resources(self) -> int:
        """释放所有资源

        Returns:
            释放的资源数
        """
        with self._resources_lock:
            resource_ids = list(self._resources.keys())

        released_count = 0
        for resource_id in resource_ids:
            if self.release_resource(resource_id):
                released_count += 1

        logger.info(f"已释放 {released_count} 个资源")

        # 强制触发垃圾回收
        gc.collect()
        self._stats['gc_triggered'] += 1

        return released_count

    def _maybe_trigger_gc(self) -> None:
        """可能触发垃圾回收"""
        current_time = time.time()
        if current_time - self._last_gc_time >= self._gc_interval:
            gc.collect()
            self._last_gc_time = current_time
            self._stats['gc_triggered'] += 1
            logger.debug("已触发垃圾回收")

    def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        with self._resources_lock:
            return {
                **self._stats,
                'memory_stats': self._get_memory_stats()
            }

    def _get_memory_stats(self) -> dict:
        """获取内存统计信息"""
        import sys
        import psutil

        try:
            process = psutil.Process()
            return {
                'rss': process.memory_info().rss // 1024 // 1024,  # MB
                'vms': process.memory_info().vms // 1024 // 1024,  # MB
                'gc_objects': len(gc.get_objects()),
                'gc_collections': gc.get_stats()
            }
        except Exception as e:
            logger.warning(f"获取内存统计失败: {e}")
            return {}

    def reset_stats(self) -> None:
        """重置统计信息"""
        with self._resources_lock:
            self._stats = {
                'total_acquired': 0,
                'total_released': 0,
                'gc_triggered': 0,
                'active_resources': len(self._resources)
            }

    def cleanup_old_resources(self, max_age_seconds: float = 300.0) -> int:
        """清理旧的资源记录

        Args:
            max_age_seconds: 最大保留时间（秒）

        Returns:
            清理的资源数
        """
        with self._resources_lock:
            current_time = time.time()
            old_resource_ids = []

            for resource_id, resource_info in self._resources.items():
                age = current_time - resource_info['acquired_at']
                if age > max_age_seconds:
                    old_resource_ids.append(resource_id)

        released_count = 0
        for resource_id in old_resource_ids:
            if self.release_resource(resource_id):
                released_count += 1

        if released_count > 0:
            logger.info(f"清理了 {released_count} 个旧资源记录")

        return released_count


@contextmanager
def managed_image(image_path: str):
    """图像资源上下文管理器

    Args:
        image_path: 图像路径

    Yields:
        PIL Image 对象

    Example:
        with managed_image("screenshot.png") as img:
            # 使用图像
            cropped = img.crop((0, 0, 100, 100))
        # 图像自动释放
    """
    manager = ResourceManager.get_instance()
    resource_id = f"managed_{image_path}_{time.time()}"

    img = manager.acquire_image(image_path, resource_id)
    if img is None:
        raise RuntimeError(f"无法加载图像: {image_path}")

    try:
        yield img
    finally:
        manager.release_image(img, resource_id)


def get_resource_manager() -> ResourceManager:
    """获取资源管理器实例（便捷函数）

    Returns:
        ResourceManager 实例
    """
    return ResourceManager.get_instance()


def cleanup_all_resources() -> int:
    """清理所有资源（便捷函数）

    Returns:
        释放的资源数
    """
    manager = get_resource_manager()
    return manager.release_all_resources()
