"""绑定的游戏信息领域模型"""
from dataclasses import dataclass


@dataclass
class BoundGame:
    """绑定的游戏信息"""
    hwnd: int
    title: str
    process_id: int
