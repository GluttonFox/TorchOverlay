"""游戏购买事件领域模型"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BuyEvent:
    """购买事件（从游戏日志解析）"""
    timestamp: datetime
    item_id: int
    item_name: str
    item_quantity: int
    gem_cost: int  # 消耗的神威辉石数量
    log_context: dict | None = None  # 原始日志上下文信息
