"""常量定义"""

# 文件路径常量
CAPTURES_DIR = "captures"
CONFIG_FILE = "config.json"
RANGE_FILE = "range.json"
ENV_FILE = ".env"

# 默认配置值
DEFAULT_WATCH_INTERVAL_MS = 500
DEFAULT_TIMEOUT_SEC = 2.5
DEFAULT_CAPTURE_TIMEOUT = 2.5

# 默认余额区域配置
DEFAULT_BALANCE_REGION = {
    "x": 1735,
    "y": 36,
    "width": 100,
    "height": 40
}

# OCR 配置默认值
DEFAULT_OCR_TIMEOUT_SEC = 15.0
DEFAULT_OCR_MAX_RETRIES = 2
DEFAULT_OCR_DEBUG_MODE = False

# 窗口标题前缀
DEFAULT_APP_TITLE_PREFIX = "Torch"

# 默认游戏窗口关键词
DEFAULT_GAME_KEYWORDS = (
    "火炬之光无限",
    "火炬之光",
    "Torchlight"
)

# 管理员标识符
ELEVATED_MARKER = "--elevated"

# DPI 配置
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
