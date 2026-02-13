# EventContext 设计更新

## 概述

参考 GameLogMonitor 项目的设计，完全重构了 `EventContext` 类，使用三个独立列表来分别存储不同类型的物品变更，使代码更清晰、更易维护。

## 设计对比

### 之前的设计

```python
class EventContext:
    """事件上下文"""
    
    def __init__(self, event_type: str, start_time: datetime, snapshot: Dict[str, int]):
        self.event_type = event_type
        self.start_time = start_time
        self.end_time: Optional[datetime] = None
        self.snapshot = snapshot
        self.changes: list = []  # ❌ 所有变更混在一起
        self.success = False
    
    def add_change(self, change: ItemChange) -> None:
        self.changes.append(change)
```

**问题**：
- 所有类型的变更混在一个列表中
- 难以区分不同类型的操作
- 需要遍历整个列表来查找特定类型的变更

### 新的设计（参考 GameLogMonitor）

```python
class EventContext:
    """事件上下文
    
    参考 GameLogMonitor 的设计，使用三个独立列表存储不同类型的物品变更：
    - ItemUpdates: 物品更新（数量变化）
    - ItemAdds: 物品添加
    - ItemDeletes: 物品删除
    """
    
    def __init__(self, event_type: str, start_time: datetime, snapshot: Dict[str, int]):
        self.event_type = event_type
        self.start_time = start_time
        self.end_time: Optional[datetime] = None
        self.snapshot = snapshot
        
        # ✅ 三个独立的列表，清晰区分不同类型的变更
        self.item_updates: list = []  # 物品更新
        self.item_adds: list = []  # 物品添加
        self.item_deletes: list = []  # 物品删除
        
        self.success = False
```

## 新增方法

### 1. `add_change(change: ItemChange)` - 智能添加

根据 `change_type` 自动添加到对应的列表：

```python
def add_change(self, change: ItemChange) -> None:
    if change.change_type == 'update':
        self.item_updates.append(change)
    elif change.change_type == 'add':
        self.item_adds.append(change)
    elif change.change_type == 'delete':
        self.item_deletes.append(change)
```

### 2. `add_update(change: ItemChange)` - 添加更新

```python
def add_update(self, change: ItemChange) -> None:
    """添加物品更新"""
    self.item_updates.append(change)
```

### 3. `add_add(change: ItemChange)` - 添加添加

```python
def add_add(self, change: ItemChange) -> None:
    """添加物品添加"""
    self.item_adds.append(change)
```

### 4. `add_delete(change: ItemChange)` - 添加删除

```python
def add_delete(self, change: ItemChange) -> None:
    """添加物品删除"""
    self.item_deletes.append(change)
```

### 5. `changes` 属性（兼容性）

```python
@property
def changes(self) -> list:
    """获取所有变更（兼容性属性）"""
    return self.item_updates + self.item_adds + self.item_deletes
```

### 6. `get_change_count()` - 获取变更数量

```python
def get_change_count(self) -> int:
    """获取总变更数量"""
    return len(self.item_updates) + len(self.item_adds) + len(self.item_deletes)
```

## 使用示例

### 基本使用

```python
# 创建事件上下文
event = EventContext(
    event_type='BuyVendorGoods',
    start_time=datetime.now(),
    snapshot={'5210': 30633, '100200': 44}
)

# 添加变更（自动分类）
event.add_change(update_change)      # 添加到 item_updates
event.add_change(add_change)        # 添加到 item_adds
event.add_change(delete_change)     # 添加到 item_deletes

# 或者使用专用方法
event.add_update(update_change)
event.add_add(add_change)
event.add_delete(delete_change)

# 获取变更统计
print(f"更新: {len(event.item_updates)}")
print(f"添加: {len(event.item_adds)}")
print(f"删除: {len(event.item_deletes)}")
print(f"总计: {event.get_change_count()}")
```

### 在事件处理中使用

```python
def _process_buy_event(self, event: EventContext, buy_events: List[BuyEvent]) -> None:
    """处理购买事件"""
    logger.info(f"  物品更新数: {len(event.item_updates)}")
    logger.info(f"  物品添加数: {len(event.item_adds)}")
    logger.info(f"  物品删除数: {len(event.item_deletes)}")
    
    # 只处理物品更新（神威辉石消耗）
    for update in event.item_updates:
        if update.base_id == GEM_BASE_ID:
            # 计算神威辉石消耗
            old_num = event.snapshot.get(GEM_BASE_ID, 0)
            new_num = update.bag_num
            gem_cost = old_num - new_num
            print(f"[购买] 消耗神威辉石: {gem_cost}")
    
    # 只处理物品添加（购买的物品）
    if event.item_adds:
        first_add = event.item_adds[0]
        print(f"[购买] 获得物品: {first_add.base_id}")
```

## 日志输出

事件结束时会输出详细的变更统计：

```
[日志解析] ========== 检测到事件结束: BuyVendorGoods (10:23:45.567890) ==========
[日志解析]   事件内变更数: 3 (更新: 1, 添加: 1, 删除: 1)
```

## 优势

### 1. 清晰的分类

- 不同类型的变更清晰分离
- 不需要遍历整个列表查找特定类型
- 代码更易读、更易维护

### 2. 性能优化

- 直接访问特定类型的列表，无需遍历
- 减少条件判断

### 3. 灵活性

- 可以独立处理不同类型的变更
- 可以单独统计或分析特定类型的变更

### 4. 兼容性

- `changes` 属性保留了向后兼容
- 原有代码仍然可以使用 `event.changes`

## 与 GameLogMonitor 的对比

| 功能 | GameLogMonitor | 当前实现 |
|---|---|---|
| 物品更新列表 | `ItemUpdates` | `item_updates` |
| 物品添加列表 | `ItemAdds` | `item_adds` |
| 物品删除列表 | `ItemDeletes` | `item_deletes` |
| 智能添加方法 | ❌ | ✅ `add_change()` |
| 专用添加方法 | ✅（使用 `List.Add()`） | ✅ `add_update/add_add/add_delete()` |
| 总变更数属性 | ❌ | ✅ `get_change_count()` |
| 兼容性属性 | ❌ | ✅ `changes` 属性 |

## 参考资料

- GameLogMonitor 项目: `C:\Users\16418\Desktop\GameLogMonitor`
- 关键文件:
  - `Core/Parsing/BaseParser.cs` - 解析器基类
  - `Parsers/BuyVendorGoodsParser.cs` - 购买解析器
  - `DTO/Parser/VendorParsersResult.cs` - 结果数据类
