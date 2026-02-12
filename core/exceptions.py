"""TorchOverlay自定义异常体系"""


class TorchOverlayError(Exception):
    """基础异常类

    所有TorchOverlay自定义异常的基类
    """
    pass


class ConfigError(TorchOverlayError):
    """配置错误"""
    pass


class OcrError(TorchOverlayError):
    """OCR识别错误"""
    pass


class CaptureError(TorchOverlayError):
    """截图错误"""
    pass


class NetworkError(TorchOverlayError):
    """网络错误"""
    pass


class ValidationError(TorchOverlayError):
    """数据验证错误"""
    pass


class PriceError(TorchOverlayError):
    """价格计算错误"""
    pass


class OverlayError(TorchOverlayError):
    """Overlay显示错误"""
    pass
