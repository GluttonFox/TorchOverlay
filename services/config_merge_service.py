"""配置合并服务 - 合并多个配置源"""
import json
from typing import Any, Optional
from pathlib import Path

from core.config import AppConfig, OcrConfig
from core.logger import get_logger
from core.exceptions import ConfigError

logger = get_logger(__name__)


class ConfigMergeService:
    """配置合并服务

    支持从多个配置源合并配置，支持深度合并、配置覆盖等策略。
    """

    def __init__(self):
        """初始化配置合并服务"""
        pass

    def merge_configs(self, *configs: dict[str, Any], strategy: str = "override") -> dict[str, Any]:
        """合并多个配置字典

        Args:
            *configs: 配置字典列表
            strategy: 合并策略
                - "override": 后面的配置覆盖前面的配置（默认）
                - "merge": 深度合并，保留所有值
                - "first": 保留第一个配置，忽略后面的配置

        Returns:
            合并后的配置字典

        Raises:
            ConfigError: 配置格式错误
        """
        if not configs:
            return {}

        if strategy == "first":
            return configs[0].copy()

        if strategy == "override":
            return self._merge_override(*configs)

        if strategy == "merge":
            return self._merge_deep(*configs)

        raise ConfigError(f"不支持的合并策略: {strategy}")

    def _merge_override(self, *configs: dict[str, Any]) -> dict[str, Any]:
        """使用覆盖策略合并配置

        后面的配置会覆盖前面的配置中的相同字段。

        Args:
            *configs: 配置字典列表

        Returns:
            合并后的配置字典
        """
        result = {}

        for config in configs:
            self._deep_update(result, config)

        return result

    def _merge_deep(self, *configs: dict[str, Any]) -> dict[str, Any]:
        """使用深度合并策略合并配置

        合并所有值，对于列表和字典进行深度合并。

        Args:
            *configs: 配置字典列表

        Returns:
            合并后的配置字典
        """
        if not configs:
            return {}

        result = configs[0].copy()

        for config in configs[1:]:
            result = self._deep_merge(result, config)

        return result

    def _deep_update(self, base: dict[str, Any], update: dict[str, Any]) -> None:
        """深度更新字典

        Args:
            base: 基础字典（会被修改）
            update: 更新字典
        """
        for key, value in update.items():
            if key in base:
                if isinstance(base[key], dict) and isinstance(value, dict):
                    # 递归合并字典
                    self._deep_update(base[key], value)
                elif isinstance(base[key], list) and isinstance(value, list):
                    # 替换列表
                    base[key] = value
                else:
                    # 覆盖值
                    base[key] = value
            else:
                # 添加新字段
                base[key] = value

    def _deep_merge(self, dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
        """深度合并两个字典

        Args:
            dict1: 第一个字典
            dict2: 第二个字典

        Returns:
            合并后的字典
        """
        result = dict1.copy()

        for key, value in dict2.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    # 递归合并字典
                    result[key] = self._deep_merge(result[key], value)
                elif isinstance(result[key], list) and isinstance(value, list):
                    # 合并列表（去重）
                    result[key] = list(set(result[key] + value))
                else:
                    # 使用第二个字典的值
                    result[key] = value
            else:
                # 添加新字段
                result[key] = value

        return result

    def merge_files(
        self,
        *file_paths: str,
        strategy: str = "override"
    ) -> dict[str, Any]:
        """从多个文件合并配置

        Args:
            *file_paths: 配置文件路径列表
            strategy: 合并策略

        Returns:
            合并后的配置字典

        Raises:
            ConfigError: 文件读取失败或格式错误
        """
        configs = []

        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                configs.append(config)
                logger.info(f"已加载配置文件: {file_path}")
            except FileNotFoundError:
                logger.warning(f"配置文件不存在，跳过: {file_path}")
            except json.JSONDecodeError as e:
                raise ConfigError(f"配置文件格式错误 ({file_path}): {e}")
            except Exception as e:
                raise ConfigError(f"读取配置文件失败 ({file_path}): {e}")

        return self.merge_configs(*configs, strategy=strategy)

    def merge_to_app_config(
        self,
        base_config: AppConfig,
        override_config: dict[str, Any]
    ) -> AppConfig:
        """合并覆盖配置到应用配置

        Args:
            base_config: 基础应用配置
            override_config: 覆盖配置字典

        Returns:
            合并后的应用配置
        """
        # 将配置转换为字典
        base_dict = base_config.to_dict()

        # 合并配置
        merged_dict = self.merge_configs(base_dict, override_config, strategy="override")

        # 转换回AppConfig
        try:
            return AppConfig.from_dict(merged_dict)
        except Exception as e:
            raise ConfigError(f"转换配置失败: {e}")

    def load_config_with_defaults(
        self,
        config_path: str,
        default_config_path: Optional[str] = None
    ) -> AppConfig:
        """加载配置，使用默认值作为基础

        Args:
            config_path: 主配置文件路径
            default_config_path: 默认配置文件路径（如果为None，使用内置默认值）

        Returns:
            应用配置对象
        """
        # 加载默认配置
        if default_config_path and Path(default_config_path).exists():
            with open(default_config_path, 'r', encoding='utf-8') as f:
                default_dict = json.load(f)
            logger.info(f"已加载默认配置: {default_config_path}")
        else:
            default_dict = AppConfig().to_dict()

        # 加载主配置（如果存在）
        if Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            logger.info(f"已加载主配置: {config_path}")
        else:
            logger.warning(f"主配置文件不存在，使用默认配置: {config_path}")
            config_dict = {}

        # 合并配置
        merged_dict = self.merge_configs(default_dict, config_dict, strategy="override")

        # 转换为AppConfig
        try:
            return AppConfig.from_dict(merged_dict)
        except Exception as e:
            raise ConfigError(f"转换配置失败: {e}")

    def compare_configs(
        self,
        config1: dict[str, Any],
        config2: dict[str, Any],
        path: str = ""
    ) -> dict[str, Any]:
        """比较两个配置的差异

        Args:
            config1: 第一个配置
            config2: 第二个配置
            path: 当前路径（递归使用）

        Returns:
            差异字典，包含 added（新增）、removed（删除）、modified（修改）字段
        """
        differences = {
            'added': [],
            'removed': [],
            'modified': {}
        }

        # 检查新增的字段
        for key in config2:
            if key not in config1:
                full_path = f"{path}.{key}" if path else key
                differences['added'].append(full_path)

        # 检查删除的字段
        for key in config1:
            if key not in config2:
                full_path = f"{path}.{key}" if path else key
                differences['removed'].append(full_path)

        # 检查修改的字段
        for key in config1:
            if key in config2:
                full_path = f"{path}.{key}" if path else key
                value1 = config1[key]
                value2 = config2[key]

                if isinstance(value1, dict) and isinstance(value2, dict):
                    # 递归比较字典
                    sub_diff = self.compare_configs(value1, value2, full_path)
                    differences['modified'].update(sub_diff['modified'])
                elif value1 != value2:
                    differences['modified'][full_path] = {
                        'old': value1,
                        'new': value2
                    }

        return differences
