# TorchOverlay 优化功能使用指南

## 📚 概述

本次优化大幅提升了代码质量和运行稳定性，主要改进包括：

1. **统一价格服务** - 合并同步和异步功能
2. **智能缓存管理** - LRU缓存 + TTL过期
3. **统一线程池** - 统一管理所有异步任务
4. **资源管理器** - 确保资源正确释放
5. **内存监控** - 实时监控和预警
6. **图像资源修复** - 消除内存泄漏

## 🚀 快速开始

### 1. 运行优化测试

验证所有优化功能是否正常工作：

```bash
python tests/optimization_test.py
```

预期输出：
```
✓ 所有测试通过！
```

### 2. 启动应用

应用会自动初始化所有管理器：

```bash
python main.py
```

启动时会看到以下日志：
```
[资源管理器] 资源管理器已初始化
[线程池管理器] 线程池管理器已初始化，最大工作线程数: 4
[内存监控] 内存监控器已初始化，警告阈值: 500.0MB, 严重阈值: 1000.0MB
[内存监控] 内存监控已启动
```

## 📖 API 使用指南

### 缓存管理

#### LRU缓存

适用于需要限制大小和自动过期的场景：

```python
from core.cache_manager import LRUCache

# 创建缓存（最大100条，TTL 60秒）
cache = LRUCache(max_size=100, default_ttl=60.0, auto_cleanup=True)

# 添加缓存
cache.set("user_123", user_data)
cache.set("session_abc", session_data, ttl=300.0)  # 自定义TTL

# 获取缓存
data = cache.get("user_123")

# 检查是否存在
if cache.get("user_123"):
    print("缓存命中！")

# 获取统计信息
stats = cache.get_stats()
print(f"命中率: {stats['hit_rate']}, 大小: {stats['size']}")

# 清空缓存
cache.clear()
```

#### Timed缓存

适用于时间序列数据（日志、事件等）：

```python
from core.cache_manager import TimedCache

# 创建缓存（最大1000条，保留1小时）
timed_cache = TimedCache(max_size=1000, max_age_seconds=3600.0)

# 添加事件
timed_cache.add("event_1", event_data, timestamp=time.time())
timed_cache.add("event_2", event_data)  # 使用当前时间

# 获取最近的N个事件
recent = timed_cache.get_recent(count=10)
for event_key, event_data, timestamp in recent:
    print(f"{event_key}: {timestamp}")

# 清理旧事件
cleaned_count = timed_cache.cleanup_old(max_age_seconds=3600.0)

# 清空
timed_cache.clear()
```

### 线程池管理

提交异步任务并获取结果：

```python
from core.thread_pool_manager import ThreadPoolManager

# 获取线程池实例（单例）
pool = ThreadPoolManager.get_instance()

# 定义任务函数
def process_image(image_path):
    # 处理图像
    return result

# 提交任务
task_id = pool.submit_task(
    process_image,
    "image.png",
    task_id="process_123",
    timeout=30.0,
    callback=lambda result: print(f"完成: {result}"),
    error_callback=lambda e: print(f"错误: {e}")
)

# 查询任务状态
status = pool.get_task_status(task_id)
print(f"状态: {status['status']}")

# 等待任务完成
result = pool.wait_for_task(task_id, timeout=60.0)

# 取消任务
pool.cancel_task(task_id)

# 获取统计
stats = pool.get_stats()
print(f"成功率: {stats['success_rate']}")
```

### 资源管理

确保资源正确释放：

```python
from core.resource_manager import ResourceManager, managed_image

# 方式1：手动管理
manager = ResourceManager.get_instance()

# 获取资源
img = manager.acquire_image("screenshot.png", resource_id="my_image")
if img:
    try:
        # 使用图像
        cropped = img.crop((0, 0, 100, 100))
        process(cropped)
    finally:
        # 释放资源
        manager.release_image(img, "my_image")

# 方式2：上下文管理器（推荐）
with managed_image("screenshot.png") as img:
    # 使用图像
    cropped = img.crop((0, 0, 100, 100))
    process(cropped)
# 图像自动释放，无需手动close()

# 释放所有资源
manager.release_all_resources()
```

