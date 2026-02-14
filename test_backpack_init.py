"""测试背包初始化状态检测"""
from services.inventory_state_manager import InventoryStateManager

# 获取单例实例
manager1 = InventoryStateManager()
print(f"第一次创建 - is_backpack_initialized: {manager1.is_backpack_initialized}")

# 标记为已初始化
manager1.mark_backpack_initialized()
print(f"mark_backpack_initialized 后 - is_backpack_initialized: {manager1.is_backpack_initialized}")

# 再次获取单例实例
manager2 = InventoryStateManager()
print(f"第二次获取（应该是同一个实例） - is_backpack_initialized: {manager2.is_backpack_initialized}")
print(f"manager1 is manager2: {manager1 is manager2}")

# 测试重置
manager1.reset_backpack_initialized()
print(f"reset_backpack_initialized 后 - is_backpack_initialized: {manager1.is_backpack_initialized}")
