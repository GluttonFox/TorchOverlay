import ctypes

def enable_per_monitor_v2_dpi_awareness() -> None:
    """
    开启 Per-Monitor v2 DPI awareness，避免高DPI下窗口/截图/overlay坐标不一致。
    """
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    except Exception:
        # 兼容旧系统/权限不足等情况
        pass
