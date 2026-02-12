"""服务接口包"""
from .icapture_service import ICaptureService
from .iocr_service import IOcrService
from .ioverlay_service import IOverlayService
from .iwindow_service import IWindowService
from .igame_binder import IGameBinder
from .iprocess_watcher import IProcessWatcher

__all__ = [
    'ICaptureService',
    'IOcrService',
    'IOverlayService',
    'IWindowService',
    'IGameBinder',
    'IProcessWatcher',
]
