import tkinter as tk
from tkinter import messagebox, ttk
from core.config import AppConfig, OcrConfig

class SettingsWindow:
    """设置窗口：用于配置OCR和应用程序参数。"""

    def __init__(self, parent: tk.Tk, cfg: AppConfig, save_callback):
        self._parent = parent
        self._cfg = cfg
        self._save_callback = save_callback

        self.window = tk.Toplevel(parent)
        self.window.title("设置")
        self.window.geometry("650x600")
        self.window.resizable(False, False)
        self.window.grab_set()  # 模态窗口

        # 保存原始的完整key
        self._original_api_key = cfg.ocr.api_key
        self._original_secret_key = cfg.ocr.secret_key

        self._setup_ui()
        self._load_config()

        # 窗口居中
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        # API类型映射：中文显示值 -> 实际API名称
        self._api_name_mapping = {
            '百度-高精度带坐标': 'accurate',
        }

        # OCR设置分组
        ocr_frame = ttk.LabelFrame(self.window, text="OCR 设置", padding=10)
        ocr_frame.place(x=20, y=20, width=610, height=240)

        # API Key
        ttk.Label(ocr_frame, text="API Key:").place(x=10, y=10)
        self.api_key_var = tk.StringVar()
        ttk.Entry(ocr_frame, textvariable=self.api_key_var, width=60).place(x=80, y=10)

        # Secret Key
        ttk.Label(ocr_frame, text="Secret Key:").place(x=10, y=40)
        self.secret_key_var = tk.StringVar()
        ttk.Entry(ocr_frame, textvariable=self.secret_key_var, width=60).place(x=80, y=40)

        # API Name
        ttk.Label(ocr_frame, text="API 类型:").place(x=10, y=70)
        self.api_name_var = tk.StringVar()
        api_name_combo = ttk.Combobox(ocr_frame, textvariable=self.api_name_var, width=40, state="readonly")
        api_name_combo['values'] = tuple(self._api_name_mapping.keys())
        api_name_combo.place(x=80, y=70)

        # 超时时间
        ttk.Label(ocr_frame, text="超时时间(秒):").place(x=10, y=100)
        self.timeout_var = tk.DoubleVar()
        ttk.Spinbox(ocr_frame, from_=5, to=60, textvariable=self.timeout_var, width=10).place(x=80, y=100)

        # 重试次数
        ttk.Label(ocr_frame, text="重试次数:").place(x=10, y=130)
        self.retries_var = tk.IntVar()
        ttk.Spinbox(ocr_frame, from_=0, to=5, textvariable=self.retries_var, width=10).place(x=80, y=130)

        # 调试模式
        self.debug_var = tk.BooleanVar()
        ttk.Checkbutton(ocr_frame, text="启用调试模式", variable=self.debug_var).place(x=10, y=160)

        # 说明
        info_text = "说明: 使用「百度-高精度带坐标」获得最佳识别效果"

        info_label = ttk.Label(
            ocr_frame,
            text=info_text,
            foreground="gray",
            justify="left",
            wraplength=590
        )
        info_label.place(x=10, y=190)

        # 应用设置分组
        app_frame = ttk.LabelFrame(self.window, text="应用设置", padding=10)
        app_frame.place(x=20, y=270, width=610, height=180)

        # 监控间隔
        ttk.Label(app_frame, text="监控间隔(ms):").place(x=10, y=10)
        self.interval_var = tk.IntVar()
        ttk.Spinbox(app_frame, from_=100, to=2000, textvariable=self.interval_var, width=10).place(x=120, y=10)

        # 税率计算开关
        self.tax_calc_var = tk.BooleanVar()
        ttk.Checkbutton(app_frame, text="开启税率计算", variable=self.tax_calc_var).place(x=10, y=40)

        # 奥秘辉石计算模式
        ttk.Label(app_frame, text="奥秘辉石模式:").place(x=10, y=70)
        self.mystery_gem_mode_var = tk.StringVar()
        mystery_gem_combo = ttk.Combobox(app_frame, textvariable=self.mystery_gem_mode_var, width=15, state="readonly")
        mystery_gem_combo['values'] = ('最小', '最大', '随机')
        mystery_gem_combo.place(x=120, y=70)

        # 奥秘辉石说明
        gem_info_text = "奥秘辉石价格: 小=50-100神威辉石, 大=100-900神威辉石"

        gem_info_label = ttk.Label(
            app_frame,
            text=gem_info_text,
            foreground="gray",
            justify="left"
        )
        gem_info_label.place(x=10, y=100)

        # 按钮
        button_frame = ttk.Frame(self.window)
        button_frame.place(x=20, y=460, width=610, height=50)

        ttk.Button(button_frame, text="保存", command=self._save_settings, width=15).place(x=320, y=10)
        ttk.Button(button_frame, text="取消", command=self.window.destroy, width=15).place(x=450, y=10)

    def _load_config(self):
        """加载当前配置到界面"""
        # 显示脱敏后的key
        self.api_key_var.set(self._mask_sensitive(self._cfg.ocr.api_key))
        self.secret_key_var.set(self._mask_sensitive(self._cfg.ocr.secret_key))

        # 将API名称转换为中文显示
        api_name = self._cfg.ocr.api_name
        chinese_name = self._get_chinese_name_for_api(api_name)
        self.api_name_var.set(chinese_name)

        self.timeout_var.set(self._cfg.ocr.timeout_sec)
        self.retries_var.set(self._cfg.ocr.max_retries)
        self.debug_var.set(self._cfg.ocr.debug_mode)
        self.interval_var.set(self._cfg.watch_interval_ms)
        self.tax_calc_var.set(self._cfg.enable_tax_calculation)

        # 加载奥秘辉石模式
        mode_map = {'min': '最小', 'max': '最大', 'random': '随机'}
        self.mystery_gem_mode_var.set(mode_map.get(self._cfg.mystery_gem_mode, '最小'))

    def _mask_sensitive(self, value: str) -> str:
        """脱敏敏感信息，只显示前4位和最后4位"""
        if not value or len(value) <= 8:
            return value
        return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"

    def _get_actual_key(self, displayed_key: str, original_key: str) -> str:
        """获取实际的key值（如果用户没有修改，使用原始值）"""
        displayed = displayed_key.strip()
        # 如果显示值包含*，说明是脱敏显示，返回原始值
        if '*' in displayed:
            return original_key
        return displayed

    def _get_chinese_name_for_api(self, api_name: str) -> str:
        """根据API名称获取中文显示值"""
        for chinese, api in self._api_name_mapping.items():
            if api == api_name:
                return chinese
        # 如果找不到，返回默认值
        return '百度-高精度带坐标'

    def _get_api_name_from_chinese(self, chinese_name: str) -> str:
        """根据中文显示值获取API名称"""
        return self._api_name_mapping.get(chinese_name, 'accurate')

    def _save_settings(self):
        """保存设置"""
        displayed_api_key = self.api_key_var.get().strip()
        displayed_secret_key = self.secret_key_var.get().strip()

        # 获取实际的key值（如果显示的是脱敏值，使用原始值）
        api_key = self._get_actual_key(displayed_api_key, self._original_api_key)
        secret_key = self._get_actual_key(displayed_secret_key, self._original_secret_key)

        if not api_key or not secret_key:
            messagebox.showwarning("警告", "API Key 和 Secret Key 不能为空！")
            return

        # 将中文显示值转换为实际API名称
        chinese_api_name = self.api_name_var.get()
        api_name = self._get_api_name_from_chinese(chinese_api_name)

        # 转换奥秘辉石模式
        mode_map = {'最小': 'min', '最大': 'max', '随机': 'random'}
        mystery_gem_mode = mode_map.get(self.mystery_gem_mode_var.get(), 'min')

        # 创建新的配置对象
        ocr_config = OcrConfig(
            api_key=api_key,
            secret_key=secret_key,
            api_name=api_name,
            timeout_sec=self.timeout_var.get(),
            max_retries=self.retries_var.get(),
            debug_mode=self.debug_var.get(),
        )

        # 保存配置
        if self._save_callback(ocr_config, self.interval_var.get(), self.tax_calc_var.get(), mystery_gem_mode):
            self.window.destroy()
