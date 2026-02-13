"""单元测试：窗口缓存服务"""
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
import threading

from services.window_cache_service import WindowCacheService, WindowInfo


class TestWindowCacheService(unittest.TestCase):
    """窗口缓存服务测试"""

    def setUp(self):
        """测试前准备"""
        self.service = WindowCacheService(cache_ttl_seconds=2, enable_cache=True)

    def tearDown(self):
        """测试后清理"""
        self.service.clear_cache()

    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.service._cache_ttl, 2)
        self.assertTrue(self.service._enable_cache)
        self.assertEqual(len(self.service._window_cache), 0)
        self.assertEqual(len(self.service._hwnd_by_name), 0)

    @patch('services.window_cache_service.win32gui')
    def test_get_window_info_success(self, mock_win32gui):
        """测试获取窗口信息成功"""
        # 模拟win32api调用
        mock_win32gui.IsWindow.return_value = True
        mock_win32gui.GetWindowText.return_value = "Test Window"
        mock_win32gui.GetClassName.return_value = "TestClass"
        mock_win32gui.GetClientRect.return_value = (0, 0, 800, 600)
        mock_win32gui.ClientToScreen.return_value = (100, 100)
        mock_win32gui.GetWindowRect.return_value = (90, 90, 900, 700)
        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32gui.IsIconic.return_value = False

        with patch('services.window_cache_service.win32process') as mock_win32process:
            mock_win32process.GetWindowThreadProcessId.return_value = (1234, 5678)

            hwnd = 12345
            window_info = self.service.get_window_info(hwnd)

            self.assertIsNotNone(window_info)
            self.assertEqual(window_info.hwnd, hwnd)
            self.assertEqual(window_info.title, "Test Window")
            self.assertEqual(window_info.class_name, "TestClass")
            self.assertEqual(window_info.client_rect, (100, 100, 800, 600))
            self.assertEqual(window_info.window_rect, (90, 90, 810, 610))
            self.assertTrue(window_info.is_visible)
            self.assertFalse(window_info.is_minimized)
            self.assertEqual(window_info.process_id, 5678)
            self.assertEqual(window_info.thread_id, 1234)

    @patch('services.window_cache_service.win32gui')
    def test_get_window_info_cache_hit(self, mock_win32gui):
        """测试缓存命中"""
        mock_win32gui.IsWindow.return_value = True
        mock_win32gui.GetWindowText.return_value = "Test Window"
        mock_win32gui.GetClassName.return_value = "TestClass"
        mock_win32gui.GetClientRect.return_value = (0, 0, 800, 600)
        mock_win32gui.ClientToScreen.return_value = (100, 100)
        mock_win32gui.GetWindowRect.return_value = (90, 90, 900, 700)
        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32gui.IsIconic.return_value = False

        with patch('services.window_cache_service.win32process') as mock_win32process:
            mock_win32process.GetWindowThreadProcessId.return_value = (1234, 5678)

            hwnd = 12345

            # 第一次查询（未命中缓存）
            info1 = self.service.get_window_info(hwnd)
            stats1 = self.service.get_stats()
            self.assertEqual(stats1['api_calls'], 1)

            # 第二次查询（命中缓存）
            info2 = self.service.get_window_info(hwnd)
            stats2 = self.service.get_stats()
            self.assertEqual(stats2['api_calls'], 1)  # API调用次数不变
            self.assertEqual(stats2['cache_hits'], 1)

            # 窗口信息应该相同
            self.assertEqual(info1.hwnd, info2.hwnd)
            self.assertEqual(info1.title, info2.title)

    @patch('services.window_cache_service.win32gui')
    def test_get_window_info_cache_expired(self, mock_win32gui):
        """测试缓存过期"""
        mock_win32gui.IsWindow.return_value = True
        mock_win32gui.GetWindowText.return_value = "Test Window"
        mock_win32gui.GetClassName.return_value = "TestClass"
        mock_win32gui.GetClientRect.return_value = (0, 0, 800, 600)
        mock_win32gui.ClientToScreen.return_value = (100, 100)
        mock_win32gui.GetWindowRect.return_value = (90, 90, 900, 700)
        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32gui.IsIconic.return_value = False

        with patch('services.window_cache_service.win32process') as mock_win32process:
            mock_win32process.GetWindowThreadProcessId.return_value = (1234, 5678)

            hwnd = 12345

            # 第一次查询
            self.service.get_window_info(hwnd)
            stats1 = self.service.get_stats()
            self.assertEqual(stats1['api_calls'], 1)

            # 等待缓存过期
            time.sleep(2.5)

            # 第二次查询（缓存过期，重新查询）
            self.service.get_window_info(hwnd)
            stats2 = self.service.get_stats()
            self.assertEqual(stats2['api_calls'], 2)  # API调用次数增加
            self.assertEqual(stats2['cache_misses'], 2)  # 两次都是miss

    @patch('services.window_cache_service.win32gui')
    def test_get_window_info_force_refresh(self, mock_win32gui):
        """测试强制刷新"""
        mock_win32gui.IsWindow.return_value = True
        mock_win32gui.GetWindowText.return_value = "Test Window"
        mock_win32gui.GetClassName.return_value = "TestClass"
        mock_win32gui.GetClientRect.return_value = (0, 0, 800, 600)
        mock_win32gui.ClientToScreen.return_value = (100, 100)
        mock_win32gui.GetWindowRect.return_value = (90, 90, 900, 700)
        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32gui.IsIconic.return_value = False

        with patch('services.window_cache_service.win32process') as mock_win32process:
            mock_win32process.GetWindowThreadProcessId.return_value = (1234, 5678)

            hwnd = 12345

            # 第一次查询
            self.service.get_window_info(hwnd)
            stats1 = self.service.get_stats()
            self.assertEqual(stats1['api_calls'], 1)

            # 强制刷新
            self.service.get_window_info(hwnd, force_refresh=True)
            stats2 = self.service.get_stats()
            self.assertEqual(stats2['api_calls'], 2)  # API调用次数增加

    @patch('services.window_cache_service.win32gui')
    def test_get_hwnd_by_title(self, mock_win32gui):
        """测试根据标题查找窗口"""
        def enum_callback(callback, _):
            """模拟枚举窗口回调"""
            # 添加一个匹配的窗口
            callback(12345, None)
            return True

        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32gui.GetWindowText.side_effect = lambda hwnd: "Test Window" if hwnd == 12345 else ""
        mock_win32gui.EnumWindows.side_effect = enum_callback

        hwnd = self.service.get_hwnd_by_title("Test")

        self.assertEqual(hwnd, 12345)

    @patch('services.window_cache_service.win32gui')
    def test_get_hwnd_by_title_cache(self, mock_win32gui):
        """测试窗口句柄缓存"""
        def enum_callback(callback, _):
            callback(12345, None)
            return True

        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32gui.GetWindowText.return_value = "Test Window"
        mock_win32gui.EnumWindows.side_effect = enum_callback

        # 第一次查询
        hwnd1 = self.service.get_hwnd_by_title("Test")
        stats1 = self.service.get_stats()

        # 第二次查询（命中缓存）
        hwnd2 = self.service.get_hwnd_by_title("Test")
        stats2 = self.service.get_stats()

        self.assertEqual(hwnd1, hwnd2)
        self.assertEqual(stats2['api_calls'], stats1['api_calls'])  # API调用次数不变
        self.assertEqual(stats2['cache_hits'] - stats1['cache_hits'], 1)  # 缓存命中增加

    def test_get_client_rect(self):
        """测试获取客户区域"""
        with patch.object(self.service, 'get_window_info') as mock_get:
            mock_info = WindowInfo(
                hwnd=12345,
                title="Test",
                class_name="TestClass",
                client_rect=(100, 100, 800, 600),
                window_rect=(90, 90, 810, 610),
                is_visible=True,
                is_minimized=False,
                process_id=5678,
                thread_id=1234,
                timestamp=time.time()
            )
            mock_get.return_value = mock_info

            rect = self.service.get_client_rect(12345)
            self.assertEqual(rect, (100, 100, 800, 600))

    def test_get_window_rect(self):
        """测试获取窗口区域"""
        with patch.object(self.service, 'get_window_info') as mock_get:
            mock_info = WindowInfo(
                hwnd=12345,
                title="Test",
                class_name="TestClass",
                client_rect=(100, 100, 800, 600),
                window_rect=(90, 90, 810, 610),
                is_visible=True,
                is_minimized=False,
                process_id=5678,
                thread_id=1234,
                timestamp=time.time()
            )
            mock_get.return_value = mock_info

            rect = self.service.get_window_rect(12345)
            self.assertEqual(rect, (90, 90, 810, 610))

    def test_is_window_visible(self):
        """测试检查窗口是否可见"""
        with patch.object(self.service, 'get_window_info') as mock_get:
            mock_info = WindowInfo(
                hwnd=12345,
                title="Test",
                class_name="TestClass",
                client_rect=(100, 100, 800, 600),
                window_rect=(90, 90, 810, 610),
                is_visible=True,
                is_minimized=False,
                process_id=5678,
                thread_id=1234,
                timestamp=time.time()
            )
            mock_get.return_value = mock_info

            visible = self.service.is_window_visible(12345)
            self.assertTrue(visible)

    def test_is_window_minimized(self):
        """测试检查窗口是否最小化"""
        with patch.object(self.service, 'get_window_info') as mock_get:
            mock_info = WindowInfo(
                hwnd=12345,
                title="Test",
                class_name="TestClass",
                client_rect=(100, 100, 800, 600),
                window_rect=(90, 90, 810, 610),
                is_visible=True,
                is_minimized=True,
                process_id=5678,
                thread_id=1234,
                timestamp=time.time()
            )
            mock_get.return_value = mock_info

            minimized = self.service.is_window_minimized(12345)
            self.assertTrue(minimized)

    def test_clear_cache(self):
        """测试清理缓存"""
        # 添加一些缓存数据
        self.service._window_cache[12345] = MagicMock()
        self.service._hwnd_by_name["Test"] = 12345

        self.assertEqual(len(self.service._window_cache), 1)
        self.assertEqual(len(self.service._hwnd_by_name), 1)

        # 清理缓存
        self.service.clear_cache()

        self.assertEqual(len(self.service._window_cache), 0)
        self.assertEqual(len(self.service._hwnd_by_name), 0)

    def test_invalidate_cache(self):
        """测试使缓存失效"""
        self.service._window_cache[12345] = MagicMock()
        self.service._hwnd_by_name["Test"] = 12345

        # 使特定窗口缓存失效
        self.service.invalidate_cache(12345)

        self.assertNotIn(12345, self.service._window_cache)
        self.assertNotIn("Test", self.service._hwnd_by_name)

    def test_invalidate_cache_all(self):
        """测试清理所有缓存"""
        self.service._window_cache[12345] = MagicMock()
        self.service._window_cache[67890] = MagicMock()
        self.service._hwnd_by_name["Test1"] = 12345
        self.service._hwnd_by_name["Test2"] = 67890

        self.service.invalidate_cache()

        self.assertEqual(len(self.service._window_cache), 0)
        self.assertEqual(len(self.service._hwnd_by_name), 0)

    def test_get_stats(self):
        """测试获取统计信息"""
        stats = self.service.get_stats()

        self.assertIn('total_queries', stats)
        self.assertIn('cache_hits', stats)
        self.assertIn('cache_misses', stats)
        self.assertIn('api_calls', stats)
        self.assertIn('window_cache_size', stats)
        self.assertIn('name_cache_size', stats)
        self.assertIn('cache_hit_rate', stats)

    def test_reset_stats(self):
        """测试重置统计信息"""
        # 添加一些统计数据
        self.service._stats['total_queries'] = 10
        self.service._stats['cache_hits'] = 5
        self.service._stats['cache_misses'] = 5
        self.service._stats['api_calls'] = 5

        self.service.reset_stats()

        self.assertEqual(self.service._stats['total_queries'], 0)
        self.assertEqual(self.service._stats['cache_hits'], 0)
        self.assertEqual(self.service._stats['cache_misses'], 0)
        self.assertEqual(self.service._stats['api_calls'], 0)

    def test_enable_cache(self):
        """测试启用缓存"""
        self.service.disable_cache()
        self.assertFalse(self.service._enable_cache)

        self.service.enable_cache()
        self.assertTrue(self.service._enable_cache)

    def test_disable_cache(self):
        """测试禁用缓存"""
        self.service.enable_cache()
        self.assertTrue(self.service._enable_cache)

        self.service.disable_cache()
        self.assertFalse(self.service._enable_cache)


if __name__ == '__main__':
    unittest.main()
