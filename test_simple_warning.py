#!/usr/bin/env python3
"""简单测试背包警告逻辑"""
from services.inventory_state_manager import InventoryStateManager

print("=" * 60)
print("测试 InventoryStateManager 单例和初始化")
print("=" * 60)

# 创建第一个实例
print("\n1. 创建第一个实例...")
manager1 = InventoryStateManager()
print(f"   _initialized_flag: {manager1._initialized_flag}")
print(f"   has _item_records: {hasattr(manager1, '_item_records')}")
if hasattr(manager1, '_item_records'):
    print(f"   _item_records 是否为空: {len(manager1._item_records) == 0}")
print(f"   is_backpack_initialized: {manager1.is_backpack_initialized}")

# 标记背包已初始化
print("\n2. 标记背包已初始化...")
manager1.mark_backpack_initialized()
print(f"   is_backpack_initialized: {manager1.is_backpack_initialized}")

# 创建第二个实例（应该是同一个）
print("\n3. 创建第二个实例（应该是同一个单例）...")
manager2 = InventoryStateManager()
print(f"   manager1 is manager2: {manager1 is manager2}")
print(f"   _initialized_flag: {manager2._initialized_flag}")
print(f"   is_backpack_initialized: {manager2.is_backpack_initialized}")

# 检查 _item_records 是否还在
print(f"   has _item_records: {hasattr(manager2, '_item_records')}")
if hasattr(manager2, '_item_records'):
    print(f"   _item_records 是否为空: {len(manager2._item_records) == 0}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
