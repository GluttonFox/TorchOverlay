"""服务接口包"""
from .icapture_service import ICaptureService
from .iocr_service import IOcrService
from .ioverlay_service import IOverlayService
from .iwindow_service import IWindowService, WindowInfo
from .igame_binder import IGameBinder, BoundGame
from .iprocess_watcher import IProcessWatcher

# 模型类从领域层导入
from domain.models.capture_result import CaptureResult
from domain.models.ocr_result import OcrResult, OcrWordResult

__all__ = [
    'ICaptureService',
    'CaptureResult',
    'IOcrService',
    'OcrResult',
    'OcrWordResult',
    'IOverlayService',
    'IWindowService',
    'WindowInfo',
    'IGameBinder',
    'BoundGame',
    'IProcessWatcher',
]
