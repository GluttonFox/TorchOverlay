"""窗口服务 - 实现IWindowService接口"""
from dataclasses import dataclass
from typing import Any

import win32gui
import win32process

from services.interfaces import IWindowService, WindowInfo
from services.overlay.target_window import get_client_rect_in_screen


class WindowService(IWindowService):
    """窗口服务 - 枚举窗口、获取窗口信息"""

    def __init__(self, keywords: tuple[str, ...]):
        self._keywords = keywords

    def find_by_keywords(self, keywords: tuple[str, ...]) -> Any | None:
        """根据关键词查找窗口

        Args:
            keywords: 关键词元组

        Returns:
            窗口信息，未找到返回None
        """
        windows: list[tuple[int, str]] = []

        def callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd) or ""
            if title.strip():
                windows.append((hwnd, title))

        win32gui.EnumWindows(callback, None)

        for hwnd, title in windows:
            low = title.lower()
            for k in keywords:
                if k.lower() in low:
                    return WindowInfo(hwnd=hwnd, title=title, class_name="")

        return None

    def is_valid(self, hwnd: int) -> bool:
        """检查窗口句柄是否有效

        Args:
            hwnd: 窗口句柄

        Returns:
            是否有效
        """
        try:
            return bool(win32gui.IsWindow(hwnd))
        except Exception:
            return False

    def is_visible(self, hwnd: int) -> bool:
        """检查窗口是否可见

        Args:
            hwnd: 窗口句柄

        Returns:
            是否可见
        """
        try:
            return win32gui.IsWindowVisible(hwnd)
        except Exception:
            return False

    def is_iconic(self, hwnd: int) -> bool:
        """检查窗口是否最小化

        Args:
            hwnd: 窗口句柄

        Returns:
            是否最小化
        """
        try:
            return win32gui.IsIconic(hwnd)
        except Exception:
            return False

    def get_client_rect(self, hwnd: int) -> tuple[int, int, int, int]:
        """获取窗口客户区域

        Args:
            hwnd: 窗口句柄

        Returns:
            (x, y, width, height)
        """
        return get_client_rect_in_screen(hwnd)

