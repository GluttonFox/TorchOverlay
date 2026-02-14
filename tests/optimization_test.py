"""优化功能测试脚本"""
import time
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.logger import get_logger
from core.cache_manager import LRUCache, TimedCache
from core.thread_pool_manager import ThreadPoolManager
from core.memory_monitor import MemoryMonitor
from core.resource_manager import ResourceManager

logger = get_logger(__name__)


def test_cache_manager():
    """测试缓存管理器"""
    print("\n" + "="*60)
    print("测试 1: 缓存管理器")
    print("="*60)

    # 测试 LRU 缓存
    print("\n[1.1] 测试 LRU 缓存...")
    lru_cache = LRUCache(max_size=5, default_ttl=2.0, auto_cleanup=True)

    # 添加条目
    for i in range(10):
        lru_cache.set(f"key_{i}", f"value_{i}")
        print(f"  添加: key_{i}")

    # 检查LRU驱逐
    assert len(lru_cache.get_stats()['size']) == 5, "LRU缓存应该保持最大5个条目"
    print(f"  ✓ LRU缓存正常工作，当前大小: {lru_cache.get_stats()['size']}")

    # 测试TTL过期
    time.sleep(2.5)
    expired = lru_cache._cleanup_expired()
    print(f"  ✓ 清理了 {expired} 个过期条目")

    # 测试统计信息
    stats = lru_cache.get_stats()
    print(f"  统计: {stats}")

    # 测试 TimedCache
    print("\n[1.2] 测试 TimedCache...")
    timed_cache = TimedCache(max_size=10, max_age_seconds=2.0)

    for i in range(15):
        timed_cache.add(f"event_{i}", f"data_{i}")

    print(f"  ✓ 添加了15个事件，当前缓存大小: {timed_cache.get_size()}")

    recent = timed_cache.get_recent(count=5)
    print(f"  ✓ 最近的5个事件: {[r[0] for r in recent]}")

    # 清理旧条目
    cleaned = timed_cache.cleanup_old()
    print(f"  ✓ 清理了 {cleaned} 个旧条目，当前大小: {timed_cache.get_size()}")

    print("\n✓ 缓存管理器测试通过\n")


def test_thread_pool_manager():
    """测试线程池管理器"""
    print("\n" + "="*60)
    print("测试 2: 线程池管理器")
    print("="*60)

    pool = ThreadPoolManager(max_workers=3)

    # 测试任务提交
    print("\n[2.1] 测试任务提交...")

    results = []

    def task_function(task_id):
        time.sleep(0.5)
        return f"result_{task_id}"

    def callback(result):
        results.append(result)
        print(f"  ✓ 任务完成: {result}")

    # 提交5个任务
    task_ids = []
    for i in range(5):
        task_id = pool.submit_task(
            task_function,
            i,
            task_id=f"test_task_{i}",
            callback=callback
        )
        task_ids.append(task_id)

    # 等待所有任务完成
    time.sleep(2)

    assert len(results) == 5, f"应该有5个结果，实际: {len(results)}"
    print(f"  ✓ 所有5个任务已完成")

    # 检查任务状态
    stats = pool.get_stats()
    print(f"  统计: {stats}")

    # 测试任务取消
    print("\n[2.2] 测试任务取消...")
    long_task_id = pool.submit_task(
        lambda: time.sleep(10),
        task_id="long_task"
    )
    time.sleep(0.1)
    cancelled = pool.cancel_task(long_task_id)
    print(f"  {'✓' if cancelled else '✗'} 任务取消: {cancelled}")

    # 清理
    pool.shutdown()
    print("\n✓ 线程池管理器测试通过\n")


def test_memory_monitor():
    """测试内存监控器"""
    print("\n" + "="*60)
    print("测试 3: 内存监控器")
    print("="*60)

    print("\n[3.1] 创建内存监控器...")
    monitor = MemoryMonitor(
        warning_threshold_mb=100.0,  # 较低的阈值以便测试
        critical_threshold_mb=200.0,
        check_interval=1.0,
        auto_cleanup_on_warning=True
    )

    # 设置回调
    warning_called = [False]

    def on_warning(usage_mb):
        warning_called[0] = True
        print(f"  ⚠️  警告回调触发: {usage_mb:.2f}MB")

    monitor.set_callbacks(on_warning=on_warning)

    # 启动监控
    print("\n[3.2] 启动监控...")
    monitor.start()
    print("  ✓ 内存监控已启动")

    # 检查当前内存
    monitor._check_memory()
    stats = monitor.get_stats()
    print(f"  当前内存: {stats['current_usage_mb']:.2f}MB")
    print(f"  峰值内存: {stats['peak_usage_mb']:.2f}MB")

    # 手动清理
    print("\n[3.3] 测试手动清理...")
    monitor.trigger_manual_cleanup()
    print("  ✓ 手动清理已触发")

    # 停止监控
    monitor.stop()
    print("  ✓ 内存监控已停止")

    print("\n✓ 内存监控器测试通过\n")


def test_resource_manager():
    """测试资源管理器"""
    print("\n" + "="*60)
    print("测试 4: 资源管理器")
    print("="*60)

    print("\n[4.1] 测试图像资源管理...")
    manager = ResourceManager.get_instance()

    # 创建测试图像
    from PIL import Image
    import os

    test_image_path = project_root / "test_temp.png"
    if test_image_path.exists():
        os.remove(test_image_path)

    # 创建测试图像
    img = Image.new('RGB', (100, 100), color='red')
    img.save(test_image_path)
    img.close()

    # 使用资源管理器加载图像
    loaded_img = manager.acquire_image(str(test_image_path), resource_id="test_image")
    assert loaded_img is not None, "应该成功加载图像"
    print(f"  ✓ 图像已加载: {loaded_img.size}")

    # 释放图像
    released = manager.release_image(loaded_img, "test_image")
    assert released, "应该成功释放图像"
    print("  ✓ 图像已释放")

    # 测试上下文管理器
    print("\n[4.2] 测试上下文管理器...")
    from core.resource_manager import managed_image

    with managed_image(str(test_image_path)) as context_img:
        print(f"  ✓ 上下文管理器中: {context_img.size}")
        assert context_img is not None

    print("  ✓ 图像已自动释放")

    # 清理测试文件
    os.remove(test_image_path)

    # 获取统计信息
    stats = manager.get_stats()
    print(f"\n  统计: {stats}")

    print("\n✓ 资源管理器测试通过\n")


def test_unified_price_service():
    """测试统一的价格服务"""
    print("\n" + "="*60)
    print("测试 5: 统一价格服务")
    print("="*60)

    from services.price_service import PriceService

    print("\n[5.1] 创建价格服务...")
    price_service = PriceService()

    # 检查状态
    status = price_service.get_status()
    print(f"  初始状态: {status.value}")

    # 检查统计
    stats = price_service.get_stats()
    print(f"  统计信息: {stats}")

    # 测试更新能力
    can_update = price_service.can_update()
    print(f"  可以更新: {can_update}")

    # 清理
    price_service.shutdown()
    print("  ✓ 价格服务已关闭")

    print("\n✓ 统一价格服务测试通过\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始优化功能测试")
    print("="*60)

    try:
        test_cache_manager()
        test_thread_pool_manager()
        test_memory_monitor()
        test_resource_manager()
        test_unified_price_service()

        print("\n" + "="*60)
        print("✓ 所有测试通过！")
        print("="*60)

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
