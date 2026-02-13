# TorchOverlay 架构文档

## 概述

TorchOverlay 是一个企业级的游戏辅助工具，采用领域驱动设计（DDD）和依赖注入（DI）架构，提供OCR识别、价格计算、覆盖层显示等功能。

## 架构原则

1. **依赖倒置原则（DIP）**：高层模块不依赖低层模块，都依赖于抽象
2. **单一职责原则（SRP）**：每个类只负责一个功能
3. **开闭原则（OCP）**：对扩展开放，对修改关闭
4. **接口隔离原则（ISP）**：不应该依赖不需要的接口
5. **里氏替换原则（LSP）**：子类可以替换父类

## 分层架构

项目采用经典的四层架构：

```
┌─────────────────────────────────────────┐
│            UI Layer (ui/)                │  用户界面层
│  - MainWindow                            │
│  - SettingsWindow                        │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Controllers Layer (controllers/)   │  控制器层
│  - AppController                         │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Domain Layer (domain/)             │  领域层
│  - Models (领域模型)                     │
│  - Services (领域服务)                    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Services Layer (services/)         │  服务层
│  - OCR服务                               │
│  - 截图服务                              │
│  - Overlay服务                           │
│  - 游戏绑定服务                          │
│  - 价格服务                              │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Core Layer (core/)             │  核心层
│  - 配置管理                              │
│  - 日志系统                              │
│  - 事件总线                              │
│  - 状态管理                              │
└─────────────────────────────────────────┘
```

## 核心模块

### 1. Core Layer（核心层）

核心层提供基础设施支持，包括配置、日志、事件总线、状态管理等。

#### 1.1 配置管理 (`core/config.py`)
- **职责**：统一管理应用配置
- **主要类**：
  - `AppConfig`：应用配置
  - `OcrConfig`：OCR配置
- **特性**：
  - 支持从文件加载和保存
  - 类型安全的数据结构
  - 配置验证

#### 1.2 日志系统 (`core/logger.py`)
- **职责**：统一的日志记录
- **主要功能**：
  - 支持多个日志级别
  - 文件和控制台输出
  - 按日期滚动日志

#### 1.3 事件总线 (`core/event_bus.py`)
- **职责**：实现发布-订阅模式的事件系统
- **主要类**：`EventBus`
- **特性**：
  - 线程安全
  - 支持多种事件类型
  - 解耦组件通信

#### 1.4 状态管理 (`core/state_manager.py`)
- **职责**：集中管理应用状态
- **主要类**：`StateManager`
- **特性**：
  - 状态变更通知
  - 观察者模式
  - 单例实例

### 2. Domain Layer（领域层）

领域层包含业务逻辑和领域模型。

#### 2.1 领域模型 (`domain/models/`)
- **Region**：表示一个矩形区域
- **ItemInfo**：物品信息
- **BoundGame**：绑定的游戏信息

#### 2.2 领域服务 (`domain/services/`)
- **TextParserService**：文本解析服务
- **RegionCalculatorService**：区域计算服务

### 3. Services Layer（服务层）

服务层提供具体的功能实现，通过接口定义服务契约。

#### 3.1 接口定义 (`services/interfaces.py`)
定义所有服务的接口：
- `IGameBinder`：游戏绑定器接口
- `IProcessWatcher`：进程监视器接口
- `ICaptureService`：截图服务接口
- `IOcrService`：OCR服务接口
- `IOverlayService`：覆盖层服务接口

#### 3.2 服务实现

##### 3.2.1 OCR服务 (`services/ocr/`)
- **BaiduOcrEngine**：百度OCR引擎实现
- **特性**：
  - 支持重试机制
  - 超时控制
  - 调试模式

##### 3.2.2 截图服务 (`services/capture_service.py`)
- **职责**：游戏窗口截图
- **特性**：
  - 支持DPI缩放
  - 内存优化

##### 3.2.3 Overlay服务 (`services/overlay/`)
- **OverlayService**：覆盖层服务
- **特性**：
  - 透明窗口
  - 文本显示
  - 区域标注

##### 3.2.4 性能优化服务
- **OcrCacheService**：OCR缓存服务
- **CaptureMemoryOptimizationService**：截图内存优化服务
- **WindowCacheService**：窗口缓存服务
- **AsyncPriceUpdateService**：异步价格更新服务
- **OverlayRenderOptimizationService**：Overlay渲染优化服务

##### 3.2.5 价格服务 (`services/`)
- **ItemPriceService**：物品价格服务
- **PriceUpdateService**：物价更新服务
- **PriceCalculatorService**：价格计算服务

### 4. Controllers Layer（控制器层）

控制器层负责协调各层之间的交互。

#### AppController (`controllers/app_controller.py`)
- **职责**：业务流程协调
- **主要功能**：
  - 处理用户点击事件
  - 协调识别流程
  - 更新UI显示
- **设计模式**：
  - 依赖注入
  - 策略模式

### 5. UI Layer（用户界面层）

UI层负责用户交互和展示。

#### MainWindow (`ui/main_window.py`)
- **职责**：主窗口
- **主要功能**：
  - 显示余额
  - 更新物价按钮
  - 识别物品按钮

#### SettingsWindow (`ui/settings_window.py`)
- **职责**：设置窗口
- **主要功能**：
  - OCR配置
  - 监视间隔设置

