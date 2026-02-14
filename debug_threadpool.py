"""详细调试线程池管理器初始化问题"""
import sys
import traceback

print("=== 开始调试线程池管理器 ===", file=sys.stderr)
sys.stderr.flush()

# 测试 1: 单独测试 logger
print("\n测试 1: 测试 logger 初始化...", file=sys.stderr)
sys.stderr.flush()
try:
    from core.logger import get_logger
    logger = get_logger("TestThreadPool")
    print("✓ Logger 初始化成功", file=sys.stderr)
    sys.stderr.flush()
except Exception as e:
    print(f"✗ Logger 初始化失败: {e}", file=sys.stderr)
    sys.stderr.flush()
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

# 测试 2: 测试线程锁
print("\n测试 2: 测试线程锁...", file=sys.stderr)
sys.stderr.flush()
try:
    import threading
    lock = threading.Lock()
    print("✓ 线程锁创建成功", file=sys.stderr)
    sys.stderr.flush()

    with lock:
        print("✓ 成功获取锁", file=sys.stderr)
        sys.stderr.flush()
        # 模拟一些工作
        import time
        time.sleep(0.01)
    print("✓ 成功释放锁", file=sys.stderr)
    sys.stderr.flush()
except Exception as e:
    print(f"✗ 线程锁测试失败: {e}", file=sys.stderr)
    sys.stderr.flush()
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

# 测试 3: 测试 super().__new__
print("\n测试 3: 测试 super().__new__()...", file=sys.stderr)
sys.stderr.flush()
try:
    class TestClass:
        _instance = None
        _lock = threading.Lock()

        def __new__(cls, *args, **kwargs):
            print("  [TestClass.__new__] 开始", file=sys.stderr)
            sys.stderr.flush()
            if cls._instance is None:
                print("  [TestClass.__new__] 实例为 None，获取锁", file=sys.stderr)
                sys.stderr.flush()
                with cls._lock:
                    print("  [TestClass.__new__] 获取锁成功", file=sys.stderr)
                    sys.stderr.flush()
                    if cls._instance is None:
                        print("  [TestClass.__new__] 创建新实例", file=sys.stderr)
                        sys.stderr.flush()
                        cls._instance = super().__new__(cls)
                        print("  [TestClass.__new__] super().__new__() 完成", file=sys.stderr)
                        sys.stderr.flush()
                        cls._instance._initialized = False
                        print("  [TestClass.__new__] 设置 _initialized = False", file=sys.stderr)
                        sys.stderr.flush()
                    else:
                        print("  [TestClass.__new__] 锁内检查，实例已存在", file=sys.stderr)
                        sys.stderr.flush()
            else:
                print("  [TestClass.__new__] 实例已存在", file=sys.stderr)
                sys.stderr.flush()
            print("  [TestClass.__new__] 返回实例", file=sys.stderr)
            sys.stderr.flush()
            return cls._instance

        def __init__(self):
            print("  [TestClass.__init__] 开始", file=sys.stderr)
            sys.stderr.flush()
            print("  [TestClass.__init__] 完成", file=sys.stderr)
            sys.stderr.flush()

    instance = TestClass()
    print("✓ super().__new__() 测试成功", file=sys.stderr)
    sys.stderr.flush()
except Exception as e:
    print(f"✗ super().__new__() 测试失败: {e}", file=sys.stderr)
    sys.stderr.flush()
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

# 测试 4: 测试 ThreadPoolExecutor
print("\n测试 4: 测试 ThreadPoolExecutor...", file=sys.stderr)
sys.stderr.flush()
try:
    from concurrent.futures import ThreadPoolExecutor
    print("  [ThreadPoolExecutor] 开始创建", file=sys.stderr)
    sys.stderr.flush()
    executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="TestWorker")
    print("✓ ThreadPoolExecutor 创建成功", file=sys.stderr)
    sys.stderr.flush()
    executor.shutdown(wait=True)
    print("✓ ThreadPoolExecutor 关闭成功", file=sys.stderr)
    sys.stderr.flush()
except Exception as e:
    print(f"✗ ThreadPoolExecutor 测试失败: {e}", file=sys.stderr)
    sys.stderr.flush()
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

# 测试 5: 测试实际的 ThreadPoolManager
print("\n测试 5: 测试实际的 ThreadPoolManager...", file=sys.stderr)
sys.stderr.flush()
try:
    from core.thread_pool_manager import ThreadPoolManager

    print("  [ThreadPoolManager] 导入成功", file=sys.stderr)
    sys.stderr.flush()

    print("  [ThreadPoolManager] 准备创建实例", file=sys.stderr)
    sys.stderr.flush()

    manager = ThreadPoolManager()
    print("✓ ThreadPoolManager 创建成功", file=sys.stderr)
    sys.stderr.flush()

except Exception as e:
    print(f"✗ ThreadPoolManager 测试失败: {e}", file=sys.stderr)
    sys.stderr.flush()
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

print("\n=== 所有测试通过 ===", file=sys.stderr)
sys.stderr.flush()
