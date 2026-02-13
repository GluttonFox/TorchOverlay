"""服务器/赛季类型定义"""
from enum import Enum


class SeasonServerType(Enum):
    """服务器类型枚举"""
    UNKNOWN = 0
    PERMANENT_ZONE = 1  # 永久区
    SEASON_ZONE = 2  # 赛季区
    EXPERT_ZONE = 3  # 专家区

    def __str__(self):
        """获取服务器类型的显示名称"""
        labels = {
            SeasonServerType.UNKNOWN: "未知区服",
            SeasonServerType.PERMANENT_ZONE: "永久区",
            SeasonServerType.SEASON_ZONE: "赛季区",
            SeasonServerType.EXPERT_ZONE: "专家区"
        }
        return labels.get(self, "未知区服")


# 服务器ID映射
SEASON_ID_MAPPING = {
    1: SeasonServerType.PERMANENT_ZONE,  # 永久区
    1201: SeasonServerType.SEASON_ZONE,  # 赛季区
    1231: SeasonServerType.EXPERT_ZONE,  # 专家区
}


def resolve_season_type(season_id: int) -> SeasonServerType:
    """根据赛季ID解析服务器类型
    
    Args:
        season_id: 赛季ID
        
    Returns:
        服务器类型，如果无法识别返回 UNKNOWN
    """
    return SEASON_ID_MAPPING.get(season_id, SeasonServerType.UNKNOWN)
