from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class OcrResult:
    ok: bool
    text: str | None = None
    raw: dict | None = None
    error: str | None = None

class IOcrEngine(ABC):
    @abstractmethod
    def recognize(self, image_path: str) -> OcrResult:
        ...
