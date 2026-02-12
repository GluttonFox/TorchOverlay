"""领域模型包"""
from .region import Region
from .item_info import ItemInfo
from .capture_result import CaptureResult
from .ocr_result import OcrResult, OcrWordResult

__all__ = [
    'Region',
    'ItemInfo',
    'CaptureResult',
    'OcrResult',
    'OcrWordResult',
]
