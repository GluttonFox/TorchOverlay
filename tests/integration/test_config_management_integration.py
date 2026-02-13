"""配置管理集成测试"""
import pytest
import tempfile
import json
from pathlib import Path
from time import sleep

from core.config import AppConfig
from services.config_manager import ConfigManager
from services.config_validator_service import ConfigValidatorService
from services.config_merge_service import ConfigMergeService
from core.exceptions import ConfigError


class TestConfigManagementIntegration:
    """配置管理集成测试类"""

    def test_load_and_save_config(self, tmp_path):
        """测试加载和保存配置"""
        config_path = tmp_path / "config.json"

        # 创建配置管理器
        config_manager = ConfigManager(config_path=str(config_path))

        try:
            # 创建并保存配置
            config = AppConfig(
                app_title_prefix="Test",
                keywords=("test",),
                watch_interval_ms=1000
            )
            config_manager.save_config(config)

            # 重新加载配置
            loaded_config = config_manager.load_config()

            assert loaded_config.app_title_prefix == "Test"
            assert loaded_config.watch_interval_ms == 1000

        finally:
            config_manager.shutdown()

    def test_config_validation_integration(self, tmp_path):
        """测试配置验证集成"""
        config_path = tmp_path / "config.json"

        # 创建配置管理器
        config_manager = ConfigManager(config_path=str(config_path))

        try:
            # 保存有效配置
            config = AppConfig()
            config_manager.save_config(config)

            # 加载并验证
            loaded_config = config_manager.load_config()
            is_valid, errors, warnings = config_manager.validate_config(loaded_config)

            assert is_valid
            assert len(errors) == 0

        finally:
            config_manager.shutdown()

    def test_config_merge_integration(self, tmp_path):
        """测试配置合并集成"""
        config_path = tmp_path / "config.json"
        default_path = tmp_path / "default.json"

        # 创建默认配置
        default_config = {
            "app_title_prefix": "Default",
            "watch_interval_ms": 500,
            "ocr": {
                "api_name": "accurate",
                "timeout_sec": 15.0
            }
        }
        default_path.write_text(json.dumps(default_config, indent=2))

        # 创建用户配置
        user_config = {
            "watch_interval_ms": 1000,
            "ocr": {
                "api_key": "test_key"
            }
        }
        config_path.write_text(json.dumps(user_config, indent=2))

        # 使用合并服务
        merge_service = ConfigMergeService()
        merged_dict = merge_service.merge_files(
            str(default_path),
            str(config_path),
            strategy="override"
        )

        assert merged_dict["app_title_prefix"] == "Default"
        assert merged_dict["watch_interval_ms"] == 1000
        assert merged_dict["ocr"]["api_name"] == "accurate"
        assert merged_dict["ocr"]["api_key"] == "test_key"

    def test_config_with_callback(self, tmp_path):
        """测试配置更新回调"""
        config_path = tmp_path / "config.json"
        callbacks = []

        def callback(old_config, new_config):
            callbacks.append((old_config, new_config))

        # 创建配置管理器
        config_manager = ConfigManager(config_path=str(config_path))

        try:
            # 注册回调
            config_manager.register_update_callback(callback)

            # 保存配置（手动触发更新）
            config = AppConfig(watch_interval_ms=1000)
            config_manager.save_config(config)

            # 手动触发重新加载
            config_manager.reload_config()

            # 验证回调被调用
            assert len(callbacks) > 0

        finally:
            config_manager.shutdown()

    def test_invalid_config_handling(self, tmp_path):
        """测试无效配置处理"""
        config_path = tmp_path / "config.json"

        # 创建无效配置
        invalid_config = {
            "app_title_prefix": "",  # 空值
            "keywords": [],  # 空列表
            "watch_interval_ms": 50,  # 太短
            "ocr": {
                "api_key": "short",  # 太短
                "secret_key": ""  # 空值
            }
        }
        config_path.write_text(json.dumps(invalid_config))

        # 创建配置管理器
        config_manager = ConfigManager(config_path=str(config_path))

        try:
            # 尝试加载配置应该失败
            with pytest.raises(ConfigError):
                config_manager.load_config()

        finally:
            config_manager.shutdown()

    def test_config_encryption_integration(self, tmp_path):
        """测试配置加密集成"""
        config_path = tmp_path / "config.json"

        # 创建配置管理器（启用加密）
        config_manager = ConfigManager(
            config_path=str(config_path),
            enable_encryption=True,
            master_password="test_password"
        )

        try:
            # 创建并保存配置（会自动加密）
            config = AppConfig()
            config_manager.save_config(config)

            # 读取加密的配置文件
            encrypted_data = json.loads(config_path.read_text())
            assert "api_key" in encrypted_data["ocr"]

            # 重新加载配置（会自动解密）
            loaded_config = config_manager.load_config()

            assert loaded_config.app_title_prefix == "Torch"

        finally:
            config_manager.shutdown()

    def test_config_compare_integration(self, tmp_path):
        """测试配置对比集成"""
        config1_path = tmp_path / "config1.json"
        config2_path = tmp_path / "config2.json"

        # 创建两个不同的配置
        config1 = {
            "a": 1,
            "b": 2,
            "ocr": {
                "api_key": "key1"
            }
        }
        config1_path.write_text(json.dumps(config1))

        config2 = {
            "a": 2,  # 修改
            "c": 3,  # 新增
            "ocr": {
                "api_key": "key2"  # 修改
            }
        }
        config2_path.write_text(json.dumps(config2))

        # 使用合并服务对比
        merge_service = ConfigMergeService()

        with open(config1_path) as f:
            config1_dict = json.load(f)
        with open(config2_path) as f:
            config2_dict = json.load(f)

        diff = merge_service.compare_configs(config1_dict, config2_dict)

        assert "c" in diff['added']
        assert "a" in diff['modified']
        assert diff['modified']['a']['old'] == 1
        assert diff['modified']['a']['new'] == 2

    def test_config_with_default_values(self, tmp_path):
        """测试使用默认值加载配置"""
        config_path = tmp_path / "config.json"
        default_path = tmp_path / "default.json"

        # 创建默认配置
        default_config = {
            "app_title_prefix": "Default",
            "watch_interval_ms": 500
        }
        default_path.write_text(json.dumps(default_config))

        # 创建部分配置（只覆盖部分字段）
        partial_config = {
            "watch_interval_ms": 1000
        }
        config_path.write_text(json.dumps(partial_config))

        # 使用合并服务加载
        merge_service = ConfigMergeService()
        config = merge_service.load_config_with_defaults(
            str(config_path),
            str(default_path)
        )

        assert config.app_title_prefix == "Default"  # 从默认值
        assert config.watch_interval_ms == 1000  # 从用户配置

    def test_config_manager_shutdown(self, tmp_path):
        """测试配置管理器关闭"""
        config_path = tmp_path / "config.json"

        # 创建配置管理器（启用热更新）
        config_manager = ConfigManager(
            config_path=str(config_path),
            enable_hot_reload=True
        )

        # 保存配置
        config = AppConfig()
        config_manager.save_config(config)

        # 关闭管理器
        config_manager.shutdown()

        # 验证服务已停止
        assert not config_manager.is_running()
