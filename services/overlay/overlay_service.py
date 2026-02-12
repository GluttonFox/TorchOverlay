import tkinter as tk
from dataclasses import dataclass
from typing import Any

from services.overlay.target_window import get_client_rect_in_screen


@dataclass
class OverlayTextItem:
    """覆盖层上的文本项"""
    text: str
    x: int  # 相对于client区域的x坐标
    y: int  # 相对于client区域的y坐标
    width: int
    height: int
    color: str = "#00FF00"  # 默认绿色
    font_size: int = 12
    background: str = "#000000"  # 背景色（半透明黑色）


class OverlayService:
    """覆盖层服务：在目标窗口上显示识别文本"""

    def __init__(self):
        self._window: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._target_hwnd: int | None = None
        self._text_items: list[Any] = []
        self._visible = False
        self._overlay_hwnd: int | None = None  # overlay窗口的句柄

    def create_overlay(self, target_hwnd: int):
        """创建覆盖层窗口"""
        if self._window is not None:
            return False

        self._target_hwnd = target_hwnd

        # 获取目标窗口的client区域位置
        x, y, width, height = get_client_rect_in_screen(target_hwnd)

        # 创建覆盖层窗口
        self._window = tk.Toplevel()
        self._window.title("OCR Overlay")
        self._window.geometry(f"{width}x{height}+{x}+{y}")
        self._window.overrideredirect(True)  # 无边框窗口
        self._window.attributes("-alpha", 0.9)  # 设置窗口透明度（0.9 = 90%不透明）
        # 不使用 -topmost，而是设置为游戏窗口的子窗口

        # 获取overlay窗口的句柄
        import win32gui
        self._overlay_hwnd = int(self._window.winfo_id())

        # 设置overlay窗口为游戏窗口的子窗口
        try:
            win32gui.SetParent(self._overlay_hwnd, target_hwnd)
        except Exception:
            pass  # 如果设置失败，继续执行

        # 创建画布（使用透明效果）
        try:
            # 尝试创建透明画布
            self._canvas = tk.Canvas(
                self._window,
                width=width,
                height=height,
                highlightthickness=0,
            )
            self._window.attributes("-transparentcolor", "white")
            self._canvas.config(bg="white")
        except Exception:
            # 如果透明失败，使用默认背景
            self._canvas = tk.Canvas(
                self._window,
                width=width,
                height=height,
                bg="#000000",
                highlightthickness=0,
            )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # 绑定窗口位置同步和可见性检查
        self._window.after(100, self._sync_window_position)

        return True

    def _sync_window_position(self):
        """同步覆盖层窗口与目标窗口的位置和可见性"""
        if self._window is None or self._target_hwnd is None:
            return

        try:
            import win32gui
            if not win32gui.IsWindow(self._target_hwnd):
                self.close()
                return

            # 检查目标窗口是否在前台
            foreground_hwnd = win32gui.GetForegroundWindow()
            target_is_foreground = (foreground_hwnd == self._target_hwnd)

            # 如果目标窗口不在前台，隐藏overlay
            if not target_is_foreground and self._visible:
                self._window.withdraw()
            # 如果目标窗口在前台，显示overlay
            elif target_is_foreground and self._visible:
                self._window.deiconify()

            # 获取新的client区域位置
            x, y, width, height = get_client_rect_in_screen(self._target_hwnd)

            # 更新覆盖层窗口位置和大小
            self._window.geometry(f"{width}x{height}+{x}+{y}")
            self._canvas.config(width=width, height=height)

            # 重新绘制文本
            if self._text_items:
                self._redraw_texts()

        except Exception:
            pass

        # 继续同步
        if self._visible:
            self._window.after(100, self._sync_window_position)

    def show_texts(self, text_items: list[OverlayTextItem]):
        """在覆盖层上显示文本"""
        if self._canvas is None:
            return

        # 清除现有文本
        self._canvas.delete("all")
        self._text_items = text_items.copy()

        # 绘制每个文本项
        for item in text_items:
            self._draw_text_item(item)

        self._visible = True

    def _draw_text_item(self, item: OverlayTextItem):
        """绘制单个文本项"""
        if self._canvas is None:
            return

        # 计算文本框大小
        text_width = len(item.text) * item.font_size * 0.6  # 估算宽度
        text_height = item.font_size + 4

        # 绘制背景（半透明效果需要用stipple模拟）
        self._canvas.create_rectangle(
            item.x,
            item.y,
            item.x + max(item.width, int(text_width)),
            item.y + max(item.height, text_height),
            fill=item.background,
            outline=item.color,
            stipple="gray50",  # 半透明效果
        )

        # 绘制文本
        self._canvas.create_text(
            item.x + 5,
            item.y + 5,
            text=item.text,
            fill=item.color,
            font=("Arial", item.font_size, "bold"),
            anchor="nw",
        )

        # 绘制边框
        self._canvas.create_rectangle(
            item.x,
            item.y,
            item.x + item.width,
            item.y + item.height,
            outline="#FFFF00",  # 黄色边框标记原始识别区域
            width=2,
        )

    def _redraw_texts(self):
        """重新绘制所有文本"""
        if self._canvas is None:
            return

        self._canvas.delete("all")
        for item in self._text_items:
            self._draw_text_item(item)

    def clear(self):
        """清除覆盖层上的所有内容"""
        if self._canvas is not None:
            self._canvas.delete("all")
        self._text_items = []

    def close(self):
        """关闭覆盖层"""
        self._visible = False
        if self._window is not None:
            self._window.destroy()
            self._window = None
            self._canvas = None
        self._text_items = []

    def is_visible(self) -> bool:
        """检查覆盖层是否可见"""
        return self._visible and self._window is not None
