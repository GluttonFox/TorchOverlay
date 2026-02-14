"""状态管理器 - 统一管理应用状态"""
from typing import Any, Optional, Dict
from core.event_bus import get_event_bus, Events
from core.logger import get_logger

logger = get_logger(__name__)


class AppState:
    """应用状态数据类"""
    def __init__(self):
        """初始化应用状态"""
        # 游戏窗口状态
        self.bound_hwnd: Optional[int] = None
        self.bound_window_title: Optional[str] = None
        self.is_window_valid: bool = True

        # 识别状态
        self.is_recognizing: bool = False
        self.last_recognition_time: Optional[float] = None
        self.recognition_count: int = 0

        # 价格更新状态
        self.is_updating_price: bool = False
        self.last_price_update_time: Optional[float] = None

        # 配置状态
        self.watch_interval_ms: int = 500
        self.debug_mode: bool = False
        self.mystery_gem_mode: str = "min"

        # UI状态
        self.ui_window_visible: bool = False

    def __repr__(self) -> str:
        """返回状态的字符串表示"""
        return f"<AppState bound={self.bound_hwnd} recognizing={self.is_recognizing}>"


class StateManager:
    """状态管理器 - 统一管理应用状态并提供状态变更通知"""

    def __init__(self):
        """初始化状态管理器"""
        self._state = AppState()
        self._event_bus = get_event_bus()

    @property
    def state(self) -> AppState:
        """获取当前状态（只读）"""
        return self._state

    def update_game_window_bound(self, hwnd: int, window_title: str) -> None:
        """更新游戏窗口绑定状态

        Args:
            hwnd: 窗口句柄
            window_title: 窗口标题
        """
        self._state.bound_hwnd = hwnd
        self._state.bound_window_title = window_title
        self._state.is_window_valid = True
        logger.info(f"[状态管理] 游戏窗口已绑定: hwnd={hwnd}, title={window_title}")
        self._event_bus.publish(Events.GAME_WINDOW_BOUND, hwnd=hwnd, title=window_title)

    def update_game_window_unbound(self) -> None:
        """更新游戏窗口解绑状态"""
        hwnd = self._state.bound_hwnd
        self._state.bound_hwnd = None
        self._state.bound_window_title = None
        self._state.is_window_valid = False
        logger.info(f"[状态管理] 游戏窗口已解绑: hwnd={hwnd}")
        self._event_bus.publish(Events.GAME_WINDOW_UNBOUND)

    def update_game_window_closed(self) -> None:
        """更新游戏窗口关闭状态"""
        hwnd = self._state.bound_hwnd
        self._state.bound_hwnd = None
        self._state.bound_window_title = None
        self._state.is_window_valid = False
        logger.info(f"[状态管理] 游戏窗口已关闭: hwnd={hwnd}")
        self._event_bus.publish(Events.GAME_WINDOW_CLOSED)

    def start_recognition(self) -> None:
        """开始识别"""
        if self._state.is_recognizing:
            logger.warning("[状态管理] 识别已经在进行中")
            return

        self._state.is_recognizing = True
        # logger.debug("[状态管理] 开始识别")
        self._event_bus.publish(Events.RECOGNITION_STARTED)

    def complete_recognition(self, success: bool, error: Optional[str] = None) -> None:
        """完成识别

        Args:
            success: 是否成功
            error: 错误信息（如果失败）
        """
        import time
        self._state.is_recognizing = False
        self._state.last_recognition_time = time.time()
        if success:
            self._state.recognition_count += 1
            # logger.debug(f"[状态管理] 识别完成 (成功), 总次数: {self._state.recognition_count}")
            self._event_bus.publish(Events.RECOGNITION_COMPLETED)
        else:
            # logger.debug(f"[状态管理] 识别完成 (失败): {error}")
            self._event_bus.publish(Events.RECOGNITION_FAILED, error=error)

    def start_price_update(self) -> None:
        """开始价格更新"""
        if self._state.is_updating_price:
            logger.warning("[状态管理] 价格更新已经在进行中")
            return

        self._state.is_updating_price = True
        # logger.debug("[状态管理] 开始价格更新")
        self._event_bus.publish(Events.PRICE_UPDATE_STARTED)

    def complete_price_update(self, success: bool, message: str) -> None:
        """完成价格更新

        Args:
            success: 是否成功
            message: 结果消息
        """
        import time
        self._state.is_updating_price = False
        if success:
            self._state.last_price_update_time = time.time()
            # logger.debug(f"[状态管理] 价格更新完成 (成功)")
        else:
            # logger.debug(f"[状态管理] 价格更新完成 (失败): {message}")
            pass

        self._event_bus.publish(
            Events.PRICE_UPDATE_COMPLETED if success else Events.PRICE_UPDATE_FAILED,
            success=success,
            message=message
        )

    def update_config(self, config_data: Dict[str, Any]) -> None:
        """更新配置

        Args:
            config_data: 配置数据字典
        """
        if 'watch_interval_ms' in config_data:
            self._state.watch_interval_ms = config_data['watch_interval_ms']
        if 'debug_mode' in config_data:
            self._state.debug_mode = config_data['debug_mode']
        if 'mystery_gem_mode' in config_data:
            self._state.mystery_gem_mode = config_data['mystery_gem_mode']

        # logger.debug(f"[状态管理] 配置已更新: {config_data}")
        self._event_bus.publish(Events.CONFIG_UPDATED, config=config_data)

    def set_ui_window_visible(self, visible: bool) -> None:
        """设置UI窗口可见状态

        Args:
            visible: 是否可见
        """
        self._state.ui_window_visible = visible
        # logger.debug(f"[状态管理] UI窗口可见状态: {visible}")
        self._event_bus.publish(
            Events.UI_WINDOW_SHOWN if visible else Events.UI_WINDOW_CLOSED
        )


# 全局状态管理器实例（单例）
_state_manager_instance: StateManager = None


def get_state_manager() -> StateManager:
    """获取全局状态管理器实例

    Returns:
        StateManager 实例
    """
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = StateManager()
    return _state_manager_instance
