# 修复购买事件识别问题

## 问题分析

### 用户反馈
用户只进行了一次购买，但是：
1. 检测到两次 `BuyVendorGoods` 事件
2. 没有创建购买事件（购买事件数为 0）

### 日志分析

```
[日志解析] ========== 检测到事件开始: BuyVendorGoods (18:24:13.263000) ==========
[日志解析]   背包快照: 244 个物品
[日志解析]   神威辉石: 30569
[物品更新] 5210: 数量=30520, 页面=102, 槽位=57
[神威辉石] 30569 -> 30520 (变化: -49)
[日志解析] ========== 检测到事件结束: BuyVendorGoods (18:24:13.263000) ==========
[日志解析]   事件内变更数: 1 (更新: 1, 添加: 0, 删除: 0)
INFO - ========== 处理事件: BuyVendorGoods, success=False ==========
INFO - ========== 事件结束 ==========
```

**问题**：
1. ✅ 检测到神威辉石消耗：-49
2. ❌ `success=False`（没有检测到 `Func_Common_BuySuccess` 标志）
3. ❌ 因为 `success=False`，所以没有处理购买事件

### 根本原因

游戏日志中没有 `Func_Common_BuySuccess` 标志，所以 `event.success` 一直是 `False`。

之前的逻辑：
```python
if event_type == 'BuyVendorGoods' and event.success:
    self._process_buy_event(event, buy_events)
```

只有当 `success=True` 时才会处理购买事件，导致购买事件被忽略。

## 解决方案

### 1. 不再依赖 success 标志

改为根据物品变化来判断购买是否成功：

```python
# 之前的逻辑（依赖 success 标志）
if event_type == 'BuyVendorGoods' and event.success:
    self._process_buy_event(event, buy_events)

# 新的逻辑（根据物品变化判断）
if event_type == 'BuyVendorGoods':
    # 检查是否有物品变化（更新、添加或删除）
    has_changes = (len(event.item_updates) > 0 or 
                 len(event.item_adds) > 0 or 
                 len(event.item_deletes) > 0)
    
    if has_changes or event.success:
        self._process_buy_event(event, buy_events)
    else:
        logger.info("  没有检测到物品变化，跳过购买事件")
```

### 2. 支持消耗型物品

对于没有物品增加的情况（消耗型物品），尝试从 `item_updates` 中查找：

```python
if non_gem_gained:
    # 有物品增加，使用第一个增加的物品
    first_gained = non_gem_gained[0]
    # 创建购买事件
    ...
else:
    # 没有物品增加（可能是消耗型物品或资源购买）
    logger.info(f"没有检测到物品增加，可能是消耗型物品")
    
    # 尝试从 item_updates 中找到最后一个更新的物品（排除神威辉石）
    for update in reversed(event.item_updates):
        if update.base_id != GEM_BASE_ID:
            logger.info(f"  候选物品（从更新中）: {update.base_id}, 数量: {update.bag_num}")
            # 消耗型物品，使用更新后的数量
            buy_event = self._create_buy_event(
                item_id=int(update.base_id),
                gem_cost=gem_cost,
                timestamp=event.end_time,
                quantity=update.bag_num or gem_cost
            )
            if buy_event:
                buy_events.append(buy_event)
                logger.info(f"✓ 创建购买事件（消耗型）: {buy_event.item_name} x{buy_event.item_quantity}, 消耗神威辉石: {buy_event.gem_cost}")
            break
```

### 3. 增强日志输出

在购买事件处理中输出更详细的信息：

```
[购买事件]  开始快照: 244 个物品
[购买事件]  当前状态: 244 个物品
[购买事件]  消耗的物品: 1 个
[购买事件]    ✓ 神威辉石消耗: 49
[购买事件]  获得的物品: 0 个
[购买事件]  没有检测到物品增加，可能是消耗型物品
```

## 购买类型

### 1. 实体物品购买

**特征**：
- 神威辉石减少
- 物品数量增加（`item_adds` 不为空）

**日志示例**：
```
[物品更新] 5210: 数量=30520 (神威辉石减少)
[物品添加] 100200: 数量=1 (物品增加)
```

**处理**：使用 `item_adds` 中的物品信息

### 2. 消耗型物品购买

**特征**：
- 神威辉石减少
- 物品数量更新（`item_updates` 不为空，但 `item_adds` 为空）

**日志示例**：
```
[物品更新] 5210: 数量=30520 (神威辉石减少)
[物品更新] 100300: 数量=824 (消耗型物品增加)
```

**处理**：从 `item_updates` 中查找（排除神威辉石）

### 3. 资源购买

**特征**：
- 神威辉石减少
- 没有其他物品变化

**日志示例**：
```
[物品更新] 5210: 数量=30520 (神威辉石减少)
```

**处理**：仅记录神威辉石消耗（无法识别购买的物品）

## 测试场景

### 场景 1：实体物品购买

**输入**：
- 神威辉石：1000 -> 950（-50）
- 物品 A：0 -> 1

**预期输出**：
- 创建购买事件：物品 A x1，消耗神威辉石 50

### 场景 2：消耗型物品购买

**输入**：
- 神威辉石：1000 -> 950（-50）
- 物品 B：100 -> 150（+50）

**预期输出**：
- 创建购买事件：物品 B x50，消耗神威辉石 50

### 场景 3：资源购买

**输入**：
- 神威辉石：1000 -> 950（-50）
- 无其他物品变化

**预期输出**：
- 记录神威辉石消耗：50
- 无法识别购买的物品

### 场景 4：重复的购买事件

**输入**：
- 两次 `BuyVendorGoods` 事件
- 第一次：神威辉石消耗（-49）
- 第二次：无变化

**预期输出**：
- 只处理第一次（有神威辉石消耗）
- 忽略第二次（无物品变化）

## 注意事项

### 1. 成功标志

游戏日志中可能没有明确的"购买成功"标志，需要根据物品变化判断：
- 神威辉石减少 → 可能有购买
- 物品数量增加 → 可能有购买

### 2. 消耗型物品

消耗型物品（如资源）通过 `item_updates` 识别，而不是 `item_adds`：
- `item_adds`：新物品添加
- `item_updates`：现有物品数量变化

### 3. 重复事件

可能会出现多个 `BuyVendorGoods` 事件，但只有真正的购买才会有物品变化：
- 过滤掉没有物品变化的事件

## 文件修改

### 修改的文件
- `services/game_log_parser_service.py`
  - `_finalize_event()`: 不再依赖 success 标志
  - `_process_buy_event()`: 支持消耗型物品
  - 增强日志输出

### 文档
- `docs/BUY_EVENT_FIX.md` - 本文档

## 测试建议

1. **实体物品购买**：确认能正常识别购买的物品和数量
2. **消耗型物品购买**：确认能从 item_updates 中识别
3. **重复事件**：确认只处理有物品变化的事件
4. **日志输出**：查看详细的控制台输出，了解处理过程

## 预期效果

修复后，购买事件应该能够：
- ✅ 正确识别实体物品购买
- ✅ 正确识别消耗型物品购买
- ✅ 忽略没有物品变化的重复事件
- ✅ 输出详细的处理日志
