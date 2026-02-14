import sys
import traceback
import tkinter as tk
from tkinter import messagebox

from services.overlay.dpi import enable_per_monitor_v2_dpi_awareness
from app.application import TorchOverlayApplication  # 如果你用的是相对导入，这里照你现有写法

# 应用版本号
APP_VERSION = "1.0.0"

def main() -> None:
    try:
        # 启用 DPI 感知
        enable_per_monitor_v2_dpi_awareness()

        # 创建应用实例（暂时禁用优化功能以避免启动问题）
        app = TorchOverlayApplication(enable_memory_monitor=False, enable_thread_pool=False)

        # 运行应用
        app.run()
    except SystemExit as e:
        raise
    except Exception:
        err = traceback.format_exc()
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("启动失败", err)
        except Exception:
            print(err)

if __name__ == "__main__":
    main()
