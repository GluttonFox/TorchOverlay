"""物品更新信息领域模型"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class UpdateItemInfo:
    """物品更新信息（数量变化）"""
    item_id: str  # 物品ID格式: BaseId_InstanceId
    base_id: str  # 基础ID（InstanceId之前的部分）
    bag_num: int  # 当前背包数量
    page_id: int  # 页面ID（100=装备, 101=技能, 102=消耗品）
    slot_id: int  # 槽位ID
    timestamp: datetime
    raw_line: str  # 原始日志行


@dataclass
class AddItemInfo:
    """物品添加信息"""
    item_id: str  # 物品ID格式: BaseId_InstanceId
    base_id: str  # 基础ID
    bag_num: int  # 添加的数量
    page_id: int  # 页面ID
    slot_id: int  # 槽位ID
    timestamp: datetime
    raw_line: str  # 原始日志行


@dataclass
class DeleteItemInfo:
    """物品删除信息"""
    item_id: str  # 物品ID格式: BaseId_InstanceId
    base_id: str  # 基础ID
    page_id: int  # 页面ID
    slot_id: int  # 槽位ID
    timestamp: datetime
    raw_line: str  # 原始日志行


@dataclass
class ItemChange:
    """物品变更的统一表示"""
    item_id: str
    base_id: str
    page_id: int
    slot_id: int
    timestamp: datetime
    
    # 变更类型
    change_type: str  # 'update', 'add', 'delete'
    
    # 数量信息
    bag_num: int | None = None  # 仅 update 和 add 有
    
    raw_line: str = ""
