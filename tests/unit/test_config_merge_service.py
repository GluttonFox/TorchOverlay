"""配置合并服务测试"""
import pytest
import tempfile
import json
from pathlib import Path

from services.config_merge_service import ConfigMergeService


class TestConfigMergeService:
    """配置合并服务测试类"""

    @pytest.fixture
    def merge_service(self):
        """配置合并服务fixture"""
        return ConfigMergeService()

    def test_merge_override_simple(self, merge_service):
        """测试简单的覆盖合并"""
        config1 = {"a": 1, "b": 2}
        config2 = {"b": 3, "c": 4}

        result = merge_service.merge_configs(config1, config2, strategy="override")

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_override_nested(self, merge_service):
        """测试嵌套字典的覆盖合并"""
        config1 = {
            "ocr": {"api_key": "key1", "timeout": 10},
            "app": {"name": "app1"}
        }
        config2 = {
            "ocr": {"api_key": "key2"},
            "app": {"version": "1.0"}
        }

        result = merge_service.merge_configs(config1, config2, strategy="override")

        assert result["ocr"]["api_key"] == "key2"  # 覆盖
        assert result["ocr"]["timeout"] == 10  # 保持
        assert result["app"]["name"] == "app1"  # 保持
        assert result["app"]["version"] == "1.0"  # 新增

    def test_merge_override_lists(self, merge_service):
        """测试列表的覆盖合并"""
        config1 = {"keywords": ["a", "b"]}
        config2 = {"keywords": ["c", "d"]}

        result = merge_service.merge_configs(config1, config2, strategy="override")

        assert result["keywords"] == ["c", "d"]  # 覆盖

    def test_merge_first_strategy(self, merge_service):
        """测试first策略"""
        config1 = {"a": 1, "b": 2}
        config2 = {"b": 3, "c": 4}

        result = merge_service.merge_configs(config1, config2, strategy="first")

        assert result == {"a": 1, "b": 2}

    def test_merge_deep_strategy(self, merge_service):
        """测试深度合并策略"""
        config1 = {"a": 1, "b": [1, 2]}
        config2 = {"a": 2, "b": [2, 3]}

        result = merge_service.merge_configs(config1, config2, strategy="merge")

        assert result["a"] == 2  # 使用第二个值
        # 列表合并并去重
        assert set(result["b"]) == {1, 2, 3}

    def test_merge_deep_nested_dicts(self, merge_service):
        """测试深度合并嵌套字典"""
        config1 = {
            "level1": {
                "level2": {
                    "a": 1,
                    "b": 2
                }
            }
        }
        config2 = {
            "level1": {
                "level2": {
                    "b": 3,
                    "c": 4
                }
            }
        }

        result = merge_service.merge_configs(config1, config2, strategy="merge")

        assert result["level1"]["level2"]["a"] == 1
        assert result["level1"]["level2"]["b"] == 3  # 使用第二个值
        assert result["level1"]["level2"]["c"] == 4

    def test_merge_multiple_configs(self, merge_service):
        """测试合并多个配置"""
        config1 = {"a": 1}
        config2 = {"b": 2}
        config3 = {"c": 3}

        result = merge_service.merge_configs(config1, config2, config3, strategy="override")

        assert result == {"a": 1, "b": 2, "c": 3}

    def test_merge_empty_configs(self, merge_service):
        """测试合并空配置"""
        result = merge_service.merge_configs()

        assert result == {}

    def test_merge_files(self, merge_service, tmp_path):
        """测试从文件合并配置"""
        # 创建临时配置文件
        file1 = tmp_path / "config1.json"
        file2 = tmp_path / "config2.json"

        file1.write_text(json.dumps({"a": 1, "b": 2}))
        file2.write_text(json.dumps({"b": 3, "c": 4}))

        result = merge_service.merge_files(str(file1), str(file2), strategy="override")

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_files_nonexistent(self, merge_service, tmp_path):
        """测试合并不存在的文件"""
        file1 = tmp_path / "config1.json"
        file2 = tmp_path / "nonexistent.json"

        file1.write_text(json.dumps({"a": 1}))

        result = merge_service.merge_files(str(file1), str(file2), strategy="override")

        assert result == {"a": 1}

    def test_compare_configs_added(self, merge_service):
        """测试比较配置 - 新增字段"""
        config1 = {"a": 1}
        config2 = {"a": 1, "b": 2}

        diff = merge_service.compare_configs(config1, config2)

        assert len(diff["added"]) == 1
        assert "b" in diff["added"]
        assert len(diff["removed"]) == 0
        assert len(diff["modified"]) == 0

    def test_compare_configs_removed(self, merge_service):
        """测试比较配置 - 删除字段"""
        config1 = {"a": 1, "b": 2}
        config2 = {"a": 1}

        diff = merge_service.compare_configs(config1, config2)

        assert len(diff["added"]) == 0
        assert len(diff["removed"]) == 1
        assert "b" in diff["removed"]
        assert len(diff["modified"]) == 0

    def test_compare_configs_modified(self, merge_service):
        """测试比较配置 - 修改字段"""
        config1 = {"a": 1}
        config2 = {"a": 2}

        diff = merge_service.compare_configs(config1, config2)

        assert len(diff["added"]) == 0
        assert len(diff["removed"]) == 0
        assert len(diff["modified"]) == 1
        assert "a" in diff["modified"]
        assert diff["modified"]["a"]["old"] == 1
        assert diff["modified"]["a"]["new"] == 2

    def test_compare_configs_nested(self, merge_service):
        """测试比较嵌套配置"""
        config1 = {"level": {"a": 1}}
        config2 = {"level": {"a": 2}}

        diff = merge_service.compare_configs(config1, config2)

        assert "level.a" in diff["modified"]
        assert diff["modified"]["level.a"]["old"] == 1
        assert diff["modified"]["level.a"]["new"] == 2

    def test_compare_configs_no_diff(self, merge_service):
        """测试比较相同的配置"""
        config1 = {"a": 1}
        config2 = {"a": 1}

        diff = merge_service.compare_configs(config1, config2)

        assert len(diff["added"]) == 0
        assert len(diff["removed"]) == 0
        assert len(diff["modified"]) == 0

    def test_load_config_with_defaults(self, merge_service, tmp_path):
        """测试使用默认配置加载"""
        default_file = tmp_path / "default.json"
        config_file = tmp_path / "config.json"

        default_file.write_text(json.dumps({"a": 1, "b": 2}))
        config_file.write_text(json.dumps({"b": 3, "c": 4}))

        config = merge_service.load_config_with_defaults(
            str(config_file),
            str(default_file)
        )

        assert config.a == 1
        assert config.b == 3  # 被覆盖
        assert config.c == 4  # 新增
