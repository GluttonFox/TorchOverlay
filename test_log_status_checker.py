"""测试日志状态检测功能"""
import sys
from services.log_status_checker_service import get_log_status_checker, LogStatus

print("=" * 70)
print("测试日志状态检测功能")
print("=" * 70)

# 获取检测器实例
checker = get_log_status_checker()

# 测试 1: 自动查找游戏日志路径
print("\n[测试 1] 自动查找游戏日志路径...")
status = checker.check_log_status()

print(f"  游戏运行: {status.game_running}")
if status.game_running:
    print(f"  进程ID: {status.process_id}")
print(f"  日志已开启: {status.is_enabled}")
print(f"  日志可访问: {status.is_accessible}")
print(f"  日志路径: {status.log_path}")
print(f"  日志大小: {status.log_size} 字节")
print(f"  有权限: {status.has_permission}")
if status.last_modified:
    print(f"  最后修改: {status.last_modified}")
if status.error_message:
    print(f"  错误信息: {status.error_message}")

# 获取状态摘要
summary = checker.get_status_summary()
print(f"\n状态摘要: {summary}")

# 测试 2: 显示详细错误消息
print("\n[测试 2] 显示详细错误消息...")
details = checker.get_formatted_error_message()
print(details)

# 测试 3: 测试手动指定日志路径
print("\n[测试 3] 测试手动指定日志路径...")
test_log_path = r"D:\TapTap\PC Games\172664\UE_game\Torchlight\Saved\Logs\UE_game.log"
status2 = checker.check_log_status(test_log_path)

print(f"  日志已开启: {status2.is_enabled}")
print(f"  日志可访问: {status2.is_accessible}")
print(f"  状态摘要: {summary}")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)
