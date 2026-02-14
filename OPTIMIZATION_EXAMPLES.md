# 优化功能使用示例

本文档提供详细的代码示例，展示如何使用优化后的功能。

## 目录

1. [配置管理](#配置管理)
2. [性能监控](#性能监控)
3. [资源管理](#资源管理)
4. [线程池](#线程池)
5. [内存监控](#内存监控)
6. [日志分析](#日志分析)
7. [综合示例](#综合示例)

---

## 配置管理

### 基础使用

```python
from core.config_access import get_config_access, get_config_value

# 获取配置访问器
config = get_config_access()

# 加载配置
app_config = config.load_config()

# 获取配置值（支持点分隔路径）
api_key = config.get("ocr.api_key", default="default_key")
timeout = config.get("ocr.timeout_sec", default=15.0)

# 设置配置值
config.set("ocr.api_key", "new_api_key")
config.set("ocr.timeout_sec", 30.0)

# 保存配置
config.save_config()
```

### 快捷方法

```python
from core.config_access import (
    get_ocr_api_key,
    set_ocr_api_key,
    get_ocr_timeout,
    set_ocr_timeout
)

# 获取快捷值
api_key = get_ocr_api_key()
timeout = get_ocr_timeout()

# 设置快捷值
set_ocr_api_key("your_api_key")
set_ocr_timeout(30.0)
```

### 配置监听

```python
from core.config_access import get_config_access

config = get_config_access()

def on_config_changed(new_config):
    print("配置已变更！")
    print(f"新超时: {new_config.ocr.timeout_sec}")

# 添加监听器
config.add_listener(on_config_changed)

# 修改配置会自动触发监听器
config.set("ocr.timeout_sec", 20.0)
```

### 完整示例

```python
class OcrService:
    def __init__(self):
        self.config = get_config_access()
        self.config.add_listener(self._on_config_change)

        # 初始加载配置
        self._load_config()

    def _load_config(self):
        self.api_key = self.config.get_ocr_api_key()
        self.timeout = self.config.get_ocr_timeout()
        print(f"加载配置: API Key={self.api_key[:10]}..., Timeout={self.timeout}s")

    def _on_config_change(self, new_config):
        print("配置已更新，重新加载...")
        self._load_config()

    def update_settings(self, new_key, new_timeout):
        self.config.set_ocr_api_key(new_key)
        self.config.set_ocr_timeout(new_timeout)
        self.config.save_config()

# 使用
service = OcrService()
service.update_settings("new_key", 30.0)
```

---

## 性能监控

### 记录指标

```python
from core.performance_monitor import get_performance_monitor

monitor = get_performance_monitor()

# 记录性能指标
monitor.record_metric(
    name="screenshot_time",
    value=125.5,
    unit="ms",
    category="capture"
)

monitor.record_metric(
    name="ocr_recognition_time",
    value=856.3,
    unit="ms",
    category="ocr"
)

monitor.record_metric(
    name="memory_usage",
    value=256.3,
    unit="MB",
    category="memory"
)

# 记录计数器
from core.performance_monitor import record_counter

record_counter("capture_success", 1, "capture")
record_counter("ocr_error", 1, "errors")
```

### 计时操作

```python
from core.performance_monitor import get_performance_monitor

monitor = get_performance_monitor()

# 开始计时
timer_id = monitor.start_timer("image_processing")

# 执行操作
result = process_image(image)

# 结束计时
elapsed = monitor.end_timer(timer_id, category="processing")
print(f"操作耗时: {elapsed:.3f}秒")
```

### 性能装饰器

```python
from core.performance_monitor import monitor_performance

@monitor_performance("ocr_recognition", "ocr")
def recognize_image(image_path):
    # 这个函数的性能会自动被监控
    result = ocr_service.recognize(image_path)
    return result

@monitor_performance("screenshot_capture", "capture")
def capture_screenshot(hwnd):
    # 这个函数的性能会自动被监控
    result = capture_service.capture(hwnd, "output.png")
    return result

# 使用
result = recognize_image("screenshot.png")
```

### 上下文管理器

```python
from core.performance_monitor import time_operation

monitor = get_performance_monitor()

# 使用上下文管理器
with time_operation("full_workflow"):
    # 复杂的工作流程
    image = capture_screenshot(hwnd)
    text = recognize_image(image)
    result = process_text(text)
    # 自动记录总耗时

print("工作流程完成！")
```

### 获取统计

```python
from core.performance_monitor import get_performance_monitor

monitor = get_performance_monitor()

# 获取指标列表
metrics = monitor.get_metrics("capture", "screenshot_time")
print(f"最近 {len(metrics)} 次截屏耗时:")
for m in metrics[:10]:
    print(f"  {m.value:.2f}ms")

# 获取统计信息
stats = monitor.get_stats("capture", "screenshot_time")
print(f"""
截图性能统计:
- 总次数: {stats['count']}
- 最快: {stats['min']:.2f}ms
- 最慢: {stats['max']:.2f}ms
- 平均: {stats['avg']:.2f}ms
- 中位数(P50): {stats['p50']:.2f}ms
- P95: {stats['p95']:.2f}ms
- P99: {stats['p99']:.2f}ms
""")

# 获取摘要
summary = monitor.get_summary()
for category, info in summary.items():
    print(f"{category}: {info['count']} 个指标")
```

### 完整示例

```python
class CaptureService:
    def __init__(self):
        self.monitor = get_performance_monitor()
        self.capture_count = 0

    def capture_image(self, hwnd):
        with time_operation("full_capture"):
            timer_id = self.monitor.start_timer("screenshot")

            try:
                # 截图
                result = self._do_capture(hwnd)

                # 记录成功计数
                from core.performance_monitor import record_counter
                record_counter("capture_success", category="capture")
                self.capture_count += 1

                return result
            finally:
                self.monitor.end_timer(timer_id, category="capture")

    def get_performance_report(self):
        stats = self.monitor.get_stats("capture", "full_capture_duration")
        return {
            'total_captures': self.capture_count,
            'avg_duration': stats['avg'],
            'p95_duration': stats['p95']
        }

# 使用
service = CaptureService()
result = service.capture_image(hwnd)
report = service.get_performance_report()
print(f"平均耗时: {report['avg_duration']:.2f}ms")
```

---

## 资源管理

### 手动管理

```python
from core.resource_manager import ResourceManager, get_resource_manager

# 获取资源管理器
rm = get_resource_manager()

# 获取图像资源
img = rm.acquire_image("screenshot.png", resource_id="my_screenshot")
if img:
    try:
        # 使用图像
        cropped = img.crop((0, 0, 100, 100))
        process(cropped)
    finally:
        # 释放资源
        rm.release_image(img, "my_screenshot")
```

### 上下文管理器（推荐）

```python
from core.resource_manager import managed_image

# 使用上下文管理器，自动释放资源
with managed_image("screenshot.png") as img:
    # 使用图像
    print(f"图像大小: {img.size}")
    cropped = img.crop((0, 0, 100, 100))
    process(cropped)
# 图像自动释放

# 多个图像
image_paths = ["img1.png", "img2.png", "img3.png"]
results = []

for path in image_paths:
    with managed_image(path) as img:
        result = process_image(img)
        results.append(result)
# 所有图像自动释放
```

### 批量处理

```python
from core.resource_manager import managed_image
from core.performance_monitor import time_operation
from core.performance_monitor import get_performance_monitor

monitor = get_performance_monitor()

def batch_process_images(image_paths):
    results = []

    with time_operation("batch_processing"):
        for i, path in enumerate(image_paths):
            # 使用上下文管理器
            with managed_image(path) as img:
                # 记录单个处理时间
                with time_operation(f"process_image_{i}"):
                    result = process_image(img)
                    results.append(result)

    return results

# 使用
paths = ["img1.png", "img2.png", "img3.png"]
results = batch_process_images(paths)
print(f"处理完成: {len(results)} 个图像")
```

---

## 线程池

### 提交任务

```python
from core.thread_pool_manager import get_thread_pool

pool = get_thread_pool()

def task_function(arg1, arg2):
    # 执行任务
    result = heavy_operation(arg1, arg2)
    return result

# 提交任务
task_id = pool.submit_task(
    task_function,
    "arg1_value",
    "arg2_value",
    task_id="my_task_123",
    timeout=30.0
)

print(f"任务已提交: {task_id}")
```

### 异步回调

```python
from core.thread_pool_manager import get_thread_pool

pool = get_thread_pool()

# 定义任务
def ocr_task(image_path):
    # 模拟耗时操作
    import time
    time.sleep(2)
    return f"OCR结果: {image_path}"

# 定义回调
def on_success(result):
    print(f"✅ 任务完成: {result}")

def on_error(exception):
    print(f"❌ 任务失败: {exception}")

# 提交任务并设置回调
task_id = pool.submit_task(
    ocr_task,
    "screenshot.png",
    task_id="ocr_task",
    callback=on_success,
    error_callback=on_error,
    timeout=60.0
)

print("任务正在后台运行...")
```

### 任务状态查询

```python
from core.thread_pool_manager import get_thread_pool

pool = get_thread_pool()

# 提交多个任务
task_ids = []
for i in range(5):
    task_id = pool.submit_task(
        lambda x: process_task(x),
        i,
        task_id=f"task_{i}"
    )
    task_ids.append(task_id)

# 查询状态
for task_id in task_ids:
    status = pool.get_task_status(task_id)
    print(f"{task_id}: {status['status']}")

# 获取统计
stats = pool.get_stats()
print(f"""
线程池统计:
- 总提交: {stats['total_submitted']}
- 已完成: {stats['total_completed']}
- 失败: {stats['total_failed']}
- 活动任务: {stats['pending_tasks']}
- 成功率: {stats['success_rate']}
""")
```

### 完整示例

```python
from core.thread_pool_manager import get_thread_pool
from core.performance_monitor import time_operation

pool = get_thread_pool()

class AsyncTaskManager:
    def __init__(self):
        self.pool = get_thread_pool()
        self.tasks = {}

    def start_task(self, task_name, task_func, *args):
        def on_complete(result):
            print(f"✅ {task_name} 完成: {result}")
            self.tasks[task_name] = {
                'status': 'completed',
                'result': result
            }

        def on_error(exception):
            print(f"❌ {task_name} 失败: {exception}")
            self.tasks[task_name] = {
                'status': 'failed',
                'error': str(exception)
            }

        # 提交任务
        with time_operation(f"submit_{task_name}"):
            task_id = self.pool.submit_task(
                task_func,
                *args,
                task_id=task_name,
                callback=on_complete,
                error_callback=on_error
            )

        return task_id

    def wait_all(self, timeout=60.0):
        """等待所有任务完成"""
        import time
        start_time = time.time()

        while True:
            stats = self.pool.get_stats()
            if stats['pending_tasks'] == 0:
                print("所有任务已完成")
                break

            if time.time() - start_time > timeout:
                print("等待超时")
                break

            time.sleep(1)

        return self.tasks

# 使用
manager = AsyncTaskManager()

# 启动多个异步任务
manager.start_task("task1", lambda: process_data("data1"))
manager.start_task("task2", lambda: process_data("data2"))
manager.start_task("task3", lambda: process_data("data3"))

# 等待所有完成
results = manager.wait_all()
```

---

## 内存监控

### 基础使用

```python
from core.memory_monitor import get_memory_monitor, MemoryMonitor

# 创建并启动监控
monitor = get_memory_monitor()

# 设置阈值
monitor = MemoryMonitor(
    warning_threshold_mb=500.0,
    critical_threshold_mb=1000.0,
    check_interval=10.0,
    auto_cleanup_on_warning=True
)

# 启动监控
monitor.start()

# 查询当前状态
current_usage = monitor.get_current_usage()
peak_usage = monitor.get_peak_usage()

print(f"当前内存: {current_usage:.2f}MB")
print(f"峰值内存: {peak_usage:.2f}MB")
```

### 回调处理

```python
from core.memory_monitor import MemoryMonitor

def on_warning(usage_mb):
    print(f"⚠️  内存警告: {usage_mb:.2f}MB")
    # 可以触发清理
    from core.resource_manager import cleanup_all_resources
    cleanup_all_resources()

def on_critical(usage_mb):
    print(f"🔴 严重警告: {usage_mb:.2f}MB")
    # 发送通知
    send_alert(f"内存严重不足: {usage_mb:.2f}MB")
    # 强制清理
    from core.resource_manager import cleanup_all_resources
    cleanup_all_resources()

def on_recovery(usage_mb):
    print(f"✅ 内存恢复: {usage_mb:.2f}MB")

# 设置回调
monitor = MemoryMonitor(
    warning_threshold_mb=500.0,
    critical_threshold_mb=1000.0
)

monitor.set_callbacks(
    on_warning=on_warning,
    on_critical=on_critical,
    on_recovery=on_recovery
)

monitor.start()
```

### 完整示例

```python
from core.memory_monitor import MemoryMonitor
from core.performance_monitor import time_operation

class MemoryAwareService:
    def __init__(self):
        self.monitor = MemoryMonitor(
            warning_threshold_mb=500.0,
            critical_threshold_mb=1000.0,
            check_interval=10.0,
            auto_cleanup_on_warning=True
        )

        # 设置回调
        self.monitor.set_callbacks(
            on_warning=self._on_warning,
            on_critical=self._on_critical,
            on_recovery=self._on_recovery
        )

    def _on_warning(self, usage_mb):
        print(f"内存警告: {usage_mb:.2f}MB")
        # 记录指标
        from core.performance_monitor import get_performance_monitor
        monitor = get_performance_monitor()
        monitor.record_metric(
            "memory_warning",
            usage_mb,
            "MB",
            "memory"
        )

    def _on_critical(self, usage_mb):
        print(f"内存严重: {usage_mb:.2f}MB")
        # 触发紧急清理
        from core.resource_manager import get_resource_manager
        rm = get_resource_manager()
        released = rm.release_all_resources()
        print(f"释放了 {released} 个资源")

    def start(self):
        print("启动服务...")
        self.monitor.start()

    def stop(self):
        print("停止服务...")
        self.monitor.stop()

    def process_large_data(self, data):
        with time_operation("process_data"):
            # 如果内存过高，会自动清理
            return process(data)

# 使用
service = MemoryAwareService()
service.start()
try:
    result = service.process_large_data(large_dataset)
finally:
    service.stop()
```

---

## 日志分析

### 基础使用

```python
from core.log_analyzer import analyze_logs, analyze_and_export

# 分析日志
report = analyze_logs(log_dir="logs", max_files=10)

# 查看摘要
print(f"日志条目总数: {report['summary']['total_entries']}")
print(f"问题总数: {report['summary']['total_issues']}")
print(f"错误数: {report['summary']['error_count']}")
print(f"警告数: {report['summary']['warning_count']}")

# 查看问题详情
for severity in ['ERROR', 'WARNING', 'INFO']:
    issues = report['issues_by_severity'].get(severity, [])
    if issues:
        print(f"\n{severity} 问题:")
        for issue in issues:
            print(f"  - {issue['category']}: {issue['message']} ({issue['count']}次)")
            for suggestion in issue['suggestions'][:2]:
                print(f"    建议: {suggestion}")
```

### 导出报告

```python
from core.log_analyzer import analyze_and_export

# 分析并导出报告
analyze_and_export(
    log_dir="logs",
    output_path="log_analysis_report.md",
    max_files=10
)

print("日志分析报告已生成: log_analysis_report.md")
```

### 定期分析

```python
import schedule
from core.log_analyzer import analyze_and_export

def run_daily_analysis():
    """每天运行一次日志分析"""
    print("执行每日日志分析...")
    try:
        analyze_and_export(
            log_dir="logs",
            output_path=f"daily_reports/report_{get_date_str()}.md"
        )
        print("日志分析完成")
    except Exception as e:
        print(f"日志分析失败: {e}")

# 设置定时任务
schedule.every().day.at("02:00").do(run_daily_analysis)

print("日志分析调度器已启动，每天02:00运行")
while True:
    schedule.run_pending()
    schedule.sleep(3600)  # 每小时检查一次
```

---

## 综合示例

### 完整的应用服务

```python
from core.config_access import get_config_access
from core.performance_monitor import get_performance_monitor, time_operation
from core.resource_manager import managed_image
from core.thread_pool_manager import get_thread_pool
from core.memory_monitor import MemoryMonitor

class OptimizedApplicationService:
    """优化后的应用服务"""

    def __init__(self):
        # 初始化各种管理器
        self.config = get_config_access()
        self.perf_monitor = get_performance_monitor()
        self.thread_pool = get_thread_pool()

        # 内存监控
        self.memory_monitor = MemoryMonitor(
            warning_threshold_mb=self.config.get("memory.warning_mb", 500.0),
            critical_threshold_mb=self.config.get("memory.critical_mb", 1000.0)
        )

        # 设置内存监控回调
        self.memory_monitor.set_callbacks(
            on_warning=self._on_memory_warning,
            on_critical=self._on_memory_critical
        )

    def start(self):
        """启动服务"""
        print("启动优化应用服务...")
        self.memory_monitor.start()
        print("✅ 内存监控已启动")

    def stop(self):
        """停止服务"""
        print("停止优化应用服务...")
        self.memory_monitor.stop()
        self.thread_pool.shutdown()
        print("✅ 服务已停止")

    def _on_memory_warning(self, usage_mb):
        """内存警告回调"""
        print(f"⚠️  内存警告: {usage_mb:.2f}MB")
        # 记录指标
        self.perf_monitor.record_metric(
            "memory_warning",
            usage_mb,
            "MB",
            "memory"
        )

    def _on_memory_critical(self, usage_mb):
        """内存严重回调"""
        print(f"🔴  内存严重: {usage_mb:.2f}MB")
        # 自动清理
        from core.resource_manager import get_resource_manager
        rm = get_resource_manager()
        released = rm.release_all_resources()
        print(f"清理了 {released} 个资源")

    def process_image_async(self, image_path, callback):
        """异步处理图像"""

        def task_func():
            with managed_image(image_path) as img:
                with time_operation("image_processing"):
                    result = self._process_image(img)
                    return result

        def on_success(result):
            print(f"✅ 图像处理完成: {image_path}")
            callback(result)

        def on_error(exception):
            print(f"❌ 图像处理失败: {exception}")

        # 提交任务
        self.thread_pool.submit_task(
            task_func,
            task_id=f"process_{image_path}",
            callback=on_success,
            error_callback=on_error
        )

    def _process_image(self, img):
        """实际图像处理"""
        # 这里实现你的图像处理逻辑
        # 示例：调整大小、OCR识别等
        return f"处理结果: {img.size}"

    def get_performance_stats(self):
        """获取性能统计"""
        capture_stats = self.perf_monitor.get_stats("capture")
        memory_stats = self.perf_monitor.get_stats("memory")

        return {
            'capture': capture_stats,
            'memory': memory_stats
        }

# 使用示例
if __name__ == "__main__":
    service = OptimizedApplicationService()
    service.start()

    try:
        # 异步处理图像
        def on_complete(result):
            print(f"最终结果: {result}")

        service.process_image_async("screenshot.png", on_complete)

        # 等待完成
        import time
        time.sleep(5)

        # 获取性能统计
        stats = service.get_performance_stats()
        print(f"\n性能统计:")
        print(f"截图: {stats['capture']}")
        print(f"内存: {stats['memory']}")

    finally:
        service.stop()
```

---

## 总结

本文档展示了优化后的各种功能的使用方法：

- ✅ **配置管理**：简化、高效、监听
- ✅ **性能监控**：指标收集、统计分析
- ✅ **资源管理**：自动释放、上下文管理
- ✅ **线程池**：异步任务、状态追踪
- ✅ **内存监控**：实时监控、自动预警
- ✅ **日志分析**：问题识别、优化建议

通过合理使用这些工具，可以：
- 📉 大幅提升代码质量
- 📉 有效控制内存使用
- 📉 精确监控性能指标
- 📉 快速定位和解决问题
- 📉 实现企业级可维护性

---

**文档版本**：1.0
**更新日期**：2026-02-14
