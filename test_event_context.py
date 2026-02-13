"""测试 EventContext 的功能"""
from datetime import datetime
from domain.models.item_update import ItemChange

# 模拟 EventContext 类（用于测试）
class EventContext:
    """事件上下文"""
    
    def __init__(self, event_type: str, start_time: datetime, snapshot: dict):
        self.event_type = event_type
        self.start_time = start_time
        self.end_time = None
        self.snapshot = snapshot
        self.item_updates = []
        self.item_adds = []
        self.item_deletes = []
        self.success = False
    
    def add_change(self, change: ItemChange) -> None:
        """根据 change_type 自动添加到对应的列表"""
        if change.change_type == 'update':
            self.item_updates.append(change)
        elif change.change_type == 'add':
            self.item_adds.append(change)
        elif change.change_type == 'delete':
            self.item_deletes.append(change)
    
    def add_update(self, change: ItemChange) -> None:
        """添加物品更新"""
        self.item_updates.append(change)
    
    def add_add(self, change: ItemChange) -> None:
        """添加物品添加"""
        self.item_adds.append(change)
    
    def add_delete(self, change: ItemChange) -> None:
        """添加物品删除"""
        self.item_deletes.append(change)
    
    @property
    def changes(self) -> list:
        """获取所有变更（兼容性属性）"""
        return self.item_updates + self.item_adds + self.item_deletes
    
    def get_change_count(self) -> int:
        """获取总变更数量"""
        return len(self.item_updates) + len(self.item_adds) + len(self.item_deletes)


# 创建测试数据
now = datetime.now()
snapshot = {'5210': 30633, '100200': 44}

# 创建事件上下文
event = EventContext(
    event_type='BuyVendorGoods',
    start_time=now,
    snapshot=snapshot
)

print("=" * 80)
print("测试 EventContext 功能")
print("=" * 80)

# 创建物品变更
update_change = ItemChange(
    item_id='5210_12345',
    base_id='5210',
    page_id=102,
    slot_id=5,
    timestamp=now,
    change_type='update',
    bag_num=30630
)

add_change = ItemChange(
    item_id='100200_67890',
    base_id='100200',
    page_id=102,
    slot_id=10,
    timestamp=now,
    change_type='add',
    bag_num=1
)

delete_change = ItemChange(
    item_id='100199_11111',
    base_id='100199',
    page_id=102,
    slot_id=8,
    timestamp=now,
    change_type='delete'
)

print("\n1. 测试 add_change（智能添加）")
print("-" * 40)
event.add_change(update_change)
print(f"添加 update 变化后:")
print(f"  item_updates: {len(event.item_updates)}")
print(f"  item_adds: {len(event.item_adds)}")
print(f"  item_deletes: {len(event.item_deletes)}")

event.add_change(add_change)
print(f"添加 add 变化后:")
print(f"  item_updates: {len(event.item_updates)}")
print(f"  item_adds: {len(event.item_adds)}")
print(f"  item_deletes: {len(event.item_deletes)}")

event.add_change(delete_change)
print(f"添加 delete 变化后:")
print(f"  item_updates: {len(event.item_updates)}")
print(f"  item_adds: {len(event.item_adds)}")
print(f"  item_deletes: {len(event.item_deletes)}")

print("\n2. 测试专用方法（add_update/add_add/add_delete）")
print("-" * 40)
event.add_update(update_change)
event.add_add(add_change)
event.add_delete(delete_change)
print(f"添加变更后:")
print(f"  item_updates: {len(event.item_updates)}")
print(f"  item_adds: {len(event.item_adds)}")
print(f"  item_deletes: {len(event.item_deletes)}")

print("\n3. 测试 changes 属性（兼容性）")
print("-" * 40)
all_changes = event.changes
print(f"所有变更（通过 changes 属性）: {len(all_changes)}")
print(f"  更新: {len(event.item_updates)}")
print(f"  添加: {len(event.item_adds)}")
print(f"  删除: {len(event.item_deletes)}")
assert len(all_changes) == 6  # 每种类型各添加了2次

print("\n4. 测试 get_change_count()")
print("-" * 40)
total_count = event.get_change_count()
print(f"总变更数: {total_count}")
assert total_count == 6

print("\n5. 测试事件统计")
print("-" * 40)
print(f"事件类型: {event.event_type}")
print(f"开始时间: {event.start_time.strftime('%H:%M:%S')}")
print(f"背包快照: {event.snapshot}")
print(f"  更新数: {len(event.item_updates)}")
print(f"  添加数: {len(event.item_adds)}")
print(f"  删除数: {len(event.item_deletes)}")
print(f"  总计: {event.get_change_count()}")

print("\n6. 查看具体变更")
print("-" * 40)
print("物品更新:")
for change in event.item_updates:
    print(f"  - {change.base_id}: {change.change_type}")

print("物品添加:")
for change in event.item_adds:
    print(f"  - {change.base_id}: {change.change_type}")

print("物品删除:")
for change in event.item_deletes:
    print(f"  - {change.base_id}: {change.change_type}")

print("\n" + "=" * 80)
print("测试完成！所有功能正常。")
print("=" * 80)
