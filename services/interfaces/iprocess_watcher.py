"""进程监视器接口"""
from abc import ABC, abstractmethod


class IProcessWatcher(ABC):
    """进程监视器接口"""

    @property
    @abstractmethod
    def interval_ms(self) -> int:
        """获取监视间隔"""
        pass

    @interval_ms.setter
    @abstractmethod
    def interval_ms(self, value: int) -> None:
        """设置监视间隔"""
        pass

    @abstractmethod
    def is_alive(self, bound: Any) -> bool:
        """检查游戏进程是否存活

        Args:
            bound: BoundGame对象

        Returns:
            是否存活
        """
        pass
