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
│   └── factories.py       # 依赖注入工厂
├── controllers/            # 控制器
│   └── app_controller.py  # 业务逻辑控制器
├── core/                   # 核心模块
│   ├── config.py          # 配置管理
│   ├── constants.py       # 常量定义
│   ├── logger.py         # 日志系统
│   └── models.py          # 数据模型
├── services/               # 服务层
│   ├── ocr/              # OCR服务
│   ├── overlay/          # 窗口覆盖相关
│   ├── admin_service.py  # 管理员权限
│   ├── capture_service.py # 截图服务
│   ├── game_binder.py    # 游戏绑定
│   ├── process_watcher.py # 进程监控
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

### 代码优化建议
详细优化建议请查看 `OPTIMIZATION_TODO.md` 文件。

## 注意事项

- 程序需要管理员权限才能正确检测和绑定游戏窗口
- 首次使用建议先配置OCR密钥
- 免费版OCR有每日调用次数限制
- 确保游戏窗口可见且未最小化
- 日志文件会自动归档，建议定期清理旧日志

## 许可证

MIT License