### 内存监控

监控和响应内存使用：

```python
from core.memory_monitor import MemoryMonitor

# 创建监控器
monitor = MemoryMonitor(
    warning_threshold_mb=500.0,   # 警告阈值
    critical_threshold_mb=1000.0,  # 严重阈值
    check_interval=10.0,           # 检查间隔（秒）
    auto_cleanup_on_warning=True      # 警告时自动清理
)

# 设置回调
def on_warning(usage_mb):
    print(f"⚠️ 内存警告: {usage_mb:.2f}MB")

def on_critical(usage_mb):
    print(f"🔴 严重警告: {usage_mb:.2f}MB")
    # 可以触发紧急清理或通知用户

def on_recovery(usage_mb):
    print(f"✅ 内存恢复: {usage_mb:.2f}MB")

monitor.set_callbacks(
    on_warning=on_warning,
    on_critical=on_critical,
    on_recovery=on_recovery
)

# 启动监控
monitor.start()

# 查询当前内存
current = monitor.get_current_usage()
peak = monitor.get_peak_usage()
print(f"当前: {current:.2f}MB, 峰值: {peak:.2f}MB")

# 手动触发清理
monitor.trigger_manual_cleanup()

# 获取统计
stats = monitor.get_stats()
print(stats)

# 停止监控
monitor.stop()
```

### 价格服务

统一的价格服务支持同步和异步：

```python
from services.price_service import PriceService

# 创建服务
price_service = PriceService(
    api_url="https://serverp.furtorch.heili.tech/price",
    update_interval_hours=1.0,
    config_path="config.json"
)

# 同步更新
success, message = price_service.update_prices()
print(f"{'成功' if success else '失败'}: {message}")

# 异步更新
def on_complete(success, message):
    print(f"更新{'成功' if success else '失败'}: {message}")

price_service.set_callbacks(on_complete=on_complete)
price_service.update_prices_async()

# 检查状态
status = price_service.get_status()
print(f"状态: {status.value}")

# 获取统计
stats = price_service.get_stats()
print(f"成功率: {stats['success_rate']}")

# 关闭服务
price_service.shutdown()
```

## 🔧 配置说明

### 调整内存监控阈值

在 `app/application.py` 中调整：

```python
monitor = MemoryMonitor(
    warning_threshold_mb=800.0,   # 根据实际情况调整
    critical_threshold_mb=1500.0,
    check_interval=10.0,
    auto_cleanup_on_warning=True
)
```

### 调整线程池大小

在 `core/thread_pool_manager.py` 中的默认值：

```python
def __init__(self, max_workers: int = 4, ...):
```

或创建时指定：

```python
pool = ThreadPoolManager(max_workers=8)  # 增加到8个工作线程
```

### 调整缓存大小

根据实际需求调整：

```python
# LRU缓存：默认50-100条
cache = LRUCache(max_size=100, default_ttl=60.0)

# Timed缓存：默认1000条
timed_cache = TimedCache(max_size=2000, max_age_seconds=3600.0)
```

## 📊 监控和调试

### 查看缓存统计

```python
stats = cache.get_stats()
print(f"""
缓存统计:
- 总查询: {stats['hits'] + stats['misses']}
- 命中: {stats['hits']}
- 未命中: {stats['misses']}
- 驱逐: {stats['evictions']}
- 过期: {stats['expirations']}
- 命中率: {stats['hit_rate']}
""")
```

### 查看线程池统计

