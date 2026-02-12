"""窗口服务接口"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class WindowInfo:
    """窗口信息"""
    hwnd: int
    title: str
    class_name: str


class IWindowService(ABC):
    """窗口服务接口"""

    @abstractmethod
    def find_by_keywords(self, keywords: tuple[str, ...]) -> WindowInfo | None:
        """根据关键词查找窗口

        Args:
            keywords: 关键词元组

        Returns:
            窗口信息，未找到返回None
        """
        pass

    @abstractmethod
    def is_valid(self, hwnd: int) -> bool:
        """检查窗口句柄是否有效

        Args:
            hwnd: 窗口句柄

        Returns:
            是否有效
        """
        pass

    @abstractmethod
    def is_visible(self, hwnd: int) -> bool:
        """检查窗口是否可见

        Args:
            hwnd: 窗口句柄

        Returns:
            是否可见
        """
        pass

    @abstractmethod
    def is_iconic(self, hwnd: int) -> bool:
        """检查窗口是否最小化

        Args:
            hwnd: 窗口句柄

        Returns:
            是否最小化
        """
        pass

    @abstractmethod
    def get_client_rect(self, hwnd: int) -> tuple[int, int, int, int]:
        """获取窗口客户区域

        Args:
            hwnd: 窗口句柄

        Returns:
            (x, y, width, height)
        """
        pass
