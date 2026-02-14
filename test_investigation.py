"""测试不同配置，找出线程池管理器卡死的原因"""
import sys

print("=" * 60)
print("测试配置 1: 完全禁用优化功能（当前配置）")
print("=" * 60)

from app.application import TorchOverlayApplication

app1 = TorchOverlayApplication(enable_memory_monitor=False, enable_thread_pool=False)
print("✓ 配置 1 成功：禁用所有优化功能\n")

print("=" * 60)
print("测试配置 2: 只启用内存监控")
print("=" * 60)

app2 = TorchOverlayApplication(enable_memory_monitor=True, enable_thread_pool=False)
print("✓ 配置 2 成功：只启用内存监控\n")

print("=" * 60)
print("测试配置 3: 只启用线程池（有问题）")
print("=" * 60)

try:
    app3 = TorchOverlayApplication(enable_memory_monitor=False, enable_thread_pool=True)
    print("✓ 配置 3 成功：只启用线程池\n")
except Exception as e:
    print(f"✗ 配置 3 失败：{e}\n")
    import traceback
    traceback.print_exc()

print("=" * 60)
print("测试配置 4: 启用所有优化（可能有问题）")
print("=" * 60)

try:
    app4 = TorchOverlayApplication(enable_memory_monitor=True, enable_thread_pool=True)
    print("✓ 配置 4 成功：启用所有优化功能\n")
except Exception as e:
    print(f"✗ 配置 4 失败：{e}\n")
    import traceback
    traceback.print_exc()

print("=" * 60)
print("测试完成")
print("=" * 60)
