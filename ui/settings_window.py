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
        self.window.geometry("500x520")
        self.window.resizable(False, False)
        self.window.grab_set()  # 模态窗口

        # 保存原始的完整key
        self._original_api_key = cfg.ocr.api_key
        self._original_secret_key = cfg.ocr.secret_key

        # API类型映射：中文显示值 -> 实际API名称
        self._api_name_mapping = {
            '百度-高精度带坐标': 'accurate',
        }

        self._setup_ui()
        self._load_config()

        # 窗口居中
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        # 创建选项卡容器
        self.notebook = ttk.Notebook(self.window)
        self.notebook.place(x=10, y=10, width=480, height=420)

        # 创建各个选项卡
        self._create_ocr_tab()
        self._create_app_tab()
        self._create_advanced_tab()

        # 按钮区域
        button_frame = ttk.Frame(self.window)
        button_frame.place(x=10, y=440, width=480, height=40)

        ttk.Button(button_frame, text="保存", command=self._save_settings, width=12).place(x=280, y=8)
        ttk.Button(button_frame, text="取消", command=self.window.destroy, width=12).place(x=370, y=8)

    def _create_ocr_tab(self):
        """创建OCR设置选项卡"""
        ocr_frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(ocr_frame, text="OCR 设置")

        # API Key
        ttk.Label(ocr_frame, text="API Key:").grid(row=0, column=0, sticky="w", pady=8)
        self.api_key_var = tk.StringVar()
        ttk.Entry(ocr_frame, textvariable=self.api_key_var, width=45).grid(row=0, column=1, sticky="w", pady=8)

        # Secret Key
        ttk.Label(ocr_frame, text="Secret Key:").grid(row=1, column=0, sticky="w", pady=8)
        self.secret_key_var = tk.StringVar()
        ttk.Entry(ocr_frame, textvariable=self.secret_key_var, width=45).grid(row=1, column=1, sticky="w", pady=8)

        # API Name
        ttk.Label(ocr_frame, text="API 类型:").grid(row=2, column=0, sticky="w", pady=8)
        self.api_name_var = tk.StringVar()
        api_name_combo = ttk.Combobox(ocr_frame, textvariable=self.api_name_var, width=30, state="readonly")
        api_name_combo['values'] = tuple(self._api_name_mapping.keys())
        api_name_combo.grid(row=2, column=1, sticky="w", pady=8)

        # 超时时间
        ttk.Label(ocr_frame, text="超时时间(秒):").grid(row=3, column=0, sticky="w", pady=8)
        self.timeout_var = tk.DoubleVar()
        ttk.Spinbox(ocr_frame, from_=5, to=60, textvariable=self.timeout_var, width=10).grid(row=3, column=1, sticky="w", pady=8)

        # 重试次数
        ttk.Label(ocr_frame, text="重试次数:").grid(row=4, column=0, sticky="w", pady=8)
        self.retries_var = tk.IntVar()
        ttk.Spinbox(ocr_frame, from_=0, to=5, textvariable=self.retries_var, width=10).grid(row=4, column=1, sticky="w", pady=8)

        # 调试模式
        self.debug_var = tk.BooleanVar()
        ttk.Checkbutton(ocr_frame, text="启用调试模式", variable=self.debug_var).grid(row=5, column=0, columnspan=2, sticky="w", pady=8)

        # 说明
        info_text = "说明: 使用「百度-高精度带坐标」获得最佳识别效果"
        info_label = ttk.Label(ocr_frame, text=info_text, foreground="gray", justify="left")
        info_label.grid(row=6, column=0, columnspan=2, sticky="w", pady=15)

    def _create_app_tab(self):
        """创建应用设置选项卡"""
        app_frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(app_frame, text="应用设置")

        # 监控间隔
        ttk.Label(app_frame, text="监控间隔(ms):").grid(row=0, column=0, sticky="w", pady=12)
        self.interval_var = tk.IntVar()
        ttk.Spinbox(app_frame, from_=100, to=2000, textvariable=self.interval_var, width=10).grid(row=0, column=1, sticky="w", pady=12)

        # 税率计算开关
        self.tax_calc_var = tk.BooleanVar()
        ttk.Checkbutton(app_frame, text="开启税率计算", variable=self.tax_calc_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=12)

        # 奥秘辉石计算模式
        ttk.Label(app_frame, text="奥秘辉石模式:").grid(row=2, column=0, sticky="w", pady=12)
        self.mystery_gem_mode_var = tk.StringVar()
        mystery_gem_combo = ttk.Combobox(app_frame, textvariable=self.mystery_gem_mode_var, width=15, state="readonly")
        mystery_gem_combo['values'] = ('最小', '最大', '随机')
        mystery_gem_combo.grid(row=2, column=1, sticky="w", pady=12)

        # 奥秘辉石说明
        gem_info_text = "奥秘辉石价格: 小=50-100神威辉石, 大=100-900神威辉石"
        gem_info_label = ttk.Label(app_frame, text=gem_info_text, foreground="gray", justify="left")
        gem_info_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=15)

        # 应用说明
        app_info = "说明: 监控间隔建议设置为 300-500ms，过小会增加CPU占用"
        app_info_label = ttk.Label(app_frame, text=app_info, foreground="gray", justify="left", wraplength=400)
        app_info_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=10)

    def _create_advanced_tab(self):
        """创建高级设置选项卡"""
        advanced_frame = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(advanced_frame, text="高级设置")

        # 兑换日志开关
        self.exchange_log_var = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="启用兑换日志", variable=self.exchange_log_var).grid(row=0, column=0, columnspan=2, sticky="w", pady=12)

        # 兑换日志说明
        exchange_log_info = "开启后，每次兑换都会记录到 exchange_log.json 文件中。\n可在主界面点击「兑换日志」按钮查看历史记录。"
        exchange_log_label = ttk.Label(advanced_frame, text=exchange_log_info, foreground="gray", justify="left", wraplength=420)
        exchange_log_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=10)

        # 分隔线
        ttk.Separator(advanced_frame, orient="horizontal").grid(row=2, column=0, columnspan=2, sticky="ew", pady=15)

        # 自动OCR开关
        self.auto_ocr_var = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="启用自动OCR", variable=self.auto_ocr_var).grid(row=3, column=0, columnspan=2, sticky="w", pady=12)

        # 自动OCR说明
        auto_ocr_info = "开启后，当检测到花费50神威辉石刷新商店时，会自动执行物品识别。\n无需手动点击「识别」按钮即可查看价格信息。"
        auto_ocr_label = ttk.Label(advanced_frame, text=auto_ocr_info, foreground="gray", justify="left", wraplength=420)
        auto_ocr_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=10)

        # 高级说明
        advanced_info = "高级设置包含系统级配置选项，请谨慎修改。\n\n" \
                       "• 兑换日志: 控制是否记录兑换操作到日志文件\n" \
                       "• 自动OCR: 检测到花费50神威辉石刷新商店后自动识别"
        advanced_info_label = ttk.Label(advanced_frame, text=advanced_info, foreground="gray", justify="left", wraplength=420)
        advanced_info_label.grid(row=5, column=0, columnspan=2, sticky="w", pady=15)

    def _load_config(self):
        """加载当前配置到界面"""
        # OCR设置
        self.api_key_var.set(self._mask_sensitive(self._cfg.ocr.api_key))
        self.secret_key_var.set(self._mask_sensitive(self._cfg.ocr.secret_key))

        # 将API名称转换为中文显示
        api_name = self._cfg.ocr.api_name
        chinese_name = self._get_chinese_name_for_api(api_name)
        self.api_name_var.set(chinese_name)

        self.timeout_var.set(self._cfg.ocr.timeout_sec)
        self.retries_var.set(self._cfg.ocr.max_retries)
        self.debug_var.set(self._cfg.ocr.debug_mode)

        # 应用设置
        self.interval_var.set(self._cfg.watch_interval_ms)
        self.tax_calc_var.set(self._cfg.enable_tax_calculation)

        # 加载奥秘辉石模式
        mode_map = {'min': '最小', 'max': '最大', 'random': '随机'}
        self.mystery_gem_mode_var.set(mode_map.get(self._cfg.mystery_gem_mode, '最小'))

        # 高级设置
        self.exchange_log_var.set(self._cfg.enable_exchange_log)
        self.auto_ocr_var.set(self._cfg.enable_auto_ocr)

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
        if self._save_callback(ocr_config, self.interval_var.get(), self.tax_calc_var.get(), mystery_gem_mode, self.exchange_log_var.get(), self.auto_ocr_var.get()):
            self.window.destroy()

