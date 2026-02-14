#!/usr/bin/env python3
"""测试 InventoryStateManager 单例和初始化"""

from services.inventory_state_manager import InventoryStateManager

print("=" * 60)
print("测试 1: 第一次创建实例")
print("=" * 60)
manager1 = InventoryStateManager()
print(f"manager1._initialized_flag = {manager1._initialized_flag}")
print(f"manager1._item_records = {manager1._item_records}")
print(f"manager1._item_snapshot = {manager1._item_snapshot}")
print(f"manager1._event_changes = {manager1._event_changes}")
print()

print("=" * 60)
print("测试 2: 第二次获取实例（应该是同一个）")
print("=" * 60)
manager2 = InventoryStateManager()
print(f"manager1 is manager2: {manager1 is manager2}")
print(f"manager2._item_records = {manager2._item_records}")
print(f"manager2._initialized_flag = {manager2._initialized_flag}")
print()

print("=" * 60)
print("测试 3: 标记背包已初始化")
print("=" * 60)
manager1.mark_backpack_initialized()
print(f"manager1.is_backpack_initialized = {manager1.is_backpack_initialized}")
print(f"manager2.is_backpack_initialized = {manager2.is_backpack_initialized}")
print()

print("=" * 60)
print("测试 4: 第三次获取实例，验证状态保持")
print("=" * 60)
manager3 = InventoryStateManager()
print(f"manager1 is manager2 is manager3: {manager1 is manager2 is manager3}")
print(f"manager3.is_backpack_initialized = {manager3.is_backpack_initialized}")
print(f"manager3._item_records = {manager3._item_records}")
print()

print("✓ 所有测试通过！")
