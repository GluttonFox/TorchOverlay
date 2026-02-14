"""配置访问工具 - 简化配置访问和管理"""
from typing import Optional, Any
from functools import lru_cache

from core.config import AppConfig
from core.logger import get_logger

logger = get_logger(__name__)


class ConfigAccess:
    """配置访问工具类

    提供便捷的配置访问接口，支持缓存和监听。
    """

    _instance: Optional['ConfigAccess'] = None

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化配置访问"""
        self._config: Optional[AppConfig] = None
        self._listeners = []

    def load_config(self, config_path: Optional[str] = None) -> AppConfig:
        """加载配置

        Args:
            config_path: 配置文件路径，None使用默认

        Returns:
            配置对象
        """
        try:
            self._config = AppConfig.load(config_path)
            logger.info(f"配置已加载: {config_path or '默认路径'}")
            self._notify_listeners()
            return self._config
        except Exception as e:
            logger.error(f"加载配置失败: {e}", exc_info=True)
            raise

    def save_config(self, config_path: Optional[str] = None) -> None:
        """保存配置

        Args:
            config_path: 配置文件路径，None使用默认
        """
        if self._config is None:
            raise RuntimeError("配置未加载，无法保存")

        try:
            self._config.save(config_path)
            logger.info(f"配置已保存: {config_path or '默认路径'}")
            self._notify_listeners()
        except Exception as e:
            logger.error(f"保存配置失败: {e}", exc_info=True)
            raise

    def get_config(self) -> AppConfig:
        """获取当前配置

        Returns:
            配置对象

        Raises:
            RuntimeError: 配置未加载
        """
        if self._config is None:
            self._config = AppConfig.load()
        return self._config

    def reload(self) -> AppConfig:
        """重新加载配置

        Returns:
            新配置对象
        """
        return self.load_config()

    @lru_cache(maxsize=32)
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（带缓存）

        Args:
            key: 配置键（支持点分隔的路径，如"ocr.api_key"）
            default: 默认值

        Returns:
            配置值

        Example:
            >>> config.get("ocr.api_key")
            "your_api_key"
            >>> config.get("ocr.timeout_sec", 15.0)
            15.0
        """
        config = self.get_config()
        keys = key.split('.')

        value = config
        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            else:
                return default

        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """设置配置值

        Args:
            key: 配置键（支持点分隔的路径）
            value: 配置值

        Example:
            >>> config.set("ocr.api_key", "new_key")
            >>> config.set("ocr.timeout_sec", 30.0)
        """
        config = self.get_config()
        keys = key.split('.')

        # 找到父对象
        obj = config
        for k in keys[:-1]:
            if hasattr(obj, k):
                obj = getattr(obj, k)
            else:
                raise AttributeError(f"配置路径不存在: {key}")

        # 设置最后一个键
        setattr(obj, keys[-1], value)

        # 清除缓存
        self.get.cache_clear()

        logger.debug(f"配置已更新: {key} = {value}")

    def add_listener(self, callback) -> None:
        """添加配置变更监听器

        Args:
            callback: 回调函数，签名为 callback(config)
        """
        if callback not in self._listeners:
            self._listeners.append(callback)
            logger.debug(f"添加配置监听器: {callback.__name__}")

    def remove_listener(self, callback) -> None:
        """移除配置变更监听器

        Args:
            callback: 要移除的回调函数
        """
        if callback in self._listeners:
            self._listeners.remove(callback)
            logger.debug(f"移除配置监听器: {callback.__name__}")

    def _notify_listeners(self) -> None:
        """通知所有监听器配置已变更"""
        for callback in self._listeners:
            try:
                callback(self._config)
            except Exception as e:
                logger.error(f"配置监听器执行失败: {e}", exc_info=True)

    # 快捷访问方法
    def get_ocr_api_key(self) -> str:
        """获取OCR API Key"""
        return self.get("ocr.api_key", "")

    def get_ocr_secret_key(self) -> str:
        """获取OCR Secret Key"""
        return self.get("ocr.secret_key", "")

    def get_ocr_api_name(self) -> str:
        """获取OCR API名称"""
        return self.get("ocr.api_name", "general_basic")

    def get_ocr_timeout(self) -> float:
        """获取OCR超时时间"""
        return self.get("ocr.timeout_sec", 15.0)

    def get_watch_interval(self) -> int:
        """获取监视间隔"""
        return self.get("watch_interval_ms", 500)

    def get_app_title_prefix(self) -> str:
        """获取应用标题前缀"""
        return self.get("app_title_prefix", "Torch")

    def set_ocr_api_key(self, api_key: str) -> None:
        """设置OCR API Key"""
        self.set("ocr.api_key", api_key)

    def set_ocr_secret_key(self, secret_key: str) -> None:
        """设置OCR Secret Key"""
        self.set("ocr.secret_key", secret_key)

    def set_ocr_api_name(self, api_name: str) -> None:
        """设置OCR API名称"""
        self.set("ocr.api_name", api_name)

    def set_ocr_timeout(self, timeout: float) -> None:
        """设置OCR超时时间"""
        self.set("ocr.timeout_sec", timeout)

    def set_watch_interval(self, interval_ms: int) -> None:
        """设置监视间隔"""
        self.set("watch_interval_ms", interval_ms)


# 全局实例
_config_access: Optional[ConfigAccess] = None


def get_config_access() -> ConfigAccess:
    """获取配置访问实例

    Returns:
        ConfigAccess 实例
    """
    global _config_access
    if _config_access is None:
        _config_access = ConfigAccess()
    return _config_access


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """加载配置（便捷函数）

    Args:
        config_path: 配置文件路径

    Returns:
        配置对象
    """
    return get_config_access().load_config(config_path)


def save_config(config_path: Optional[str] = None) -> None:
    """保存配置（便捷函数）

    Args:
        config_path: 配置文件路径
    """
    return get_config_access().save_config(config_path)


def get_config_value(key: str, default: Any = None) -> Any:
    """获取配置值（便捷函数）

    Args:
        key: 配置键
        default: 默认值

    Returns:
        配置值
    """
    return get_config_access().get(key, default)


def set_config_value(key: str, value: Any) -> None:
    """设置配置值（便捷函数）

    Args:
        key: 配置键
        value: 配置值
    """
    return get_config_access().set(key, value)


# 快捷访问函数
def get_ocr_api_key() -> str:
    """获取OCR API Key"""
    return get_config_access().get_ocr_api_key()


def get_ocr_secret_key() -> str:
    """获取OCR Secret Key"""
    return get_config_access().get_ocr_secret_key()


def get_ocr_timeout() -> float:
    """获取OCR超时时间"""
    return get_config_access().get_ocr_timeout()


def set_ocr_api_key(api_key: str) -> None:
    """设置OCR API Key"""
    return get_config_access().set_ocr_api_key(api_key)


def set_ocr_secret_key(secret_key: str) -> None:
    """设置OCR Secret Key"""
    return get_config_access().set_ocr_secret_key(secret_key)
