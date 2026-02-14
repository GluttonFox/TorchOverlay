"""逐步测试主程序的各个组件"""
import sys

print("测试 1: 导入基础模块...")
try:
    import tkinter as tk
    from tkinter import messagebox
    print("✓ tkinter 导入成功")
except Exception as e:
    print(f"✗ tkinter 导入失败: {e}")
    sys.exit(1)

print("\n测试 2: 测试 DPI 感知...")
try:
    from services.overlay.dpi import enable_per_monitor_v2_dpi_awareness
    enable_per_monitor_v2_dpi_awareness()
    print("✓ DPI 感知已启用")
except Exception as e:
    print(f"✗ DPI 感知启用失败: {e}")
    import traceback
    traceback.print_exc()

print("\n测试 3: 加载配置...")
try:
    from core.config import AppConfig
    cfg = AppConfig.load()
    print(f"✓ 配置已加载")
    print(f"  - API Name: {cfg.ocr.api_name}")
    print(f"  - Debug Mode: {cfg.ocr.debug_mode}")
except Exception as e:
    print(f"✗ 配置加载失败: {e}")
    import traceback
    traceback.print_exc()

print("\n测试 4: 创建应用实例...")
try:
    from app.application import TorchOverlayApplication
    app = TorchOverlayApplication()
    print("✓ 应用实例已创建")
except Exception as e:
    print(f"✗ 应用实例创建失败: {e}")
    import traceback
    traceback.print_exc()

print("\n测试 5: 创建工厂...")
try:
    app = TorchOverlayApplication()
    factory = app._factory
    print("✓ 工厂已创建")
except Exception as e:
    print(f"✗ 工厂创建失败: {e}")
    import traceback
    traceback.print_exc()

print("\n测试 6: 检查管理员权限...")
try:
    from services.admin_service import AdminService
    admin = AdminService(cfg)
    is_admin = admin.is_admin()
    print(f"✓ 管理员权限检查完成")
    print(f"  - 是否管理员: {is_admin}")
except Exception as e:
    print(f"✗ 管理员权限检查失败: {e}")
    import traceback
    traceback.print_exc()

print("\n测试 7: 创建控制器...")
try:
    controller = factory.create_controller()
    print("✓ 控制器已创建")
except Exception as e:
    print(f"✗ 控制器创建失败: {e}")
    import traceback
    traceback.print_exc()

print("\n测试 8: 创建主窗口（不运行）...")
try:
    window = factory.create_main_window(controller)
    print("✓ 主窗口已创建（未显示）")
except Exception as e:
    print(f"✗ 主窗口创建失败: {e}")
    import traceback
    traceback.print_exc()

print("\n所有测试完成！")
print("\n现在尝试运行完整程序...")
print("如果程序立即退出，请查看上面的错误信息。")
input("按回车键继续运行主程序（或 Ctrl+C 退出）...")

print("\n运行主程序...")
try:
    from app.application import TorchOverlayApplication
    TorchOverlayApplication().run()
except Exception as e:
    print(f"主程序运行失败: {e}")
    import traceback
    traceback.print_exc()
