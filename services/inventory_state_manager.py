"""背包状态管理器 - 追踪物品数量变化"""
import threading
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass

from core.logger import get_logger
from domain.models.item_update import ItemChange

logger = get_logger(__name__)


# 常量定义
GEM_BASE_ID = "5210"  # 神威辉石基础ID

# 页面ID定义
PAGE_ID_EQUIPMENT = 100  # 装备页
PAGE_ID_SKILL = 101  # 技能页
PAGE_ID_CONSUMABLE = 102  # 消耗品页
PAGE_ID_WAREHOUSE = -1  # 仓库页


@dataclass
class ItemRecord:
    """物品记录"""
    base_id: str  # 基础ID
    item_id: str | None = None  # 完整ID（BaseId_InstanceId）
    bag_num: int = 0  # 背包数量
    page_id: int = 0
    slot_id: int = 0
    last_update: datetime | None = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'base_id': self.base_id,
            'item_id': self.item_id,
            'bag_num': self.bag_num,
            'page_id': self.page_id,
            'slot_id': self.slot_id,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }


class InventoryStateManager:
    """背包状态管理器
    
    功能：
    1. 追踪背包中所有物品的数量
    2. 记录物品的添加、更新、删除操作
    3. 提供背包快照功能
    4. 判断背包是否已初始化
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized_flag = False
        return cls._instance
    
    def __init__(self):
        """初始化"""
        # 单例模式下避免重复初始化
        if hasattr(self, '_initialized'):
            return

        self._initialized = False
        self._item_records: Dict[str, ItemRecord] = {}  # {item_id: ItemRecord} - 使用完整item_id（包含实例ID）作为key
        self._item_snapshot: Dict[str, int] = {}  # 快照: {base_id: bag_num} - 用于兼容性
        self._event_changes: list = []  # 当前事件内的物品变更
        logger.info("背包状态管理器已初始化")
    
    @property
    def is_backpack_initialized(self) -> bool:
        """背包是否已初始化"""
        return self._initialized_flag
    
    def mark_backpack_initialized(self) -> None:
        """标记背包已初始化"""
        self._initialized_flag = True
        logger.info(f"背包初始化完成，当前物品数量: {len(self._item_records)}")
        # logger.debug(f"背包物品: {list(self._item_records.keys())[:10]}...")
    
    def reset_backpack_initialized(self) -> None:
        """重置背包初始化标志"""
        self._initialized_flag = False
        self._item_records.clear()
        self._item_snapshot.clear()
        logger.info("背包初始化标志已重置")
    
    def create_snapshot(self) -> Dict[str, int]:
        """创建背包快照

        累加同一 base_id 的所有实例（不同槽位）的数量

        Returns:
            快照字典: {base_id: bag_num}
        """
        snapshot = {}
        for item_id, record in self._item_records.items():
            base_id = record.base_id
            if base_id not in snapshot:
                snapshot[base_id] = 0
            snapshot[base_id] += record.bag_num
        return snapshot

    def create_instance_snapshot(self) -> Dict[str, int]:
        """创建物品实例快照

        保存每个 item_id（包含实例ID）的数量，用于精确计算消耗

        Returns:
            实例快照字典: {item_id: bag_num}
        """
        instance_snapshot = {}
        for item_id, record in self._item_records.items():
            instance_snapshot[item_id] = record.bag_num
        return instance_snapshot
    
    def restore_snapshot(self, snapshot: Dict[str, int]) -> None:
        """恢复快照到当前状态"""
        self._item_snapshot = snapshot.copy()
    
    def apply_item_change(self, change: ItemChange) -> None:
        """应用物品变更

        使用完整的 item_id（包含实例ID）作为 key，这样可以区分不同槽位的同一物品

        Args:
            change: 物品变更信息
        """
        item_id = change.item_id or change.base_id  # 使用完整item_id作为key
        base_id = change.base_id

        if change.change_type == 'add':
            # 添加物品
            if item_id not in self._item_records:
                self._item_records[item_id] = ItemRecord(
                    base_id=base_id,
                    item_id=item_id,
                    bag_num=change.bag_num or 0,
                    page_id=change.page_id,
                    slot_id=change.slot_id,
                    last_update=change.timestamp
                )
                # logger.debug(f"[ADD] 新物品: {base_id}({item_id}), 数量: {change.bag_num}")
                print(f"[物品添加] {base_id}: 数量={change.bag_num}, 页面={change.page_id}, 槽位={change.slot_id}")
            else:
                # 物品已存在，更新数量
                record = self._item_records[item_id]
                old_num = record.bag_num
                record.bag_num = change.bag_num or record.bag_num
                record.last_update = change.timestamp
                # logger.debug(f"[ADD] 物品更新: {base_id}({item_id}), {old_num} -> {record.bag_num}")
                print(f"[状态更新] {base_id}: {old_num} -> {record.bag_num}")

        elif change.change_type == 'update':
            # 更新物品数量
            if item_id not in self._item_records:
                self._item_records[item_id] = ItemRecord(
                    base_id=base_id,
                    item_id=item_id,
                    bag_num=change.bag_num or 0,
                    page_id=change.page_id,
                    slot_id=change.slot_id,
                    last_update=change.timestamp
                )
                # logger.debug(f"[UPDATE] 新物品: {base_id}({item_id}), 数量: {change.bag_num}")
            else:
                record = self._item_records[item_id]
                old_num = record.bag_num
                record.bag_num = change.bag_num or record.bag_num
                record.last_update = change.timestamp
                # logger.debug(f"[UPDATE] 物品更新: {base_id}({item_id}), {old_num} -> {record.bag_num}")

                # 输出神威辉石的变化（调试）
                if base_id == GEM_BASE_ID:
                    print(f"[神威辉石] {old_num} -> {record.bag_num} (变化: {record.bag_num - old_num})")
                else:
                    print(f"[状态更新] {base_id}: {old_num} -> {record.bag_num}")

        elif change.change_type == 'delete':
            # 删除物品
            if item_id in self._item_records:
                old_num = self._item_records[item_id].bag_num
                del self._item_records[item_id]
                # logger.debug(f"[DELETE] 物品删除: {base_id}({item_id}), 原数量: {old_num}")
                print(f"[物品删除] {base_id}, 原数量: {old_num}")

        # 记录到事件变更列表
        self._event_changes.append(change)
    
    def clear_event_changes(self) -> None:
        """清空当前事件的变更列表"""
        self._event_changes.clear()
    
    def get_event_changes(self) -> list:
        """获取当前事件内的所有物品变更"""
        return self._event_changes.copy()
    
    def get_item_num(self, base_id: str) -> int:
        """获取物品总数量

        累加同一 base_id 的所有实例（不同槽位）的数量

        Args:
            base_id: 物品基础ID

        Returns:
            物品总数量，如果不存在返回0
        """
        total = 0
        for item_id, record in self._item_records.items():
            if record.base_id == base_id:
                total += record.bag_num
        return total
    
    def get_all_items(self) -> Dict[str, ItemRecord]:
        """获取所有物品记录"""
        return self._item_records.copy()
    
    def get_item_names(self) -> list:
        """获取所有物品的基础ID列表"""
        return list(self._item_records.keys())
    
    def calculate_changes(self, snapshot: Dict[str, int]) -> tuple[list, list]:
        """计算快照和当前状态之间的变化
        
        Args:
            snapshot: 快照字典 {base_id: bag_num}
            
        Returns:
            (spent_items, gained_items) - 消耗的物品列表和获得的物品列表
            格式: [{'base_id': str, 'delta': int, 'quantity': int}]
        """
        spent_items = []
        gained_items = []
        
        all_base_ids = set(snapshot.keys()) | set(self._item_records.keys())
        
        for base_id in all_base_ids:
            old_num = snapshot.get(base_id, 0)
            new_num = self.get_item_num(base_id)
            delta = new_num - old_num
            
            if delta != 0:
                change_info = {
                    'base_id': base_id,
                    'delta': delta,
                    'quantity': abs(delta)
                }
                if delta < 0:
                    spent_items.append(change_info)
                else:
                    gained_items.append(change_info)
        
        return spent_items, gained_items
