from dataclasses import dataclass

@dataclass(frozen=True)
class AppConfig:
    app_title_prefix: str = "Torch"
    keywords: tuple[str, ...] = ("火炬之光无限", "火炬之光", "Torchlight")
    watch_interval_ms: int = 500
    elevated_marker: str = "--elevated"
