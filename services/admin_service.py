import sys
import ctypes
from core.config import AppConfig

class AdminService:
    """管理员权限检测与提权重启。"""

    def __init__(self, cfg: AppConfig | None = None):
        self._cfg = cfg or AppConfig()

    def is_admin(self) -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def ensure_admin_or_restart(self) -> None:
        if self._cfg.elevated_marker in sys.argv:
            return
        if self.is_admin():
            return

        params = " ".join([f'"{a}"' for a in sys.argv] + [f'"{self._cfg.elevated_marker}"'])
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            params,
            None,
            1
        )
        raise SystemExit(0)
