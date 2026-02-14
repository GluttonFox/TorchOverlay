"""调试主程序启动流程"""
import sys
import traceback
import time

print("=" * 70)
print("调试主程序启动流程")
print("=" * 70)

print("\n[步骤 1] 导入 core.logger ...")
try:
    from core.logger import get_logger
    logger = get_logger(__name__)
    print("✓ core.logger 导入成功")
except Exception as e:
    print(f"✗ core.logger 导入失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n[步骤 2] 导入 core.thread_pool_manager ...")
try:
    from core.thread_pool_manager import ThreadPoolManager
    print("✓ core.thread_pool_manager 导入成功")
except Exception as e:
    print(f"✗ core.thread_pool_manager 导入失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n[步骤 3] 导入 core.memory_monitor ...")
try:
    from core.memory_monitor import MemoryMonitor
    print("✓ core.memory_monitor 导入成功")
except Exception as e:
    print(f"✗ core.memory_monitor 导入失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n[步骤 4] 导入 app.factories ...")
try:
    from app.factories import AppFactory
    print("✓ app.factories 导入成功")
except Exception as e:
    print(f"✗ app.factories 导入失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n[步骤 5] 导入 app.application ...")
try:
    from app.application import TorchOverlayApplication
    print("✓ app.application 导入成功")
except Exception as e:
    print(f"✗ app.application 导入失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n[步骤 6] 创建 TorchOverlayApplication 实例（不启用优化）...")
try:
    app1 = TorchOverlayApplication(enable_memory_monitor=False, enable_thread_pool=False)
    print("✓ TorchOverlayApplication 创建成功（不启用优化）")
except Exception as e:
    print(f"✗ TorchOverlayApplication 创建失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n[步骤 7] 创建 TorchOverlayApplication 实例（启用线程池）...")
try:
    app2 = TorchOverlayApplication(enable_memory_monitor=False, enable_thread_pool=True)
    print("✓ TorchOverlayApplication 创建成功（启用线程池）")
except Exception as e:
    print(f"✗ TorchOverlayApplication 创建失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n[步骤 8] 调用 _initialize_managers()（启用线程池）...")
try:
    app2._initialize_managers()
    print("✓ _initialize_managers() 调用成功")
    print(f"  - 线程池已创建: {app2._thread_pool is not None}")
except Exception as e:
    print(f"✗ _initialize_managers() 调用失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n[步骤 9] 创建 AppFactory ...")
try:
    app3 = TorchOverlayApplication(enable_memory_monitor=False, enable_thread_pool=False)
    factory = AppFactory()
    print("✓ AppFactory 创建成功")
except Exception as e:
    print(f"✗ AppFactory 创建失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n[步骤 10] 创建控制器（这会创建所有服务）...")
try:
    controller = factory.create_controller()
    print("✓ 控制器创建成功")
except Exception as e:
    print(f"✗ 控制器创建失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n[步骤 11] 清理资源...")
try:
    app2._cleanup_managers()
    print("✓ 资源清理成功")
except Exception as e:
    print(f"✗ 资源清理失败: {e}")
    traceback.print_exc()

print("\n" + "=" * 70)
print("所有步骤完成！")
print("=" * 70)
