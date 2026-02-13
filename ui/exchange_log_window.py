import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime
from typing import List, Dict
from core.logger import get_logger

logger = get_logger(__name__)


class ExchangeLogWindow:
    """兑换日志窗口 - 记录和显示所有的兑换记录"""

    def __init__(self, parent):
        """初始化兑换日志窗口

        Args:
            parent: 父窗口
        """
        self.window = tk.Toplevel(parent)
        self.window.title("兑换日志")
        self.window.geometry("1000x600")
        self.window.resizable(True, True)

        # 日志文件路径
        self._log_file = os.path.join(os.path.dirname(__file__), '..', 'exchange_log.json')
        self._logs = []
        self._filtered_logs = []

        self._setup_ui()
        self._load_logs()

        # 窗口居中
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        """设置UI界面"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.window)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        # 搜索框
        ttk.Label(toolbar, text="搜索:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search)
        ttk.Entry(toolbar, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)

        # 筛选器
        ttk.Label(toolbar, text="物品名称:").pack(side=tk.LEFT, padx=5)
        self.item_filter_var = tk.StringVar()
        self.item_filter = ttk.Combobox(toolbar, textvariable=self.item_filter_var, width=20)
        self.item_filter['values'] = []
        self.item_filter.bind('<<ComboboxSelected>>', self._on_filter)
        self.item_filter.pack(side=tk.LEFT, padx=5)

        # 按钮区
        ttk.Button(toolbar, text="刷新", command=self._load_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="导出", command=self._export_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="清空", command=self._clear_logs).pack(side=tk.LEFT, padx=5)

        # 统计信息
        stats_frame = ttk.Frame(self.window)
        stats_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.lbl_stats = ttk.Label(stats_frame, text="总记录: 0 | 总盈亏: 0.00")
        self.lbl_stats.pack(side=tk.LEFT)

        # 表格
        table_frame = ttk.Frame(self.window)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 滚动条
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Treeview 表格
        self.tree = ttk.Treeview(
            table_frame,
            columns=('time', 'item_name', 'quantity', 'original_price', 'converted_price', 'profit', 'status'),
            show='headings',
            yscrollcommand=scrollbar.set
        )
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=self.tree.yview)

        # 设置列标题
        self.tree.heading('time', text='时间')
        self.tree.heading('item_name', text='物品名称')
        self.tree.heading('quantity', text='数量')
        self.tree.heading('original_price', text='原价')
        self.tree.heading('converted_price', text='转换价')
        self.tree.heading('profit', text='盈亏')
        self.tree.heading('status', text='状态')

        # 设置列宽
        self.tree.column('time', width=150, anchor='center')
        self.tree.column('item_name', width=200, anchor='w')
        self.tree.column('quantity', width=80, anchor='center')
        self.tree.column('original_price', width=100, anchor='e')
        self.tree.column('converted_price', width=100, anchor='e')
        self.tree.column('profit', width=100, anchor='e')
        self.tree.column('status', width=80, anchor='center')

    def _load_logs(self):
        """加载日志数据"""
        try:
            if os.path.exists(self._log_file):
                with open(self._log_file, 'r', encoding='utf-8') as f:
                    self._logs = json.load(f)
            else:
                self._logs = []

            self._filtered_logs = self._logs.copy()
            self._update_table()
            self._update_stats()
            self._update_item_filter()
            logger.info(f"加载了 {len(self._logs)} 条兑换记录")
        except Exception as e:
            logger.error(f"加载兑换日志失败: {e}")
            messagebox.showerror("错误", f"加载兑换日志失败：{e}")

    def _update_table(self):
        """更新表格显示"""
        # 清空表格
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 添加数据
        for log in reversed(self._filtered_logs):
            # 根据盈亏值设置颜色标签
            profit = log.get('profit', 0)
            if profit > 0:
                tags = ('profit',)
            elif profit < 0:
                tags = ('loss',)
            else:
                tags = ('even',)

            self.tree.insert('', 'end', values=(
                log.get('time', ''),
                log.get('item_name', ''),
                log.get('quantity', ''),
                f"{log.get('original_price', 0):.4f}",
                f"{log.get('converted_price', 0):.4f}",
                f"{profit:.4f}",
                log.get('status', '完成')
            ), tags=tags)

        # 设置颜色标签
        self.tree.tag_configure('profit', foreground='#00FF00')
        self.tree.tag_configure('loss', foreground='#FF0000')
        self.tree.tag_configure('even', foreground='#FFFF00')

    def _update_stats(self):
        """更新统计信息"""
        if not self._filtered_logs:
            self.lbl_stats.config(text="总记录: 0 | 总盈亏: 0.00")
            return

        total_count = len(self._filtered_logs)
        total_profit = sum(log.get('profit', 0) for log in self._filtered_logs)

        self.lbl_stats.config(
            text=f"总记录: {total_count} | 总盈亏: {total_profit:.4f}"
        )

    def _update_item_filter(self):
        """更新物品筛选列表"""
        if not self._logs:
            return

        # 获取所有物品名称
        item_names = set()
        for log in self._logs:
            item_names.add(log.get('item_name', ''))

        self.item_filter['values'] = sorted(list(item_names))

    def _on_search(self, *args):
        """搜索处理"""
        search_text = self.search_var.get().lower()
        item_filter_text = self.item_filter_var.get()

        self._filtered_logs = []
        for log in self._logs:
            # 物品名称筛选
            if item_filter_text and log.get('item_name', '') != item_filter_text:
                continue

            # 关键词搜索
            if search_text:
                log_text = f"{log.get('item_name', '')} {log.get('status', '')} {log.get('time', '')}".lower()
                if search_text not in log_text:
                    continue

            self._filtered_logs.append(log)

        self._update_table()
        self._update_stats()

    def _on_filter(self, event=None):
        """物品筛选处理"""
        self._on_search()

    def _export_logs(self):
        """导出日志"""
        try:
            if not self._filtered_logs:
                messagebox.showwarning("警告", "没有可导出的记录")
                return

            # 生成导出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = os.path.join(
                os.path.dirname(self._log_file),
                f'exchange_log_export_{timestamp}.json'
            )

            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self._filtered_logs, f, ensure_ascii=False, indent=2)

            messagebox.showinfo("成功", f"日志已导出到:\n{export_file}")
            logger.info(f"导出了 {len(self._filtered_logs)} 条兑换记录到 {export_file}")
        except Exception as e:
            logger.error(f"导出兑换日志失败: {e}")
            messagebox.showerror("错误", f"导出失败：{e}")

    def _clear_logs(self):
        """清空所有日志"""
        if not self._logs:
            messagebox.showwarning("警告", "没有可清空的记录")
            return

        if messagebox.askyesno("确认", "确定要清空所有兑换记录吗？此操作不可恢复。"):
            try:
                self._logs = []
                self._filtered_logs = []
                self._update_table()
                self._update_stats()
                self._item_filter['values'] = []

                # 删除日志文件
                if os.path.exists(self._log_file):
                    os.remove(self._log_file)

                messagebox.showinfo("成功", "兑换记录已清空")
                logger.info("清空了所有兑换记录")
            except Exception as e:
                logger.error(f"清空兑换日志失败: {e}")
                messagebox.showerror("错误", f"清空失败：{e}")

    def add_log(self, log_data: Dict):
        """添加一条兑换记录

        Args:
            log_data: 兑换记录数据
        """
        try:
            # 添加时间戳
            log_data['time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 添加到日志列表
            self._logs.append(log_data)

            # 保存到文件
            self._save_logs()

            # 更新显示
            self._filtered_logs = self._logs.copy()
            self._update_table()
            self._update_stats()
            self._update_item_filter()

            logger.info(f"添加兑换记录: {log_data}")
        except Exception as e:
            logger.error(f"添加兑换记录失败: {e}")

    def _save_logs(self):
        """保存日志到文件"""
        try:
            with open(self._log_file, 'w', encoding='utf-8') as f:
                json.dump(self._logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存兑换日志失败: {e}")
            raise
