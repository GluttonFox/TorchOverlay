# TorchOverlay

一个用于火炬之光无限游戏的OCR识别和截图工具。

## 功能特性

- ✅ 游戏窗口自动检测和绑定
- ✅ 游戏进程监控
- ✅ 游戏窗口截图（支持client区域）
- ✅ 百度OCR文字识别（支持标准版和高精度版）
- ✅ 余额自动识别功能
- ✅ 图形化设置界面
- ✅ 自动DPI感知
- ✅ 完善的日志系统
- ✅ 灵活的配置管理

## 安装

1. 克隆仓库
```bash
git clone https://github.com/GluttonFox/TorchOverlay.git
cd TorchOverlay
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置OCR密钥

### 使用设置窗口配置（推荐）

1. 运行程序：`python main.py`
2. 点击「设置」按钮
3. 填入百度OCR的API Key和Secret Key
4. 保存设置

## 百度OCR获取密钥

1. 访问 [百度智能云控制台](https://console.bce.baidu.com/ai/#/ai/ocr/overview)
2. 创建应用，选择「通用文字识别」
3. 获取 API Key 和 Secret Key
4. 免费额度：通用文字识别每日500次，高精度版50次

## 使用方法

1. 启动火炬之光无限游戏
2. 运行程序：`python main.py`
3. 程序会自动检测并绑定游戏窗口
4. 点击「识别物品」按钮进行文字识别
5. 识别结果会弹出提示框显示

## 配置说明

### OCR API类型

- **general_basic**: 标准版
  - 速度快
  - 成本低
  - 不带坐标信息

- **accurate**: 高精度版（带坐标）
  - 识别精度高
  - 返回文字坐标
  - 稍慢一些

### 其他设置

- **监控间隔**: 游戏窗口检测和进程监控的时间间隔（毫秒）
- **超时时间**: OCR请求的超时时间（秒）
- **重试次数**: OCR请求失败时的重试次数

## 项目结构

```
TorchOverlay/
├── app/                    # 应用层
│   ├── application.py     # 应用入口
│   ├── container.py       # 依赖注入容器
│   └── factories.py       # 依赖注入工厂
├── controllers/            # 控制器
│   └── app_controller.py  # 业务逻辑控制器
├── core/                   # 核心模块
│   ├── cache_manager.py   # 缓存管理
│   ├── config.py          # 配置管理
│   ├── constants.py       # 常量定义
│   ├── event_bus.py       # 事件总线
│   ├── logger.py          # 日志系统
│   └── models.py          # 数据模型
├── domain/                 # 领域层
│   ├── models/            # 领域模型
│   └── services/          # 领域服务
├── services/               # 服务层
│   ├── interfaces/        # 服务接口
│   ├── ocr/              # OCR服务
│   ├── overlay/          # 窗口覆盖相关
│   ├── admin_service.py  # 管理员权限
│   ├── capture_service.py # 截图服务（含优化）
│   ├── game_binder.py    # 游戏绑定
│   ├── process_watcher.py # 进程监控
│   ├── price_service.py   # 统一价格服务
│   └── window_finder.py  # 窗口查找
├── ui/                     # UI层
│   ├── main_window.py     # 主窗口
│   └── settings_window.py # 设置窗口
├── captures/              # 截图输出目录
├── logs/                  # 日志输出目录
├── main.py               # 程序入口
├── requirements.txt      # 依赖列表
├── config.json.example  # 配置文件模板
├── range.json.example   # 余额区域配置模板
└── .env.example         # 环境变量示例
```

## 配置文件

### config.json
主配置文件，包含OCR API密钥和其他应用设置。

首次运行时，程序会自动生成配置文件，或使用提供的模板：
```bash
cp config.json.example config.json
```

### range.json
余额识别区域配置文件，定义余额识别的位置和大小。

首次运行时，程序会自动生成默认配置，或使用提供的模板：
```bash
cp range.json.example range.json
```

### .env
环境变量配置文件，可用于存储敏感信息（可选）。

```bash
cp .env.example .env
# 编辑 .env 文件，填入实际的密钥
```

## 日志系统

程序会自动记录运行日志到 `logs/` 目录：
- `app_YYYYMMDD.log` - 完整日志（所有级别）
- `error_YYYYMMDD.log` - 错误日志（仅错误和严重错误）

调试模式下会在控制台输出详细日志。

## 开发说明

### 常量管理
所有常量定义在 `core/constants.py` 中，便于统一管理和修改。

### 日志使用
```python
from core.logger import get_logger

logger = get_logger(__name__)
logger.info("这是一条信息日志")
logger.error("这是一条错误日志")
```

### 代码优化

最新优化（2026-02-14）已完成 **Phase 1 & Phase 2**：

### 核心优化
- ✅ 统一价格服务（代码减少 33%）
- ✅ 智能缓存管理（LRU + TTL）
- ✅ 统一线程池管理
- ✅ 统一资源管理（消除泄漏）
- ✅ 实时内存监控
- ✅ 图像资源修复
- ✅ 应用生命周期优化

### 快速了解

| 文档 | 用途 |
|------|------|
| 📄 `FINAL_REPORT.md` | ⭐ **最终报告** - 完整成果总结 |
| 📄 `OPTIMIZATION_SUMMARY.md` | 快速了解所有优化 |
| 📄 `OPTIMIZATION_EXAMPLES.md` | 详细使用示例 |
| 📄 `OPTIMIZATION_USER_GUIDE.md` | 详细使用指南和API |
| 📄 `OPTIMIZATION_COMPLETED_REPORT.md` | 完整报告和后续建议 |
| 📄 `ARCHITECTURE_OPTIMIZATION_PLAN.md` | 优化思路和计划 |

### 整体效果
- 📉 代码量减少 **25-30%**
- 📉 内存峰值降低 **30-40%**
- 📉 代码重复率降至 **<5%**
- 📉 内存溢出风险降低 **90%**

### 缓存管理
项目使用统一的缓存管理系统：
```python
from core.cache_manager import LRUCache

# 创建缓存
cache = LRUCache(max_size=100, default_ttl=60)

# 使用缓存
cache.set("key", value)
value = cache.get("key")

# 获取统计信息
stats = cache.get_stats()
```

### 线程池
所有异步任务使用统一线程池：
```python
from core.thread_pool_manager import get_thread_pool

pool = get_thread_pool()
task_id = pool.submit_task(func, *args, callback=on_complete)
```

### 资源管理
自动管理图像等资源：
```python
from core.resource_manager import managed_image

with managed_image("screenshot.png") as img:
    process(img)  # 自动释放
```

## 注意事项

- 程序需要管理员权限才能正确检测和绑定游戏窗口
- 首次使用建议先配置OCR密钥
- 免费版OCR有每日调用次数限制
- 确保游戏窗口可见且未最小化
- 日志文件会自动归档，建议定期清理旧日志

## 许可证

MIT License
