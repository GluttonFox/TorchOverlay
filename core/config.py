import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class OcrConfig:
    api_key: str = ""
    secret_key: str = ""
    api_name: str = "accurate"
    timeout_sec: float = 15.0
    max_retries: int = 2

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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'AppConfig':
        ocr_data = data.pop('ocr', {})
        ocr_config = OcrConfig.from_dict(ocr_data)
        return cls(ocr=ocr_config, **data)

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
