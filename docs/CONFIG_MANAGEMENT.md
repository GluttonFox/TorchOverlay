# 配置管理文档

本文档描述TorchOverlay项目的配置管理系统。

## 概述

配置管理系统提供了一套完整的配置管理解决方案，包括：

- **配置验证**: 验证配置的有效性，防止配置错误
- **配置热更新**: 自动检测配置文件变化并重新加载
- **配置加密**: 加密敏感信息（如API密钥）
- **配置合并**: 合并多个配置源
- **统一管理**: 提供一致的配置管理接口

## 核心组件

### 1. ConfigValidatorService

配置验证服务，验证配置的合法性和完整性。

```python
from services.config_validator_service import ConfigValidatorService
from core.config import AppConfig

validator = ConfigValidatorService()

# 验证配置对象
config = AppConfig()
is_valid, errors, warnings = validator.validate_app_config(config)

# 验证配置字典
config_dict = {"app_title_prefix": "Torch"}
is_valid, errors, warnings = validator.validate_dict(config_dict)
```

#### 验证规则

| 字段 | 验证规则 | 错误/警告 |
|------|---------|-----------|
| app_title_prefix | 不能为空 | 错误 |
| keywords | 不能为空，每个关键词不能为空 | 错误 |
| watch_interval_ms | 100ms - 60000ms | 错误/警告 |
| ocr.api_key | 长度 >= 10 | 错误 |
| ocr.secret_key | 长度 >= 10 | 错误 |
| ocr.api_name | general_basic, accurate, webimage, general | 警告 |
| ocr.timeout_sec | 1s - 60s | 错误/警告 |
| ocr.max_retries | 0 - 10 | 错误/警告 |
| mystery_gem_mode | min, max, random | 错误 |

### 2. ConfigHotReloadService

配置热更新服务，自动检测配置文件变化并重新加载。

```python
from services.config_hot_reload_service import ConfigHotReloadService

# 创建热更新服务
hot_reload = ConfigHotReloadService(
    config_path="config.json",
    check_interval_sec=2.0
)

# 定义回调函数
def on_config_changed(old_config, new_config):
    print(f"配置已更新")

# 注册回调
hot_reload.register_callback(on_config_changed)

# 启动服务
hot_reload.start()

# 手动触发重新加载
hot_reload.trigger_manual_reload()

# 停止服务
hot_reload.stop()
```

#### 特性

- 自动检测文件修改
- 线程安全
- 支持回调通知
- 支持手动触发

### 3. ConfigEncryptionService

配置加密服务，加密和解密敏感信息。

```python
from services.config_encryption_service import ConfigEncryptionService

# 创建加密服务
encryption = ConfigEncryptionService(master_password="your_password")

# 加密单个值
encrypted = encryption.encrypt_value("secret_key")

# 解密单个值
decrypted = encryption.decrypt_value(encrypted)

# 加密配置字典
config_dict = {"api_key": "secret"}
encrypted_dict = encryption.encrypt_dict(config_dict)

# 解密配置字典
decrypted_dict = encryption.decrypt_dict(encrypted_dict)

# 加密配置文件
encryption.encrypt_config_file("config.json", "config_encrypted.json")

# 解密配置文件
encryption.decrypt_config_file("config_encrypted.json", "config_decrypted.json")

# 检查加密状态
status = encryption.get_encryption_status(config_dict)
```

#### 敏感字段

以下字段会被自动加密：
- api_key
- secret_key
- password
- token
- access_key

### 4. ConfigMergeService

配置合并服务，合并多个配置源。

```python
from services.config_merge_service import ConfigMergeService

merge_service = ConfigMergeService()

# 合并配置（override策略）
result = merge_service.merge_configs(
    config1, config2, config3,
    strategy="override"  # 后面的覆盖前面的
)

# 合并配置（merge策略）
result = merge_service.merge_configs(
    config1, config2,
    strategy="merge"  # 深度合并
)

# 从文件合并
result = merge_service.merge_files(
    "default.json",
    "user.json",
    "environment.json"
)

# 比较配置
diff = merge_service.compare_configs(config1, config2)
# diff['added']: 新增的字段
# diff['removed']: 删除的字段
# diff['modified']: 修改的字段
```

#### 合并策略

