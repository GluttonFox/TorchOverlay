"""服务接口包"""
from .icapture_service import ICaptureService, CaptureResult
from .iocr_service import IOcrService, OcrResult, OcrWordResult
from .ioverlay_service import IOverlayService
from .iwindow_service import IWindowService
from .igame_binder import IGameBinder, BoundGame
from .iprocess_watcher import IProcessWatcher
from .iwindow_service import WindowInfo

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
