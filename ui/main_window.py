import tkinter as tk
from tkinter import messagebox, ttk
import json
import os
from datetime import datetime
from core.config import AppConfig, OcrConfig
from domain.models import BoundGame
from ui.settings_window import SettingsWindow

class MainWindow:
    """UI 层：只做展示与交互，不做业务判断。"""

    def __init__(self, cfg: AppConfig, controller):
        self._cfg = cfg
        self._controller = controller

        self.root = tk.Tk()
        self.root.geometry("620x450")
        self.root.resizable(False, False)

        self.lbl_header = tk.Label(self.root, text="", font=("Segoe UI", 12, "bold"), anchor="w")
        self.lbl_header.place(x=16, y=14, width=588, height=28)

        # 余额显示区域
        tk.Label(self.root, text="当前余额：", font=("Segoe UI", 12, "bold")).place(x=16, y=55)
        self.lbl_balance = tk.Label(self.root, text="--", font=("Segoe UI", 16, "bold"), fg="#2ECC71")
        self.lbl_balance.place(x=120, y=50, width=250, height=35)

        # 物品识别结果表格
        tk.Label(self.root, text="物品识别结果：", font=("Segoe UI", 12, "bold")).place(x=16, y=100)

        # 更新物价按钮和时间显示
        self.btn_update_price = tk.Button(
            self.root,
            text="更新物价",
            font=("Segoe UI", 9),
            command=self._controller.on_update_price_click
        )
        self.btn_update_price.place(x=300, y=100, width=80, height=24)

        self.lbl_last_update = tk.Label(
            self.root,
            text="上次更新：未更新",
            font=("Segoe UI", 9),
            fg="#666666"
        )
        self.lbl_last_update.place(x=390, y=102, width=180, height=20)

        # 从config.json加载上次更新时间
        self._load_last_update_time()

        # 创建表格
        columns = ("index", "name", "quantity", "price", "original_price", "converted_price", "profit_ratio")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=8)
        self.tree.heading("index", text="序号")
        self.tree.heading("name", text="物品名称")
        self.tree.heading("quantity", text="物品数量")
        self.tree.heading("price", text="辉石数量")
        self.tree.heading("original_price", text="原始价格")
        self.tree.heading("converted_price", text="转换价格")
        self.tree.heading("profit_ratio", text="盈亏比")

        self.tree.column("index", width=40, anchor="center", stretch=False)
        self.tree.column("name", width=200, anchor="w", stretch=False)
        self.tree.column("quantity", width=80, anchor="center", stretch=False)
        self.tree.column("price", width=80, anchor="center", stretch=False)
        self.tree.column("original_price", width=80, anchor="center", stretch=False)
        self.tree.column("converted_price", width=80, anchor="center", stretch=False)
        self.tree.column("profit_ratio", width=80, anchor="center", stretch=False)

        self.tree.place(x=16, y=125, width=588, height=220)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.tree.yview)
        scrollbar.place(x=600, y=125, width=20, height=220)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 按钮区域
        self.btn_detect = tk.Button(
            self.root,
            text="识别物品",
            font=("Segoe UI", 9),
            state="disabled",
            command=self._controller.on_detect_click
        )
        self.btn_detect.place(x=16, y=360, width=175, height=30)

        self.btn_settings = tk.Button(
            self.root,
            text="⚙ 设置",
            font=("Segoe UI", 10),
            command=self._open_settings
        )
        self.btn_settings.place(x=386, y=410, width=218, height=34)

        self.root.after(0, self._controller.on_window_shown)

    def set_bind_state(self, bound: BoundGame | None):
        if bound:
            title = f"{self._cfg.app_title_prefix}-已绑定-{bound.title}"
            self.root.title(title)
            self.lbl_header.config(text=title)
            self.btn_detect.config(state="normal")
        else:
            title = f"{self._cfg.app_title_prefix}-未绑定"
            self.root.title(title)
            self.lbl_header.config(text=title)
            self.btn_detect.config(state="disabled")

        self._check_ocr_config()

    def _check_ocr_config(self):
        """检查OCR配置是否已设置"""
        if not self._cfg.ocr.api_key or not self._cfg.ocr.secret_key:
            pass  # 可以在这里添加UI提示

    def ask_bind_retry_or_exit(self) -> bool:
        return messagebox.askokcancel(
            "未检测到游戏",
            "未检测到游戏窗口。\n\n请先开启【火炬之光 / 火炬之光无限】后点击【确定】重试。\n点击【取消】将退出程序。"
        )

    def show_info(self, msg: str):
        messagebox.showinfo("提示", msg)

    def update_balance(self, balance: str):
        """更新余额显示"""
        self.lbl_balance.config(text=balance)

    def update_last_update_time(self, last_update_time):
        """更新最后更新时间显示"""
        if last_update_time is None:
            self.lbl_last_update.config(text="上次更新：未更新")
        else:
            time_str = last_update_time.strftime("%Y-%m-%d %H:%M")
            self.lbl_last_update.config(text=f"上次更新：{time_str}")

    def _load_last_update_time(self):
        """从config.json加载上次更新时间"""
        try:
            config_path = AppConfig.get_config_path()
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                if 'last_price_update' in config_data and config_data['last_price_update']:
                    try:
                        last_update = datetime.fromisoformat(config_data['last_price_update'])
                        self.update_last_update_time(last_update)
                    except ValueError:
                        self.lbl_last_update.config(text="上次更新：未更新")
                else:
                    self.lbl_last_update.config(text="上次更新：未更新")
        except Exception as e:
            print(f"加载上次更新时间失败: {e}")
            self.lbl_last_update.config(text="上次更新：未更新")

    def clear_items_table(self):
        """清空物品表格"""
        for item in self.tree.get_children():
            self.tree.delete(item)

    def add_item_result(self, index: int, region: str, name: str, quantity: str, price: str,
                       original_price: str = "--", converted_price: str = "--", profit_ratio: str = "--"):
        """添加物品识别结果到表格"""
        self.tree.insert("", "end", values=(index, name, quantity, price, original_price, converted_price, profit_ratio))

    def schedule(self, delay_ms: int, fn):
        self.root.after(delay_ms, fn)

    def close(self):
        self.root.destroy()

    def run(self):
        self.set_bind_state(None)
        self.root.mainloop()

    def _open_settings(self):
        """打开设置窗口"""
        # 每次打开前从controller获取最新配置
        latest_cfg = self._controller.get_config()
        SettingsWindow(self.root, latest_cfg, self._save_config_callback)

    def _save_config_callback(self, ocr_config: OcrConfig, watch_interval_ms: int) -> bool:
        """保存配置回调"""
        try:
            result = self._controller.update_config(ocr_config, watch_interval_ms)
            if result:
                # 更新UI中保存的配置引用
                self._cfg = self._controller.get_config()
            return result
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败：{e}")
            return False
