"""兑换监控服务 - 定期验证购买记录并保存到日志"""
import threading
import time
from typing import Callable, Optional

from core.logger import get_logger
from services.exchange_verification_service import ExchangeVerificationService
from services.exchange_log_service import ExchangeLogService
from services.refresh_log_service import RefreshLogService

logger = get_logger(__name__)


class ExchangeMonitorService:
    """兑换监控服务 - 定期执行验证和保存操作"""

    # 默认检查间隔（秒）
    DEFAULT_CHECK_INTERVAL = 5

    def __init__(self,
                 verification_service: ExchangeVerificationService,
                 exchange_log_service: ExchangeLogService,
                 refresh_log_service: RefreshLogService,
                 check_interval: float = 5.0):
        """初始化监控服务

        Args:
            verification_service: 兑换验证服务
            exchange_log_service: 兑换日志服务
            refresh_log_service: 刷新日志服务
            check_interval: 检查间隔（秒）
        """
        self._verification_service = verification_service
        self._exchange_log_service = exchange_log_service
        self._refresh_log_service = refresh_log_service
        self._check_interval = check_interval

        # 回调函数
        self._on_exchange_verified_callback: Optional[Callable] = None
        self._on_refresh_logged_callback: Optional[Callable] = None

        # 监控线程
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def set_callbacks(self,
                     on_exchange_verified: Optional[Callable] = None,
                     on_refresh_logged: Optional[Callable] = None) -> None:
        """设置回调函数

        Args:
            on_exchange_verified: 兑换验证通过回调，参数为ExchangeRecord对象列表
            on_refresh_logged: 刷新记录保存回调，参数为RefreshEvent对象列表
        """
        self._on_exchange_verified_callback = on_exchange_verified
        self._on_refresh_logged_callback = on_refresh_logged
        logger.info("监控服务回调函数已设置")

    def start(self) -> None:
        """启动监控"""
        if self._running:
            logger.warning("监控服务已在运行")
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print(f"[兑换监控] 启动成功，每 {self._check_interval} 秒验证一次兑换记录")
        logger.info("兑换监控服务已启动")

    def stop(self) -> None:
        """停止监控"""
        if not self._running:
            return

        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("兑换监控服务已停止")

    def _monitor_loop(self) -> None:
        """监控循环"""
        logger.info("开始执行定期验证和保存任务")

        while self._running:
            try:
                # 1. 验证购买记录
                verified_records = self._verification_service.verify_purchases()

                if verified_records:
                    logger.info(f"验证通过 {len(verified_records)} 条兑换记录")

                    # 保存到兑换日志
                    if self._exchange_log_service.add_records(verified_records):
                        logger.info("兑换记录已保存到exchange_log.json")

                        # 触发回调
                        if self._on_exchange_verified_callback:
                            try:
                                self._on_exchange_verified_callback(verified_records)
                            except Exception as e:
                                logger.error(f"兑换验证通过回调执行失败: {e}", exc_info=True)

                # 2. 获取并保存刷新事件
                refresh_events = self._verification_service.get_refresh_events()

                if refresh_events:
                    # 只保存新的刷新事件（这里简单处理，保存所有）
                    if self._refresh_log_service.add_records(refresh_events):
                        logger.info(f"刷新记录已保存到refresh_log.json ({len(refresh_events)} 条)")
                        print(f"[兑换监控] ✓ 保存了 {len(refresh_events)} 条刷新记录到 refresh_log.json")

                        # 触发回调
                        if self._on_refresh_logged_callback:
                            try:
                                self._on_refresh_logged_callback(refresh_events)
                            except Exception as e:
                                logger.error(f"刷新记录保存回调执行失败: {e}", exc_info=True)

                # 3. 清理过期记录
                cleaned_count = self._verification_service.clean_expired_records()
                if cleaned_count > 0:
                    logger.info(f"清理了 {cleaned_count} 条过期OCR记录")
                    print(f"[兑换监控] 清理了 {cleaned_count} 条过期的OCR记录")

            except Exception as e:
                logger.error(f"监控任务执行失败: {e}", exc_info=True)

            # 等待下次检查
            time.sleep(self._check_interval)

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
