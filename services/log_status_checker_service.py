"""日志状态检测服务 - 检测游戏日志是否开启和可访问"""
import os
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LogStatus:
    """日志状态信息"""
    is_enabled: bool  # 日志是否开启
    is_accessible: bool  # 日志是否可访问
    log_path: Optional[str]  # 日志文件路径
    log_size: int  # 日志文件大小（字节）
    last_modified: Optional[datetime]  # 最后修改时间
    error_message: Optional[str]  # 错误信息
    has_permission: bool  # 是否有访问权限
    game_running: bool  # 游戏是否运行
    process_id: Optional[int]  # 游戏进程ID


class LogStatusChecker:
    """日志状态检测器"""

    _instance: Optional['LogStatusChecker'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化日志状态检测器"""
        if self._initialized:
            return

        self._current_status: Optional[LogStatus] = None
        self._last_check_time: Optional[datetime] = None
        self._initialized = True
        logger.info("日志状态检测器已初始化")

    @classmethod
    def get_instance(cls) -> 'LogStatusChecker':
        """获取日志状态检测器单例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def check_log_status(self, log_path: Optional[str] = None) -> LogStatus:
        """检测日志状态

        Args:
            log_path: 日志文件路径，如果为None，尝试从游戏进程自动查找

        Returns:
            LogStatus 对象，包含日志状态信息
        """
        try:
            # 如果没有提供日志路径，尝试从游戏进程查找
            if log_path is None:
                log_path = self._find_game_log_path()

            # 检查游戏是否运行
            game_running, process_id = self._check_game_running()

            # 如果找不到日志路径
            if log_path is None:
                return LogStatus(
                    is_enabled=False,
                    is_accessible=False,
                    log_path=None,
                    log_size=0,
                    last_modified=None,
                    error_message="未找到游戏日志文件",
                    has_permission=True,
                    game_running=game_running,
                    process_id=process_id
                )

            # 检查文件是否存在
            if not os.path.exists(log_path):
                return LogStatus(
                    is_enabled=False,
                    is_accessible=False,
                    log_path=log_path,
                    log_size=0,
                    last_modified=None,
                    error_message=f"日志文件不存在: {log_path}",
                    has_permission=True,
                    game_running=game_running,
                    process_id=process_id
                )

            # 检查文件大小（判断日志是否开启）
            file_size = os.path.getsize(log_path)

            # 如果文件为空或太小（小于 1KB），认为日志未开启
            if file_size < 1024:
                return LogStatus(
                    is_enabled=False,
                    is_accessible=True,
                    log_path=log_path,
                    log_size=file_size,
                    last_modified=datetime.fromtimestamp(os.path.getmtime(log_path)),
                    error_message=f"日志文件为空或太小（{file_size} 字节），游戏可能未开启日志",
                    has_permission=True,
                    game_running=game_running,
                    process_id=process_id
                )

            # 检查文件是否可读
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # 尝试读取最后几行
                    lines = f.readlines()[-5:]
                    if not lines:
                        return LogStatus(
                            is_enabled=False,
                            is_accessible=True,
                            log_path=log_path,
                            log_size=file_size,
                            last_modified=datetime.fromtimestamp(os.path.getmtime(log_path)),
                            error_message="日志文件无法读取内容",
                            has_permission=True,
                            game_running=game_running,
                            process_id=process_id
                        )

            except PermissionError:
                return LogStatus(
                    is_enabled=False,
                    is_accessible=False,
                    log_path=log_path,
                    log_size=file_size,
                    last_modified=datetime.fromtimestamp(os.path.getmtime(log_path)),
                    error_message="权限不足，无法读取日志文件。请以管理员模式运行程序",
                    has_permission=False,
                    game_running=game_running,
                    process_id=process_id
                )
            except Exception as e:
                return LogStatus(
                    is_enabled=False,
                    is_accessible=False,
                    log_path=log_path,
                    log_size=file_size,
                    last_modified=datetime.fromtimestamp(os.path.getmtime(log_path)),
                    error_message=f"读取日志文件失败: {str(e)}",
                    has_permission=False,
                    game_running=game_running,
                    process_id=process_id
                )

            # 所有检查通过
            self._current_status = LogStatus(
                is_enabled=True,
                is_accessible=True,
                log_path=log_path,
                log_size=file_size,
                last_modified=datetime.fromtimestamp(os.path.getmtime(log_path)),
                error_message=None,
                has_permission=True,
                game_running=game_running,
                process_id=process_id
            )

            logger.info(f"日志状态检查成功: {log_path} ({file_size} 字节)")

        except Exception as e:
            logger.error(f"检测日志状态时出错: {e}", exc_info=True)
            self._current_status = LogStatus(
                is_enabled=False,
                is_accessible=False,
                log_path=log_path,
                log_size=0,
                last_modified=None,
                error_message=f"检测日志状态失败: {str(e)}",
                has_permission=False,
                game_running=False,
                process_id=None
            )

        self._last_check_time = datetime.now()
        return self._current_status

    def _find_game_log_path(self) -> Optional[str]:
        """查找游戏日志路径

        Returns:
            日志文件路径，如果找不到则返回None
        """
        try:
            import psutil

            # 直接通过进程名查找，避免遍历所有进程
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    # 只检查进程名，避免获取exe路径（这会更快）
                    if 'torchlight_infinite' in proc.info['name'].lower():
                        # 获取进程的 exe 路径
                        try:
                            exe_path = proc.exe()
                            if exe_path:
                                # 构建日志文件路径
                                # 进程在 UE_game\Binaries\Win64\ 下，需要向上查找
                                process_dir = os.path.dirname(exe_path)
                                current_dir = process_dir
                                ue_game_dir = None

                                # 最多向上查找3层
                                for _ in range(3):
                                    parent_dir = os.path.dirname(current_dir)
                                    if os.path.basename(parent_dir) == "UE_game":
                                        ue_game_dir = parent_dir
                                        break
                                    current_dir = parent_dir

                                # 如果找到 UE_game 目录，构建日志路径
                                if ue_game_dir:
                                    log_path = os.path.join(ue_game_dir, "Torchlight", "Saved", "Logs", "UE_game.log")
                                    logger.debug(f"找到游戏日志路径: {log_path}")
                                    return log_path
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            # 如果获取exe路径失败，跳过这个进程
                            continue
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            logger.warning("未找到游戏进程 torchlight_infinite")
            return None

        except ImportError:
            logger.warning("psutil 模块未安装，无法自动查找游戏日志路径")
            return None
        except Exception as e:
            logger.error(f"查找游戏日志路径时出错: {e}", exc_info=True)
            return None

    def _check_game_running(self) -> tuple[bool, Optional[int]]:
        """检查游戏是否运行

        Returns:
            (是否运行, 进程ID)
        """
        try:
            import psutil

            # 直接通过进程名查找，避免遍历所有进程
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    # 只检查进程名，避免不必要的属性访问
                    if 'torchlight_infinite' in proc.info['name'].lower():
                        return True, proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            return False, None

        except ImportError:
            logger.warning("psutil 模块未安装，无法检查游戏运行状态")
            return False, None
        except Exception as e:
            logger.error(f"检查游戏运行状态时出错: {e}", exc_info=True)
            return False, None

    def get_status_summary(self) -> str:
        """获取状态摘要字符串

        Returns:
            状态摘要字符串
        """
        if self._current_status is None:
            return "未检测"

        status = self._current_status

        if not status.game_running:
            return "⚠️ 游戏未运行"

        if not status.is_accessible:
            if not status.has_permission:
                return "❌ 权限不足"
            else:
                return f"❌ {status.error_message or '日志不可访问'}"

        if not status.is_enabled:
            return f"⚠️ {status.error_message or '日志未开启'}"

        # 日志正常
        size_mb = status.log_size / 1024 / 1024
        return f"✓ 日志正常 ({size_mb:.1f} MB)"

    def get_formatted_error_message(self) -> str:
        """获取格式化的错误消息

        Returns:
            格式化的错误消息，适合在UI中显示
        """
        status = self._current_status
        if status is None:
            return "日志状态未知"

        if status.is_enabled and status.is_accessible:
            return f"日志状态正常\n路径: {status.log_path}\n大小: {status.log_size / 1024 / 1024:.2f} MB"

        error_lines = []
        error_lines.append("⚠️ 日志状态检测警告：")

        if not status.game_running:
            error_lines.append("• 游戏未运行")
            error_lines.append("  请先启动游戏")

        elif not status.is_accessible:
            if not status.has_permission:
                error_lines.append("• 权限不足")
                error_lines.append("  请以管理员模式运行本程序")
            elif status.error_message:
                error_lines.append(f"• {status.error_message}")

        elif not status.is_enabled:
            if status.error_message:
                error_lines.append(f"• {status.error_message}")

            error_lines.append("\n💡 提示：")
            error_lines.append("• 请检查游戏日志功能是否已开启")
            error_lines.append("• 日志文件位置: 游戏安装目录/UE_game/Torchlight/Saved/Logs/UE_game.log")

        return "\n".join(error_lines)


def get_log_status_checker() -> LogStatusChecker:
    """获取日志状态检测器实例（便捷函数）

    Returns:
        LogStatusChecker 实例
    """
    return LogStatusChecker.get_instance()
