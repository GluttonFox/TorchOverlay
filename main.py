import traceback
import tkinter as tk
from tkinter import messagebox

from services.overlay.dpi import enable_per_monitor_v2_dpi_awareness
from app.application import TorchOverlayApplication  # 如果你用的是相对导入，这里照你现有写法

def main():
    try:
        enable_per_monitor_v2_dpi_awareness()
        TorchOverlayApplication().run()
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
