from dataclasses import dataclass, field

@dataclass
class OcrConfig:
    api_key: str = ""
    secret_key: str = ""
    api_name: str = "accurate"
    timeout_sec: float = 15.0
    max_retries: int = 2

@dataclass(frozen=True)
class AppConfig:
    app_title_prefix: str = "Torch"
    keywords: tuple[str, ...] = ("火炬之光无限", "火炬之光", "Torchlight")
    watch_interval_ms: int = 500
    elevated_marker: str = "--elevated"
    ocr: OcrConfig = field(default_factory=OcrConfig)
