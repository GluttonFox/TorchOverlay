"""事件总线测试"""
import pytest
from unittest.mock import Mock

from core.event_bus import EventBus, Events


class TestEventBus:
    """事件总线测试类"""

    @pytest.fixture
    def event_bus(self):
        """事件总线fixture"""
        return EventBus()

    def test_subscribe_and_publish(self, event_bus):
        """测试订阅和发布事件"""
        # 创建模拟订阅者
        subscriber1 = Mock()
        subscriber2 = Mock()

        # 订阅事件
        event_bus.subscribe(Events.RECOGNITION_STARTED, subscriber1)
        event_bus.subscribe(Events.RECOGNITION_STARTED, subscriber2)

        # 发布事件
        event_bus.publish(Events.RECOGNITION_STARTED, hwnd=123)

        # 验证所有订阅者都收到了事件
        subscriber1.assert_called_once_with(hwnd=123)
        subscriber2.assert_called_once_with(hwnd=123)

    def test_unsubscribe(self, event_bus):
        """测试取消订阅"""
        subscriber = Mock()

        # 订阅事件
        event_bus.subscribe(Events.RECOGNITION_STARTED, subscriber)

        # 发布事件
        event_bus.publish(Events.RECOGNITION_STARTED, test="data1")
        assert subscriber.call_count == 1

        # 取消订阅
        event_bus.unsubscribe(Events.RECOGNITION_STARTED, subscriber)

        # 再次发布事件
        event_bus.publish(Events.RECOGNITION_STARTED, test="data2")
        # 订阅者不应该再次收到事件
        assert subscriber.call_count == 1

    def test_different_events(self, event_bus):
        """测试不同类型的事件"""
        subscriber_recognition = Mock()
        subscriber_price = Mock()

        # 订阅不同事件
        event_bus.subscribe(Events.RECOGNITION_STARTED, subscriber_recognition)
        event_bus.subscribe(Events.PRICE_UPDATE_STARTED, subscriber_price)

        # 发布识别事件
        event_bus.publish(Events.RECOGNITION_STARTED, balance=1000)
        assert subscriber_recognition.called
        assert not subscriber_price.called

        # 发布价格更新事件
        event_bus.publish(Events.PRICE_UPDATE_STARTED)
        assert subscriber_price.called

    def test_event_with_multiple_params(self, event_bus):
        """测试多参数事件"""
        subscriber = Mock()

        event_bus.subscribe(Events.RECOGNITION_COMPLETED, subscriber)

        # 发布多参数事件
        event_bus.publish(
            Events.RECOGNITION_COMPLETED,
            balance="10,000",
            items_count=8
        )

        subscriber.assert_called_once_with(balance="10,000", items_count=8)

    def test_subscribe_multiple_times(self, event_bus):
        """测试多次订阅同一事件"""
        subscriber = Mock()

        # 同一个订阅者订阅两次
        event_bus.subscribe(Events.RECOGNITION_STARTED, subscriber)
        event_bus.subscribe(Events.RECOGNITION_STARTED, subscriber)

        # 发布一次事件
        event_bus.publish(Events.RECOGNITION_STARTED, test="data")

        # 订阅者应该被调用两次（因为订阅了两次）
        assert subscriber.call_count == 2

    def test_unsubscribe_nonexistent(self, event_bus):
        """测试取消不存在的订阅"""
        subscriber = Mock()

        # 取消不存在的订阅不应该抛出异常
        event_bus.unsubscribe(Events.RECOGNITION_STARTED, subscriber)
        event_bus.publish(Events.RECOGNITION_STARTED, test="data")

        assert not subscriber.called

    def test_clear_all_subscribers(self, event_bus):
        """测试清除所有订阅者"""
        subscriber1 = Mock()
        subscriber2 = Mock()

        # 订阅事件
        event_bus.subscribe(Events.RECOGNITION_STARTED, subscriber1)
        event_bus.subscribe(Events.PRICE_UPDATE_STARTED, subscriber2)

        # 清除所有订阅者
        event_bus.clear_all()

        # 发布事件
        event_bus.publish(Events.RECOGNITION_STARTED, test="data")
        event_bus.publish(Events.PRICE_UPDATE_STARTED, test="data")

        # 订阅者都不应该收到事件
        assert not subscriber1.called
        assert not subscriber2.called

    def test_clear_specific_event(self, event_bus):
        """测试清除特定事件的所有订阅者"""
        subscriber1 = Mock()
        subscriber2 = Mock()

        # 订阅不同事件
        event_bus.subscribe(Events.RECOGNITION_STARTED, subscriber1)
        event_bus.subscribe(Events.PRICE_UPDATE_STARTED, subscriber2)

        # 清除识别事件的订阅者
        event_bus.clear_event(Events.RECOGNITION_STARTED)

        # 发布事件
        event_bus.publish(Events.RECOGNITION_STARTED, test="data")
        event_bus.publish(Events.PRICE_UPDATE_STARTED, test="data")

        # 只有价格更新的订阅者应该收到事件
        assert not subscriber1.called
        assert subscriber2.called

    def test_get_subscribers_count(self, event_bus):
        """测试获取订阅者数量"""
        subscriber1 = Mock()
        subscriber2 = Mock()

        assert event_bus.get_subscribers_count(Events.RECOGNITION_STARTED) == 0

        event_bus.subscribe(Events.RECOGNITION_STARTED, subscriber1)
        assert event_bus.get_subscribers_count(Events.RECOGNITION_STARTED) == 1

        event_bus.subscribe(Events.RECOGNITION_STARTED, subscriber2)
        assert event_bus.get_subscribers_count(Events.RECOGNITION_STARTED) == 2

    def test_single_event_bus_instance(self):
        """测试事件总线单例"""
        bus1 = EventBus.get_instance()
        bus2 = EventBus.get_instance()

        # 应该是同一个实例
        assert bus1 is bus2

        # 在一个实例中订阅
        subscriber = Mock()
        bus1.subscribe(Events.RECOGNITION_STARTED, subscriber)

        # 在另一个实例中发布，订阅者应该能收到
        bus2.publish(Events.RECOGNITION_STARTED, test="data")
        assert subscriber.called
