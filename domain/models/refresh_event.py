"""商店刷新事件领域模型"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RefreshEvent:
    """商店刷新事件（从游戏日志解析）"""
    timestamp: datetime
    gem_cost: int  # 消耗的神威辉石数量（通常为50）
    log_context: dict | None = None  # 原始日志上下文信息
