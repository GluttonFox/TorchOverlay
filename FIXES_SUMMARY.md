# 问题修复总结

## 问题1: 多个缩进错误

### 描述
代码中存在多处 if/elif/else/except/finally 语句块只有注释，没有实际代码的情况，导致 IndentationError。

### 修复位置
1. **controllers/app_controller.py** (第111-113行) - `if` 块
2. **core/state_manager.py** (第134-136行) - `else` 块
3. **services/overlay/overlay_service.py** (第105-107行) - 内层 `if` 块
4. **services/ui_update_service.py** (第169-171行) - `except` 块
5. **services/game_log_parser_service.py** (第498-500行) - `if` 块
6. **services/game_log_parser_service.py** (第808-816行) - `else` 块
7. **services/game_log_parser_service.py** (第1147-1150行) - `except` 块
8. **services/game_log_parser_service.py** (第429-437行) - `EventContext()` 调用参数缩进错误

### 解决方案
在所有空的控制流语句块中添加 `pass` 语句，修正缩进错误。

---

## 问题2: 窗口不显示 - UI 附加时序问题

### 描述
程序启动后主窗口不显示。错误信息：
```
AttributeError: 'NoneType' object has no attribute 'set_bind_state'
```

### 根本原因
在 `MainWindow.__init__` 中使用了 `self.root.after(0, self._controller.on_window_shown)`，这会在窗口创建后立即调用 `on_window_shown()`。但此时 `controller.attach_ui(window)` 还没有执行，所以 `self._ui` 还是 `None`。

### 解决方案
将 `self.root.after(0, self._controller.on_window_shown)` 从 `__init__` 移到 `run()` 方法中，在 `mainloop()` 之前显式调用。

**修改前：**
```python
def __init__(self, cfg: AppConfig, controller):
    # ... 创建窗口组件 ...
    self.root.after(0, self._controller.on_window_shown)

def run(self):
    self.set_bind_state(None)
    self.root.mainloop()
```

**修改后：**
```python
def __init__(self, cfg: AppConfig, controller):
    # ... 创建窗口组件 ...

def run(self):
    self.set_bind_state(None)
    # 在 mainloop 之前调用 on_window_shown，确保 UI 已经附加
    if self._controller:
        self._controller.on_window_shown()
    self.root.mainloop()
```

---

## 问题3: 线程池管理器初始化导致程序卡死

### 描述
启用线程池管理器后，程序在初始化时卡死，没有任何输出。

### 根本原因
线程池管理器使用了单例模式和线程锁，在 `__new__` 方法中使用了双检锁模式：
```python
def __new__(cls, *args, **kwargs):
    if cls._instance is None:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
    return cls._instance
```

在某些情况下（可能与 logger 初始化、系统锁机制或其他未知因素），这段代码会导致程序卡死。具体原因需要进一步调查，可能涉及：
- Python 的 `__new__` 方法调用时机
- 线程锁的实现细节
- logger 的初始化过程

### 临时解决方案
在启动时禁用线程池管理器和内存监控：
```python
app = TorchOverlayApplication(enable_memory_monitor=False, enable_thread_pool=False)
```

### 长期解决方案（待实施）
1. 将管理器改为懒加载模式，只在真正需要时才初始化
2. 重构单例模式的实现，避免使用锁
3. 或者为这些优化功能提供更简单的实现

---

## 当前状态

✅ 程序可以正常启动并显示窗口
✅ 所有缩进错误已修复
✅ UI 附加时序问题已解决
⚠️ 线程池管理器和内存监控暂时禁用（避免启动卡死）

---

## 建议后续工作

1. **调查线程池管理器卡死问题**
   - 重新设计单例模式
   - 测试不同的线程锁实现
   - 或改用 `concurrent.futures` 的默认线程池

2. **考虑是否真的需要这些优化功能**
   - 检查代码中是否真的使用了线程池
   - 评估内存监控的必要性
   - 如果不需要，可以直接删除

3. **如果需要保留优化功能，采用懒加载模式**
   - 不要在应用启动时初始化
   - 在第一次使用时再创建
   - 这样可以避免启动时的问题

---

## 修改的文件列表

1. `main.py` - 禁用优化功能
2. `app/application.py` - 修复 UI 附加时序，清理调试代码
3. `ui/main_window.py` - 修复 UI 附加时序，清理调试代码
4. `controllers/app_controller.py` - 修复缩进错误
5. `core/state_manager.py` - 修复缩进错误
6. `services/overlay/overlay_service.py` - 修复缩进错误
7. `services/ui_update_service.py` - 修复缩进错误
8. `services/game_log_parser_service.py` - 修复多处缩进错误
9. `core/thread_pool_manager.py` - 添加调试代码（已清理）

---

## 测试结果

- ✅ 缩进错误全部修复，linter 显示 0 错误
- ✅ 窗口可以正常显示
- ✅ 程序可以正常运行
- ✅ 游戏窗口绑定功能正常
- ⚠️ 线程池管理器暂时禁用（需要进一步修复）
- ⚠️ 内存监控暂时禁用（需要进一步修复）
