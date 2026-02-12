import os
import json
from dataclasses import dataclass, field, asdict
from typing import Any


def _calculate_scale(client_width: int, client_height: int) -> tuple[float, float]:
    """计算缩放比例

    Args:
        client_width: 窗口client区域宽度
        client_height: 窗口client区域高度

    Returns:
        (scale_x, scale_y): x和y方向的缩放比例
    """
    # 基准分辨率（1920x1080）
    base_width = 1920
    base_height = 1080

    return client_width / base_width, client_height / base_height


def _create_balance_region(scale_x: float, scale_y: float) -> dict[str, int]:
    """创建余额区域

    Args:
        scale_x: x方向缩放比例
        scale_y: y方向缩放比例

    Returns:
        余额区域定义 {x, y, width, height, name}
    """
    # 基准余额区域坐标
    base_balance = {
        "x": 1735,
        "y": 36,
        "width": 100,
        "height": 40,
        "name": "余额区域"
    }

    return {
        "x": int(base_balance["x"] * scale_x),
        "y": int(base_balance["y"] * scale_y),
        "width": int(base_balance["width"] * scale_x),
        "height": int(base_balance["height"] * scale_y),
        "name": base_balance["name"]
    }


def _create_item_regions(scale_x: float, scale_y: float) -> list[dict[str, Any]]:
    """创建物品区域

    Args:
        scale_x: x方向缩放比例
        scale_y: y方向缩放比例

    Returns:
        物品区域列表，每个区域包含 {x, y, width, height, name}
    """
    # 基准物品区域网格参数
    base_items = {
        "start_x": 423,
        "start_y": 157,
        "width": 200,
        "height": 200,
        "horizontal_spacing": 10,
        "vertical_spacing": 10,
        "rows": 2,
        "cols": 6
    }

    # 生成物品区域（第1行6列，第2行2列）
    item_regions = []
    for row in range(base_items["rows"]):
        cols_in_row = 2 if row == 1 else 6
        for col in range(cols_in_row):
            x = int((base_items["start_x"] + col * (base_items["width"] + base_items["horizontal_spacing"])) * scale_x)
            y = int((base_items["start_y"] + row * (base_items["height"] + base_items["vertical_spacing"])) * scale_y)
            width = int(base_items["width"] * scale_x)
            height = int(base_items["height"] * scale_y)

            item_regions.append({
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "name": f"item_r{row}_c{col}"
            })

    return item_regions


def get_regions_for_resolution(client_width: int, client_height: int) -> tuple[dict[str, int], list[dict[str, Any]]]:
    """根据分辨率自适应计算识别区域

    Args:
        client_width: 窗口client区域宽度
        client_height: 窗口client区域高度

    Returns:
        (balance_region, item_regions): 余额区域和物品区域列表
    """
    # 计算缩放比例
    scale_x, scale_y = _calculate_scale(client_width, client_height)

    # 创建余额区域
    balance_region = _create_balance_region(scale_x, scale_y)

    # 创建物品区域
    item_regions = _create_item_regions(scale_x, scale_y)

    return balance_region, item_regions


def get_bounding_box(regions: list[dict[str, Any]]) -> dict[str, Any]:
    """计算包含所有区域的最小边界框

    Args:
        regions: 区域列表

    Returns:
        包含所有区域的边界框 {x, y, width, height}
    """
    if not regions:
        return {"x": 0, "y": 0, "width": 0, "height": 0}

    min_x = min(r['x'] for r in regions)
    min_y = min(r['y'] for r in regions)
    max_x = max(r['x'] + r['width'] for r in regions)
    max_y = max(r['y'] + r['height'] for r in regions)

    return {
        "x": min_x,
        "y": min_y,
        "width": max_x - min_x,
        "height": max_y - min_y
    }


def get_combined_item_region(item_regions: list[dict[str, Any]]) -> dict[str, Any]:
    """计算包含所有物品区域的最小边界框

    Args:
        item_regions: 物品区域列表

    Returns:
        包含所有区域的边界框 {x, y, width, height}
    """
    return get_bounding_box(item_regions)


def get_combined_region(balance_region: dict[str, Any], item_regions: list[dict[str, Any]]) -> dict[str, Any]:
    """计算包含余额和所有物品区域的最小边界框

    Args:
        balance_region: 余额区域
        item_regions: 物品区域列表

    Returns:
        包含所有区域的边界框 {x, y, width, height}
    """
    all_regions = [balance_region] + item_regions
    return get_bounding_box(all_regions)


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
    last_price_update: str = ""  # 上次物价更新时间（ISO格式字符串）

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
