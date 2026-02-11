import tkinter as tk
from tkinter import messagebox
from core.config import AppConfig
from core.models import BoundGame

class MainWindow:
    """UI 层：只做展示与交互，不做业务判断。"""

    def __init__(self, cfg: AppConfig, controller):
        self._cfg = cfg
        self._controller = controller

        self.root = tk.Tk()
        self.root.geometry("620x280")
        self.root.resizable(False, False)

        self.lbl_header = tk.Label(self.root, text="", font=("Segoe UI", 12, "bold"), anchor="w")
        self.lbl_header.place(x=16, y=14, width=588, height=28)

        self.lbl_status = tk.Label(self.root, text="", font=("Segoe UI", 10), anchor="w", justify="left")
        self.lbl_status.place(x=16, y=52, width=588, height=60)

        self.btn_detect = tk.Button(
            self.root,
            text="识别物品（暂未实现）",
            font=("Segoe UI", 10),
            state="disabled",
            command=self._controller.on_detect_click
        )
        self.btn_detect.place(x=16, y=210, width=588, height=34)

        self.root.after(0, self._controller.on_window_shown)

    def set_bind_state(self, bound: BoundGame | None):
        if bound:
            title = f"{self._cfg.app_title_prefix}-已绑定-{bound.title}"
            self.root.title(title)
            self.lbl_header.config(text=title)
            self.lbl_status.config(text=f"状态：已绑定\n窗口：{bound.title}\nPID：{bound.pid}")
            self.btn_detect.config(state="normal")
        else:
            title = f"{self._cfg.app_title_prefix}-未绑定"
            self.root.title(title)
            self.lbl_header.config(text=title)
            self.lbl_status.config(text="状态：未绑定")
            self.btn_detect.config(state="disabled")

    def ask_bind_retry_or_exit(self) -> bool:
        return messagebox.askokcancel(
            "未检测到游戏",
            "未检测到游戏窗口。\n\n请先开启【火炬之光 / 火炬之光无限】后点击【确定】重试。\n点击【取消】将退出程序。"
        )

    def show_info(self, msg: str):
        messagebox.showinfo("提示", msg)

    def schedule(self, delay_ms: int, fn):
        self.root.after(delay_ms, fn)

    def close(self):
        self.root.destroy()

    def run(self):
        self.set_bind_state(None)
        self.root.mainloop()
