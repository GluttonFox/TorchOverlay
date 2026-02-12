import sys
import traceback
import tkinter as tk
from tkinter import messagebox

from services.overlay.dpi import enable_per_monitor_v2_dpi_awareness
from app.application import TorchOverlayApplication  # 如果你用的是相对导入，这里照你现有写法

def main():
    try:
        print("Starting application...")
        sys.stdout.flush()
        enable_per_monitor_v2_dpi_awareness()
        print("DPI awareness enabled.")
        sys.stdout.flush()
        TorchOverlayApplication().run()
    except SystemExit as e:
        print(f"SystemExit: {e.code}")
        sys.stdout.flush()
        raise
    except Exception:
        err = traceback.format_exc()
        print(f"Error occurred:\n{err}")
        sys.stdout.flush()
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("启动失败", err)
        except Exception:
            print(err)

if __name__ == "__main__":
    main()
