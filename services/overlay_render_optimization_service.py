"""Overlay渲染优化服务 - 优化Overlay渲染性能"""
import time
import win32gui
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from core.logger import get_logger
from services.overlay.overlay_service import OverlayTextItem

logger = get_logger(__name__)


@dataclass
class RenderCacheItem:
    """渲染缓存项"""
    canvas_id: int  # Canvas item ID
    last_modified: float  # 最后修改时间
    is_dirty: bool  # 是否需要重绘


class OverlayRenderOptimizationService:
    """Overlay渲染优化服务

    通过脏标记、增量更新、批量渲染等策略优化Overlay性能。
    """

    def __init__(
        self,
        optimize_interval_ms: int = 100,
        enable_dirty_tracking: bool = True,
        enable_batch_rendering: bool = True
    ):
        """初始化渲染优化服务

        Args:
            optimize_interval_ms: 优化检查间隔（毫秒）
            enable_dirty_tracking: 是否启用脏标记跟踪
            enable_batch_rendering: 是否启用批量渲染
        """
        self._optimize_interval_ms = optimize_interval_ms
        self._enable_dirty_tracking = enable_dirty_tracking
        self._enable_batch_rendering = enable_batch_rendering

        # 渲染状态
        self._text_items: List[OverlayTextItem] = []
        self._regions: List[Dict[str, Any]] = []
        self._canvas_item_cache: Dict[str, RenderCacheItem] = {}  # Canvas item缓存
        self._region_item_cache: Dict[str, RenderCacheItem] = {}  # 区域item缓存

        # 脏标记
        self._is_content_dirty = True  # 内容是否需要重绘
        self._is_position_dirty = True  # 位置是否需要重绘

        # 统计信息
        self._stats = {
            'total_renders': 0,
            'skipped_renders': 0,
            'full_renders': 0,
            'incremental_renders': 0,
            'average_render_time_ms': 0.0
        }
        self._render_times: List[float] = []

        # 同步控制
        self._last_sync_time = 0.0
        self._sync_count = 0

        # 目标窗口信息
        self._target_hwnd: Optional[int] = None
        self._last_window_position: Optional[tuple[int, int, int, int]] = None
        self._last_foreground_check: Optional[bool] = None

    def update_text_items(self, text_items: List[OverlayTextItem], force_full_render: bool = False) -> bool:
        """更新文本项（智能更新）

        Args:
            text_items: 新的文本项列表
            force_full_render: 是否强制全量渲染

        Returns:
            内容是否发生变化
        """
        # 检查内容是否发生变化
        if not force_full_render and self._are_text_items_same(text_items):
            # logger.debug("文本项未变化，跳过更新")
            return False

        # 更新文本项
        self._text_items = text_items.copy()

        # 标记内容脏
        if self._enable_dirty_tracking:
            self._is_content_dirty = True
            self._invalidate_text_cache_items()

        # logger.debug(f"文本项已更新，共 {len(text_items)} 个项")
        return True

    def update_regions(self, regions: List[Dict[str, Any]], force_full_render: bool = False) -> bool:
        """更新区域

        Args:
            regions: 新的区域列表
            force_full_render: 是否强制全量渲染

        Returns:
            内容是否发生变化
        """
        # 检查区域是否发生变化
        if not force_full_render and self._are_regions_same(regions):
            # logger.debug("区域未变化，跳过更新")
            return False

        # 更新区域
        self._regions = regions.copy()

        # 标记内容脏
        if self._enable_dirty_tracking:
            self._is_content_dirty = True
            self._invalidate_region_cache_items()

        # logger.debug(f"区域已更新，共 {len(regions)} 个区域")
        return True

    def should_render(self, target_hwnd: int, force: bool = False) -> bool:
        """检查是否需要渲染

        Args:
            target_hwnd: 目标窗口句柄
            force: 是否强制渲染

        Returns:
            是否需要渲染
        """
        current_time = time.time()

        # 检查优化间隔
        time_since_last_render = (current_time - self._last_sync_time) * 1000
        if not force and time_since_last_render < self._optimize_interval_ms:
            return False

        # 检查脏标记
        if not force and not self._is_content_dirty and not self._is_position_dirty:
            return False

        # 检查目标窗口
        if self._target_hwnd is None:
            self._target_hwnd = target_hwnd
            return True

        # 检查窗口位置是否变化
        position_changed = self._is_window_position_changed(target_hwnd)
        if position_changed:
            self._is_position_dirty = True

        # 检查前台窗口状态
        foreground_changed = self._is_foreground_window_changed(target_hwnd)

        # 如果既没有内容变化，也没有位置变化，也没有前台变化，则不需要渲染
        if not force and not self._is_content_dirty and not position_changed and not foreground_changed:
            self._stats['skipped_renders'] += 1
            return False

        self._last_sync_time = current_time
        self._sync_count += 1

        return True

    def prepare_render(self) -> tuple[bool, str]:
        """准备渲染

        Returns:
            (是否需要渲染, 渲染模式: "full" | "incremental" | "none")
        """
        if not self._is_content_dirty and not self._is_position_dirty:
            self._stats['skipped_renders'] += 1
            return False, "none"

        # 确定渲染模式
        if self._is_content_dirty:
            render_mode = "full"
            self._stats['full_renders'] += 1
        else:
            render_mode = "incremental"
            self._stats['incremental_renders'] += 1

        return True, render_mode

    def on_render_complete(self, render_time_ms: float, render_mode: str) -> None:
        """渲染完成回调

        Args:
            render_time_ms: 渲染耗时（毫秒）
            render_mode: 渲染模式
        """
        self._stats['total_renders'] += 1

        # 记录渲染时间
        self._render_times.append(render_time_ms)
        if len(self._render_times) > 100:  # 只保留最近100次
            self._render_times.pop(0)

        # 计算平均渲染时间
        avg_time = sum(self._render_times) / len(self._render_times)
        self._stats['average_render_time_ms'] = avg_time

        # 清除脏标记
        if render_mode == "full":
            self._is_content_dirty = False
        self._is_position_dirty = False

        # logger.debug(f"渲染完成: 模式={render_mode}, 耗时={render_time_ms:.2f}ms")

    def get_render_mode(self) -> str:
        """获取渲染模式

        Returns:
            渲染模式: "full" | "incremental"
        """
        if self._is_content_dirty:
            return "full"
        return "incremental"

    def force_full_render(self) -> None:
        """强制下次全量渲染"""
        self._is_content_dirty = True
        self._is_position_dirty = True
        self._invalidate_all_cache_items()

    def clear_content(self) -> None:
        """清除所有内容"""
        self._text_items = []
        self._regions = []
        self._is_content_dirty = True
        self._invalidate_all_cache_items()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            **self._stats,
            'text_items_count': len(self._text_items),
            'regions_count': len(self._regions),
            'cached_canvas_items': len(self._canvas_item_cache),
            'cached_region_items': len(self._region_item_cache),
            'content_dirty': self._is_content_dirty,
            'position_dirty': self._is_position_dirty,
            'sync_count': self._sync_count
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            'total_renders': 0,
            'skipped_renders': 0,
            'full_renders': 0,
            'incremental_renders': 0,
            'average_render_time_ms': 0.0
        }
        self._render_times = []
        self._sync_count = 0

    def enable_dirty_tracking(self) -> None:
        """启用脏标记跟踪"""
        self._enable_dirty_tracking = True
        logger.info("脏标记跟踪已启用")

    def disable_dirty_tracking(self) -> None:
        """禁用脏标记跟踪"""
        self._enable_dirty_tracking = False
        logger.info("脏标记跟踪已禁用")

    def _are_text_items_same(self, new_items: List[OverlayTextItem]) -> bool:
        """检查文本项是否相同

        Args:
            new_items: 新的文本项列表

        Returns:
            是否相同
        """
        if len(self._text_items) != len(new_items):
            return False

        for old_item, new_item in zip(self._text_items, new_items):
            if (old_item.text != new_item.text or
                old_item.x != new_item.x or
                old_item.y != new_item.y or
                old_item.width != new_item.width or
                old_item.height != new_item.height or
                old_item.color != new_item.color or
                old_item.font_size != new_item.font_size):
                return False

        return True

    def _are_regions_same(self, new_regions: List[Dict[str, Any]]) -> bool:
        """检查区域是否相同

        Args:
            new_regions: 新的区域列表

        Returns:
            是否相同
        """
        if len(self._regions) != len(new_regions):
            return False

        for old_region, new_region in zip(self._regions, new_regions):
            if (old_region.get('x') != new_region.get('x') or
                old_region.get('y') != new_region.get('y') or
                old_region.get('width') != new_region.get('width') or
                old_region.get('height') != new_region.get('height') or
                old_region.get('name') != new_region.get('name')):
                return False

        return True

    def _is_window_position_changed(self, target_hwnd: int) -> bool:
        """检查窗口位置是否变化

        Args:
            target_hwnd: 目标窗口句柄

        Returns:
            是否变化
        """
        try:
            x, y, width, height = win32gui.GetWindowRect(target_hwnd)
            current_position = (x, y, width, height)

            if self._last_window_position is None:
                self._last_window_position = current_position
                return False

            if current_position != self._last_window_position:
                self._last_window_position = current_position
                return True

            return False
        except Exception as e:
            logger.error(f"检查窗口位置失败: {e}")
            return False

    def _is_foreground_window_changed(self, target_hwnd: int) -> bool:
        """检查前台窗口是否变化

        Args:
            target_hwnd: 目标窗口句柄

        Returns:
            是否变化
        """
        try:
            foreground_hwnd = win32gui.GetForegroundWindow()
            target_is_foreground = (foreground_hwnd == target_hwnd)

            if self._last_foreground_check is None:
                self._last_foreground_check = target_is_foreground
                return False

            if target_is_foreground != self._last_foreground_check:
                self._last_foreground_check = target_is_foreground
                return True

            return False
        except Exception as e:
            logger.error(f"检查前台窗口失败: {e}")
            return False

    def _invalidate_text_cache_items(self) -> None:
        """标记所有文本缓存项为脏"""
        for cache_item in self._canvas_item_cache.values():
            cache_item.is_dirty = True

    def _invalidate_region_cache_items(self) -> None:
        """标记所有区域缓存项为脏"""
        for cache_item in self._region_item_cache.values():
            cache_item.is_dirty = True

    def _invalidate_all_cache_items(self) -> None:
        """标记所有缓存项为脏"""
        self._invalidate_text_cache_items()
        self._invalidate_region_cache_items()

    def get_text_items(self) -> List[OverlayTextItem]:
        """获取文本项列表

        Returns:
            文本项列表
        """
        return self._text_items.copy()

    def get_regions(self) -> List[Dict[str, Any]]:
        """获取区域列表

        Returns:
            区域列表
        """
        return self._regions.copy()

    def set_optimize_interval(self, interval_ms: int) -> None:
        """设置优化间隔

        Args:
            interval_ms: 优化间隔（毫秒）
        """
        self._optimize_interval_ms = interval_ms
        logger.info(f"优化间隔已设置为 {interval_ms}ms")
