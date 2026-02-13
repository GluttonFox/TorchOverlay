"""测试新的日志解析逻辑"""
import re
from datetime import datetime

# 测试正则表达式
ITEM_UPDATE_PATTERN = re.compile(
    r"ItemChange@\s+Update\s+Id=([^\s]+)\s+BagNum=(\d+)\s+in\s+PageId=(-?\d+)\s+SlotId=(\d+)"
)
ITEM_ADD_PATTERN = re.compile(
    r"ItemChange@\s+Add\s+Id=([^\s]+)\s+BagNum=(\d+)\s+in\s+PageId=(\d+)\s+SlotId=(\d+)"
)
ITEM_DELETE_PATTERN = re.compile(
    r"ItemChange@\s+Delete\s+Id=([^\s]+)\s+in\s+PageId=(\d+)\s+SlotId=(\d+)"
)

EVENT_START_PATTERN = re.compile(r"ItemChange@\s+ProtoName=(\w+)\s+start")
EVENT_END_PATTERN = re.compile(r"ItemChange@\s+ProtoName=(\w+)\s+end")

# 测试日志行
test_lines = [
    # 购买事件开始
    "[2026.02.14-10.23.45:123][902]GameLog: Display: [Game] ItemChange@ ProtoName=BuyVendorGoods start",
    
    # 神威辉石更新（消耗）
    "[2026.02.14-10.23.45:234][902]GameLog: Display: [Game] ItemChange@ Update Id=5210_12345 BagNum=30633 in PageId=102 SlotId=5",
    
    # 物品添加（购买的物品）
    "[2026.02.14-10.23.45:345][902]GameLog: Display: [Game] ItemChange@ Add Id=100200_67890 BagNum=1 in PageId=102 SlotId=10",
    
    # 购买成功
    "[2026.02.14-10.23.45:456][902]GameLog: Display: [Game] Func_Common_BuySuccess",
    
    # 购买事件结束
    "[2026.02.14-10.23.45:567][902]GameLog: Display: [Game] ItemChange@ ProtoName=BuyVendorGoods end",
    
    # 刷新事件开始
    "[2026.02.14-10.24.00:111][902]GameLog: Display: [Game] ItemChange@ ProtoName=RefreshVendorShop start",
    
    # 刷新成功
    "[2026.02.14-10.24.00:222][902]GameLog: Display: [Game] Func_Vendor_refreshSuccess",
    
    # 刷新事件结束
    "[2026.02.14-10.24.00:333][902]GameLog: Display: [Game] ItemChange@ ProtoName=RefreshVendorShop end",
]

print("=" * 80)
print("测试新的日志解析逻辑")
print("=" * 80)

for line in test_lines:
    print(f"\n原始日志: {line}")
    
    # 测试事件边界
    event_start = EVENT_START_PATTERN.search(line)
    if event_start:
        print(f"  ✓ 事件开始: {event_start.group(1)}")
    
    event_end = EVENT_END_PATTERN.search(line)
    if event_end:
        print(f"  ✓ 事件结束: {event_end.group(1)}")
    
    # 测试物品更新
    update_match = ITEM_UPDATE_PATTERN.search(line)
    if update_match:
        item_id = update_match.group(1)
        bag_num = update_match.group(2)
        page_id = update_match.group(3)
        slot_id = update_match.group(4)
        base_id = item_id.split('_')[0]
        print(f"  ✓ 物品更新: base_id={base_id}, bag_num={bag_num}, page_id={page_id}, slot_id={slot_id}")
    
    # 测试物品添加
    add_match = ITEM_ADD_PATTERN.search(line)
    if add_match:
        item_id = add_match.group(1)
        bag_num = add_match.group(2)
        page_id = add_match.group(3)
        slot_id = add_match.group(4)
        base_id = item_id.split('_')[0]
        print(f"  ✓ 物品添加: base_id={base_id}, bag_num={bag_num}, page_id={page_id}, slot_id={slot_id}")
    
    # 测试物品删除
    delete_match = ITEM_DELETE_PATTERN.search(line)
    if delete_match:
        item_id = delete_match.group(1)
        page_id = delete_match.group(2)
        slot_id = delete_match.group(3)
        base_id = item_id.split('_')[0]
        print(f"  ✓ 物品删除: base_id={base_id}, page_id={page_id}, slot_id={slot_id}")
    
    # 测试成功标志
    if "Func_Common_BuySuccess" in line:
        print(f"  ✓ 购买成功")
    
    if "Func_Vendor_refreshSuccess" in line:
        print(f"  ✓ 刷新成功")

print("\n" + "=" * 80)
print("测试完成！")
print("=" * 80)
