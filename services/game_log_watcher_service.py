"""游戏日志监控服务 - 持续监控游戏日志文件变化"""
import threading
import time
from typing import Callable, Optional

from core.logger import get_logger
from services.game_log_parser_service import GameLogParserService

logger = get_logger(__name__)


class GameLogWatcherService:
    """游戏日志监控服务 - 定期解析游戏日志"""

    # 默认检查间隔（秒）
    DEFAULT_CHECK_INTERVAL = 2

    def __init__(self, game_log_path: str | None = None, check_interval: float = 2.0):
        """初始化日志监控服务

        Args:
            game_log_path: 游戏日志文件路径
            check_interval: 检查间隔（秒）
        """
        self._parser = GameLogParserService(game_log_path)
        self._check_interval = check_interval

        # 回调函数
        self._on_buy_event_callback: Optional[Callable] = None
        self._on_refresh_event_callback: Optional[Callable] = None

        # 监控线程
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def set_callbacks(self, on_buy_event: Optional[Callable] = None,
                     on_refresh_event: Optional[Callable] = None) -> None:
        """设置事件回调函数

        Args:
            on_buy_event: 购买事件回调，参数为BuyEvent对象
            on_refresh_event: 刷新事件回调，参数为RefreshEvent对象
        """
        self._on_buy_event_callback = on_buy_event
        self._on_refresh_event_callback = on_refresh_event
        logger.info("事件回调函数已设置")

    def start(self) -> None:
        """启动日志监控"""
        if self._running:
            logger.warning("日志监控已在运行")
            return

        logger.info(f"[DEBUG] 游戏日志监控启动，购买回调: {self._on_buy_event_callback is not None}, 刷新回调: {self._on_refresh_event_callback is not None}")

        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        print(f"[日志监控] 启动成功，每 {self._check_interval} 秒检查一次日志")
        logger.info("游戏日志监控已启动")

    def stop(self) -> None:
        """停止日志监控"""
        if not self._running:
            return

        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        print("[日志监控] 已停止")
        logger.info("游戏日志监控已停止")

    def _watch_loop(self) -> None:
        """监控循环"""
        logger.info(f"开始监控日志文件: {self._parser.game_log_path}")

        import os
        if os.path.exists(self._parser.game_log_path):
            file_size = os.path.getsize(self._parser.game_log_path)
            print(f"[日志监控] 正在监控: {self._parser.game_log_path} (大小: {file_size} 字节)")
        else:
            print(f"[日志监控] ⚠ 日志文件不存在: {self._parser.game_log_path}")

        while self._running:
            try:
                # 解析新事件
                buy_events, refresh_events = self._parser.parse_new_events()

                logger.info(f"[DEBUG] 解析到购买事件: {len(buy_events)}, 刷新事件: {len(refresh_events)}, 购买回调已设置: {self._on_buy_event_callback is not None}")

                # 触发购买事件回调
                if buy_events and self._on_buy_event_callback:
                    for event in buy_events:
                        try:
                            logger.info(f"[DEBUG] 即将调用购买回调: {event.item_name}")
                            self._on_buy_event_callback(event)
                            logger.info(f"[DEBUG] 购买回调调用完成: {event.item_name}")
                        except Exception as e:
                            logger.error(f"购买事件回调执行失败: {e}", exc_info=True)
                elif buy_events and not self._on_buy_event_callback:
                    logger.warning(f"检测到 {len(buy_events)} 个购买事件，但回调函数未设置！")

                # 触发刷新事件回调
                if refresh_events and self._on_refresh_event_callback:
                    for event in refresh_events:
                        try:
                            self._on_refresh_event_callback(event)
                        except Exception as e:
                            logger.error(f"刷新事件回调执行失败: {e}", exc_info=True)
                elif refresh_events and not self._on_refresh_event_callback:
                    logger.warning(f"检测到 {len(refresh_events)} 个刷新事件，但回调函数未设置！")

            except Exception as e:
                logger.error(f"解析日志失败: {e}", exc_info=True)

            # 等待下次检查
            time.sleep(self._check_interval)

    def reset_position(self) -> None:
        """重置日志读取位置"""
        self._parser.reset_position()
        logger.info("日志读取位置已重置")

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
