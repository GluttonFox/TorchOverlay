#!/usr/bin/env python3
"""直接测试背包警告覆盖层的显示"""
import tkinter as tk
from ui.main_window import MainWindow
from app.factories import AppFactory
from controllers.app_controller import AppController

def test_backpack_warning():
    print("=" * 60)
    print("测试背包警告覆盖层")
    print("=" * 60)

    # 创建主窗口
    print("[测试] 创建 AppFactory...")
    factory = AppFactory()
    print(f"[测试] AppFactory 创建成功")

    print("[测试] 创建 Controller...")
    controller = factory.create_controller()
    print(f"[测试] Controller 创建成功")

    print("[测试] 创建 MainWindow...")
    window = factory.create_main_window(controller)
    print(f"[测试] MainWindow 创建成功")

    # 等待窗口初始化完成
    window.root.update()

    # 测试显示警告
    print("\n[测试] 调用 show_backpack_warning(show=True)...")
    window.show_backpack_warning(show=True)
    window.root.update()

    # 检查警告覆盖层是否可见
    is_mapped = window._backpack_warning_frame.winfo_ismapped()
    print(f"[测试] 警告覆盖层是否可见: {is_mapped}")

    # 获取警告覆盖层的位置和大小
    x = window._backpack_warning_frame.winfo_x()
    y = window._backpack_warning_frame.winfo_y()
    width = window._backpack_warning_frame.winfo_width()
    height = window._backpack_warning_frame.winfo_height()
    print(f"[测试] 警告覆盖层位置: ({x}, {y})")
    print(f"[测试] 警告覆盖层大小: {width}x{height}")

    # 检查警告覆盖层是否有子元素
    children = window._backpack_warning_frame.winfo_children()
    print(f"[测试] 警告覆盖层子元素数量: {len(children)}")
    for i, child in enumerate(children):
        print(f"[测试] 子元素 {i}: {child.__class__.__name__}")

    # 保持窗口显示 3 秒
    print("\n[测试] 窗口将显示 3 秒，请观察警告覆盖层...")
    window.root.after(3000, window.root.destroy)
    window.run()

    print("[测试] 测试完成")

if __name__ == "__main__":
    test_backpack_warning()
