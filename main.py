import traceback
import tkinter as tk
from tkinter import messagebox

from app.application import TorchOverlayApplication  # 如果你用的是相对导入，这里照你现有写法

def main():
    try:
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
