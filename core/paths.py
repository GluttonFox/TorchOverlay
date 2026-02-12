"""项目路径管理工具类"""
import os
from pathlib import Path


class ProjectPaths:
    """项目路径工具类，集中管理所有项目路径"""

    PROJECT_ROOT = Path(os.getcwd())
    CAPTURES_DIR = PROJECT_ROOT / "captures"
    LOGS_DIR = PROJECT_ROOT / "logs"
    CONFIG_FILE = PROJECT_ROOT / "config.json"

    @classmethod
    def ensure_dirs(cls) -> None:
        """确保所有必要目录存在"""
        cls.CAPTURES_DIR.mkdir(exist_ok=True)
        cls.LOGS_DIR.mkdir(exist_ok=True)

    @classmethod
    def get_capture_path(cls, name: str) -> str:
        """获取截图文件路径

        Args:
            name: 文件名

        Returns:
            完整的文件路径
        """
        return str(cls.CAPTURES_DIR / name)

    @classmethod
    def get_log_path(cls, name: str) -> str:
        """获取日志文件路径

        Args:
            name: 文件名

        Returns:
            完整的文件路径
        """
        return str(cls.LOGS_DIR / name)

    @classmethod
    def get_config_path(cls) -> str:
        """获取配置文件路径

        Returns:
            配置文件的完整路径
        """
        return str(cls.CONFIG_FILE)
