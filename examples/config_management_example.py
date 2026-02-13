"""配置管理使用示例

本文件展示了如何在TorchOverlay项目中使用配置管理服务。
"""

from core.config import AppConfig
from services.config_manager import ConfigManager
from services.config_validator_service import ConfigValidatorService
from services.config_merge_service import ConfigMergeService
from core.logger import get_logger

logger = get_logger(__name__)


def example_basic_config_manager():
    """示例1：使用配置管理器的基本功能"""
    print("\n=== 示例1：基本配置管理 ===")

    # 创建配置管理器（不启用热更新和加密）
    config_manager = ConfigManager(
        enable_hot_reload=False,
        enable_encryption=False
    )

    try:
        # 加载配置
        config = config_manager.load_config()
        print(f"配置加载成功: {config.app_title_prefix}")
        print(f"监视间隔: {config.watch_interval_ms}ms")
        print(f"调试模式: {config.ocr.debug_mode}")

        # 保存配置
        config.watch_interval_ms = 1000
        config_manager.save_config(config)
        print("配置已保存")

    except Exception as e:
        print(f"配置操作失败: {e}")

    finally:
        config_manager.shutdown()


def example_hot_reload():
    """示例2：使用配置热更新"""
    print("\n=== 示例2：配置热更新 ===")

    def on_config_changed(old_config, new_config):
        """配置更新回调"""
        print(f"配置已更新!")
        print(f"  旧监视间隔: {old_config.watch_interval_ms}ms")
        print(f"  新监视间隔: {new_config.watch_interval_ms}ms")

    # 创建配置管理器（启用热更新）
    config_manager = ConfigManager(enable_hot_reload=True)

    try:
        # 加载配置
        config = config_manager.load_config()
        print(f"配置加载成功")

        # 注册配置更新回调
        config_manager.register_update_callback(on_config_changed)

        print("配置热更新已启用，请修改config.json文件...")
        print("按Ctrl+C停止")

        # 保持运行以监听配置变化
        import time
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n停止配置热更新")
    finally:
        config_manager.shutdown()


def example_encryption():
    """示例3：使用配置加密"""
    print("\n=== 示例3：配置加密 ===")

    # 创建配置管理器（启用加密）
    config_manager = ConfigManager(
        enable_encryption=True,
        master_password="your_secure_password"  # 生产环境应该从环境变量或安全存储获取
    )

    try:
        # 加载配置（会自动解密）
        config = config_manager.load_config()
        print(f"配置加载成功（已解密）")

        # 保存配置（会自动加密）
        config_manager.save_config(config, encrypt=True)
        print("配置已保存（已加密）")

    except Exception as e:
        print(f"配置操作失败: {e}")

    finally:
        config_manager.shutdown()


def example_encryption_cli():
    """示例4：加密/解密配置文件的命令行操作"""
    print("\n=== 示例4：加密/解密配置文件 ===")

    from services.config_encryption_service import ConfigEncryptionService
    from core.exceptions import ConfigError

    # 创建加密服务
    encryption_service = ConfigEncryptionService(master_password="your_secure_password")

    try:
        # 加密配置文件
        input_file = "config.json"
        output_file = "config_encrypted.json"

        encryption_service.encrypt_config_file(input_file, output_file)
        print(f"配置文件已加密: {output_file}")

        # 解密配置文件
        decrypted_file = "config_decrypted.json"
        encryption_service.decrypt_config_file(output_file, decrypted_file)
        print(f"配置文件已解密: {decrypted_file}")

        # 检查加密状态
        import json
        with open(input_file, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)

        status = encryption_service.get_encryption_status(config_dict)
        print(f"加密状态: {status}")

    except ConfigError as e:
        print(f"加密操作失败: {e}")


def example_merge_configs():
    """示例5：合并多个配置"""
    print("\n=== 示例5：合并配置 ===")

    merge_service = ConfigMergeService()

    # 定义多个配置
    default_config = {
        "app_title_prefix": "Torch",
        "keywords": ["火炬之光无限"],
        "watch_interval_ms": 500,
        "ocr": {
            "api_name": "accurate",
            "timeout_sec": 15.0
        }
    }

    user_config = {
        "watch_interval_ms": 1000,
        "ocr": {
            "api_key": "user_key",
            "secret_key": "user_secret"
        }
    }

    environment_config = {
        "watch_interval_ms": 2000,
        "ocr": {
            "debug_mode": True
        }
    }

    # 使用override策略（后面的配置覆盖前面的）
    merged = merge_service.merge_configs(
        default_config,
        user_config,
        environment_config,
        strategy="override"
    )

    print("合并后的配置（override策略）:")
    print(f"  watch_interval_ms: {merged['watch_interval_ms']}")  # 2000
    print(f"  ocr.api_name: {merged['ocr']['api_name']}")  # accurate
    print(f"  ocr.api_key: {merged['ocr']['api_key']}")  # user_key
    print(f"  ocr.debug_mode: {merged['ocr']['debug_mode']}")  # True

    # 使用merge策略（深度合并）
    merged_deep = merge_service.merge_configs(
        default_config,
        user_config,
        environment_config,
        strategy="merge"
    )

    print("\n合并后的配置（merge策略）:")
    print(f"  keywords: {merged_deep['keywords']}")


