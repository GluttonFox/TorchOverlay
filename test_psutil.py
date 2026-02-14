"""测试 psutil 是否可用"""
import sys

print("=" * 50)
print("测试 psutil 模块")
print("=" * 50)

try:
    import psutil
    print("✓ psutil 导入成功")
    print(f"  版本: {psutil.__version__}")

    # 测试进程检测
    print("\n测试进程检测...")
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'torchlight' in proc.info['name'].lower():
                print(f"  找到进程: {proc.info['name']} (PID: {proc.info['pid']})")
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

except ImportError:
    print("✗ psutil 模块未安装")
    sys.exit(1)
except Exception as e:
    print(f"✗ psutil 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)
