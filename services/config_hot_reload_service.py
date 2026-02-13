"""配置热更新服务 - 监视配置文件变化并自动重新加载"""
import os
import threading
import time
from typing import Callable, Optional

from core.config import AppConfig
from core.logger import get_logger
from services.config_validator_service import ConfigValidatorService

logger = get_logger(__name__)


class ConfigHotReloadService:
    """配置热更新服务

    监视配置文件的变化，并在文件修改时自动重新加载配置。
    """

    def __init__(
        self,
        config_path: str | None = None,
        check_interval_sec: float = 2.0,
        validator: Optional[ConfigValidatorService] = None
    ):
        """初始化配置热更新服务

        Args:
            config_path: 配置文件路径（如果为None，使用默认路径）
            check_interval_sec: 检查间隔（秒）
            validator: 配置验证器（如果为None，创建默认验证器）
        """
        self._config_path = config_path or AppConfig.get_config_path()
        self._check_interval_sec = check_interval_sec
        self._validator = validator or ConfigValidatorService()

        self._current_config: Optional[AppConfig] = None
        self._last_modified_time: Optional[float] = None
        self._is_running = False
        self._thread: Optional[threading.Thread] = None

        # 回调函数列表
        self._callbacks: list[Callable[[AppConfig, AppConfig], None]] = []

        # 锁，确保线程安全
        self._lock = threading.Lock()

    def start(self, initial_config: Optional[AppConfig] = None) -> None:
        """启动热更新服务

        Args:
            initial_config: 初始配置（如果为None，从文件加载）
        """
        with self._lock:
            if self._is_running:
                logger.warning("配置热更新服务已在运行")
                return

            # 加载初始配置
            if initial_config:
                self._current_config = initial_config
            else:
                self._load_initial_config()

            # 获取初始修改时间
            self._update_last_modified_time()

            # 启动监视线程
            self._is_running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()

            logger.info(f"配置热更新服务已启动，监视文件: {self._config_path}")

    def stop(self) -> None:
        """停止热更新服务"""
        with self._lock:
            if not self._is_running:
                return

            self._is_running = False

        # 等待线程结束
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        logger.info("配置热更新服务已停止")

    def _load_initial_config(self) -> None:
        """加载初始配置"""
        try:
            self._current_config = AppConfig.load()
            logger.info("初始配置加载成功")
        except Exception as e:
            logger.error(f"加载初始配置失败: {e}")
            self._current_config = AppConfig()  # 使用默认配置

    def _update_last_modified_time(self) -> None:
        """更新最后修改时间"""
        try:
            self._last_modified_time = os.path.getmtime(self._config_path)
        except Exception as e:
            logger.warning(f"获取配置文件修改时间失败: {e}")

    def _monitor_loop(self) -> None:
        """监视循环（在独立线程中运行）"""
        while self._is_running:
            try:
                # 检查文件是否修改
                if self._check_file_modified():
                    self._reload_config()

                # 等待下一次检查
                time.sleep(self._check_interval_sec)

            except Exception as e:
                logger.error(f"配置热更新监视循环出错: {e}", exc_info=True)
                # 出错后等待一段时间再继续
                time.sleep(self._check_interval_sec)

    def _check_file_modified(self) -> bool:
        """检查文件是否被修改

        Returns:
            文件是否被修改
        """
        try:
            current_mtime = os.path.getmtime(self._config_path)
            if self._last_modified_time is None:
                self._last_modified_time = current_mtime
                return False

            if current_mtime > self._last_modified_time:
                self._last_modified_time = current_mtime
                return True

            return False
        except Exception as e:
            logger.warning(f"检查文件修改时间失败: {e}")
            return False

    def _reload_config(self) -> None:
        """重新加载配置"""
        try:
            logger.info("检测到配置文件变化，正在重新加载...")

            # 保存旧配置
            old_config = self._current_config

            # 加载新配置
            new_config = AppConfig.load()

            # 验证新配置
            self._validator.validate_app_config(new_config)

            # 更新当前配置
            with self._lock:
                self._current_config = new_config

            # 通知所有回调
            self._notify_callbacks(old_config, new_config)

            logger.info("配置重新加载成功")

        except Exception as e:
            logger.error(f"重新加载配置失败: {e}", exc_info=True)

    def _notify_callbacks(self, old_config: AppConfig, new_config: AppConfig) -> None:
        """通知所有注册的回调函数

        Args:
            old_config: 旧配置
            new_config: 新配置
        """
        for callback in self._callbacks:
            try:
                callback(old_config, new_config)
            except Exception as e:
                logger.error(f"配置更新回调执行失败: {e}", exc_info=True)

    def register_callback(self, callback: Callable[[AppConfig, AppConfig], None]) -> None:
        """注册配置更新回调函数

        当配置更新时，所有注册的回调函数都会被调用。

        Args:
            callback: 回调函数，接收 (old_config, new_config) 参数
        """
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)
                logger.info(f"已注册配置更新回调: {callback.__name__ if hasattr(callback, '__name__') else 'unknown'}")

    def unregister_callback(self, callback: Callable[[AppConfig, AppConfig], None]) -> None:
        """取消注册配置更新回调函数

        Args:
            callback: 要取消注册的回调函数
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
                logger.info(f"已取消注册配置更新回调: {callback.__name__ if hasattr(callback, '__name__') else 'unknown'}")

    def get_current_config(self) -> Optional[AppConfig]:
        """获取当前配置

        Returns:
            当前配置，如果未加载则返回None
        """
        with self._lock:
            return self._current_config

    def is_running(self) -> bool:
        """检查服务是否正在运行

        Returns:
            服务是否正在运行
        """
        with self._lock:
            return self._is_running

    def trigger_manual_reload(self) -> None:
        """手动触发配置重新加载"""
        logger.info("手动触发配置重新加载")
        self._reload_config()
