"""OCR服务接口"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class OcrWordResult:
    """单个识别文字块的结果"""
    text: str
    x: int  # 左上角x坐标
    y: int  # 左上角y坐标
    width: int
    height: int
    raw: dict | None = None


@dataclass
class OcrResult:
    """OCR识别结果"""
    ok: bool
    text: str | None = None
    words: list[OcrWordResult] | None = None  # 包含位置信息的文字块列表
    raw: dict | None = None
    error: str | None = None


class IOcrService(ABC):
    """OCR服务接口"""

    @abstractmethod
    def recognize(self, image_path: str) -> OcrResult:
        """识别图片中的文字

        Args:
            image_path: 图片路径

        Returns:
            OCR识别结果
        """
        pass
