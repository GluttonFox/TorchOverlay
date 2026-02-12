"""游戏绑定器接口"""
from abc import ABC, abstractmethod
from typing import Any

from domain.models import BoundGame


class IGameBinder(ABC):
    """游戏绑定器接口"""

    @property
    @abstractmethod
    def bound(self) -> BoundGame | None:
        """获取当前绑定的游戏"""
        pass

    @abstractmethod
    def try_bind(self) -> bool:
        """尝试绑定游戏

        Returns:
            是否绑定成功
        """
        pass

    @abstractmethod
    def is_bound_hwnd_valid(self) -> bool:
        """检查绑定的窗口句柄是否有效

        Returns:
            是否有效
        """
        pass