def example_validate_config():
    """示例6：验证配置"""
    print("\n=== 示例6：配置验证 ===")

    validator = ConfigValidatorService()

    # 有效配置
    valid_config = AppConfig(
        app_title_prefix="Torch",
        keywords=("火炬之光无限",),
        watch_interval_ms=500,
        ocr__api_key="test_api_key_123",
        ocr__secret_key="test_secret_key_456",
        ocr__api_name="accurate",
        ocr__timeout_sec=15.0,
        ocr__max_retries=2
    )

    try:
        is_valid, errors, warnings = validator.validate_app_config(valid_config)
        print(f"配置有效: {is_valid}")
        if errors:
            print(f"错误: {errors}")
        if warnings:
            print(f"警告: {warnings}")
    except Exception as e:
        print(f"验证失败: {e}")

    # 无效配置
    invalid_config_dict = {
        "app_title_prefix": "",
        "keywords": [],
        "watch_interval_ms": 50,  # 太短
        "ocr": {
            "api_key": "short",  # 太短
            "secret_key": ""  # 为空
        }
    }

    try:
        is_valid, errors, warnings = validator.validate_dict(invalid_config_dict)
        print(f"\n无效配置验证:")
        print(f"  是否有效: {is_valid}")
        print(f"  错误: {errors}")
        print(f"  警告: {warnings}")
    except Exception as e:
        print(f"验证失败: {e}")


def example_compare_configs():
    """示例7：比较配置差异"""
    print("\n=== 示例7：比较配置 ===")

    merge_service = ConfigMergeService()

    config1 = {
        "a": 1,
        "b": 2,
        "ocr": {
            "api_key": "key1",
            "timeout": 10
        }
    }

    config2 = {
        "a": 2,  # 修改
        "c": 3,  # 新增
        "ocr": {
            "api_key": "key2",  # 修改
            "debug_mode": True  # 新增
        }
    }

    # 比较配置
    diff = merge_service.compare_configs(config1, config2)

    print("配置差异:")
    print(f"  新增: {diff['added']}")
    print(f"  删除: {diff['removed']}")
    print(f"  修改:")
    for key, change in diff['modified'].items():
        print(f"    {key}: {change['old']} -> {change['new']}")


def example_full_integration():
    """示例8：完整集成示例"""
    print("\n=== 示例8：完整集成示例 ===")

    from core.event_bus import get_event_bus, Events

    # 创建事件总线
    event_bus = get_event_bus()

    # 创建配置管理器（启用所有功能）
    config_manager = ConfigManager(
        enable_hot_reload=True,
        enable_encryption=True,
        master_password="your_secure_password"
    )

    try:
        # 加载配置
        config = config_manager.load_config()
        print(f"配置加载成功")

        # 配置更新时发布事件
        def on_config_update(old_config, new_config):
            print(f"配置已更新")
            # 发布配置更新事件
            event_bus.publish(
                Events.CONFIG_UPDATED,
                old_config=old_config,
                new_config=new_config
            )

        # 注册回调
        config_manager.register_update_callback(on_config_update)

        # 订阅配置更新事件
        def on_config_updated(old_config, new_config, **kwargs):
            print(f"收到配置更新事件")
            print(f"  旧配置: {old_config.watch_interval_ms}ms")
            print(f"  新配置: {new_config.watch_interval_ms}ms")

        event_bus.subscribe(Events.CONFIG_UPDATED, on_config_updated)

        print("完整集成已启动，按Ctrl+C停止")

        import time
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n停止")
    finally:
        config_manager.shutdown()


if __name__ == "__main__":
    # 运行所有示例
    example_basic_config_manager()
    # example_hot_reload()  # 需要手动停止
    example_encryption()
    # example_encryption_cli()  # 需要config.json文件
    example_merge_configs()
    example_validate_config()
    example_compare_configs()
    # example_full_integration()  # 需要手动停止
