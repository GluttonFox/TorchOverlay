"""OCR服务接口"""
from abc import ABC, abstractmethod
from typing import Any

from domain.models.ocr_result import OcrWordResult, OcrResult


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
