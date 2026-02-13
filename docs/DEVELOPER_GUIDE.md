# TorchOverlay 开发者指南

## 目录

- [快速开始](#快速开始)
- [开发环境搭建](#开发环境搭建)
- [项目结构](#项目结构)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [测试指南](#测试指南)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)

## 快速开始

### 前置要求

- Python 3.9+
- Windows 10/11
- Git

### 安装步骤

1. **克隆仓库**
```bash
git clone <repository-url>
cd TorchOverlay
```

2. **创建虚拟环境**
```bash
python -m venv venv
venv\Scripts\activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置应用**
```bash
cp config.json.example config.json
# 编辑 config.json 填入配置信息
```

5. **运行应用**
```bash
python main.py
```

## 开发环境搭建

### 推荐IDE

- **PyCharm**：功能强大的Python IDE
- **VS Code**：轻量级，插件丰富
- **Sublime Text**：快速、简洁

### 必需插件

- **Python**：Python语言支持
- **Pylance**：代码提示和错误检查
- **Python Test Explorer**：测试支持
- **GitLens**：Git集成

### 环境变量

创建 `.env` 文件（可选）：

```env
# 调试模式
DEBUG=True

# 日志级别
LOG_LEVEL=DEBUG

# 测试环境
TESTING=False
```

## 项目结构

```
TorchOverlay/
├── app/                    # 应用启动和工厂
│   ├── application.py      # 应用入口
│   ├── container.py       # 依赖注入容器
│   └── factories.py       # 工厂类
├── controllers/           # 控制器层
│   └── app_controller.py  # 主控制器
├── core/                  # 核心层
│   ├── config.py         # 配置管理
│   ├── event_bus.py      # 事件总线
│   ├── logger.py         # 日志系统
│   └── state_manager.py  # 状态管理
├── domain/               # 领域层
│   ├── models/           # 领域模型
│   └── services/         # 领域服务
├── services/             # 服务层
│   ├── interfaces.py     # 服务接口
│   ├── ocr/             # OCR服务
│   ├── overlay/         # Overlay服务
│   └── ...              # 其他服务
├── ui/                   # 用户界面层
│   ├── main_window.py   # 主窗口
│   └── settings_window.py # 设置窗口
├── tests/                # 测试
│   ├── unit/           # 单元测试
│   └── integration/    # 集成测试
├── docs/                # 文档
├── examples/            # 示例代码
├── logs/                # 日志文件
├── config.json          # 配置文件
├── requirements.txt    # 依赖列表
└── main.py             # 程序入口
```

## 开发流程

### 1. 创建新功能

#### 步骤1：定义接口（如果需要）

在 `services/interfaces.py` 中定义新服务接口：

```python
class INewService(Protocol):
    def do_something(self, param: str) -> None:
        """执行某些操作"""
        ...
```

#### 步骤2：实现服务

在 `services/` 下创建服务实现：

```python
from core.logger import get_logger
from services.interfaces import INewService

logger = get_logger(__name__)

class NewService(INewService):
    def __init__(self, config=None):
        self._config = config

    def do_something(self, param: str) -> None:
        logger.info(f"执行操作: {param}")
        # 实现逻辑
        ...
```

#### 步骤3：更新工厂类

在 `app/factories.py` 中添加工厂方法：

```python
def create_new_service(self) -> INewService:
    """创建新服务"""
    return NewService(self.get_config())
```

#### 步骤4：集成到控制器

在 `controllers/app_controller.py` 中注入服务：

```python
def __init__(
    self,
    ...
    new_service: INewService,
):
    self._new_service = new_service
```

#### 步骤5：编写测试

创建测试文件 `tests/unit/test_new_service.py`：

```python
import unittest
from unittest.mock import Mock
from services.new_service import NewService

class TestNewService(unittest.TestCase):
    def setUp(self):
        self.service = NewService()

    def test_do_something(self):
        self.service.do_something("test")
        # 断言

if __name__ == '__main__':
    unittest.main()
```

#### 步骤6：更新文档

更新相关文档，说明新功能的使用方法。

### 2. 修改现有功能

#### 步骤1：理解现有代码
- 阅读相关文档
- 查看现有实现
- 运行现有测试

#### 步骤2：编写测试
- 为修改编写测试
- 确保测试通过

#### 步骤3：实现修改
- 遵循现有代码风格
- 保持接口稳定
- 添加必要的注释

#### 步骤4：验证测试
```bash
python -m pytest tests/
```

#### 步骤5：更新文档

### 3. 调试技巧

#### 使用日志

```python
from core.logger import get_logger

logger = get_logger(__name__)
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
```

#### 使用断点

在IDE中设置断点，使用调试器逐步执行。

#### 配置调试模式

在 `config.json` 中设置：
```json
{
  "ocr": {
    "debug_mode": true
  }
}
```

## 代码规范

### 命名规范

- **类名**：大驼峰命名（PascalCase）
  ```python
  class MyService:
  ```

- **函数名**：小写加下划线（snake_case）
  ```python
  def do_something():
  ```

- **常量**：全大写加下划线
  ```python
  MAX_CACHE_SIZE = 100
  ```

- **私有方法**：前缀下划线
  ```python
  def _private_method(self):
  ```

### 类型注解

**必须**为所有公开方法添加类型注解：

```python
def process_data(self, data: list[str]) -> dict[str, int]:
    """处理数据"""
    result = {}
    for item in data:
        result[item] = len(item)
    return result
```

### 文档字符串

**必须**为所有类和公开方法添加文档字符串：

```python
class MyService:
    """我的服务类

    这个类实现了某些功能。
    """

    def process_data(self, data: list[str]) -> dict[str, int]:
        """处理数据

        Args:
            data: 要处理的数据列表

        Returns:
            处理结果的字典
        """
        ...
```

### 导入顺序

```python
# 1. 标准库
import os
import time

# 2. 第三方库
from pywin32 import win32gui

# 3. 本地模块
from core.logger import get_logger
from services.interfaces import ISomeInterface
```

### 异常处理

```python
try:
    # 尝试执行的代码
    result = some_operation()
except SpecificError as e:
    # 处理特定异常
    logger.error(f"操作失败: {e}")
    raise
except Exception as e:
    # 处理其他异常
    logger.error(f"未知错误: {e}")
    raise
```

## 测试指南

### 运行测试

#### 运行所有测试
```bash
python -m pytest tests/
```

#### 运行单个测试文件
```bash
python -m pytest tests/unit/test_my_service.py
```

#### 运行单个测试用例
```bash
python -m pytest tests/unit/test_my_service.py::TestMyService::test_method
```

#### 查看测试覆盖率
```bash
python -m pytest --cov=services tests/
```

### 编写测试

#### 单元测试示例

```python
import unittest
from unittest.mock import Mock, patch
from services.my_service import MyService

class TestMyService(unittest.TestCase):
    def setUp(self):
        """测试前准备"""
        self.service = MyService()

    def tearDown(self):
        """测试后清理"""
        pass

    def test_method_success(self):
        """测试成功场景"""
        result = self.service.method()
        self.assertEqual(result, expected_value)

    def test_method_failure(self):
        """测试失败场景"""
        with self.assertRaises(ExpectedException):
            self.service.method()

    @patch('services.my_service.external_function')
    def test_method_with_mock(self, mock_func):
        """测试使用Mock"""
        mock_func.return_value = mock_value
        result = self.service.method()
        self.assertEqual(result, expected_value)

if __name__ == '__main__':
    unittest.main()
```

### 测试最佳实践

1. **命名清晰**：测试方法名应该描述测试的场景
2. **独立测试**：每个测试应该独立运行
3. **使用Mock**：模拟外部依赖
4. **测试边界**：测试正常和异常情况
5. **保持简单**：每个测试只测试一个功能

## 常见问题

### Q1: 如何添加新的OCR引擎？

**A**: 实现 `IOcrService` 接口：

```python
from services.interfaces import IOcrService

class MyOcrEngine(IOcrService):
    def recognize(self, image_path: str) -> OcrResult:
        # 实现识别逻辑
        pass
```

然后在工厂类中添加创建方法。

### Q2: 如何调试日志？

**A**: 配置日志级别和输出：

```python
import logging

# 设置日志级别
logging.getLogger().setLevel(logging.DEBUG)

# 或者配置文件中设置
```

### Q3: 如何处理配置变更？

**A**: 使用ConfigManager监听配置变化：

```python
from services.config_manager import ConfigManager

config = ConfigManager(
    config_path="config.json",
    enable_hot_reload=True
)

def on_config_change(new_config):
    # 处理配置变更
    pass

config.register_callback(on_config_change)
```

### Q4: 如何发布事件？

**A**: 使用EventBus发布事件：

```python
from core.event_bus import EventBus, Events

event_bus = EventBus.get_instance()

# 订阅事件
def on_recognition_completed(**kwargs):
    print(f"识别完成: {kwargs}")

event_bus.subscribe(Events.RECOGNITION_COMPLETED, on_recognition_completed)

# 发布事件
event_bus.publish(Events.RECOGNITION_COMPLETED, balance=100, items_count=5)
```

### Q5: 如何优化性能？

**A**: 使用内置的性能优化服务：

```python
from services.ocr_cache_service import OcrCacheService
from services.async_price_update_service import AsyncPriceUpdateService

# 使用OCR缓存
cached_ocr = OcrCacheService(ocr_service)

# 使用异步价格更新
async_updater = AsyncPriceUpdateService()
async_updater.update_prices_async()
```

## 贡献指南

### 提交规范

提交信息格式：
```
<type>(<scope>): <subject>

<body>

<footer>
```

类型（type）：
- `feat`: 新功能
- `fix`: 修复Bug
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 添加测试
- `chore`: 构建/工具链相关

示例：
```
feat(ocr): 添加新的OCR引擎支持

- 添加GoogleVisionEngine
- 更新工厂类
- 添加单元测试

Closes #123
```

### 代码审查

提交PR前检查：
- [ ] 代码符合规范
- [ ] 添加了测试
- [ ] 更新了文档
- [ ] 通过所有测试
- [ ] 没有lint错误

### 版本发布

版本号格式：`MAJOR.MINOR.PATCH`

- `MAJOR`: 不兼容的API修改
- `MINOR`: 向下兼容的功能新增
- `PATCH`: 向下兼容的问题修正

## 参考资源

- [Python官方文档](https://docs.python.org/3/)
- [PEP 8 - 代码风格](https://peps8.org/)
- [pytest文档](https://docs.pytest.org/)
- [SOLID原则](https://en.wikipedia.org/wiki/SOLID)

## 联系方式

如有问题，请提交Issue或联系维护者。

---

**祝您开发愉快！**
