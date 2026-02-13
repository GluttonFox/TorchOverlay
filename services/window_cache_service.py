"""窗口缓存服务 - 缓存窗口信息以减少Win32 API调用"""
import time
import win32gui
import win32process
from typing import Optional, Tuple
from dataclasses import dataclass

from core.logger import get_logger

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
        enable_cache: bool = True
    ):
        """初始化窗口缓存服务

        Args:
            cache_ttl_seconds: 缓存过期时间（秒），默认2秒
            enable_cache: 是否启用缓存，默认True
        """
        self._cache_ttl = cache_ttl_seconds
        self._enable_cache = enable_cache

        # 窗口信息缓存
        self._window_cache: dict[int, WindowInfo] = {}

        # 窗口句柄缓存（按窗口名）
        self._hwnd_by_name: dict[str, int] = {}

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
            if self._check_cache(hwnd):
                self._stats['cache_hits'] += 1
                logger.debug(f"窗口信息缓存命中: hwnd={hwnd}")
                return self._window_cache[hwnd]

        # 缓存未命中，查询API
        self._stats['cache_misses'] += 1
        self._stats['api_calls'] += 1

        window_info = self._query_window_info(hwnd)
        if window_info:
            self._add_to_cache(hwnd, window_info)
            logger.debug(f"窗口信息已缓存: hwnd={hwnd}, title={window_info.title[:20]}")

        return window_info

    def get_hwnd_by_title(self, title: str, force_refresh: bool = False) -> Optional[int]:
        """根据窗口标题获取窗口句柄（带缓存）

        Args:
            title: 窗口标题（部分匹配）
            force_refresh: 是否强制刷新，忽略缓存

        Returns:
            窗口句柄，如果未找到则返回None
        """
        self._stats['total_queries'] += 1

        # 检查缓存
        if self._enable_cache and not force_refresh:
            if title in self._hwnd_by_name:
                self._stats['cache_hits'] += 1
                cached_hwnd = self._hwnd_by_name[title]

                # 验证窗口是否仍然存在
                if win32gui.IsWindow(cached_hwnd):
                    logger.debug(f"窗口句柄缓存命中: title={title}, hwnd={cached_hwnd}")
                    return cached_hwnd
                else:
                    # 窗口已不存在，移除缓存
                    del self._hwnd_by_name[title]

        # 缓存未命中，查询API
        self._stats['cache_misses'] += 1
        self._stats['api_calls'] += 1

        hwnd = self._find_window_by_title(title)
        if hwnd:
            self._hwnd_by_name[title] = hwnd
            logger.debug(f"窗口句柄已缓存: title={title}, hwnd={hwnd}")

        return hwnd

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

    def _check_cache(self, hwnd: int) -> bool:
        """检查缓存是否有效

        Args:
            hwnd: 窗口句柄

        Returns:
            是否命中有效缓存
        """
        if hwnd not in self._window_cache:
            return False

        # 检查是否过期
        window_info = self._window_cache[hwnd]
        if time.time() - window_info.timestamp > self._cache_ttl:
            del self._window_cache[hwnd]
            logger.debug(f"窗口信息缓存已过期: hwnd={hwnd}")
            return False

        # 检查窗口是否仍然存在
        if not win32gui.IsWindow(hwnd):
            del self._window_cache[hwnd]
            logger.debug(f"窗口已不存在，移除缓存: hwnd={hwnd}")
            return False

        return True

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

    def _find_window_by_title(self, title: str) -> Optional[int]:
        """根据窗口标题查找窗口句柄

        Args:
            title: 窗口标题（部分匹配）

        Returns:
            窗口句柄，如果未找到则返回None
        """
        result_hwnd = None

        def enum_callback(hwnd, _):
            """枚举窗口回调函数"""
            nonlocal result_hwnd

            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title in window_title:
                    result_hwnd = hwnd
                    return False  # 停止枚举
            return True  # 继续枚举

        win32gui.EnumWindows(enum_callback, None)
        return result_hwnd

    def _add_to_cache(self, hwnd: int, window_info: WindowInfo) -> None:
        """添加到缓存

        Args:
            hwnd: 窗口句柄
            window_info: 窗口信息
        """
        self._window_cache[hwnd] = window_info

        # 清理过期的缓存
        self._cleanup_expired_cache()

    def _cleanup_expired_cache(self) -> int:
        """清理过期的缓存条目

        Returns:
            清理的条目数
        """
        cleaned_count = 0
        current_time = time.time()

        expired_hwnds = []
        for hwnd, window_info in self._window_cache.items():
            if current_time - window_info.timestamp > self._cache_ttl:
                expired_hwnds.append(hwnd)

        for hwnd in expired_hwnds:
            del self._window_cache[hwnd]
            cleaned_count += 1

        if cleaned_count > 0:
            logger.debug(f"清理了 {cleaned_count} 个过期窗口缓存")

        return cleaned_count

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
            self._hwnd_by_name.clear()
            logger.info("窗口名缓存已清理")

    def invalidate_cache(self, hwnd: Optional[int] = None) -> None:
        """使缓存失效

        Args:
            hwnd: 指定窗口句柄，如果为None则清理所有缓存
        """
        if hwnd is not None:
            if hwnd in self._window_cache:
                del self._window_cache[hwnd]
                logger.debug(f"窗口缓存已失效: hwnd={hwnd}")

            # 同时清理名称缓存中指向该句柄的条目
            titles_to_remove = []
            for title, cached_hwnd in self._hwnd_by_name.items():
                if cached_hwnd == hwnd:
                    titles_to_remove.append(title)

            for title in titles_to_remove:
                del self._hwnd_by_name[title]
                logger.debug(f"窗口名缓存已失效: title={title}")
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
            'window_cache_size': len(self._window_cache),
            'name_cache_size': len(self._hwnd_by_name),
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
