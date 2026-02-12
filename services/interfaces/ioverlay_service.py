"""Overlay服务接口"""
from abc import ABC, abstractmethod
from typing import Any


class IOverlayService(ABC):
    """Overlay服务接口"""

    @abstractmethod
    def create_overlay(self, target_hwnd: int) -> bool:
        """创建Overlay窗口

        Args:
            target_hwnd: 目标窗口句柄

        Returns:
            是否创建成功
        """
        pass

    @abstractmethod
    def show_regions(self, regions: list[dict[str, Any]]) -> None:
        """显示区域边框

        Args:
            regions: 区域列表
        """
        pass

    @abstractmethod
    def show_texts(self, text_items: list[Any]) -> None:
        """在覆盖层上显示文本

        Args:
            text_items: 文本项列表
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空Overlay"""
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭Overlay"""
        pass

    @abstractmethod
    def is_visible(self) -> bool:
        """检查Overlay是否可见

        Returns:
            是否可见
        """
        pass
