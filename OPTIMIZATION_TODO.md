# 代码优化建议

## 1. 项目结构优化

### 当前结构
```
TorchOverlay/
├── app/              # 应用层
├── controllers/      # 控制器
├── core/             # 核心配置和模型
├── services/         # 服务层
│   ├── ocr/         # OCR服务
│   └── overlay/     # Overlay服务
├── ui/              # UI层
└── main.py          # 入口
```

### 优化建议
当前结构已经很合理，建议保持。

## 2. 代码质量优化

### 2.1 错误处理

**当前问题**：部分错误处理不够完善

**建议改进**：
- `services/admin_service.py` - 添加异常日志
- `services/capture_service.py` - 超时处理可以更精细
- `controllers/app_controller.py` - 添加更多边界检查

### 2.2 类型注解

**当前问题**：部分函数缺少返回类型

**建议改进**：
```python
# 当前
def find_first_match(self) -> tuple[int | None, str | None]:

# 优化后（添加别名）
from typing import Tuple, Optional

HwndTitleResult = Tuple[Optional[int], Optional[str]]

def find_first_match(self) -> HwndTitleResult:
```

### 2.3 常量管理

**建议**：创建 `constants.py` 文件，集中管理常量
```python
# core/constants.py
DEFAULT_WATCH_INTERVAL_MS = 500
DEFAULT_TIMEOUT_SEC = 2.5
CAPTURE_OUTPUT_DIR = "captures"
```

## 3. 性能优化

### 3.1 截图服务优化

**当前问题**：每次截图都会创建临时文件

**建议**：使用内存缓存减少磁盘IO
```python
import io

def capture_to_memory(self, ...):
    """截图到内存，返回字节流"""
    buffer = io.BytesIO()
    # 保存到 buffer 而不是文件
    return buffer.getvalue()
```

### 3.2 OCR 请求优化

**建议**：
- 添加请求缓存（短时间内相同图片不重复请求）
- 实现请求队列，避免并发过多

### 3.3 窗口查找优化

**当前问题**：`EnumWindows` 每次都遍历所有窗口

**建议**：
- 缓存最近找到的窗口
- 添加快速检查机制

## 4. 安全性优化

### 4.1 敏感信息处理

**当前问题**：range.json 可能包含敏感坐标信息

**建议**：
- 添加 `.gitignore` 确保 `range.json` 不被提交
- 添加配置文件模板 `range.json.example`

### 4.2 API 密钥管理

**当前问题**：config.json 中明文存储 API 密钥

**建议**：
```python
# 使用环境变量或加密存储
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('BAIDU_OCR_API_KEY')
```

## 5. 构建优化

### 5.1 依赖版本锁定

**建议**：使用 requirements.txt 的精确版本
```bash
# 生成精确版本
pip freeze > requirements-lock.txt
```

### 5.2 添加启动脚本

**建议**：创建启动脚本
```python
# scripts/run.py
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import main
if __name__ == "__main__":
    main()
```

### 5.3 添加打包配置

**建议**：创建 `pyproject.toml` 支持 `pip install`
```toml
[project]
name = "torch-overlay"
version = "1.0.0"
requires-python = ">=3.9"
dependencies = [
    "pywin32>=306",
    "psutil>=5.9.0",
    "Pillow>=10.0.0",
]
```

## 6. 日志系统

**建议**：添加统一的日志系统
```python
# core/logger.py
import logging
from pathlib import Path

def setup_logger(name: str = "TorchOverlay"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 文件处理器
    fh = logging.FileHandler('app.log')
    fh.setLevel(logging.DEBUG)
    
    # 控制台处理器
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger
```

## 7. 测试

**建议**：添加单元测试
```
tests/
├── test_config.py
├── test_ocr.py
└── test_capture.py
```

## 8. 文档完善

**建议**：
- 添加 API 文档（使用 Sphinx）
- 添加架构图
- 完善开发文档

## 9. 代码清理

### 9.1 删除不必要的文件
- 清理 `captures/` 目录下的测试截图
- 添加 `captures/` 到 `.gitignore`

### 9.2 .gitignore 优化
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so

# 虚拟环境
venv/
env/

# IDE
.vscode/
.idea/

# 项目特定
captures/
*.log
config.json
range.json
.env
```

## 10. 优先级建议

### 高优先级
1. 添加日志系统
2. 完善 `.gitignore`
3. 优化错误处理
4. 添加常量管理

### 中优先级
5. 性能优化（截图缓存）
6. 安全性改进（API密钥加密）
7. 添加单元测试

### 低优先级
8. 打包配置
9. 文档完善
10. 代码重构