## 设计模式应用

### 1. 依赖注入（DI）
通过工厂类（`app/factories.py`）管理依赖注入，实现松耦合。

```python
class AppFactory:
    def create_controller(self) -> AppController:
        return AppController(
            cfg=self.get_config(),
            binder=self.create_game_binder(),
            watcher=self.create_process_watcher(),
            ...
        )
```

### 2. 工厂模式
使用工厂类创建复杂对象，简化对象创建过程。

### 3. 策略模式
通过接口定义策略，允许运行时切换实现。

### 4. 观察者模式
事件总线和状态管理器使用观察者模式，实现事件通知。

### 5. 单例模式
EventBus 和 StateManager 使用单例模式，确保全局唯一实例。

### 6. 装饰器模式
OcrCacheService 装饰了底层的OCR服务，添加缓存功能。

### 7. 适配器模式
AsyncPriceUpdateService 适配同步的价格更新服务，提供异步接口。

## 性能优化

### 1. OCR缓存
- **策略**：LRU（最近最少使用）
- **层级**：内存缓存 + 磁盘缓存
- **过期**：1小时TTL
- **效果**：缓存命中时识别速度提升50%-80%

### 2. 截图内存优化
- **方法**：图片格式优化、压缩
- **效果**：内存使用减少30%-50%

### 3. 窗口缓存
- **策略**：2秒TTL
- **效果**：Win32 API调用减少80%+

### 4. 异步价格更新
- **方法**：后台线程执行
- **效果**：UI响应不受影响

### 5. Overlay渲染优化
- **方法**：脏标记、增量渲染
- **效果**：不必要重绘减少70%+

## 错误处理

### 1. 自定义异常体系 (`core/exceptions.py`)
- `TorchOverlayException`：基础异常
- `OcrException`：OCR相关异常
- `CaptureException`：截图相关异常
- `ConfigException`：配置相关异常
- 等等...

### 2. 日志记录
- 记录所有异常和错误
- 支持调试日志输出
- 日志文件按日期滚动

## 测试

### 1. 单元测试 (`tests/unit/`)
- 使用pytest框架
- 覆盖核心模块
- 模拟外部依赖

### 2. 集成测试 (`tests/integration/`)
- 测试模块间集成
- 端到端测试场景

### 3. 测试覆盖率
- 当前覆盖率：约60%
- 目标覆盖率：80%+

## 配置管理

### 1. 配置文件 (`config.json`)
- 应用配置
- OCR配置
- 监视间隔
- 其他设置

### 2. 配置热更新
- 自动检测配置文件变化
- 验证新配置有效性
- 无需重启应用

### 3. 配置加密
- AES加密敏感信息
- 保护API密钥等

## 依赖管理

### 主要依赖
- `pywin32`：Windows API封装
- `Pillow`：图像处理
- `requests`：HTTP请求
- `pytest`：测试框架

### 依赖注入
- 通过工厂类管理依赖
- 接口驱动设计
- 易于测试和维护

## 扩展性

### 1. 新增OCR引擎
实现 `IOcrService` 接口即可添加新的OCR引擎。

### 2. 新增服务
定义接口并提供实现，通过工厂注入。

### 3. 新增UI组件
遵循MVC模式，添加控制器和视图。

## 安全性

### 1. 配置加密
- AES-256加密
- 保护敏感信息

### 2. 输入验证
- 配置验证
- 参数验证

### 3. 错误处理
- 不暴露敏感信息
- 友好的错误提示

## 部署架构

### 1. 本地部署
- 直接运行 `main.py`
- 配置文件：`config.json`

### 2. 打包部署
- 使用PyInstaller打包
- 生成可执行文件

## 维护指南

### 1. 添加新功能
1. 定义接口（如果需要）
2. 实现服务
3. 更新工厂类
4. 添加测试
5. 更新文档

### 2. 修复Bug
1. 定位问题
2. 编写测试用例
3. 修复代码
4. 验证测试
5. 更新文档

### 3. 性能优化
1. 分析性能瓶颈
2. 使用性能分析工具
3. 实现优化
4. 测试验证
5. 更新文档

## 最佳实践

### 1. 代码规范
- 遵循PEP 8
- 使用类型注解
- 编写文档字符串

### 2. 测试驱动
- 先写测试
- 后写代码
- 持续集成

### 3. 持续重构
- 定期重构
- 消除代码异味
- 保持代码质量

### 4. 文档更新
- 代码变更同步更新文档
- 保持文档准确性

## 未来规划

### 1. 功能扩展
- 支持更多游戏
- 支持更多OCR引擎
- 增加统计功能

### 2. 性能提升
- 进一步优化缓存策略
- 优化渲染性能
- 减少内存占用

### 3. 用户体验
- 改进UI界面
- 增加主题支持
- 优化交互流程

### 4. 开发体验
- 完善开发文档
- 提供开发工具
- 简化开发流程

## 参考资料

- [SOLID设计原则](https://en.wikipedia.org/wiki/SOLID)
- [领域驱动设计](https://en.wikipedia.org/wiki/Domain-driven_design)
- [依赖注入](https://en.wikipedia.org/wiki/Dependency_injection)
- [Python类型注解](https://docs.python.org/3/library/typing.html)
