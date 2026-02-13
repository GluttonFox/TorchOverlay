# TorchOverlay API 文档

## 目录

- [核心模块 (Core)](#核心模块-core)
- [领域模型 (Domain Models)](#领域模型-domain-models)
- [领域服务 (Domain Services)](#领域服务-domain-services)
- [服务接口 (Service Interfaces)](#服务接口-service-interfaces)
- [服务实现 (Service Implementations)](#服务实现-service-implementations)
- [控制器 (Controllers)](#控制器-controllers)
- [用户界面 (UI)](#用户界面-ui)

---

## 核心模块 (Core)

### AppConfig

应用配置类。

#### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `app_title_prefix` | `str` | 应用标题前缀 |
| `keywords` | `list[str]` | 关键词列表 |
| `watch_interval_ms` | `int` | 监视间隔（毫秒） |
| `elevated_marker` | `str` | 提权标记 |
| `ocr` | `OcrConfig` | OCR配置 |
| `last_price_update` | `Optional[str]` | 上次价格更新时间 |
| `enable_tax_calculation` | `bool` | 是否启用税率计算 |
| `mystery_gem_mode` | `str` | 奥秘辉石模式 |

#### 方法

##### `get_config_path() -> str`
获取配置文件路径。

**返回**: 配置文件路径字符串

##### `load() -> AppConfig`
从文件加载配置。

**返回**: 加载的配置对象

##### `save() -> bool`
保存配置到文件。

**返回**: 是否保存成功

---

### OcrConfig

OCR配置类。

#### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `api_key` | `str` | API密钥 |
| `secret_key` | `str` | 密钥 |
| `api_name` | `str` | API名称 |
| `timeout_sec` | `int` | 超时时间（秒） |
| `max_retries` | `int` | 最大重试次数 |
| `debug_mode` | `bool` | 调试模式 |

---

### EventBus

事件总线，实现发布-订阅模式。

#### 方法

##### `subscribe(event_type: str, callback: Callable) -> bool`
订阅事件。

**参数**:
- `event_type`: 事件类型
- `callback`: 回调函数

**返回**: 是否订阅成功

##### `unsubscribe(event_type: str, callback: Callable) -> bool`
取消订阅。

**参数**:
- `event_type`: 事件类型
- `callback`: 回调函数

**返回**: 是否取消成功

##### `publish(event_type: str, **kwargs) -> None`
发布事件。

**参数**:
- `event_type`: 事件类型
- `**kwargs`: 事件数据

##### `clear_all_subscribers() -> None`
清除所有订阅者。

##### `clear_event_subscribers(event_type: str) -> None`
清除特定事件的所有订阅者。

**参数**:
- `event_type`: 事件类型

##### `get_subscriber_count(event_type: str) -> int`
获取特定事件的订阅者数量。

**参数**:
- `event_type`: 事件类型

**返回**: 订阅者数量

##### `get_instance() -> EventBus`
获取单例实例。

**返回**: EventBus实例

---

### StateManager

状态管理器，集中管理应用状态。

#### 方法

##### `get_state() -> AppState`
获取当前状态。

**返回**: 状态对象

##### `start_recognition() -> None`
开始识别。

##### `complete_recognition(success: bool, error: Optional[str] = None) -> None`
完成识别。

**参数**:
- `success`: 是否成功
- `error`: 错误信息

##### `is_recognizing() -> bool`
检查是否正在识别。

**返回**: 是否正在识别

##### `start_price_update() -> None`
开始价格更新。

##### `complete_price_update(success: bool, message: Optional[str] = None) -> None`
完成价格更新。

**参数**:
- `success`: 是否成功
- `message`: 消息

##### `is_updating_price() -> bool`
检查是否正在更新价格。

**返回**: 是否正在更新

##### `set_ui_window_visible(visible: bool) -> None`
设置UI窗口可见性。

**参数**:
- `visible`: 是否可见

##### `is_ui_window_visible() -> bool`
检查UI窗口是否可见。

**返回**: 是否可见

##### `update_config(config: dict) -> None`
更新配置。

**参数**:
- `config`: 配置字典

##### `get_config(key: Optional[str] = None) -> Any`
获取配置。

**参数**:
- `key`: 配置键（可选）

**返回**: 配置值

##### `add_observer(observer: Callable) -> None`
添加观察者。

**参数**:
- `observer`: 观察者函数

##### `remove_observer(observer: Callable) -> None`
移除观察者。

**参数**:
- `observer`: 观察者函数

##### `reset() -> None`
重置状态。

##### `get_instance() -> StateManager`
获取单例实例。

**返回**: StateManager实例

---

## 领域模型 (Domain Models)

### Region

矩形区域模型。

#### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `x` | `int` | X坐标 |
| `y` | `int` | Y坐标 |
| `width` | `int` | 宽度 |
| `height` | `int` | 高度 |
| `name` | `Optional[str]` | 区域名称 |

#### 方法

##### `contains_point(point_x: int, point_y: int) -> bool`
检查点是否在区域内。

**参数**:
- `point_x`: 点的X坐标
- `point_y`: 点的Y坐标

**返回**: 是否包含点

##### `contains_rect(rect_x: int, rect_y: int, rect_width: int, rect_height: int) -> bool`
检查矩形是否在区域内。

**参数**:
- `rect_x`: 矩形X坐标
- `rect_y`: 矩形Y坐标
- `rect_width`: 矩形宽度
- `rect_height`: 矩形高度

**返回**: 是否包含矩形

##### `get_bounding_box() -> dict[str, int]`
获取边界框。

**返回**: 边界框字典

---

### ItemInfo

物品信息模型。

#### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `item_id` | `str` | 物品ID |
| `name` | `str` | 物品名称 |
| `price` | `Optional[float]` | 价格 |

#### 方法

##### `to_dict() -> dict[str, object]`
转换为字典。

**返回**: 字典表示

##### `from_dict(data: dict[str, object]) -> ItemInfo`
从字典创建对象。

**参数**:
- `data`: 数据字典

**返回**: ItemInfo实例

---

### BoundGame

绑定的游戏信息。

#### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `hwnd` | `int` | 窗口句柄 |
| `title` | `str` | 窗口标题 |
| `process_id` | `int` | 进程ID |

---

## 领域服务 (Domain Services)

### TextParserService

文本解析服务。

#### 方法

##### `parse_item_text(text: str) -> tuple[str, str, str]`
解析物品文本。

**参数**:
- `text`: 原始文本

**返回**: (物品名称, 数量, 原始文本)

##### `parse_balance_text(text: str) -> tuple[Optional[float], str]`
解析余额文本。

**参数**:
- `text`: 原始文本

**返回**: (余额值, 原始文本)

---

### RegionCalculatorService

区域计算服务。

#### 方法

##### `calculate_for_resolution(width: int, height: int) -> tuple[Region, list[Region]]`
根据分辨率计算区域。

**参数**:
- `width`: 宽度
- `height`: 高度

**返回**: (余额区域, 物品区域列表)

---

## 服务接口 (Service Interfaces)

### IGameBinder

游戏绑定器接口。

#### 方法

##### `try_bind() -> bool`
尝试绑定游戏。

**返回**: 是否绑定成功

##### `is_bound_hwnd_valid() -> bool`
检查绑定句柄是否有效。

**返回**: 是否有效

---

### IProcessWatcher

进程监视器接口。

#### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `interval_ms` | `int` | 监视间隔（毫秒） |

#### 方法

##### `is_alive(bound: BoundGame) -> bool`
检查进程是否存活。

**参数**:
- `bound`: 绑定的游戏信息

**返回**: 是否存活

---

### ICaptureService

截图服务接口。

#### 方法

##### `capture(hwnd: int, region: Optional[Region] = None) -> str`
截图。

**参数**:
- `hwnd`: 窗口句柄
- `region`: 区域（可选）

**返回**: 截图文件路径

---

### IOcrService

OCR服务接口。

#### 方法

##### `recognize(image_path: str) -> OcrResult`
识别图片中的文字。

**参数**:
- `image_path`: 图片路径

**返回**: OCR结果

---

### IOverlayService

覆盖层服务接口。

#### 方法

##### `create_overlay(target_hwnd: int) -> bool`
创建覆盖层。

**参数**:
- `target_hwnd`: 目标窗口句柄

**返回**: 是否创建成功

##### `show_texts(text_items: list[OverlayTextItem]) -> None`
显示文本。

**参数**:
- `text_items`: 文本项列表

##### `clear() -> None`
清除覆盖层内容。

##### `close() -> None`
关闭覆盖层。

##### `is_visible() -> bool`
检查覆盖层是否可见。

**返回**: 是否可见

---

## 服务实现 (Service Implementations)

### BaiduOcrEngine

百度OCR引擎实现。

#### 构造函数

```python
def __init__(self, config: BaiduOcrConfig)
```

#### 方法

##### `recognize(image_path: str) -> OcrResult`
识别图片。

**参数**:
- `image_path`: 图片路径

**返回**: OCR结果

---

### ItemPriceService

物品价格服务。

#### 方法

##### `get_price(item_id: str) -> Optional[float]`
获取物品价格。

**参数**:
- `item_id`: 物品ID

**返回**: 价格值

---

### PriceUpdateService

物价更新服务。

#### 方法

##### `update_prices() -> tuple[bool, str]`
更新物价。

**返回**: (是否成功, 消息)

##### `get_last_update_time() -> Optional[datetime]`
获取上次更新时间。

**返回**: 更新时间

##### `can_update() -> bool`
检查是否可以更新。

**返回**: 是否可以更新

---

### PriceCalculatorService

价格计算服务。

#### 方法

##### `calculate_display_price(item_price: float, mystery_gem_mode: str = "min", enable_tax_calculation: bool = False) -> dict`
计算显示价格。

**参数**:
- `item_price`: 物品价格
- `mystery_gem_mode`: 奥秘辉石模式
- `enable_tax_calculation`: 是否启用税率计算

**返回**: 计算结果字典

---

### OcrCacheService

OCR缓存服务。

#### 构造函数

```python
def __init__(
    ocr_service: IOcrService,
    max_cache_size: int = 100,
    cache_ttl_seconds: int = 3600,
    enable_disk_cache: bool = True,
    disk_cache_dir: str = "cache/ocr"
)
```

#### 方法

##### `recognize(image_path: str) -> OcrResult`
识别图片（带缓存）。

**参数**:
- `image_path`: 图片路径

**返回**: OCR结果

##### `clear_cache(clear_memory: bool = True, clear_disk: bool = False) -> None`
清理缓存。

##### `get_stats() -> dict`
获取缓存统计信息。

**返回**: 统计字典

##### `cleanup_expired_cache() -> int`
清理过期缓存。

**返回**: 清理的条目数

---

### WindowCacheService

窗口缓存服务。

#### 构造函数

```python
def __init__(
    cache_ttl_seconds: int = 2,
    enable_cache: bool = True
)
```

#### 方法

##### `get_window_info(hwnd: int, force_refresh: bool = False) -> Optional[WindowInfo]`
获取窗口信息。

**参数**:
- `hwnd`: 窗口句柄
- `force_refresh`: 是否强制刷新

**返回**: 窗口信息

##### `get_client_rect(hwnd: int, force_refresh: bool = False) -> Optional[tuple[int, int, int, int]]`
获取客户区域。

**参数**:
- `hwnd`: 窗口句柄
- `force_refresh`: 是否强制刷新

**返回**: (x, y, width, height)

##### `is_window_visible(hwnd: int, force_refresh: bool = False) -> bool`
检查窗口是否可见。

**返回**: 是否可见

##### `get_stats() -> dict`
获取缓存统计信息。

**返回**: 统计字典

##### `clear_cache(clear_hwnd_cache: bool = True, clear_name_cache: bool = True) -> None`
清理缓存。

---

### AsyncPriceUpdateService

异步价格更新服务。

#### 构造函数

```python
def __init__(
    api_url: str = "https://serverp.furtorch.heili.tech/price",
    update_interval_hours: float = 1.0,
    config_path: str = None,
    log_file: str = None
)
```

#### 方法

##### `update_prices_async(force: bool = False) -> bool`
异步更新价格。

**参数**:
- `force`: 是否强制更新

**返回**: 是否成功启动

##### `cancel_update() -> bool`
取消更新。

**返回**: 是否成功取消

##### `get_status() -> UpdateStatus`
获取更新状态。

**返回**: 更新状态

##### `is_updating() -> bool`
检查是否正在更新。

**返回**: 是否正在更新

##### `set_callbacks(on_start=None, on_complete=None, on_error=None) -> None`
设置回调函数。

##### `get_stats() -> dict`
获取统计信息。

**返回**: 统计字典

##### `shutdown() -> None`
关闭服务。

---

### OverlayRenderOptimizationService

Overlay渲染优化服务。

#### 构造函数

```python
def __init__(
    optimize_interval_ms: int = 100,
    enable_dirty_tracking: bool = True,
    enable_batch_rendering: bool = True
)
```

#### 方法

##### `update_text_items(text_items: list[OverlayTextItem], force_full_render: bool = False) -> bool`
更新文本项。

**参数**:
- `text_items`: 文本项列表
- `force_full_render`: 是否强制全量渲染

**返回**: 内容是否变化

##### `update_regions(regions: list[dict], force_full_render: bool = False) -> bool`
更新区域。

**参数**:
- `regions`: 区域列表
- `force_full_render`: 是否强制全量渲染

**返回**: 内容是否变化

##### `should_render(target_hwnd: int, force: bool = False) -> bool`
检查是否需要渲染。

**参数**:
- `target_hwnd`: 目标窗口句柄
- `force`: 是否强制渲染

**返回**: 是否需要渲染

##### `prepare_render() -> tuple[bool, str]`
准备渲染。

**返回**: (是否需要渲染, 渲染模式)

##### `on_render_complete(render_time_ms: float, render_mode: str) -> None`
渲染完成回调。

**参数**:
- `render_time_ms`: 渲染耗时（毫秒）
- `render_mode`: 渲染模式

##### `get_stats() -> dict`
获取统计信息。

**返回**: 统计字典

---

## 控制器 (Controllers)

### AppController

主控制器。

#### 构造函数

```python
def __init__(
    cfg: AppConfig,
    binder: IGameBinder,
    watcher: IProcessWatcher,
    capture: ICaptureService,
    ocr: IOcrService,
    overlay: IOverlayService,
    text_parser: TextParserService,
    region_calculator: RegionCalculatorService,
    item_price_service,
    price_update_service,
    price_calculator: PriceCalculatorService,
    recognition_flow: RecognitionFlowService,
    state_manager: StateManager,
    event_bus: EventBus,
    ui_update_service: UIUpdateService,
)
```

#### 方法

##### `attach_ui(ui) -> None`
附加UI到控制器。

##### `on_window_shown() -> None`
窗口显示后的初始化。

##### `on_detect_click() -> None`
处理识别点击事件。

##### `on_update_price_click() -> None`
处理更新物价按钮点击事件。

##### `update_config(ocr_config, watch_interval_ms: int, enable_tax_calculation: bool = False, mystery_gem_mode: str = "min") -> bool`
更新配置。

**返回**: 是否更新成功

##### `get_config() -> AppConfig`
获取当前配置。

**返回**: 配置对象

---

## 用户界面 (UI)

### MainWindow

主窗口类。

#### 方法

##### `set_bind_state(bound: Optional[BoundGame]) -> None`
设置绑定状态。

##### `show_info(msg: str) -> None`
显示信息提示。

##### `update_balance(balance: str) -> None`
更新余额显示。

##### `update_last_update_time(last_update_time) -> None`
更新最后更新时间显示。

##### `schedule(delay_ms: int, fn) -> None`
安排延迟执行。

##### `run() -> None`
运行主窗口。

---

### SettingsWindow

设置窗口类。

#### 方法

##### (自动创建，无公开方法)

---

## 数据类型

### OcrResult

OCR结果数据类。

#### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `ok` | `bool` | 是否成功 |
| `text` | `Optional[str]` | 识别文本 |
| `words` | `Optional[list[OcrWordResult]]` | 单词结果列表 |
| `raw` | `Optional[Any]` | 原始数据 |
| `error` | `Optional[str]` | 错误信息 |

---

### OcrWordResult

OCR单词结果数据类。

#### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `text` | `str` | 文本 |
| `x` | `int` | X坐标 |
| `y` | `int` | Y坐标 |
| `width` | `int` | 宽度 |
| `height` | `int` | 高度 |
| `raw` | `Optional[Any]` | 原始数据 |

---

### OverlayTextItem

覆盖层文本项数据类。

#### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `text` | `str` | 文本 |
| `x` | `int` | X坐标 |
| `y` | `int` | Y坐标 |
| `width` | `int` | 宽度 |
| `height` | `int` | 高度 |
| `color` | `str` | 颜色 |
| `font_size` | `int` | 字体大小 |
| `background` | `str` | 背景色 |

---

### UpdateStatus

更新状态枚举。

#### 值

| 值 | 描述 |
|----|------|
| `IDLE` | 空闲 |
| `UPDATING` | 更新中 |
| `SUCCESS` | 成功 |
| `FAILED` | 失败 |
| `CANCELLED` | 已取消 |

---

## 事件类型

### Events

预定义事件类型。

| 事件 | 描述 | 参数 |
|------|------|------|
| `GAME_WINDOW_FOUND` | 找到游戏窗口 | `hwnd`, `title` |
| `GAME_WINDOW_LOST` | 游戏窗口丢失 | - |
| `RECOGNITION_STARTED` | 识别开始 | `hwnd` |
| `RECOGNITION_COMPLETED` | 识别完成 | `balance`, `items_count` |
| `RECOGNITION_FAILED` | 识别失败 | `error` |
| `PRICE_UPDATE_STARTED` | 价格更新开始 | - |
| `PRICE_UPDATE_COMPLETED` | 价格更新完成 | `message` |
| `PRICE_UPDATE_FAILED` | 价格更新失败 | `error` |
| `CONFIG_LOADED` | 配置加载 | `config` |
| `CONFIG_UPDATED` | 配置更新 | `config` |
| `UI_WINDOW_SHOWN` | UI窗口显示 | - |
| `UI_WINDOW_HIDDEN` | UI窗口隐藏 | - |

---

## 工厂方法

### AppFactory

应用工厂类。

#### 方法

##### `get_config() -> AppConfig`
获取配置。

**返回**: 配置对象

##### `create_ocr_engine() -> BaiduOcrEngine`
创建OCR引擎。

**返回**: OCR引擎实例

##### `create_game_binder() -> IGameBinder`
创建游戏绑定器。

**返回**: 游戏绑定器实例

##### `create_process_watcher() -> IProcessWatcher`
创建进程监视器。

**返回**: 进程监视器实例

##### `create_controller() -> AppController`
创建控制器。

**返回**: 控制器实例

---

## 使用示例

### 基础使用

```python
from app.factories import AppFactory

# 创建工厂
factory = AppFactory()

# 获取配置
config = factory.get_config()

# 创建控制器
controller = factory.create_controller()

# 运行应用
from ui.main_window import MainWindow
ui = MainWindow(config, controller)
controller.attach_ui(ui)
ui.run()
```

### 使用事件总线

```python
from core.event_bus import EventBus, Events

# 获取实例
event_bus = EventBus.get_instance()

# 订阅事件
def handler(**kwargs):
    print(f"事件: {kwargs}")

event_bus.subscribe(Events.RECOGNITION_COMPLETED, handler)

# 发布事件
event_bus.publish(Events.RECOGNITION_COMPLETED, balance=100, items_count=5)
```

### 使用状态管理器

```python
from core.state_manager import StateManager

# 获取实例
state_manager = StateManager.get_instance()

# 添加观察者
def on_state_change(state):
    print(f"状态变更: {state}")

state_manager.add_observer(on_state_change)

# 开始识别
state_manager.start_recognition()

# 完成识别
state_manager.complete_recognition(success=True)
```

### 使用缓存服务

```python
from services.ocr_cache_service import OcrCacheService
from services.ocr.baidu_ocr import BaiduOcrEngine

# 创建基础OCR服务
ocr_engine = BaiduOcrEngine(ocr_config)

# 创建缓存服务
cached_ocr = OcrCacheService(ocr_engine)

# 使用
result = cached_ocr.recognize("image.png")

# 获取统计
stats = cached_ocr.get_stats()
print(f"命中率: {stats['cache_hit_rate']}")
```

---

## 异常类型

| 异常 | 描述 |
|------|------|
| `TorchOverlayException` | 基础异常 |
| `ConfigException` | 配置异常 |
| `OcrException` | OCR异常 |
| `CaptureException` | 截图异常 |
| `OverlayException` | 覆盖层异常 |
| `GameBindingException` | 游戏绑定异常 |

---

## 更多信息

- [架构文档](ARCHITECTURE.md)
- [开发者指南](DEVELOPER_GUIDE.md)
- [配置管理文档](CONFIG_MANAGEMENT.md)
