import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class BalanceRegionConfig:
    """余额识别区域配置（内部配置，不在UI中展示）"""
    x: int = 1735
    y: int = 36
    width: int = 100
    height: int = 40

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'BalanceRegionConfig':
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def get_config_path() -> str:
        """获取余额区域配置文件路径"""
        return os.path.join(os.getcwd(), "range.json")

    @classmethod
    def load(cls) -> 'BalanceRegionConfig':
        """从 range.json 加载配置"""
        config_path = cls.get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return cls.from_dict(data)
            except Exception as e:
                print(f"加载余额区域配置文件失败: {e}")
        return cls()

    def save(self) -> bool:
        """保存配置到 range.json"""
        try:
            config_path = self.get_config_path()
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存余额区域配置文件失败: {e}")
            return False

@dataclass
class ItemRegionConfig:
    """单个物品识别区域配置"""
    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ItemRegionConfig':
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class ItemRegionsConfig:
    """物品识别区域配置集合"""
    regions: dict[str, ItemRegionConfig] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ItemRegionsConfig':
        regions = {}
        for key, value in data.items():
            if isinstance(value, dict):
                regions[key] = ItemRegionConfig(**value)
        return cls(regions=regions)

    def to_dict(self) -> dict[str, Any]:
        return {key: value.to_dict() for key, value in self.regions.items()}

    @staticmethod
    def get_config_path() -> str:
        """获取物品区域配置文件路径"""
        return os.path.join(os.getcwd(), "items.json")

    @classmethod
    def load(cls) -> 'ItemRegionsConfig':
        """从 items.json 加载配置"""
        config_path = cls.get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return cls.from_dict(data)
            except Exception as e:
                print(f"加载物品区域配置文件失败: {e}")
        # 如果文件不存在，返回默认配置
        return cls.get_default()

    def save(self) -> bool:
        """保存配置到 items.json"""
        try:
            config_path = self.get_config_path()
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存物品区域配置文件失败: {e}")
            return False

    @classmethod
    def get_default(cls) -> 'ItemRegionsConfig':
        """获取默认物品区域配置"""
        default_regions = {
            "item_r0_c0": ItemRegionConfig(x=480, y=240, width=220, height=280),
            "item_r0_c1": ItemRegionConfig(x=720, y=240, width=220, height=280),
            "item_r0_c2": ItemRegionConfig(x=960, y=240, width=220, height=280),
            "item_r0_c3": ItemRegionConfig(x=1200, y=240, width=220, height=280),
            "item_r0_c4": ItemRegionConfig(x=1440, y=240, width=220, height=280),
            "item_r0_c5": ItemRegionConfig(x=1680, y=240, width=220, height=280),
            "item_r1_c0": ItemRegionConfig(x=480, y=560, width=220, height=280),
            "item_r1_c1": ItemRegionConfig(x=720, y=560, width=220, height=280),
        }
        return cls(regions=default_regions)

@dataclass
class OcrConfig:
    api_key: str = ""
    secret_key: str = ""
    api_name: str = "accurate"
    timeout_sec: float = 15.0
    max_retries: int = 2
    debug_mode: bool = False  # 调试模式开关

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'OcrConfig':
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class AppConfig:
    app_title_prefix: str = "Torch"
    keywords: tuple[str, ...] = ("火炬之光无限", "火炬之光", "Torchlight")
    watch_interval_ms: int = 500
    elevated_marker: str = "--elevated"
    ocr: OcrConfig = field(default_factory=OcrConfig)
    balance_region: BalanceRegionConfig = field(default_factory=BalanceRegionConfig)
    item_regions: ItemRegionsConfig = field(default_factory=ItemRegionsConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'AppConfig':
        # 复制字典以避免修改原始数据
        data_copy = data.copy()

        # 转换 keywords 回元组（JSON 加载后会变成列表）
        if 'keywords' in data_copy and isinstance(data_copy['keywords'], list):
            data_copy['keywords'] = tuple(data_copy['keywords'])

        # 处理 ocr 配置
        ocr_data = data_copy.pop('ocr', {})
        ocr_config = OcrConfig.from_dict(ocr_data)

        return cls(ocr=ocr_config, **data_copy)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    @staticmethod
    def get_config_path() -> str:
        """获取配置文件路径"""
        return os.path.join(os.getcwd(), "config.json")

    @classmethod
    def load(cls) -> 'AppConfig':
        """从文件加载配置"""
        config_path = cls.get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return cls.from_dict(data)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
        return cls()

    def save(self) -> bool:
        """保存配置到文件"""
        try:
            config_path = self.get_config_path()
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
