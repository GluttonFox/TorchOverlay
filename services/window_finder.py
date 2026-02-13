import win32gui
import win32process
import psutil

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

    @staticmethod
    def get_process_path(pid: int) -> str | None:
        """获取进程的可执行文件路径

        Args:
            pid: 进程ID

        Returns:
            进程的可执行文件路径，如果获取失败返回None
        """
        try:
            process = psutil.Process(pid)
            return process.exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            return None
