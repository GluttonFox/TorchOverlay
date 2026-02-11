import psutil
from core.models import BoundGame

class ProcessWatcher:
    """进程/窗口存活检测（策略类，便于后续替换/扩展）。"""

    def __init__(self, interval_ms: int = 500):
        self.interval_ms = interval_ms

    def is_alive(self, bound: BoundGame) -> bool:
        try:
            p = psutil.Process(bound.pid)
            return p.is_running()
        except Exception:
            return False
