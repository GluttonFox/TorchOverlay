"""截图结果领域模型"""
from dataclasses import dataclass


@dataclass
class CaptureResult:
    """截图结果"""
    ok: bool
    path: str | None = None
    error: str | None = None
