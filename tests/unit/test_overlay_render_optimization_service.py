"""单元测试：Overlay渲染优化服务"""
import time
import unittest
from unittest.mock import Mock, patch

from services.overlay_render_optimization_service import OverlayRenderOptimizationService
from services.overlay.overlay_service import OverlayTextItem


class TestOverlayRenderOptimizationService(unittest.TestCase):
    """Overlay渲染优化服务测试"""

    def setUp(self):
        """测试前准备"""
        self.service = OverlayRenderOptimizationService(
            optimize_interval_ms=100,
            enable_dirty_tracking=True,
            enable_batch_rendering=True
        )

        # 测试数据
        self.test_text_items = [
            OverlayTextItem(
                text="Item 1",
                x=10,
                y=10,
                width=100,
                height=20,
                color="#00FF00",
                font_size=12
            ),
            OverlayTextItem(
                text="Item 2",
                x=10,
                y=40,
                width=100,
                height=20,
                color="#FF0000",
                font_size=12
            )
        ]

        self.test_regions = [
            {
                'x': 10,
                'y': 10,
                'width': 100,
                'height': 20,
                'name': 'Region 1'
            },
            {
                'x': 10,
                'y': 40,
                'width': 100,
                'height': 20,
                'name': 'Region 2'
            }
        ]

    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.service._optimize_interval_ms, 100)
        self.assertTrue(self.service._enable_dirty_tracking)
        self.assertTrue(self.service._enable_batch_rendering)
        self.assertTrue(self.service._is_content_dirty)
        self.assertTrue(self.service._is_position_dirty)
        self.assertEqual(len(self.service._text_items), 0)
        self.assertEqual(len(self.service._regions), 0)

    def test_update_text_items(self):
        """测试更新文本项"""
        # 第一次更新
        changed = self.service.update_text_items(self.test_text_items)
        self.assertTrue(changed)
        self.assertEqual(len(self.service._text_items), 2)
        self.assertTrue(self.service._is_content_dirty)

        # 相同内容更新
        changed = self.service.update_text_items(self.test_text_items)
        self.assertFalse(changed)

        # 强制更新
        changed = self.service.update_text_items(self.test_text_items, force_full_render=True)
        self.assertTrue(changed)

    def test_update_text_items_with_changes(self):
        """测试更新变化的文本项"""
        # 更新初始内容
        self.service.update_text_items(self.test_text_items)

        # 修改文本内容
        new_items = self.test_text_items.copy()
        new_items[0].text = "Modified Item"

        changed = self.service.update_text_items(new_items)
        self.assertTrue(changed)

        # 修改位置
        new_items[0].x = 20

        changed = self.service.update_text_items(new_items)
        self.assertTrue(changed)

    def test_update_regions(self):
        """测试更新区域"""
        # 第一次更新
        changed = self.service.update_regions(self.test_regions)
        self.assertTrue(changed)
        self.assertEqual(len(self.service._regions), 2)
        self.assertTrue(self.service._is_content_dirty)

        # 相同内容更新
        changed = self.service.update_regions(self.test_regions)
        self.assertFalse(changed)

        # 强制更新
        changed = self.service.update_regions(self.test_regions, force_full_render=True)
        self.assertTrue(changed)

    def test_update_regions_with_changes(self):
        """测试更新变化的区域"""
        # 更新初始内容
        self.service.update_regions(self.test_regions)

        # 修改区域
        new_regions = self.test_regions.copy()
        new_regions[0]['x'] = 20

        changed = self.service.update_regions(new_regions)
        self.assertTrue(changed)

    def test_should_render(self):
        """测试是否需要渲染"""
        target_hwnd = 12345

        # 初始状态应该需要渲染
        should = self.service.should_render(target_hwnd)
        self.assertTrue(should)

        # 清除脏标记
        self.service._is_content_dirty = False
        self.service._is_position_dirty = False

        # 不应该需要渲染
        should = self.service.should_render(target_hwnd)
        self.assertFalse(should)

        # 强制渲染
        should = self.service.should_render(target_hwnd, force=True)
        self.assertTrue(should)

    def test_should_render_with_interval(self):
        """测试渲染间隔控制"""
        target_hwnd = 12345

        # 第一次渲染
        should = self.service.should_render(target_hwnd)
        self.assertTrue(should)

        # 立即再次检查（间隔未到）
        should = self.service.should_render(target_hwnd)
        self.assertFalse(should)

        # 等待间隔
        time.sleep(0.15)

        # 应该可以渲染
        should = self.service.should_render(target_hwnd, force=True)
        self.assertTrue(should)

    @patch('services.overlay_render_optimization_service.win32gui')
    def test_should_render_with_position_change(self, mock_win32gui):
        """测试窗口位置变化触发渲染"""
        target_hwnd = 12345

        # 清除脏标记
        self.service._is_content_dirty = False
        self.service._is_position_dirty = False

        # 第一次调用
        mock_win32gui.GetWindowRect.return_value = (0, 0, 800, 600)
        should = self.service.should_render(target_hwnd)
        self.assertFalse(should)

        # 窗口位置变化
        mock_win32gui.GetWindowRect.return_value = (100, 100, 900, 700)
        should = self.service.should_render(target_hwnd, force=True)
        self.assertTrue(should)
        self.assertTrue(self.service._is_position_dirty)

    @patch('services.overlay_render_optimization_service.win32gui')
    def test_should_render_with_foreground_change(self, mock_win32gui):
        """测试前台窗口变化触发渲染"""
        target_hwnd = 12345

        # 清除脏标记
        self.service._is_content_dirty = False
        self.service._is_position_dirty = False

        # 第一次调用（不在前台）
        mock_win32gui.GetForegroundWindow.return_value = 99999
        should = self.service.should_render(target_hwnd)
        self.assertFalse(should)

        # 窗口变为前台
        mock_win32gui.GetForegroundWindow.return_value = 12345
        should = self.service.should_render(target_hwnd, force=True)
        self.assertTrue(should)

    def test_prepare_render(self):
        """测试准备渲染"""
        # 内容脏
        should, mode = self.service.prepare_render()
        self.assertTrue(should)
        self.assertEqual(mode, "full")

        # 清除内容脏
        self.service._is_content_dirty = False

        # 位置脏
        should, mode = self.service.prepare_render()
        self.assertTrue(should)
        self.assertEqual(mode, "incremental")

        # 都不脏
        self.service._is_position_dirty = False
        should, mode = self.service.prepare_render()
        self.assertFalse(should)
        self.assertEqual(mode, "none")

    def test_on_render_complete(self):
        """测试渲染完成回调"""
        # 模拟渲染
        self.service.on_render_complete(10.5, "full")

        stats = self.service.get_stats()
        self.assertEqual(stats['total_renders'], 1)
        self.assertEqual(stats['full_renders'], 1)
        self.assertAlmostEqual(stats['average_render_time_ms'], 10.5)

        # 模拟多次渲染
        for i in range(5):
            self.service.on_render_complete(5.0 + i, "incremental")

        stats = self.service.get_stats()
        self.assertEqual(stats['total_renders'], 6)
        self.assertEqual(stats['incremental_renders'], 5)

        # 清除脏标记
        self.assertFalse(self.service._is_content_dirty)
        self.assertFalse(self.service._is_position_dirty)

    def test_get_render_mode(self):
        """测试获取渲染模式"""
        # 内容脏
        self.service._is_content_dirty = True
        mode = self.service.get_render_mode()
        self.assertEqual(mode, "full")

        # 只有位置脏
        self.service._is_content_dirty = False
        self.service._is_position_dirty = True
        mode = self.service.get_render_mode()
        self.assertEqual(mode, "incremental")

    def test_force_full_render(self):
        """测试强制全量渲染"""
        # 清除脏标记
        self.service._is_content_dirty = False
        self.service._is_position_dirty = False

        # 强制全量渲染
        self.service.force_full_render()

        self.assertTrue(self.service._is_content_dirty)
        self.assertTrue(self.service._is_position_dirty)

    def test_clear_content(self):
        """测试清除内容"""
        # 添加内容
        self.service.update_text_items(self.test_text_items)
        self.service.update_regions(self.test_regions)

        self.assertEqual(len(self.service._text_items), 2)
        self.assertEqual(len(self.service._regions), 2)

        # 清除内容
        self.service.clear_content()

        self.assertEqual(len(self.service._text_items), 0)
        self.assertEqual(len(self.service._regions), 0)
        self.assertTrue(self.service._is_content_dirty)

    def test_get_stats(self):
        """测试获取统计信息"""
        stats = self.service.get_stats()

        self.assertIn('total_renders', stats)
        self.assertIn('skipped_renders', stats)
        self.assertIn('full_renders', stats)
        self.assertIn('incremental_renders', stats)
        self.assertIn('average_render_time_ms', stats)
        self.assertIn('text_items_count', stats)
        self.assertIn('regions_count', stats)
        self.assertIn('cached_canvas_items', stats)
        self.assertIn('cached_region_items', stats)
        self.assertIn('content_dirty', stats)
        self.assertIn('position_dirty', stats)
        self.assertIn('sync_count', stats)

    def test_reset_stats(self):
        """测试重置统计信息"""
        # 添加一些统计数据
        self.service._stats['total_renders'] = 10
        self.service._stats['skipped_renders'] = 5
        self.service._sync_count = 15

        self.service.reset_stats()

        self.assertEqual(self.service._stats['total_renders'], 0)
        self.assertEqual(self.service._stats['skipped_renders'], 0)
        self.assertEqual(self.service._sync_count, 0)

    def test_enable_disable_dirty_tracking(self):
        """测试启用/禁用脏标记跟踪"""
        self.service.disable_dirty_tracking()
        self.assertFalse(self.service._enable_dirty_tracking)

        self.service.enable_dirty_tracking()
        self.assertTrue(self.service._enable_dirty_tracking)

    def test_get_text_items(self):
        """测试获取文本项"""
        self.service.update_text_items(self.test_text_items)

        items = self.service.get_text_items()
        self.assertEqual(len(items), 2)

        # 修改返回的列表不应该影响原始数据
        items.clear()
        self.assertEqual(len(self.service._text_items), 2)

    def test_get_regions(self):
        """测试获取区域"""
        self.service.update_regions(self.test_regions)

        regions = self.service.get_regions()
        self.assertEqual(len(regions), 2)

        # 修改返回的列表不应该影响原始数据
        regions.clear()
        self.assertEqual(len(self.service._regions), 2)

    def test_set_optimize_interval(self):
        """测试设置优化间隔"""
        self.service.set_optimize_interval(200)
        self.assertEqual(self.service._optimize_interval_ms, 200)

    def test_text_items_length_difference(self):
        """测试文本项长度不同"""
        self.service.update_text_items(self.test_text_items)

        # 不同长度应该返回变化
        new_items = self.test_text_items[:1]
        changed = self.service.update_text_items(new_items)
        self.assertTrue(changed)

    def test_regions_length_difference(self):
        """测试区域长度不同"""
        self.service.update_regions(self.test_regions)

        # 不同长度应该返回变化
        new_regions = self.test_regions[:1]
        changed = self.service.update_regions(new_regions)
        self.assertTrue(changed)


if __name__ == '__main__':
    unittest.main()
