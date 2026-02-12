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

@dataclass
class ItemGridConfig:
    """物品识别区域网格配置"""
    # 起始位置
    start_x: int = 480
    start_y: int = 240

    # 单个物品槽大小
    width: int = 220
    height: int = 280

    # 间距
    horizontal_spacing: int = 40  # 列间距
    vertical_spacing: int = 40    # 行间距

    # 网格大小
    rows: int = 2  # 行数
    cols: int = 6  # 列数（第1行6列，第2行2列）

    def get_region(self, row: int, col: int) -> dict[str, int] | None:
        """获取指定行列的物品区域配置"""
        # 检查行列是否有效
        if row >= self.rows:
            return None

        # 第1行有6列，第2行只有2列
        if row == 1 and col >= 2:
            return None

        x = self.start_x + col * (self.width + self.horizontal_spacing)
        y = self.start_y + row * (self.height + self.vertical_spacing)

        return {
            "x": x,
            "y": y,
            "width": self.width,
            "height": self.height,
            "name": f"item_r{row}_c{col}"
        }

    def get_all_regions(self) -> list[dict[str, Any]]:
        """获取所有物品区域"""
        regions = []
        for row in range(self.rows):
            # 第1行有6列，第2行只有2列
            cols_in_row = 2 if row == 1 else 6
            for col in range(cols_in_row):
                region = self.get_region(row, col)
                if region:
                    regions.append(region)
        return regions

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ItemGridConfig':
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class RegionsConfig:
    """区域配置集合（包含余额和物品区域）"""
    balance: BalanceRegionConfig = field(default_factory=BalanceRegionConfig)
    items: ItemGridConfig = field(default_factory=ItemGridConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'RegionsConfig':
        balance_data = data.get('balance', {})
        items_data = data.get('items', {})

        return cls(
            balance=BalanceRegionConfig(**balance_data),
            items=ItemGridConfig(**items_data)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            'balance': self.balance.to_dict(),
            'items': self.items.to_dict()
        }

    @staticmethod
    def get_config_path() -> str:
        """获取区域配置文件路径"""
        return os.path.join(os.getcwd(), "range.json")

    @classmethod
    def load(cls) -> 'RegionsConfig':
        """从 range.json 加载配置"""
        config_path = cls.get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return cls.from_dict(data)
            except Exception as e:
                print(f"加载区域配置文件失败: {e}")
        return cls()

    def save(self) -> bool:
        """保存配置到 range.json"""
        try:
            config_path = self.get_config_path()
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存区域配置文件失败: {e}")
            return False

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
    regions: RegionsConfig = field(default_factory=RegionsConfig)

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