| 策略 | 描述 |
|------|------|
| override | 后面的配置覆盖前面的配置（默认） |
| merge | 深度合并，保留所有值 |
| first | 保留第一个配置，忽略后面的 |

### 5. ConfigManager

配置管理器，统一的管理入口。

```python
from services.config_manager import ConfigManager

# 创建配置管理器
config_manager = ConfigManager(
    enable_hot_reload=True,      # 启用热更新
    enable_encryption=True,       # 启用加密
    master_password="password"    # 加密主密码
)

# 加载配置
config = config_manager.load_config()

# 保存配置
config_manager.save_config(config)

# 重新加载配置
config = config_manager.reload_config()

# 获取当前配置
config = config_manager.get_config()

# 验证配置
is_valid, errors, warnings = config_manager.validate_config(config)

# 注册更新回调
def on_update(old, new):
    print(f"配置已更新")

config_manager.register_update_callback(on_update)

# 关闭管理器
config_manager.shutdown()
```

## 使用场景

### 场景1：开发环境

```python
# 不启用热更新和加密
config_manager = ConfigManager(
    enable_hot_reload=False,
    enable_encryption=False
)
config = config_manager.load_config()
```

### 场景2：生产环境

```python
# 启用热更新和加密
config_manager = ConfigManager(
    enable_hot_reload=True,
    enable_encryption=True,
    master_password=os.getenv("CONFIG_PASSWORD")
)
config = config_manager.load_config()
```

### 场景3：多环境配置

```python
# 使用默认配置 + 用户配置
merge_service = ConfigMergeService()
config = merge_service.load_config_with_defaults(
    config_path="config.json",
    default_config_path="config.default.json"
)
```

### 场景4：配置对比

```python
# 比较两个配置
merge_service = ConfigMergeService()
diff = merge_service.compare_configs(old_config, new_config)

print(f"新增: {diff['added']}")
print(f"删除: {diff['removed']}")
print(f"修改: {diff['modified']}")
```

## 最佳实践

### 1. 配置验证

在生产环境加载配置后始终进行验证：

```python
config_manager = ConfigManager()
config = config_manager.load_config()
is_valid, errors, warnings = config_manager.validate_config(config)

if not is_valid:
    logger.error(f"配置验证失败: {errors}")
    raise ConfigError("配置无效")
```

### 2. 配置加密

在生产环境始终加密敏感信息：

```python
# 加密配置文件
from services.config_encryption_service import ConfigEncryptionService

encryption = ConfigEncryptionService(master_password=os.getenv("CONFIG_PASSWORD"))
encryption.encrypt_config_file("config.json", "config.json.enc")
```

### 3. 配置热更新

在生产环境谨慎使用热更新，建议：

```python
# 只在开发和测试环境启用
if environment in ["development", "testing"]:
    config_manager = ConfigManager(enable_hot_reload=True)
else:
    config_manager = ConfigManager(enable_hot_reload=False)
```

### 4. 配置备份

在修改配置前先备份：

```python
import shutil
from datetime import datetime

backup_path = f"config.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
shutil.copy("config.json", backup_path)
```

## 故障排除

### 问题1：配置加载失败

**症状**: `ConfigError: 加载配置失败`

**原因**: 配置文件格式错误或路径错误

**解决**:
1. 检查配置文件路径是否正确
2. 验证JSON格式是否正确
3. 使用配置验证器检查配置

### 问题2：配置验证失败

**症状**: 验证返回错误列表

**原因**: 配置不符合验证规则

**解决**:
1. 查看错误消息，了解具体问题
2. 修正配置值
3. 参考`config.json.example`示例

### 问题3：热更新不工作

**症状**: 修改配置文件后没有重新加载

**原因**: 文件监视服务未正常工作

**解决**:
1. 检查热更新服务是否启动
2. 检查文件路径是否正确
3. 查看日志了解详细错误

### 问题4：加密/解密失败

**症状**: `ConfigError: 解密值失败`

**原因**: 主密码不正确或数据损坏

**解决**:
1. 确认主密码正确
2. 检查加密文件是否损坏
3. 从备份恢复配置

## 参考资源

- [配置管理使用示例](../examples/config_management_example.py)
- [配置验证服务测试](../tests/unit/test_config_validator_service.py)
- [配置合并服务测试](../tests/unit/test_config_merge_service.py)
- [配置数据模型](../core/config.py)
