from domain.models import BoundGame
from services.interfaces import IGameBinder
from services.window_finder import WindowFinder

class GameBinder(IGameBinder):
    """绑定逻辑封装：只负责'找窗口 -> 生成绑定对象'。"""

    def __init__(self, finder: WindowFinder):
        self._finder = finder
        self._bound: BoundGame | None = None

    @property
    def bound(self) -> BoundGame | None:
        return self._bound

    def try_bind(self) -> bool:
        hwnd, title = self._finder.find_first_match()
        if not hwnd or not title:
            self._bound = None
            return False

        pid = self._finder.get_pid(hwnd)
        self._bound = BoundGame(hwnd=hwnd, pid=pid, title=title)
        return True

    def is_bound_hwnd_valid(self) -> bool:
        return bool(self._bound) and self._finder.is_hwnd_valid(self._bound.hwnd)
