"""窗口缓存服务 - 缓存窗口信息以减少Win32 API调用"""
import time
import win32gui
import win32process
from typing import Optional, Tuple
from dataclasses import dataclass

from core.logger import get_logger
from core.cache_manager import LRUCache

logger = get_logger(__name__)


@dataclass
class WindowInfo:
    """窗口信息"""
    hwnd: int  # 窗口句柄
    title: str  # 窗口标题
    class_name: str  # 窗口类名
    client_rect: tuple[int, int, int, int]  # 客户区域 (x, y, w, h)
    window_rect: tuple[int, int, int, int]  # 窗口区域 (x, y, w, h)
    is_visible: bool  # 是否可见
    is_minimized: bool  # 是否最小化
    process_id: int  # 进程ID
    thread_id: int  # 线程ID
    timestamp: float  # 缓存时间戳


class WindowCacheService:
    """窗口缓存服务

    通过缓存窗口信息来减少Win32 API调用，提高性能。
    适用于频繁查询同一窗口信息的场景。
    """

    def __init__(
        self,
        cache_ttl_seconds: int = 2,
        enable_cache: bool = True,
        max_cache_size: int = 50
    ):
        """初始化窗口缓存服务

        Args:
            cache_ttl_seconds: 缓存过期时间（秒），默认2秒
            enable_cache: 是否启用缓存，默认True
            max_cache_size: 最大缓存条目数
        """
        self._cache_ttl = cache_ttl_seconds
        self._enable_cache = enable_cache
        self._max_cache_size = max_cache_size

        # 使用LRUCache替代普通字典
        self._window_cache = LRUCache(
            max_size=max_cache_size,
            default_ttl=cache_ttl_seconds,
            auto_cleanup=True
        )

        # 窗口句柄缓存（按窗口名）
        self._hwnd_by_name_cache = LRUCache(
            max_size=20,
            default_ttl=cache_ttl_seconds,
            auto_cleanup=True
        )

        # 统计信息
        self._stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls': 0
        }

    def get_window_info(self, hwnd: int, force_refresh: bool = False) -> Optional[WindowInfo]:
        """获取窗口信息（带缓存）

        Args:
            hwnd: 窗口句柄
            force_refresh: 是否强制刷新，忽略缓存

        Returns:
            窗口信息，如果获取失败则返回None
        """
        self._stats['total_queries'] += 1

        # 检查缓存
        if self._enable_cache and not force_refresh:
            cached_info = self._window_cache.get(hwnd)
            if cached_info:
                self._stats['cache_hits'] += 1
                return cached_info

        # 缓存未命中，查询API
        self._stats['cache_misses'] += 1
        self._stats['api_calls'] += 1

        window_info = self._query_window_info(hwnd)
        if window_info:
            self._window_cache.set(hwnd, window_info)

        return window_info

    def get_hwnd_by_title(
        self,
        title: str,
        force_refresh: bool = False,
        partial_match: bool = True
    ) -> Optional[int]:
        """根据窗口标题获取窗口句柄（带缓存）

        Args:
            title: 窗口标题（部分匹配）
            force_refresh: 是否强制刷新，忽略缓存
            partial_match: 是否部分匹配标题

        Returns:
            窗口句柄，如果未找到则返回None
        """
        self._stats['total_queries'] += 1

        # 检查缓存
        if self._enable_cache and not force_refresh and not partial_match:
            cached_hwnd = self._hwnd_by_name_cache.get(title)
            if cached_hwnd:
                self._stats['cache_hits'] += 1
                # 验证窗口是否仍然有效
                if win32gui.IsWindow(cached_hwnd):
                    return cached_hwnd

        # 缓存未命中或部分匹配，查询API
        self._stats['cache_misses'] += 1
        self._stats['api_calls'] += 1

        hwnd = None
        if partial_match:
            hwnd = self._find_window_by_partial_title(title)
        else:
            try:
                hwnd = win32gui.FindWindow(None, title)
            except Exception as e:
                logger.warning(f"查找窗口失败: {e}")

        if hwnd and not partial_match:
            self._hwnd_by_name_cache.set(title, hwnd)

        return hwnd

    def _find_window_by_partial_title(self, partial_title: str) -> Optional[int]:
        """通过部分标题查找窗口

        Args:
            partial_title: 部分窗口标题

        Returns:
            窗口句柄，如果未找到则返回None
        """
        def callback(hwnd, result):
            title = win32gui.GetWindowText(hwnd)
            if partial_title.lower() in title.lower() and win32gui.IsWindowVisible(hwnd):
                result.append(hwnd)
            return True

        result = []
        try:
            win32gui.EnumWindows(callback, result)
        except Exception as e:
            logger.warning(f"枚举窗口失败: {e}")

        return result[0] if result else None

    def get_client_rect(self, hwnd: int, force_refresh: bool = False) -> Optional[Tuple[int, int, int, int]]:
        """获取窗口客户区域（带缓存）

        Args:
            hwnd: 窗口句柄
            force_refresh: 是否强制刷新，忽略缓存

        Returns:
            客户区域 (x, y, w, h)，如果获取失败则返回None
        """
        window_info = self.get_window_info(hwnd, force_refresh)
        if window_info:
            return window_info.client_rect
        return None

    def get_window_rect(self, hwnd: int, force_refresh: bool = False) -> Optional[Tuple[int, int, int, int]]:
        """获取窗口区域（带缓存）

        Args:
            hwnd: 窗口句柄
            force_refresh: 是否强制刷新，忽略缓存

        Returns:
            窗口区域 (x, y, w, h)，如果获取失败则返回None
        """
        window_info = self.get_window_info(hwnd, force_refresh)
        if window_info:
            return window_info.window_rect
        return None

    def is_window_visible(self, hwnd: int, force_refresh: bool = False) -> bool:
        """检查窗口是否可见（带缓存）

        Args:
            hwnd: 窗口句柄
            force_refresh: 是否强制刷新，忽略缓存

        Returns:
            是否可见
        """
        window_info = self.get_window_info(hwnd, force_refresh)
        if window_info:
            return window_info.is_visible
        return False

    def is_window_minimized(self, hwnd: int, force_refresh: bool = False) -> bool:
        """检查窗口是否最小化（带缓存）

        Args:
            hwnd: 窗口句柄
            force_refresh: 是否强制刷新，忽略缓存

        Returns:
            是否最小化
        """
        window_info = self.get_window_info(hwnd, force_refresh)
        if window_info:
            return window_info.is_minimized
        return False

    def get_window_title(self, hwnd: int, force_refresh: bool = False) -> Optional[str]:
        """获取窗口标题（带缓存）

        Args:
            hwnd: 窗口句柄
            force_refresh: 是否强制刷新，忽略缓存

        Returns:
            窗口标题，如果获取失败则返回None
        """
        window_info = self.get_window_info(hwnd, force_refresh)
        if window_info:
            return window_info.title
        return None

    def _query_window_info(self, hwnd: int) -> Optional[WindowInfo]:
        """查询窗口信息

        Args:
            hwnd: 窗口句柄

        Returns:
            窗口信息，如果获取失败则返回None
        """
        try:
            # 获取窗口标题
            title = win32gui.GetWindowText(hwnd)

            # 获取窗口类名
            class_name = win32gui.GetClassName(hwnd)

            # 获取客户区域
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            x, y = win32gui.ClientToScreen(hwnd, (0, 0))
            w = right - left
            h = bottom - top
            client_rect = (x, y, w, h)

            # 获取窗口区域
            rect = win32gui.GetWindowRect(hwnd)
            window_rect = (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])

            # 检查窗口状态
            is_visible = win32gui.IsWindowVisible(hwnd)
            is_minimized = win32gui.IsIconic(hwnd)

            # 获取进程和线程ID
            _, process_id = win32process.GetWindowThreadProcessId(hwnd)
            thread_id = win32process.GetWindowThreadProcessId(hwnd)[0]

            return WindowInfo(
                hwnd=hwnd,
                title=title,
                class_name=class_name,
                client_rect=client_rect,
                window_rect=window_rect,
                is_visible=is_visible,
                is_minimized=is_minimized,
                process_id=process_id,
                thread_id=thread_id,
                timestamp=time.time()
            )

        except Exception as e:
            logger.error(f"查询窗口信息失败: hwnd={hwnd}, error={e}")
            return None

    def clear_cache(self, clear_hwnd_cache: bool = True, clear_name_cache: bool = True) -> None:
        """清理缓存

        Args:
            clear_hwnd_cache: 是否清理窗口信息缓存
            clear_name_cache: 是否清理窗口名缓存
        """
        if clear_hwnd_cache:
            self._window_cache.clear()
            logger.info("窗口信息缓存已清理")

        if clear_name_cache:
            self._hwnd_by_name_cache.clear()
            logger.info("窗口名缓存已清理")

    def invalidate_cache(self, hwnd: Optional[int] = None) -> None:
        """使缓存失效

        Args:
            hwnd: 指定窗口句柄，如果为None则清理所有缓存
        """
        if hwnd is not None:
            if hwnd in self._window_cache:
                del self._window_cache[hwnd]
                # logger.debug(f"窗口缓存已失效: hwnd={hwnd}")

            # 同时清理名称缓存中指向该句柄的条目
            # (LRUCache会自动清理，这里不需要额外处理)
        else:
            self.clear_cache()

    def get_stats(self) -> dict:
        """获取缓存统计信息

        Returns:
            统计信息字典
        """
        total_cache_queries = self._stats['cache_hits'] + self._stats['cache_misses']
        hit_rate = (
            self._stats['cache_hits'] / total_cache_queries * 100
            if total_cache_queries > 0 else 0.0
        )

        return {
            **self._stats,
            'window_cache_size': self._window_cache.get_size(),
            'name_cache_size': self._hwnd_by_name_cache.get_size(),
            'cache_hit_rate': f"{hit_rate:.2f}%"
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls': 0
        }

    def enable_cache(self) -> None:
        """启用缓存"""
        self._enable_cache = True
        logger.info("窗口缓存已启用")

    def disable_cache(self) -> None:
        """禁用缓存"""
        self._enable_cache = False
        logger.info("窗口缓存已禁用")
