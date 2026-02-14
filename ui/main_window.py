import tkinter as tk
from tkinter import messagebox, ttk
import json
import os
from datetime import datetime
from core.config import AppConfig, OcrConfig
from domain.models import BoundGame
from ui.settings_window import SettingsWindow
from ui.exchange_log_window import ExchangeLogWindow
from core.logger import get_logger

logger = get_logger(__name__)

class MainWindow:
    """UI 层：只做展示与交互，不做业务判断。"""

    def __init__(self, cfg: AppConfig, controller):
        self._cfg = cfg
        self._controller = controller

        self.root = tk.Tk()
        self.root.geometry("620x200")
        self.root.resizable(False, False)

        # 余额显示区域（顶部）
        tk.Label(self.root, text="当前余额：", font=("Segoe UI", 11, "bold")).place(x=20, y=25)
        self.lbl_balance = tk.Label(self.root, text="--", font=("Segoe UI", 18, "bold"), fg="#2ECC71")
        self.lbl_balance.place(x=110, y=18, width=200, height=40)

        # 初火源质价格显示（右侧）
        self.lbl_source_price = tk.Label(
            self.root,
            text="初火源质:神威辉石 1:--",
            font=("Segoe UI", 9),
            fg="#666666"
        )
        self.lbl_source_price.place(x=330, y=25, width=270, height=20)

        # 更新物价按钮和时间显示（中间区域）
        self.btn_update_price = tk.Button(
            self.root,
            text="更新物价",
            font=("Segoe UI", 9),
            command=self._controller.on_update_price_click
        )
        self.btn_update_price.place(x=20, y=80, width=90, height=28)

        self.lbl_last_update = tk.Label(
            self.root,
            text="上次更新：未更新",
            font=("Segoe UI", 9),
            fg="#666666"
        )
        self.lbl_last_update.place(x=120, y=85, width=200, height=18)

        # 从config.json加载上次更新时间
        self._load_last_update_time()

        # 加载初火源质价格
        self._load_source_price()

        # 背包初始化警告覆盖层
        self._backpack_warning_frame = tk.Frame(
            self.root,
            bg="#2C2C2C",
            highlightbackground="#FF6B6B",
            highlightthickness=1
        )
        # 暂时不显示，等背包状态确定后再决定
        # self._backpack_warning_frame.place(x=0, y=0, width=620, height=200)

        # 按钮区域（底部）
        self.btn_detect = tk.Button(
            self.root,
            text="识别物品",
            font=("Segoe UI", 9),
            state="disabled",
            command=self._controller.on_detect_click
        )
        self.btn_detect.place(x=20, y=130, width=110, height=32)

        self.btn_exchange_log = tk.Button(
            self.root,
            text="📋 兑换日志",
            font=("Segoe UI", 9),
            command=self._open_exchange_log
        )
        self.btn_exchange_log.place(x=135, y=130, width=110, height=32)

        # 根据配置控制兑换日志按钮的显示
        if not cfg.enable_exchange_log:
            self.btn_exchange_log.place_forget()

        self.btn_settings = tk.Button(
            self.root,
            text="⚙ 设置",
            font=("Segoe UI", 10),
            command=self._open_settings
        )
        self.btn_settings.place(x=380, y=130, width=220, height=32)

        # 版本号显示（在底部右下角）
        self.lbl_version = tk.Label(
            self.root,
            text=f"v{cfg.version}",
            font=("Segoe UI", 8),
            fg="#999999"
        )
        self.lbl_version.place(x=585, y=180, anchor="e")

    def set_bind_state(self, bound: BoundGame | None):
        if bound:
            title = f"{self._cfg.app_title_prefix}-已绑定-{bound.title}"
            self.root.title(title)
            self.btn_detect.config(state="normal")
        else:
            title = f"{self._cfg.app_title_prefix}-未绑定"
            self.root.title(title)
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

    def add_item_result(self, index: int, region_name: str, item_name: str,
                       item_quantity: str, item_price: str, original_price: str,
                       converted_price: str, profit_ratio: str):
        """添加物品识别结果到显示（暂时实现，后续可改为表格显示）

        Args:
            index: 索引
            region_name: 区域名称
            item_name: 物品名称
            item_quantity: 数量
            item_price: 价格
            original_price: 原始价格
            converted_price: 转换价格
            profit_ratio: 利润比率
        """
        # 暂时在控制台输出，后续可以实现表格显示
        logger.info(f"物品 {index} ({region_name}): {item_name} x{item_quantity}, "
                   f"价格={item_price}, 原价={original_price}, 转换价={converted_price}, "
                   f"利润={profit_ratio}")

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

    def _load_source_price(self):
        """从item.json加载初火源质价格"""
        try:
            item_path = os.path.join(os.path.dirname(__file__), '..', 'item.json')
            if os.path.exists(item_path):
                with open(item_path, 'r', encoding='utf-8') as f:
                    item_data = json.load(f)

                # 初火源质的价格固定为1，神威辉石的ID是5210
                if '5210' in item_data:
                    gem_price = item_data['5210'].get('Price')
                    if gem_price is not None and gem_price != 0:
                        converted_price = 1 / gem_price
                        price_str = f"{converted_price:.4f}"
                        self.lbl_source_price.config(text=f"初火源质:神威辉石 1:{price_str}")
        except Exception as e:
            logger.error(f"加载初火源质价格失败: {e}")

    def update_source_price(self):
        """更新初火源质价格显示"""
        try:
            item_path = os.path.join(os.path.dirname(__file__), '..', 'item.json')
            if os.path.exists(item_path):
                with open(item_path, 'r', encoding='utf-8') as f:
                    item_data = json.load(f)

                # 初火源质的价格固定为1，神威辉石的ID是5210
                if '5210' in item_data:
                    gem_price = item_data['5210'].get('Price')
                    if gem_price is not None and gem_price != 0:
                        converted_price = 1 / gem_price
                        price_str = f"{converted_price:.4f}"
                        self.lbl_source_price.config(text=f"初火源质:神威辉石 1:{price_str}")
                    else:
                        self.lbl_source_price.config(text="初火源质:神威辉石 1:--")
        except Exception as e:
            logger.error(f"更新初火源质价格失败: {e}")
            self.lbl_source_price.config(text="初火源质:神威辉石 1:--")

    def schedule(self, delay_ms: int, fn):
        self.root.after(delay_ms, fn)

    def close(self):
        self.root.destroy()

    def run(self):
        self.set_bind_state(None)

        # 在 mainloop 之前调用 on_window_shown，确保 UI 已经附加
        if self._controller:
            self._controller.on_window_shown()

        self.root.mainloop()

    def _open_settings(self):
        """打开设置窗口"""
        # 每次打开前从controller获取最新配置
        latest_cfg = self._controller.get_config()
        SettingsWindow(self.root, latest_cfg, self._save_config_callback)

    def _open_exchange_log(self):
        """打开兑换日志窗口"""
        try:
            ExchangeLogWindow(self.root)
        except Exception as e:
            logger.error(f"打开兑换日志窗口失败: {e}")
            messagebox.showerror("错误", f"打开兑换日志失败：{e}")

    def _save_config_callback(self, ocr_config: OcrConfig, watch_interval_ms: int, enable_tax_calculation: bool = False, mystery_gem_mode: str = "min", enable_exchange_log: bool = True, enable_auto_ocr: bool = False) -> bool:
        """保存配置回调"""
        try:
            result = self._controller.update_config(ocr_config, watch_interval_ms, enable_tax_calculation, mystery_gem_mode, enable_exchange_log, enable_auto_ocr)
            if result:
                # 更新UI中保存的配置引用
                self._cfg = self._controller.get_config()
                # 更新兑换日志按钮的显示状态
                self._update_exchange_log_button()
            return result
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败：{e}")
            return False

    def _update_exchange_log_button(self):
        """根据配置更新兑换日志按钮的显示状态"""
        if self._cfg.enable_exchange_log:
            self.btn_exchange_log.place(x=135, y=130, width=110, height=32)
        else:
            self.btn_exchange_log.place_forget()

    def show_backpack_warning(self, show: bool = True) -> None:
        """显示或隐藏背包未初始化警告

        Args:
            show: True 显示警告，False 隐藏警告
        """
        print(f"[调试] show_backpack_warning 被调用，show={show}")

        if show:
            print(f"[调试] 准备显示警告覆盖层")

            # 创建警告内容
            if not self._backpack_warning_frame.winfo_children():
                # 警告图标
                warning_label = tk.Label(
                    self._backpack_warning_frame,
                    text="⚠️",
                    font=("Segoe UI", 48),
                    bg="#2C2C2C",
                    fg="#FF6B6B"
                )
                warning_label.pack(pady=(25, 15))

                # 警告标题
                title_label = tk.Label(
                    self._backpack_warning_frame,
                    text="背包未初始化",
                    font=("Segoe UI", 18, "bold"),
                    bg="#2C2C2C",
                    fg="#FFFFFF"
                )
                title_label.pack(pady=(0, 15))

                # 警告说明
                desc_label = tk.Label(
                    self._backpack_warning_frame,
                    text="请打开日志后返回人物登录界面",
                    font=("Segoe UI", 11),
                    bg="#2C2C2C",
                    fg="#E0E0E0",
                    wraplength=500,
                    justify="center"
                )
                desc_label.pack(pady=(0, 15))

                # 提示信息
                hint_label = tk.Label(
                    self._backpack_warning_frame,
                    text="检测到 LoadUILogicProgress=3 时会自动初始化背包\n重新登录游戏即可触发",
                    font=("Segoe UI", 9),
                    bg="#2C2C2C",
                    fg="#999999",
                    wraplength=500,
                    justify="center"
                )
                hint_label.pack(pady=(0, 20))

            # 显示警告覆盖层
            self._backpack_warning_frame.place(x=0, y=0, width=620, height=200)
            # 提升到最上层，确保覆盖所有元素
            self._backpack_warning_frame.lift()
            logger.info("显示背包未初始化警告")
            print(f"[调试] 警告覆盖层已显示并提升到最上层")
        else:
            # 隐藏警告覆盖层
            self._backpack_warning_frame.place_forget()
            logger.info("隐藏背包未初始化警告")
            print(f"[调试] 警告覆盖层已隐藏")
