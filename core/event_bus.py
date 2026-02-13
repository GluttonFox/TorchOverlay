"""事件总线 - 解耦组件间的通信"""
from typing import Callable, Dict, List, Any
from core.logger import get_logger

logger = get_logger(__name__)


class EventBus:
    """简单的事件总线实现，用于组件间解耦通信"""

    def __init__(self):
        """初始化事件总线"""
        self._listeners: Dict[str, List[Callable]] = {}

    def subscribe(self, event_name: str, callback: Callable) -> None:
        """订阅事件

        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)
        logger.debug(f"[事件总线] 订阅事件: {event_name}")

    def unsubscribe(self, event_name: str, callback: Callable) -> None:
        """取消订阅事件

        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        if event_name in self._listeners:
            try:
                self._listeners[event_name].remove(callback)
                logger.debug(f"[事件总线] 取消订阅事件: {event_name}")
            except ValueError:
                logger.warning(f"[事件总线] 尝试取消不存在的回调: {event_name}")

    def publish(self, event_name: str, *args, **kwargs) -> None:
        """发布事件

        Args:
            event_name: 事件名称
            *args: 位置参数
            **kwargs: 关键字参数
        """
        if event_name not in self._listeners or not self._listeners[event_name]:
            logger.debug(f"[事件总线] 发布事件（无监听器）: {event_name}")
            return

        logger.debug(f"[事件总线] 发布事件: {event_name}, 监听器数量: {len(self._listeners[event_name])}")

        for callback in self._listeners[event_name]:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"[事件总线] 回调执行失败: {event_name}, 错误: {e}", exc_info=True)


# 全局事件总线实例（单例）
_event_bus_instance: EventBus = None


def get_event_bus() -> EventBus:
    """获取全局事件总线实例

    Returns:
        EventBus 实例
    """
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventBus()
    return _event_bus_instance


# 预定义事件名称
class Events:
    """预定义的事件名称常量"""
    # 游戏窗口事件
    GAME_WINDOW_BOUND = "game_window_bound"
    GAME_WINDOW_UNBOUND = "game_window_unbound"
    GAME_WINDOW_CLOSED = "game_window_closed"

    # 识别事件
    RECOGNITION_STARTED = "recognition_started"
    RECOGNITION_COMPLETED = "recognition_completed"
    RECOGNITION_FAILED = "recognition_failed"

    # 价格事件
    PRICE_UPDATE_STARTED = "price_update_started"
    PRICE_UPDATE_COMPLETED = "price_update_completed"
    PRICE_UPDATE_FAILED = "price_update_failed"

    # 配置事件
    CONFIG_UPDATED = "config_updated"
    CONFIG_RELOADED = "config_reloaded"

    # UI事件
    UI_WINDOW_SHOWN = "ui_window_shown"
    UI_WINDOW_CLOSED = "ui_window_closed"