```python
stats = pool.get_stats()
print(f"""
线程池统计:
- 总提交: {stats['total_submitted']}
- 总完成: {stats['total_completed']}
- 总失败: {stats['total_failed']}
- 总取消: {stats['total_cancelled']}
- 活动任务: {stats['pending_tasks']}
- 最大工作线程: {stats['max_workers']}
- 成功率: {stats['success_rate']}
""")
```

### 查看内存统计

```python
stats = monitor.get_stats()
print(f"""
内存统计:
- 当前使用: {stats['current_usage_mb']:.2f}MB
- 峰值使用: {stats['peak_usage_mb']:.2f}MB
- 警告次数: {stats['warning_count']}
- 严重次数: {stats['critical_count']}
- 恢复次数: {stats['recovery_count']}
- 清理次数: {stats['cleanup_count']}
- 是否监控中: {stats['is_monitoring']}
""")
```

## 🐛 故障排查

### 问题1：内存持续增长

**症状**：应用运行一段时间后内存持续增长

**解决**：
1. 检查是否有资源未释放
2. 使用 `managed_image` 上下文管理器
3. 触发手动清理：`monitor.trigger_manual_cleanup()`
4. 查看统计：`manager.get_stats()`

### 问题2：缓存占用过高

**症状**：缓存大小超出预期

**解决**：
1. 检查TTL设置
2. 启用自动清理：`auto_cleanup=True`
3. 手动清理：`cache._cleanup_expired()`
4. 调整max_size：`LRUCache(max_size=50)`

### 问题3：任务堆积

**症状**：线程池任务完成缓慢

**解决**：
1. 增加工作线程：`ThreadPoolManager(max_workers=8)`
2. 检查任务是否阻塞
3. 查看统计：`pool.get_stats()`
4. 取消长时间任务：`pool.cancel_task(task_id)`

## 📈 性能优化建议

### 1. 图像处理优化

```python
# 推荐使用上下文管理器
with managed_image(path) as img:
    # 处理图像
    pass
# 自动释放，无需手动管理
```

### 2. 缓存策略

```python
# 根据数据特性选择合适的缓存
# 频繁访问且有限制：LRU
cache = LRUCache(max_size=100, default_ttl=60.0)

# 时间序列数据：TimedCache
timed_cache = TimedCache(max_size=1000, max_age_seconds=3600.0)
```

### 3. 异步任务

```python
# 耗时操作使用线程池
pool.submit_task(
    long_running_function,
    arg1, arg2,
    callback=on_complete,
    error_callback=on_error
)
```

## 📝 最佳实践

### 1. 资源管理

- ✅ 始终使用 `managed_image` 处理图像
- ✅ 及时释放不再使用的资源
- ✅ 避免在循环中重复创建资源
- ✅ 使用上下文管理器自动清理

### 2. 缓存使用

- ✅ 根据实际需求设置合理的max_size
- ✅ 设置适当的TTL避免过期数据
- ✅ 启用auto_cleanup自动清理
- ✅ 定期查看统计信息

### 3. 线程池

- ✅ 避免直接创建线程
- ✅ 为长时任务设置合理的timeout
- ✅ 实现错误回调处理异常
- ✅ 应用退出前shutdown线程池

### 4. 内存监控

- ✅ 设置合理的阈值
- ✅ 实现回调响应该告警
- ✅ 定期查看内存统计
- ✅ 手动触发清理及时释放

## 🔗 相关文档

- `ARCHITECTURE_OPTIMIZATION_PLAN.md` - 完整优化计划
- `OPTIMIZATION_COMPLETED_REPORT.md` - 详细完成报告
- `README.md` - 项目概述
- `docs/DEVELOPER_GUIDE.md` - 开发指南

## 💡 提示

1. **测试环境**：先在测试环境验证优化效果
2. **监控指标**：持续监控内存、性能、稳定性
3. **渐进调整**：根据实际使用情况调整参数
4. **反馈问题**：遇到问题及时记录和报告
5. **定期检查**：定期查看统计信息优化配置

---

**文档版本**：1.0
**更新日期**：2026-02-14
