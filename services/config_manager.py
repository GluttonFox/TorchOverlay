"""配置管理器 - 统一的配置管理入口"""
import json
from typing import Callable, Optional, Any
from pathlib import Path

from core.config import AppConfig
from core.logger import get_logger
from core.exceptions import ConfigError
from services.config_validator_service import ConfigValidatorService
from services.config_hot_reload_service import ConfigHotReloadService
from services.config_encryption_service import ConfigEncryptionService, get_encryption_service
from services.config_merge_service import ConfigMergeService

logger = get_logger(__name__)


class ConfigManager:
    """配置管理器

    统一的配置管理入口，整合验证、热更新、加密、合并等功能。
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        enable_hot_reload: bool = True,
        enable_encryption: bool = False,
        master_password: Optional[str] = None
    ):
        """初始化配置管理器

        Args:
            config_path: 配置文件路径（如果为None，使用默认路径）
            enable_hot_reload: 是否启用配置热更新
            enable_encryption: 是否启用配置加密
            master_password: 加密主密码
        """
        self._config_path = config_path or AppConfig.get_config_path()
        self._enable_hot_reload = enable_hot_reload
        self._enable_encryption = enable_encryption

        # 创建子服务
        self._validator = ConfigValidatorService()
        self._merge_service = ConfigMergeService()
        self._encryption_service = (
            get_encryption_service(master_password) if enable_encryption else None
        )
        self._hot_reload_service = None

        # 当前配置
        self._current_config: Optional[AppConfig] = None

        # 配置更新回调
        self._update_callbacks: list[Callable[[AppConfig, AppConfig], None]] = []

    def load_config(self, config_path: Optional[str] = None) -> AppConfig:
        """加载配置

        Args:
            config_path: 配置文件路径（如果为None，使用默认路径）

        Returns:
            应用配置对象

        Raises:
            ConfigError: 配置加载或验证失败
        """
        path = config_path or self._config_path

        try:
            # 读取配置文件
            with open(path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)

            # 如果启用了加密，解密配置
            if self._enable_encryption and self._encryption_service:
                config_dict = self._encryption_service.decrypt_dict(config_dict)
                logger.info("配置已解密")

            # 验证配置
            self._validator.validate_dict(config_dict)

            # 转换为AppConfig
            config = AppConfig.from_dict(config_dict)

            # 保存当前配置
            self._current_config = config

            # 启动热更新服务
            if self._enable_hot_reload and self._hot_reload_service is None:
                self._start_hot_reload()

            logger.info(f"配置加载成功: {path}")
            return config

        except FileNotFoundError:
            logger.warning(f"配置文件不存在，使用默认配置: {path}")
            config = AppConfig()
            self._current_config = config
            return config
        except json.JSONDecodeError as e:
            raise ConfigError(f"配置文件格式错误: {e}")
        except Exception as e:
            raise ConfigError(f"加载配置失败: {e}")

    def save_config(
        self,
        config: AppConfig,
        config_path: Optional[str] = None,
        encrypt: Optional[bool] = None
    ) -> None:
        """保存配置

        Args:
            config: 要保存的配置对象
            config_path: 配置文件路径（如果为None，使用默认路径）
            encrypt: 是否加密（如果为None，使用管理器设置）

        Raises:
            ConfigError: 配置保存失败
        """
        path = config_path or self._config_path
        should_encrypt = encrypt if encrypt is not None else self._enable_encryption

        try:
            # 验证配置
            self._validator.validate_app_config(config)

            # 转换为字典
            config_dict = config.to_dict()

            # 如果需要加密，加密配置
            if should_encrypt and self._encryption_service:
                config_dict = self._encryption_service.encrypt_dict(config_dict)
                logger.info("配置已加密")

            # 确保目录存在
            Path(path).parent.mkdir(parents=True, exist_ok=True)

            # 保存到文件
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=4, ensure_ascii=False)

            # 更新当前配置
            self._current_config = config

            logger.info(f"配置保存成功: {path}")

        except Exception as e:
            raise ConfigError(f"保存配置失败: {e}")

    def get_config(self) -> Optional[AppConfig]:
        """获取当前配置

        Returns:
            当前配置，如果未加载则返回None
        """
        return self._current_config

    def reload_config(self) -> AppConfig:
        """重新加载配置

        Returns:
            重新加载后的配置

        Raises:
            ConfigError: 配置加载失败
        """
        logger.info("重新加载配置")
        return self.load_config()

    def validate_config(self, config: AppConfig) -> tuple[bool, list[str], list[str]]:
        """验证配置

        Args:
            config: 要验证的配置对象

        Returns:
            (是否有效, 错误列表, 警告列表)
        """
        return self._validator.validate_app_config(config)

    def _start_hot_reload(self) -> None:
        """启动热更新服务"""
        if self._hot_reload_service is None:
            self._hot_reload_service = ConfigHotReloadService(
                config_path=self._config_path,
                validator=self._validator
            )

            # 注册内部回调
            self._hot_reload_service.register_callback(self._on_config_changed)

            # 启动服务
            self._hot_reload_service.start(self._current_config)

            logger.info("配置热更新服务已启动")

    def _stop_hot_reload(self) -> None:
        """停止热更新服务"""
        if self._hot_reload_service:
            self._hot_reload_service.stop()
            self._hot_reload_service = None
            logger.info("配置热更新服务已停止")

    def _on_config_changed(self, old_config: AppConfig, new_config: AppConfig) -> None:
        """配置更新回调（内部使用）

        Args:
            old_config: 旧配置
            new_config: 新配置
        """
        # 更新当前配置
        self._current_config = new_config

        # 通知外部回调
        for callback in self._update_callbacks:
            try:
                callback(old_config, new_config)
            except Exception as e:
                logger.error(f"配置更新回调执行失败: {e}", exc_info=True)

    def register_update_callback(
        self,
        callback: Callable[[AppConfig, AppConfig], None]
    ) -> None:
        """注册配置更新回调

        Args:
            callback: 回调函数，接收 (old_config, new_config) 参数
        """
        if callback not in self._update_callbacks:
            self._update_callbacks.append(callback)
            logger.info(f"已注册配置更新回调: {callback.__name__ if hasattr(callback, '__name__') else 'unknown'}")

    def unregister_update_callback(
        self,
        callback: Callable[[AppConfig, AppConfig], None]
    ) -> None:
        """取消注册配置更新回调

        Args:
            callback: 要取消注册的回调函数
        """
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)
            logger.info(f"已取消注册配置更新回调: {callback.__name__ if hasattr(callback, '__name__') else 'unknown'}")

    def merge_configs(
        self,
        *configs: dict[str, Any],
        strategy: str = "override"
    ) -> dict[str, Any]:
        """合并多个配置

        Args:
            *configs: 配置字典列表
            strategy: 合并策略

        Returns:
            合并后的配置字典
        """
        return self._merge_service.merge_configs(*configs, strategy=strategy)

    def encrypt_config_file(
        self,
        input_path: str,
        output_path: str
    ) -> None:
        """加密配置文件

        Args:
            input_path: 输入配置文件路径
            output_path: 输出加密配置文件路径

        Raises:
            ConfigError: 加密失败
        """
        if not self._encryption_service:
            raise ConfigError("配置加密服务未启用")

        self._encryption_service.encrypt_config_file(input_path, output_path)

    def decrypt_config_file(
        self,
        input_path: str,
        output_path: str
    ) -> None:
        """解密配置文件

        Args:
            input_path: 输入加密配置文件路径
            output_path: 输出解密配置文件路径

        Raises:
            ConfigError: 解密失败
        """
        if not self._encryption_service:
            raise ConfigError("配置加密服务未启用")

        self._encryption_service.decrypt_config_file(input_path, output_path)

    def shutdown(self) -> None:
        """关闭配置管理器"""
        self._stop_hot_reload()
        self._update_callbacks.clear()
        logger.info("配置管理器已关闭")
