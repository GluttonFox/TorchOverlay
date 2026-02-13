"""单元测试：异步价格更新服务"""
import json
import os
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
from datetime import datetime

from services.async_price_update_service import AsyncPriceUpdateService, UpdateStatus


class TestAsyncPriceUpdateService(unittest.TestCase):
    """异步价格更新服务测试"""

    def setUp(self):
        """测试前准备"""
        # 创建临时配置文件
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'test_config.json')
        self.item_path = os.path.join(self.temp_dir, 'item.json')

        # 创建测试配置
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump({}, f)

        # 创建测试物品文件
        self.test_items = {
            '10001': {'Name': 'Test Item 1', 'Price': 100},
            '10002': {'Name': 'Test Item 2', 'Price': 200}
        }
        with open(self.item_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_items, f)

        # 创建服务
        self.service = AsyncPriceUpdateService(
            api_url="http://test-api.com/price",
            update_interval_hours=1.0,
            config_path=self.config_path,
            log_file=os.path.join(self.temp_dir, 'test_log.log')
        )

    def tearDown(self):
        """测试后清理"""
        self.service.shutdown()

        # 清理临时文件
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        if os.path.exists(self.item_path):
            os.remove(self.item_path)

    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.service._api_url, "http://test-api.com/price")
        self.assertEqual(self.service._update_interval_hours, 1.0)
        self.assertEqual(self.service._status, UpdateStatus.IDLE)
        self.assertIsNone(self.service._last_update_time)

    def test_get_status(self):
        """测试获取状态"""
        status = self.service.get_status()
        self.assertEqual(status, UpdateStatus.IDLE)

    def test_is_updating(self):
        """测试检查是否正在更新"""
        self.assertFalse(self.service.is_updating())

    @patch('services.async_price_update_service.urllib.request')
    def test_update_prices_async_success(self, mock_urllib):
        """测试异步更新价格成功"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'data': {
                '10001': 150,
                '10002': 250
            }
        }).encode('utf-8')
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urllib.urlopen.return_value = mock_response

        # 设置回调
        callback_results = {'start': False, 'complete': False, 'result': None}

        def on_start():
            callback_results['start'] = True

        def on_complete(success, message):
            callback_results['complete'] = True
            callback_results['result'] = (success, message)

        self.service.set_callbacks(on_start=on_start, on_complete=on_complete)

        # 启动异步更新
        success = self.service.update_prices_async()
        self.assertTrue(success)

        # 等待更新完成
        time.sleep(1.0)

        # 验证回调被调用
        self.assertTrue(callback_results['start'])
        self.assertTrue(callback_results['complete'])
        self.assertTrue(callback_results['result'][0])  # success

        # 验证价格已更新
        with open(self.item_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        self.assertEqual(items['10001']['Price'], 150)
        self.assertEqual(items['10002']['Price'], 250)

        # 验证状态
        self.assertEqual(self.service.get_status(), UpdateStatus.SUCCESS)

    @patch('services.async_price_update_service.urllib.request')
    def test_update_prices_async_failure(self, mock_urllib):
        """测试异步更新价格失败"""
        # 模拟网络错误
        mock_urllib.urlopen.side_effect = Exception("Network error")

        # 设置错误回调
        error_result = {'error': None}

        def on_error(e):
            error_result['error'] = e

        self.service.set_callbacks(on_error=on_error)

        # 启动异步更新
        success = self.service.update_prices_async()
        self.assertTrue(success)

        # 等待更新完成
        time.sleep(1.0)

        # 验证错误回调被调用
        self.assertIsNotNone(error_result['error'])

        # 验证状态
        self.assertEqual(self.service.get_status(), UpdateStatus.FAILED)

    def test_update_prices_async_duplicate(self):
        """测试重复启动更新"""
        # 启动第一次更新（使用mock避免实际API调用）
        with patch('services.async_price_update_service.urllib.request') as mock_urllib:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps({'data': {}}).encode('utf-8')
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urllib.urlopen.return_value = mock_response

            success1 = self.service.update_prices_async()
            self.assertTrue(success1)

            # 尝试启动第二次更新
            success2 = self.service.update_prices_async()
            self.assertFalse(success2)

        # 等待完成
        time.sleep(1.0)

    def test_cancel_update(self):
        """测试取消更新"""
        # 使用长时间延迟的mock来模拟长时间更新
        def slow_read(*args, **kwargs):
            time.sleep(0.5)
            return json.dumps({'data': {}}).encode('utf-8')

        with patch('services.async_price_update_service.urllib.request') as mock_urllib:
            mock_response = Mock()
            mock_response.read.side_effect = slow_read
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urllib.urlopen.return_value = mock_response

            # 启动更新
            self.service.update_prices_async()

            # 立即取消
            success = self.service.cancel_update()
            self.assertTrue(success)

            # 等待线程结束
            time.sleep(1.0)

            # 验证状态
            self.assertIn(self.service.get_status(), [UpdateStatus.CANCELLED, UpdateStatus.FAILED])

    def test_cancel_update_when_not_updating(self):
        """测试在没有更新时取消"""
        success = self.service.cancel_update()
        self.assertFalse(success)

    def test_get_last_result(self):
        """测试获取上次结果"""
        # 初始状态应该返回None
        result = self.service.get_last_result()
        self.assertIsNone(result)

    def test_get_last_update_time(self):
        """测试获取上次更新时间"""
        # 初始状态应该返回None
        time = self.service.get_last_update_time()
        self.assertIsNone(time)

    @patch('services.async_price_update_service.urllib.request')
    def test_get_last_update_time_after_update(self, mock_urllib):
        """测试更新后获取上次更新时间"""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({'data': {}}).encode('utf-8')
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urllib.urlopen.return_value = mock_response

        self.service.update_prices_async()
        time.sleep(1.0)

        last_time = self.service.get_last_update_time()
        self.assertIsNotNone(last_time)
        self.assertIsInstance(last_time, datetime)

    def test_can_update(self):
        """测试检查是否可以更新"""
        # 初始状态应该可以更新
        self.assertTrue(self.service.can_update())

    @patch('services.async_price_update_service.urllib.request')
    def test_can_update_after_update(self, mock_urllib):
        """测试更新后检查是否可以更新"""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({'data': {}}).encode('utf-8')
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urllib.urlopen.return_value = mock_response

        # 执行更新
        self.service.update_prices_async()
        time.sleep(1.0)

        # 刚更新完，不能再次更新
        self.assertFalse(self.service.can_update())

    @patch('services.async_price_update_service.urllib.request')
    def test_force_update(self, mock_urllib):
        """测试强制更新"""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({'data': {}}).encode('utf-8')
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urllib.urlopen.return_value = mock_response

        # 第一次更新
        self.service.update_prices_async()
        time.sleep(1.0)

        # 强制第二次更新
        success = self.service.update_prices_async(force=True)
        self.assertTrue(success)
        time.sleep(1.0)

    def test_get_stats(self):
        """测试获取统计信息"""
        stats = self.service.get_stats()

        self.assertIn('total_updates', stats)
        self.assertIn('successful_updates', stats)
        self.assertIn('failed_updates', stats)
        self.assertIn('cancelled_updates', stats)
        self.assertIn('total_items_updated', stats)
        self.assertIn('last_update_time', stats)
        self.assertIn('current_status', stats)
        self.assertIn('success_rate', stats)

    def test_reset_stats(self):
        """测试重置统计信息"""
        # 添加一些统计数据
        self.service._stats['total_updates'] = 10
        self.service._stats['successful_updates'] = 5
        self.service._stats['failed_updates'] = 5
        self.service._stats['cancelled_updates'] = 0

        self.service.reset_stats()

        self.assertEqual(self.service._stats['total_updates'], 0)
        self.assertEqual(self.service._stats['successful_updates'], 0)
        self.assertEqual(self.service._stats['failed_updates'], 0)
        self.assertEqual(self.service._stats['cancelled_updates'], 0)

    def test_set_callbacks(self):
        """测试设置回调"""
        on_start = Mock()
        on_complete = Mock()
        on_error = Mock()

        self.service.set_callbacks(
            on_start=on_start,
            on_complete=on_complete,
            on_error=on_error
        )

        self.assertEqual(self.service._on_start_callback, on_start)
        self.assertEqual(self.service._on_complete_callback, on_complete)
        self.assertEqual(self.service._on_error_callback, on_error)

    def test_shutdown(self):
        """测试关闭服务"""
        # 模拟正在更新的状态
        self.service._status = UpdateStatus.UPDATING

        self.service.shutdown()

        # 验证状态
        self.assertEqual(self.service.get_status(), UpdateStatus.CANCELLED)

    @patch('services.async_price_update_service.urllib.request')
    def test_skip_item_100300(self, mock_urllib):
        """测试跳过初火源质（ID: 100300）"""
        # 在测试物品中添加100300
        self.test_items['100300'] = {'Name': '初火源质', 'Price': 1}
        with open(self.item_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_items, f)

        # API返回包含100300
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'data': {
                '100300': 999  # API返回999，但应该被跳过
            }
        }).encode('utf-8')
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urllib.urlopen.return_value = mock_response

        self.service.update_prices_async()
        time.sleep(1.0)

        # 验证100300的价格没有被更新
        with open(self.item_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        self.assertEqual(items['100300']['Price'], 1)  # 应该保持原值

    @patch('services.async_price_update_service.urllib.request')
    def test_only_update_changed_items(self, mock_urllib):
        """测试只更新价格变化的物品"""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'data': {
                '10001': 150,  # 价格变化
                '10002': 200   # 价格未变化
            }
        }).encode('utf-8')
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urllib.urlopen.return_value = mock_response

        self.service.update_prices_async()
        time.sleep(1.0)

        # 验证统计
        stats = self.service.get_stats()
        self.assertEqual(stats['total_items_updated'], 1)  # 只更新了1个物品


if __name__ == '__main__':
    unittest.main()
