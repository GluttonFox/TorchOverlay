# TorchOverlay 部署文档

## 目录

- [概述](#概述)
- [环境要求](#环境要求)
- [本地部署](#本地部署)
- [打包部署](#打包部署)
- [配置管理](#配置管理)
- [日志管理](#日志管理)
- [故障排查](#故障排查)
- [升级指南](#升级指南)

---

## 概述

TorchOverlay 支持多种部署方式：

1. **本地部署**：直接运行Python脚本
2. **打包部署**：使用PyInstaller打包为可执行文件
3. **安装包部署**：创建Windows安装包（可选）

---

## 环境要求

### 系统要求

- **操作系统**: Windows 10/11 (64位)
- **内存**: 最小2GB，推荐4GB+
- **磁盘空间**: 最小100MB，推荐500MB+

### 软件依赖

#### 运行时依赖
- Python 3.9 或更高版本
- pywin32 306+

#### 开发依赖（仅开发需要）
- pytest 7.0+
- pytest-cov 4.0+
- pylint 2.0+

### 网络要求

- 需要访问百度OCR API
- 需要访问价格更新API

---

## 本地部署

### 步骤1：安装Python

1. 从 [Python官网](https://www.python.org/downloads/) 下载Python 3.9+
2. 运行安装程序，**务必勾选 "Add Python to PATH"**
3. 验证安装：
```bash
python --version
```

### 步骤2：获取代码

#### 方式A：克隆Git仓库
```bash
git clone <repository-url>
cd TorchOverlay
```

#### 方式B：下载压缩包
1. 下载最新版本的压缩包
2. 解压到目标目录

### 步骤3：创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate
```

### 步骤4：安装依赖

```bash
# 安装所有依赖
pip install -r requirements.txt

# 或单独安装
pip install pywin32 Pillow requests
```

### 步骤5：配置应用

1. 复制配置示例文件：
```bash
copy config.json.example config.json
```

2. 编辑 `config.json`：
```json
{
  "app_title_prefix": "TorchOverlay",
  "keywords": ["火炬之光", "Torchlight"],
  "watch_interval_ms": 5000,
  "ocr": {
    "api_key": "your_api_key_here",
    "secret_key": "your_secret_key_here",
    "api_name": "baidu_ocr",
    "timeout_sec": 30,
    "max_retries": 3,
    "debug_mode": false
  },
  "last_price_update": null,
  "enable_tax_calculation": true,
  "mystery_gem_mode": "min"
}
```

### 步骤6：运行应用

```bash
python main.py
```

### 步骤7：验证部署

1. 启动游戏（火炬之光/火炬之光无限）
2. 点击"识别物品"按钮
3. 检查是否能正常识别

---

## 打包部署

### 准备工作

1. 确保Python环境已配置
2. 安装PyInstaller：
```bash
pip install pyinstaller
```

### 使用PyInstaller打包

#### 基础打包

```bash
pyinstaller --onefile --name TorchOverlay main.py
```

#### 完整打包（推荐）

创建 `build.spec` 文件：

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json.example', '.'),
        ('item.json', '.'),
        ('ITEM_REGIONS.md', '.'),
    ],
    hiddenimports=[
        'pywin32',
        'win32gui',
        'win32con',
        'win32api',
        'win32process',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TorchOverlay',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以指定图标文件
)
```

执行打包：

```bash
pyinstaller build.spec
```

#### 打包选项说明

| 选项 | 描述 |
|------|------|
| `--onefile` | 打包为单个可执行文件 |
| `--onedir` | 打包为目录（默认） |
| `--noconsole` | 不显示控制台窗口 |
| `--icon=xxx.ico` | 指定图标文件 |
| `--add-data` | 添加数据文件 |
| `--hidden-import` | 添加隐藏导入 |

### 打包后目录结构

```
dist/
└── TorchOverlay.exe      # 可执行文件

build/                     # 构建临时文件（可删除）
└── TorchOverlay/

TorchOverlay.spec         # 打包配置文件
```

### 创建安装包（可选）

#### 使用Inno Setup

1. 下载 [Inno Setup](https://jrsoftware.org/isdl.php)
2. 创建 `install.iss` 文件：

```inno
[Setup]
AppName=TorchOverlay
AppVersion=1.0.0
DefaultDirName={commonpf}\TorchOverlay
DefaultGroupName=TorchOverlay
OutputBaseFilename=TorchOverlay-Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\TorchOverlay.exe"; DestDir: "{app}"
Source: "config.json.example"; DestDir: "{app}"
Source: "item.json"; DestDir: "{app}"

[Icons]
Name: "{group}\TorchOverlay"; Filename: "{app}\TorchOverlay.exe"
Name: "{commondesktop}\TorchOverlay"; Filename: "{app}\TorchOverlay.exe"

[Run]
Filename: "{app}\TorchOverlay.exe"; Description: "启动 TorchOverlay"; Flags: nowait postinstall skipifsilent
```

3. 编译安装包：
```bash
ISCC.exe install.iss
```

---

## 配置管理

### 配置文件位置

- **本地部署**: 项目根目录的 `config.json`
- **打包部署**: 可执行文件同目录的 `config.json`

### 配置项说明

#### 应用配置

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `app_title_prefix` | string | 应用标题前缀 | "TorchOverlay" |
| `keywords` | array | 游戏关键词 | ["火炬之光", "Torchlight"] |
| `watch_interval_ms` | int | 监视间隔（毫秒） | 5000 |

#### OCR配置

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `api_key` | string | 百度OCR API密钥 | - |
| `secret_key` | string | 百度OCR密钥 | - |
| `api_name` | string | API名称 | "baidu_ocr" |
| `timeout_sec` | int | 超时时间（秒） | 30 |
| `max_retries` | int | 最大重试次数 | 3 |
| `debug_mode` | bool | 调试模式 | false |

#### 功能配置

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| `enable_tax_calculation` | bool | 启用税率计算 | true |
| `mystery_gem_mode` | string | 奥秘辉石模式 | "min" |

### 配置验证

应用启动时会自动验证配置：

1. OCR配置必需项检查
2. API密钥格式验证
3. 数值范围验证
4. 枚举值验证

验证失败会显示错误提示。

### 配置热更新

应用支持配置热更新，无需重启：

1. 修改 `config.json` 文件
2. 应用会自动检测变化
3. 验证新配置
4. 应用新配置

---

## 日志管理

### 日志位置

- **应用日志**: `logs/app_YYYYMMDD.log`
- **错误日志**: `logs/error_YYYYMMDD.log`
- **价格更新日志**: `logs/price_update.log`

### 日志级别

| 级别 | 说明 |
|------|------|
| DEBUG | 调试信息 |
| INFO | 一般信息 |
| WARNING | 警告信息 |
| ERROR | 错误信息 |

### 日志配置

在 `core/logger.py` 中配置：

```python
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 文件日志
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
```

### 日志查看

#### Windows

使用记事本或其他文本编辑器打开日志文件。

#### Linux/Mac

```bash
tail -f logs/app_$(date +%Y%m%d).log
```

### 日志清理

日志文件会自动按日期滚动，但建议定期清理旧日志：

```bash
# 删除30天前的日志
for /f "delims=" %f in ('dir /b /o-d logs\*.log ^| more +30') do del "logs\%f"
```

---

## 故障排查

### 常见问题

#### Q1: 启动时报"找不到模块"错误

**解决方案**：
```bash
# 重新安装依赖
pip install -r requirements.txt

# 或升级pip
python -m pip install --upgrade pip
```

#### Q2: OCR识别失败

**可能原因**：
- API密钥未配置或无效
- 网络连接问题
- API调用次数超限

**解决方案**：
1. 检查 `config.json` 中的API配置
2. 测试网络连接
3. 检查百度OCR控制台的调用次数

#### Q3: 游戏窗口绑定失败

**可能原因**：
- 游戏未启动
- 游戏进程名称不匹配
- 权限不足

**解决方案**：
1. 确保游戏已启动
2. 以管理员身份运行应用
3. 检查游戏进程名称

#### Q4: 覆盖层不显示

**可能原因**：
- DPI设置问题
- 窗口层级问题
- 透明色设置问题

**解决方案**：
1. 检查DPI缩放设置
2. 以管理员身份运行
3. 查看 `logs/error_YYYYMMDD.log` 日志

#### Q5: 价格更新失败

**可能原因**：
- API服务不可用
- 网络连接问题
- 更新间隔未到

**解决方案**：
1. 检查网络连接
2. 查看错误日志
3. 检查上次更新时间

### 调试模式

启用调试模式获取更多信息：

1. 修改 `config.json`：
```json
{
  "ocr": {
    "debug_mode": true
  }
}
```

2. 查看详细日志输出

### 性能问题

#### 应用卡顿

**可能原因**：
- OCR识别耗时
- 频繁更新价格
- 窗口同步过于频繁

**解决方案**：
1. 启用OCR缓存
2. 增加更新间隔
3. 使用性能优化服务

#### 内存占用过高

**可能原因**：
- 图片缓存过多
- 临时文件未清理
- 内存泄漏

**解决方案**：
1. 定期重启应用
2. 清理缓存文件
3. 查看内存使用情况

---

## 升级指南

### 版本检查

```bash
python main.py --version
```

或查看 `README.md` 获取最新版本信息。

### 升级步骤

#### 步骤1：备份

备份重要文件：
- `config.json`
- `item.json`（如果有修改）

#### 步骤2：停止应用

关闭正在运行的应用。

#### 步骤3：下载新版本

```bash
git pull origin main
```

或下载最新压缩包并解压。

#### 步骤4：更新依赖

```bash
pip install --upgrade -r requirements.txt
```

#### 步骤5：恢复配置

将备份的配置文件复制回去。

#### 步骤6：运行应用

```bash
python main.py
```

### 配置迁移

检查新版本的配置是否有变化：

1. 对比 `config.json.example`
2. 添加新的配置项
3. 删除废弃的配置项（如有）

### 数据迁移

如果数据结构有变化：

1. 备份旧数据
2. 使用迁移脚本（如有）
3. 验证数据完整性

---

## 安全建议

### 配置安全

1. 不要将 `config.json` 提交到Git
2. 使用环境变量存储敏感信息
3. 定期更换API密钥

### 运行安全

1. 以普通用户身份运行（非管理员）
2. 定期更新依赖包
3. 关注安全公告

### 数据安全

1. 定期备份配置和数据
2. 加密敏感信息
3. 限制访问权限

---

## 监控和维护

### 健康检查

定期检查应用状态：

1. 检查日志文件
2. 验证功能正常
3. 监控性能指标

### 备份策略

建议定期备份：

- 配置文件
- 物品数据
- 日志文件（重要日志）

### 性能监控

关注以下指标：

- OCR识别时间
- 价格更新成功率
- 内存使用情况
- 响应时间

---

## 技术支持

### 获取帮助

1. 查看 [常见问题](#常见问题)
2. 阅读 [开发者指南](DEVELOPER_GUIDE.md)
3. 提交Issue到GitHub

### 联系方式

- GitHub Issues
- 邮件：support@example.com

---

## 许可证

TorchOverlay 使用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解版本更新历史。

---

**文档版本**: 1.0.0
**最后更新**: 2026-02-13
