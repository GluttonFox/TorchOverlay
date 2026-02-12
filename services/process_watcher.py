import psutil
from domain.models import BoundGame
from services.interfaces import IProcessWatcher

class ProcessWatcher(IProcessWatcher):
    """进程/窗口存活检测（策略类，便于后续替换/扩展）。"""

    def __init__(self, interval_ms: int = 500):
        self._interval_ms = interval_ms

    @property
    def interval_ms(self) -> int:
        return self._interval_ms

    @interval_ms.setter
    def interval_ms(self, value: int) -> None:
        self._interval_ms = value

    def is_alive(self, bound: BoundGame) -> bool:
        try:
            p = psutil.Process(bound.pid)
            return p.is_running()
        except Exception:
            return False
