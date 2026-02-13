"""配置验证服务测试"""
import pytest

from core.config import AppConfig, OcrConfig
from services.config_validator_service import ConfigValidatorService
from core.exceptions import ConfigError


class TestConfigValidatorService:
    """配置验证服务测试类"""

    @pytest.fixture
    def validator(self):
        """配置验证器fixture"""
        return ConfigValidatorService()

    @pytest.fixture
    def valid_config(self):
        """有效配置fixture"""
        return AppConfig(
            app_title_prefix="Torch",
            keywords=("火炬之光无限",),
            watch_interval_ms=500,
            ocr=OcrConfig(
                api_key="test_api_key_123",
                secret_key="test_secret_key_456",
                api_name="accurate",
                timeout_sec=15.0,
                max_retries=2,
                debug_mode=False
            )
        )

    def test_validate_valid_config(self, validator, valid_config):
        """测试验证有效配置"""
        is_valid, errors, warnings = validator.validate_app_config(valid_config)

        assert is_valid
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_empty_api_key(self, validator, valid_config):
        """测试空的API Key"""
        valid_config.ocr.api_key = ""

        with pytest.raises(ConfigError):
            validator.validate_app_config(valid_config)

    def test_validate_short_api_key(self, validator, valid_config):
        """测试过短的API Key"""
        valid_config.ocr.api_key = "short"

        is_valid, errors, warnings = validator.validate_app_config(valid_config)

        assert not is_valid
        assert any("api_key" in error for error in errors)

    def test_validate_empty_secret_key(self, validator, valid_config):
        """测试空的Secret Key"""
        valid_config.ocr.secret_key = ""

        with pytest.raises(ConfigError):
            validator.validate_app_config(valid_config)

    def test_validate_invalid_api_name(self, validator, valid_config):
        """测试无效的API名称"""
        valid_config.ocr.api_name = "invalid_api"

        is_valid, errors, warnings = validator.validate_app_config(valid_config)

        # 应该有警告但不应该有错误
        assert is_valid or len(errors) == 0
        assert len(warnings) > 0

    def test_validate_timeout_too_short(self, validator, valid_config):
        """测试过短的超时时间"""
        valid_config.ocr.timeout_sec = 0.5

        is_valid, errors, warnings = validator.validate_app_config(valid_config)

        assert not is_valid
        assert any("timeout_sec" in error for error in errors)

    def test_validate_timeout_too_long(self, validator, valid_config):
        """测试过长的超时时间"""
        valid_config.ocr.timeout_sec = 100.0

        is_valid, errors, warnings = validator.validate_app_config(valid_config)

        # 应该有警告但不应该有错误
        assert is_valid or len(errors) == 0
        assert len(warnings) > 0
        assert any("timeout_sec" in warning for warning in warnings)

    def test_validate_max_retries_invalid(self, validator, valid_config):
        """测试无效的最大重试次数"""
        valid_config.ocr.max_retries = 20

        is_valid, errors, warnings = validator.validate_app_config(valid_config)

        # 应该有警告但不应该有错误
        assert is_valid or len(errors) == 0
        assert len(warnings) > 0

    def test_validate_empty_keywords(self, validator):
        """测试空的关键词"""
        config = AppConfig(keywords=())

        with pytest.raises(ConfigError):
            validator.validate_app_config(config)

    def test_validate_watch_interval_too_short(self, validator, valid_config):
        """测试过短的监视间隔"""
        valid_config.watch_interval_ms = 50

        is_valid, errors, warnings = validator.validate_app_config(valid_config)

        assert not is_valid
        assert any("watch_interval_ms" in error for error in errors)

    def test_validate_watch_interval_too_long(self, validator, valid_config):
        """测试过长的监视间隔"""
        valid_config.watch_interval_ms = 120000

        is_valid, errors, warnings = validator.validate_app_config(valid_config)

        # 应该有警告但不应该有错误
        assert is_valid or len(errors) == 0
        assert len(warnings) > 0

    def test_validate_invalid_mystery_gem_mode(self, validator, valid_config):
        """测试无效的奥秘辉石模式"""
        valid_config.mystery_gem_mode = "invalid_mode"

        with pytest.raises(ConfigError):
            validator.validate_app_config(valid_config)

    def test_validate_valid_mystery_gem_modes(self, validator, valid_config):
        """测试有效的奥秘辉石模式"""
        valid_modes = ["min", "max", "random"]

        for mode in valid_modes:
            valid_config.mystery_gem_mode = mode
            is_valid, errors, warnings = validator.validate_app_config(valid_config)

            assert is_valid
            assert len(errors) == 0

    def test_validate_invalid_enable_tax_calculation(self, validator, valid_config):
        """测试无效的税率计算标志"""
        valid_config.enable_tax_calculation = "true"  # 字符串而不是布尔值

        is_valid, errors, warnings = validator.validate_app_config(valid_config)

        assert not is_valid
        assert any("enable_tax_calculation" in error for error in errors)

    def test_validate_dict_valid(self, validator, valid_config):
        """测试验证有效的配置字典"""
        config_dict = valid_config.to_dict()

        is_valid, errors, warnings = validator.validate_dict(config_dict)

        assert is_valid
        assert len(errors) == 0

    def test_validate_dict_invalid(self, validator):
        """测试验证无效的配置字典"""
        config_dict = {"invalid": "config"}

        is_valid, errors, warnings = validator.validate_dict(config_dict)

        assert not is_valid
        assert len(errors) > 0

    def test_get_default_config(self, validator):
        """测试获取默认配置"""
        default_config = validator.get_default_config()

        assert isinstance(default_config, AppConfig)
        assert default_config.app_title_prefix == "Torch"
        assert default_config.keywords == ("火炬之光无限", "火炬之光", "Torchlight")
