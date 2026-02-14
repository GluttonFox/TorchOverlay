import tkinter as tk
from dataclasses import dataclass
from typing import Any

from services.interfaces import IOverlayService
from services.overlay.target_window import get_client_rect_in_screen
from core.logger import get_logger

logger = get_logger(__name__)


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
    background: str = ""  # 背景色（空字符串表示透明）


class OverlayService(IOverlayService):
    """覆盖层服务：在目标窗口上显示识别文本"""

    def __init__(self):
        self._window: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._target_hwnd: int | None = None
        self._text_items: list[Any] = []
        self._regions: list[dict[str, Any]] = []
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
        self._window.attributes("-alpha", 0.95)  # 设置窗口透明度（0.95 = 95%不透明，更明显）
        self._window.attributes("-topmost", True)  # 设置为顶层窗口

        # 获取overlay窗口的句柄
        import win32gui
        import win32con
        self._overlay_hwnd = int(self._window.winfo_id())

        # 设置overlay窗口为游戏窗口的子窗口，确保跟随游戏窗口
        try:
            win32gui.SetParent(self._overlay_hwnd, target_hwnd)
        except Exception:
            pass  # 如果设置失败，继续执行

        # 设置透明色（将灰色设为透明）
        self._window.attributes("-transparentcolor", "#CCCCCC")

        # 创建画布，使用灰色背景（会被透明化）
        self._canvas = tk.Canvas(
            self._window,
            width=width,
            height=height,
            highlightthickness=0,
            bg="#CCCCCC"  # 灰色背景会被透明化
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
                logger.warning("目标窗口已关闭，关闭overlay")
                self.close()
                return

            # 检查目标窗口是否在前台
            foreground_hwnd = win32gui.GetForegroundWindow()
            target_is_foreground = (foreground_hwnd == self._target_hwnd)

            # 只在目标窗口在前台时显示overlay
            if target_is_foreground and self._visible:
                self._window.deiconify()
                # logger.debug("Overlay窗口已显示（目标窗口在前台）")
            else:
                if not target_is_foreground and self._visible:
                    # logger.debug("Overlay窗口已隐藏（目标窗口不在前台）")
                    pass
                self._window.withdraw()

            # 获取新的client区域位置
            x, y, width, height = get_client_rect_in_screen(self._target_hwnd)

            # 更新覆盖层窗口位置和大小
            self._window.geometry(f"{width}x{height}+{x}+{y}")
            self._canvas.config(width=width, height=height)

            # 重新绘制文本
            if self._text_items and target_is_foreground:
                self._redraw_texts()

        except Exception as e:
            logger.error(f"同步窗口位置时出错: {e}")

        # 继续同步
        if self._visible:
            self._window.after(100, self._sync_window_position)

    def show_texts(self, text_items: list[OverlayTextItem]):
        """在覆盖层上显示文本"""
        if self._canvas is None:
            logger.warning("Canvas为空，无法显示文本")
            return

        # 清除现有内容
        self._canvas.delete("all")
        self._text_items = text_items.copy()

        # 绘制每个文本项
        for item in text_items:
            self._draw_text_item(item)
            # logger.debug(f"显示文本: {item.text} 在位置 ({item.x}, {item.y})")

        self._visible = True
        logger.info(f"Overlay已显示，包含 {len(text_items)} 个文本项")

        # 立即触发一次窗口位置同步
        if self._window:
            self._sync_window_position()

    def show_regions(self, regions: list[dict[str, Any]]):
        """在覆盖层上显示区域边框（用于测试）"""
        if self._canvas is None:
            return

        # 清除现有内容
        self._canvas.delete("all")
        self._regions = regions.copy()

        # 绘制每个区域边框
        for region in regions:
            self._draw_region(region)

        self._visible = True

    def _draw_region(self, region: dict[str, Any]):
        """绘制单个区域边框"""
        if self._canvas is None:
            return

        x = region['x']
        y = region['y']
        width = region['width']
        height = region['height']
        name = region.get('name', '')

        # 绘制边框（红色）
        self._canvas.create_rectangle(
            x,
            y,
            x + width,
            y + height,
            outline="#FF0000",  # 红色边框
            width=2,
        )

        # 绘制区域名称（在边框上方）
        if name:
            self._canvas.create_text(
                x,
                y - 12,
                text=name,
                fill="#FF0000",
                font=("Arial", 10, "bold"),
                anchor="nw",
            )

    def _draw_text_item(self, item: OverlayTextItem):
        """绘制单个文本项"""
        if self._canvas is None:
            return

        # 计算文本的水平居中位置
        center_x = item.x + item.width // 2

        # 绘制背景（如果指定了背景色）
        if item.background and item.background != "":
            self._canvas.create_rectangle(
                item.x,
                item.y,
                item.x + item.width,
                item.y + item.height,
                fill=item.background,
                outline=""
            )

        # 绘制文本（居中靠上）
        self._canvas.create_text(
            center_x,
            item.y + 10,
            text=item.text,
            fill=item.color,
            font=("Arial", item.font_size, "bold"),
            anchor="n",
            justify="center"
        )

        # logger.debug(f"绘制文本: {item.text} 在 ({center_x}, {item.y + 10}), 颜色: {item.color}")

    def _redraw_texts(self):
        """重新绘制所有内容"""
        if self._canvas is None:
            return

        self._canvas.delete("all")

        # 先绘制区域边框（如果有）
        if self._regions:
            for region in self._regions:
                self._draw_region(region)

        # 再绘制文本（如果有）
        for item in self._text_items:
            self._draw_text_item(item)

    def clear(self):
        """清除覆盖层上的所有内容"""
        if self._canvas is not None:
            self._canvas.delete("all")
        self._text_items = []
        self._regions = []

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
