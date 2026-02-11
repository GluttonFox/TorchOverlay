import win32gui
import win32process

class WindowFinder:
    """枚举窗口并按标题关键字匹配。"""

    def __init__(self, keywords: tuple[str, ...]):
        self._keywords = keywords

    def find_first_match(self) -> tuple[int | None, str | None]:
        windows: list[tuple[int, str]] = []

        def callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd) or ""
            if title.strip():
                windows.append((hwnd, title))

        win32gui.EnumWindows(callback, None)

        for hwnd, title in windows:
            low = title.lower()
            for k in self._keywords:
                if k.lower() in low:
                    return hwnd, title

        return None, None

    @staticmethod
    def get_pid(hwnd: int) -> int:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return int(pid)

    @staticmethod
    def is_hwnd_valid(hwnd: int) -> bool:
        try:
            return bool(win32gui.IsWindow(hwnd))
        except Exception:
            return False
