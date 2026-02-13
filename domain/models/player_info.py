"""玩家信息领域模型"""
from dataclasses import dataclass
from datetime import datetime

from domain.models.season import SeasonServerType


@dataclass
class PlayerInfo:
    """玩家信息"""
    name: str  # 玩家名
    season_id: int | None = None  # 赛季ID
    season_type: SeasonServerType = SeasonServerType.UNKNOWN  # 服务器类型
    timestamp: datetime | None = None  # 更新时间
    
    def __str__(self):
        """获取玩家信息的字符串表示"""
        season_str = str(self.season_type)
        if self.season_id:
            season_str += f" (ID: {self.season_id})"
        return f"{self.name} - {season_str}"
