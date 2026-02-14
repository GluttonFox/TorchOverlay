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
                 check_interval: float = 5.0,
                 config=None,
                 controller=None):
        """初始化监控服务

        Args:
            verification_service: 兑换验证服务
            exchange_log_service: 兑换日志服务
            refresh_log_service: 刷新日志服务
            check_interval: 检查间隔（秒）
            config: 应用配置（可选）
            controller: 控制器（可选，用于自动OCR功能）
        """
        self._verification_service = verification_service
        self._exchange_log_service = exchange_log_service
        self._refresh_log_service = refresh_log_service
        self._check_interval = check_interval
        self._config = config
        self._controller = controller

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

        # 打印自动OCR配置状态
        if self._config:
            logger.info(f"[自动OCR] 配置状态: enable_auto_ocr={self._config.enable_auto_ocr}")
            print(f"[自动OCR] 配置状态: enable_auto_ocr={self._config.enable_auto_ocr}")
        else:
            logger.warning("[自动OCR] 配置未初始化")
            print(f"[自动OCR] ⚠️ 配置未初始化")

        while self._running:
            try:
                # 1. 验证购买记录
                verified_records = self._verification_service.verify_purchases()

                if verified_records:
                    logger.info(f"验证通过 {len(verified_records)} 条兑换记录")

                    # 保存到兑换日志（仅在启用时）
                    if self._config and self._config.enable_exchange_log:
                        if self._exchange_log_service.add_records(verified_records):
                            logger.info("兑换记录已保存到exchange_log.json")
                    else:
                        logger.debug("兑换日志功能已禁用，跳过保存")

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

                        # 自动OCR：检测到花费50神威辉石刷新商店时，自动执行OCR识别
                        for event in refresh_events:
                            logger.info(f"[自动OCR] 检测到刷新事件: 消耗神威辉石={event.gem_cost}")
                            print(f"[自动OCR] 检测到刷新事件: 消耗神威辉石={event.gem_cost}")

                            if event.gem_cost == 50:
                                # 检查自动OCR是否启用
                                if not self._config:
                                    logger.warning("[自动OCR] 配置未初始化")
                                    print(f"[自动OCR] ❌ 配置未初始化，无法自动识别")
                                elif not self._config.enable_auto_ocr:
                                    logger.info("[自动OCR] 自动OCR功能未启用")
                                    print(f"[自动OCR] ℹ️ 自动OCR功能未启用，请在设置中开启")
                                elif not self._controller:
                                    logger.warning("[自动OCR] 控制器未初始化")
                                    print(f"[自动OCR] ❌ 控制器未初始化")
                                elif not self._controller._ui:
                                    logger.warning("[自动OCR] UI未初始化")
                                    print(f"[自动OCR] ❌ UI未初始化")
                                else:
                                    logger.info(f"检测到花费50神威辉石刷新商店，触发自动OCR")
                                    print(f"[自动OCR] ✓ 检测到刷新商店，开始自动识别...")
                                    try:
                                        # 在UI线程中执行OCR
                                        self._controller._ui.schedule(0, self._controller.on_detect_click)
                                    except Exception as e:
                                        logger.error(f"自动OCR执行失败: {e}", exc_info=True)
                                        print(f"[自动OCR] ❌ 执行失败: {e}")
                                break  # 只触发一次

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
