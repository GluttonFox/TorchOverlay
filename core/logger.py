"""日志系统配置"""

import logging
import sys
from pathlib import Path
from datetime import datetime


class TorchLogger:
    """统一的日志管理器"""

    _loggers = {}

    @classmethod
    def get_logger(cls, name: str = "TorchOverlay") -> logging.Logger:
        """获取或创建日志记录器"""
        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        # 避免重复添加处理器
        if not logger.handlers:
            cls._setup_handlers(logger)
        
        cls._loggers[name] = logger
        return logger

    @classmethod
    def _setup_handlers(cls, logger: logging.Logger):
        """设置日志处理器"""
        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 文件名（按日期）
        log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        
        # 文件处理器（所有级别）
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(cls._get_formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'))
        
        # 错误文件处理器（只记录错误和严重错误）
        error_fh = logging.FileHandler(log_dir / f"error_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8')
        error_fh.setLevel(logging.ERROR)
        error_fh.setFormatter(cls._get_formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'))
        
        # 控制台处理器（INFO 及以上）
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(cls._get_formatter('%(levelname)s - %(message)s'))
        
        # 添加处理器
        logger.addHandler(fh)
        logger.addHandler(error_fh)
        logger.addHandler(ch)

    @staticmethod
    def _get_formatter(fmt: str) -> logging.Formatter:
        """创建格式化器"""
        return logging.Formatter(fmt, datefmt='%Y-%m-%d %H:%M:%S')


# 便捷函数
def get_logger(name: str = "TorchOverlay") -> logging.Logger:
    """获取日志记录器"""
    return TorchLogger.get_logger(name)
