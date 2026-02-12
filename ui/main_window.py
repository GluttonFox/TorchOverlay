import tkinter as tk
from tkinter import messagebox
from core.config import AppConfig, OcrConfig
from core.models import BoundGame
from ui.settings_window import SettingsWindow

class MainWindow:
    """UI 层：只做展示与交互，不做业务判断。"""

    def __init__(self, cfg: AppConfig, controller):
        self._cfg = cfg
        self._controller = controller

        self.root = tk.Tk()
        self.root.geometry("620x310")
        self.root.resizable(False, False)

        self.lbl_header = tk.Label(self.root, text="", font=("Segoe UI", 12, "bold"), anchor="w")
        self.lbl_header.place(x=16, y=14, width=588, height=28)

        self.lbl_status = tk.Label(self.root, text="", font=("Segoe UI", 10), anchor="w", justify="left")
        self.lbl_status.place(x=16, y=52, width=588, height=60)

        self.btn_detect = tk.Button(
            self.root,
            text="识别物品",
            font=("Segoe UI", 10),
            state="disabled",
            command=self._controller.on_detect_click
        )
        self.btn_detect.place(x=16, y=210, width=360, height=34)

        self.btn_settings = tk.Button(
            self.root,
            text="⚙ 设置",
            font=("Segoe UI", 10),
            command=self._open_settings
        )
        self.btn_settings.place(x=386, y=210, width=218, height=34)

        self.lbl_info = tk.Label(self.root, text="提示：首次使用请点击「设置」配置OCR参数", font=("Segoe UI", 9), fg="gray")
        self.lbl_info.place(x=16, y=255, width=588, height=20)

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

        self._check_ocr_config()

    def _check_ocr_config(self):
        """检查OCR配置是否已设置"""
        if not self._cfg.ocr.api_key or not self._cfg.ocr.secret_key:
            self.lbl_info.config(fg="orange")
            self.lbl_info.config(text="⚠ 警告：未配置OCR参数，请点击「设置」按钮配置API Key和Secret Key")

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

    def _open_settings(self):
        """打开设置窗口"""
        SettingsWindow(self.root, self._cfg, self._save_config_callback)

    def _save_config_callback(self, ocr_config: OcrConfig, watch_interval_ms: int) -> bool:
        """保存配置回调"""
        try:
            result = self._controller.update_config(ocr_config, watch_interval_ms)
            if result:
                self.lbl_info.config(fg="gray")
                self.lbl_info.config(text="提示：配置已保存，可以开始使用识别功能")
            return result
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败：{e}")
            return False
