"""OCR识别结果领域模型"""
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
    words: list[OcrWordResult] | None = None
    raw: dict | None = None
    error: str | None = None
