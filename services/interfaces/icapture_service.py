"""截图服务接口"""
from abc import ABC, abstractmethod
from typing import Any

from domain.models.capture_result import CaptureResult


class ICaptureService(ABC):
    """截图服务接口"""

    @abstractmethod
    def capture_window(self, hwnd: int, out_path: str, timeout_sec: float = 2.5) -> CaptureResult:
        """截取整个窗口

        Args:
            hwnd: 窗口句柄
            out_path: 输出路径
            timeout_sec: 超时时间

        Returns:
            截图结果
        """
        pass

    @abstractmethod
    def capture_region(
        self,
        hwnd: int,
        out_path: str,
        region: dict[str, Any],
        timeout_sec: float = 2.5,
        preprocess: bool = False
    ) -> CaptureResult:
        """截取指定区域

        Args:
            hwnd: 窗口句柄
            out_path: 输出路径
            region: 区域定义 {x, y, width, height}
            timeout_sec: 超时时间
            preprocess: 是否预处理

        Returns:
            截图结果
        """
        pass

    @abstractmethod
    def capture_client(self, hwnd: int, out_path: str, timeout_sec: float = 2.5) -> CaptureResult:
        """截取客户区域

        Args:
            hwnd: 窗口句柄
            out_path: 输出路径
            timeout_sec: 超时时间

        Returns:
            截图结果
        """
        pass
