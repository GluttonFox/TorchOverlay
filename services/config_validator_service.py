"""配置验证服务 - 负责配置项的合法性验证"""
from typing import Any
from dataclasses import fields

from core.config import AppConfig, OcrConfig
from core.exceptions import ConfigError
from core.logger import get_logger

logger = get_logger(__name__)


class ConfigValidatorService:
    """配置验证服务"""

    # OCR配置验证规则
    VALID_OCR_API_NAMES = {"general_basic", "accurate", "webimage", "general"}
    VALID_MYSTERY_GEM_MODES = {"min", "max", "random"}

    # 值范围验证
    MIN_WATCH_INTERVAL_MS = 100
    MAX_WATCH_INTERVAL_MS = 60000
    MIN_TIMEOUT_SEC = 1.0
    MAX_TIMEOUT_SEC = 60.0
    MIN_MAX_RETRIES = 0
    MAX_MAX_RETRIES = 10

    def __init__(self):
        """初始化配置验证服务"""
        self._errors = []
        self._warnings = []

    def validate_app_config(self, config: AppConfig) -> tuple[bool, list[str], list[str]]:
        """验证应用配置

        Args:
            config: 应用配置对象

        Returns:
            (是否有效, 错误列表, 警告列表)
        """
        self._errors = []
        self._warnings = []

        # 验证基本字段
        self._validate_app_title_prefix(config.app_title_prefix)
        self._validate_keywords(config.keywords)
        self._validate_watch_interval(config.watch_interval_ms)
        self._validate_mystery_gem_mode(config.mystery_gem_mode)

        # 验证OCR配置
        self._validate_ocr_config(config.ocr)

        # 验证上次更新时间
        self._validate_last_price_update(config.last_price_update)

        # 验证税率计算标志
        self._validate_enable_tax_calculation(config.enable_tax_calculation)

        is_valid = len(self._errors) == 0

        if not is_valid:
            error_msg = f"配置验证失败: {self._errors}"
            logger.error(error_msg)
            raise ConfigError(error_msg)

        if self._warnings:
            for warning in self._warnings:
                logger.warning(f"配置警告: {warning}")

        return is_valid, self._errors.copy(), self._warnings.copy()

    def _validate_app_title_prefix(self, prefix: str) -> None:
        """验证应用标题前缀"""
        if not prefix or not prefix.strip():
            self._errors.append("app_title_prefix 不能为空")

    def _validate_keywords(self, keywords: tuple[str, ...]) -> None:
        """验证关键词"""
        if not keywords or len(keywords) == 0:
            self._errors.append("keywords 不能为空")
        else:
            for i, keyword in enumerate(keywords):
                if not keyword or not keyword.strip():
                    self._errors.append(f"keywords[{i}] 不能为空")

    def _validate_watch_interval(self, interval_ms: int) -> None:
        """验证监视间隔"""
        if not isinstance(interval_ms, int):
            self._errors.append(f"watch_interval_ms 必须是整数，当前类型: {type(interval_ms)}")
        elif interval_ms < self.MIN_WATCH_INTERVAL_MS:
            self._errors.append(f"watch_interval_ms 不能小于 {self.MIN_WATCH_INTERVAL_MS}ms")
        elif interval_ms > self.MAX_WATCH_INTERVAL_MS:
            self._warnings.append(f"watch_interval_ms 较大 ({interval_ms}ms)，可能导致性能问题")

    def _validate_mystery_gem_mode(self, mode: str) -> None:
        """验证奥秘辉石处理模式"""
        if mode not in self.VALID_MYSTERY_GEM_MODES:
            self._errors.append(
                f"mystery_gem_mode 必须是 {self.VALID_MYSTERY_GEM_MODES} 之一，当前值: {mode}"
            )

    def _validate_ocr_config(self, ocr_config: OcrConfig) -> None:
        """验证OCR配置"""
        # 验证API Key
        if not ocr_config.api_key or not ocr_config.api_key.strip():
            self._errors.append("ocr.api_key 不能为空")
        elif len(ocr_config.api_key) < 10:
            self._errors.append("ocr.api_key 长度不能小于10个字符")

        # 验证Secret Key
        if not ocr_config.secret_key or not ocr_config.secret_key.strip():
            self._errors.append("ocr.secret_key 不能为空")
        elif len(ocr_config.secret_key) < 10:
            self._errors.append("ocr.secret_key 长度不能小于10个字符")

        # 验证API名称
        if ocr_config.api_name not in self.VALID_OCR_API_NAMES:
            self._warnings.append(
                f"ocr.api_name '{ocr_config.api_name}' 可能不是有效的百度OCR API类型"
            )

        # 验证超时时间
        if not isinstance(ocr_config.timeout_sec, (int, float)):
            self._errors.append(f"ocr.timeout_sec 必须是数字，当前类型: {type(ocr_config.timeout_sec)}")
        elif ocr_config.timeout_sec < self.MIN_TIMEOUT_SEC:
            self._errors.append(f"ocr.timeout_sec 不能小于 {self.MIN_TIMEOUT_SEC}秒")
        elif ocr_config.timeout_sec > self.MAX_TIMEOUT_SEC:
            self._warnings.append(
                f"ocr.timeout_sec 较大 ({ocr_config.timeout_sec}秒)，可能导致请求超时"
            )

        # 验证最大重试次数
        if not isinstance(ocr_config.max_retries, int):
            self._errors.append(f"ocr.max_retries 必须是整数，当前类型: {type(ocr_config.max_retries)}")
        elif ocr_config.max_retries < self.MIN_MAX_RETRIES:
            self._errors.append(f"ocr.max_retries 不能小于 {self.MIN_MAX_RETRIES}")
        elif ocr_config.max_retries > self.MAX_MAX_RETRIES:
            self._warnings.append(
                f"ocr.max_retries 较大 ({ocr_config.max_retries}次)，可能导致长时间等待"
            )

    def _validate_last_price_update(self, last_update: str) -> None:
        """验证上次价格更新时间"""
        if last_update and last_update.strip():
            try:
                # 尝试解析ISO格式时间
                from datetime import datetime
                datetime.fromisoformat(last_update)
            except (ValueError, TypeError) as e:
                self._warnings.append(f"last_price_update 格式无效: {last_update} ({e})")

    def _validate_enable_tax_calculation(self, enable: bool) -> None:
        """验证税率计算标志"""
        if not isinstance(enable, bool):
            self._errors.append(f"enable_tax_calculation 必须是布尔值，当前类型: {type(enable)}")

    def validate_dict(self, config_dict: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
        """验证配置字典

        Args:
            config_dict: 配置字典

        Returns:
            (是否有效, 错误列表, 警告列表)
        """
        try:
            # 尝试将字典转换为配置对象
            config = AppConfig.from_dict(config_dict)
            return self.validate_app_config(config)
        except Exception as e:
            self._errors.append(f"配置字典格式错误: {e}")
            return False, self._errors.copy(), self._warnings.copy()

    def get_default_config(self) -> AppConfig:
        """获取默认配置"""
        return AppConfig()
