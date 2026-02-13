"""EventBus使用示例

本文件展示了如何在TorchOverlay项目中使用EventBus实现事件驱动架构。
"""

from core.event_bus import get_event_bus, Events
from core.logger import get_logger

logger = get_logger(__name__)


class RecognitionEventHandler:
    """识别事件处理器示例"""

    def __init__(self):
        # 获取事件总线单例
        self.event_bus = get_event_bus()
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅所有相关事件"""
        self.event_bus.subscribe(Events.RECOGNITION_STARTED, self.on_recognition_started)
        self.event_bus.subscribe(Events.RECOGNITION_COMPLETED, self.on_recognition_completed)
        self.event_bus.subscribe(Events.RECOGNITION_FAILED, self.on_recognition_failed)

    def on_recognition_started(self, hwnd: int):
        """处理识别开始事件"""
        logger.info(f"[事件] 识别开始 - 窗口句柄: {hwnd}")
        # 可以在这里执行一些初始化操作，如：
        # - 更新UI状态显示"识别中..."
        # - 记录开始时间用于性能分析
        # - 准备日志文件

    def on_recognition_completed(self, balance: str, items_count: int):
        """处理识别完成事件"""
        logger.info(f"[事件] 识别完成 - 余额: {balance}, 物品数量: {items_count}")
        # 可以在这里执行一些完成后的操作，如：
        # - 更新统计信息
        # - 发送通知
        # - 保存识别历史

    def on_recognition_failed(self, error: str):
        """处理识别失败事件"""
        logger.error(f"[事件] 识别失败 - 错误: {error}")
        # 可以在这里执行一些错误处理操作，如：
        # - 显示错误提示
        # - 记录错误日志
        # - 触发重试逻辑


class PriceUpdateEventHandler:
    """价格更新事件处理器示例"""

    def __init__(self):
        self.event_bus = get_event_bus()
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅所有相关事件"""
        self.event_bus.subscribe(Events.PRICE_UPDATE_STARTED, self.on_price_update_started)
        self.event_bus.subscribe(Events.PRICE_UPDATE_COMPLETED, self.on_price_update_completed)
        self.event_bus.subscribe(Events.PRICE_UPDATE_FAILED, self.on_price_update_failed)

    def on_price_update_started(self):
        """处理价格更新开始事件"""
        logger.info("[事件] 价格更新开始")
        # 可以在这里执行一些初始化操作，如：
        # - 显示进度条
        # - 禁用更新按钮

    def on_price_update_completed(self, message: str):
        """处理价格更新完成事件"""
        logger.info(f"[事件] 价格更新完成 - 消息: {message}")
        # 可以在这里执行一些完成后的操作，如：
        # - 重新加载价格数据
        # - 更新UI显示
        # - 记录更新历史

    def on_price_update_failed(self, message: str):
        """处理价格更新失败事件"""
        logger.error(f"[事件] 价格更新失败 - 消息: {message}")
        # 可以在这里执行一些错误处理操作，如：
        # - 显示错误提示
        # - 记录错误日志


class GameWindowEventHandler:
    """游戏窗口事件处理器示例"""

    def __init__(self):
        self.event_bus = get_event_bus()
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅所有相关事件"""
        self.event_bus.subscribe(Events.GAME_WINDOW_BOUND, self.on_window_bound)
        self.event_bus.subscribe(Events.GAME_WINDOW_LOST, self.on_window_lost)
        self.event_bus.subscribe(Events.GAME_WINDOW_MINIMIZED, self.on_window_minimized)
        self.event_bus.subscribe(Events.GAME_WINDOW_RESTORED, self.on_window_restored)

    def on_window_bound(self, hwnd: int, title: str):
        """处理窗口绑定事件"""
        logger.info(f"[事件] 游戏窗口绑定 - 句柄: {hwnd}, 标题: {title}")
        # 可以在这里执行一些初始化操作，如：
        # - 创建overlay
        # - 开始进程监视
        # - 调整UI布局

    def on_window_lost(self, reason: str):
        """处理窗口丢失事件"""
        logger.warning(f"[事件] 游戏窗口丢失 - 原因: {reason}")
        # 可以在这里执行一些清理操作，如：
        # - 关闭overlay
        # - 停止监视
        # - 显示提示用户重新绑定

    def on_window_minimized(self, hwnd: int):
        """处理窗口最小化事件"""
        logger.info(f"[事件] 游戏窗口最小化 - 句柄: {hwnd}")
        # 可以在这里执行一些操作，如：
        # - 隐藏overlay
        # - 暂停识别

    def on_window_restored(self, hwnd: int):
        """处理窗口恢复事件"""
        logger.info(f"[事件] 游戏窗口恢复 - 句柄: {hwnd}")
        # 可以在这里执行一些操作，如：
        # - 显示overlay
        # - 恢复识别


class StatisticsEventHandler:
    """统计事件处理器示例"""

    def __init__(self):
        self.event_bus = get_event_bus()
        self.recognition_count = 0
        self.price_update_count = 0
        self._subscribe_events()

    def _subscribe_events(self):
        """订阅所有相关事件"""
        self.event_bus.subscribe(Events.RECOGNITION_COMPLETED, self.on_recognition_completed)
        self.event_bus.subscribe(Events.PRICE_UPDATE_COMPLETED, self.on_price_update_completed)

    def on_recognition_completed(self, balance: str, items_count: int):
        """记录识别统计"""
        self.recognition_count += 1
        logger.info(f"[统计] 总识别次数: {self.recognition_count}")

    def on_price_update_completed(self, message: str):
        """记录价格更新统计"""
        self.price_update_count += 1
        logger.info(f"[统计] 总价格更新次数: {self.price_update_count}")

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            'recognition_count': self.recognition_count,
            'price_update_count': self.price_update_count
        }


# 使用示例
def example_usage():
    """EventBus使用示例"""
    # 创建事件处理器
    recognition_handler = RecognitionEventHandler()
    price_handler = PriceUpdateEventHandler()
    window_handler = GameWindowEventHandler()
    stats_handler = StatisticsEventHandler()

    # 模拟事件发布
    event_bus = get_event_bus()

    # 模拟识别流程
    event_bus.publish(Events.GAME_WINDOW_BOUND, hwnd=12345, title="火炬之光无限")
    event_bus.publish(Events.RECOGNITION_STARTED, hwnd=12345)
    event_bus.publish(Events.RECOGNITION_COMPLETED, balance="10,000", items_count=8)

    # 模拟价格更新流程
    event_bus.publish(Events.PRICE_UPDATE_STARTED)
    event_bus.publish(Events.PRICE_UPDATE_COMPLETED, message="成功更新100个物品价格")

    # 获取统计信息
    stats = stats_handler.get_statistics()
    logger.info(f"统计信息: {stats}")


# 动态订阅示例
def dynamic_subscription_example():
    """动态订阅示例"""
    event_bus = get_event_bus()

    def custom_callback(hwnd: int, **kwargs):
        """自定义回调函数"""
        logger.info(f"自定义回调: hwnd={hwnd}, kwargs={kwargs}")

    # 动态订阅事件
    event_bus.subscribe(Events.RECOGNITION_STARTED, custom_callback)

    # 发布事件
    event_bus.publish(Events.RECOGNITION_STARTED, hwnd=12345)

    # 取消订阅
    event_bus.unsubscribe(Events.RECOGNITION_STARTED, custom_callback)

    # 再次发布事件，自定义回调不会被调用
    event_bus.publish(Events.RECOGNITION_STARTED, hwnd=67890)


if __name__ == "__main__":
    # 运行示例
    example_usage()
    dynamic_subscription_example()
