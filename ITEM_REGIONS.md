# 物品识别区域配置

## 概述

物品识别区域采用网格布局配置，通过定义起始位置、大小和间距，自动生成所有物品槽的识别区域。

## 配置文件

配置文件：`range.json`

## 配置结构

```json
{
  "balance": {
    "x": 1735,
    "y": 36,
    "width": 100,
    "height": 40
  },
  "items": {
    "start_x": 480,
    "start_y": 240,
    "width": 220,
    "height": 280,
    "horizontal_spacing": 40,
    "vertical_spacing": 40,
    "rows": 2,
    "cols": 6
  }
}
```

## 物品区域参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| start_x | int | 480 | 起始 x 坐标 |
| start_y | int | 240 | 起始 y 坐标 |
| width | int | 220 | 物品槽宽度（像素） |
| height | int | 280 | 物品槽高度（像素） |
| horizontal_spacing | int | 40 | 列间距（像素） |
| vertical_spacing | int | 40 | 行间距（像素） |
| rows | int | 2 | 行数 |
| cols | int | 6 | 列数（第一行） |

## 生成的物品区域

根据配置，系统会自动生成以下物品区域：

| 区域名称 | x | y | width | height |
|---------|---|---|-------|--------|
| item_r0_c0 | 480 | 240 | 220 | 280 |
| item_r0_c1 | 740 | 240 | 220 | 280 |
| item_r0_c2 | 1000 | 240 | 220 | 280 |
| item_r0_c3 | 1260 | 240 | 220 | 280 |
| item_r0_c4 | 1520 | 240 | 220 | 280 |
| item_r0_c5 | 1780 | 240 | 220 | 280 |
| item_r1_c0 | 480 | 560 | 220 | 280 |
| item_r1_c1 | 740 | 560 | 220 | 280 |

**说明**：
- 第 0 行：6 列（0-5）
- 第 1 行：2 列（0-1）
- 计算公式：
  - `x = start_x + col * (width + horizontal_spacing)`
  - `y = start_y + row * (height + vertical_spacing)`

## 配置说明

### 调整物品槽大小

如果游戏界面中物品槽的大小不同，只需修改 `width` 和 `height`：

```json
"items": {
  "width": 240,
  "height": 300,
  ...
}
```

### 调整间距

如果物品槽之间的间距不同，修改间距参数：

```json
"items": {
  "horizontal_spacing": 50,
  "vertical_spacing": 50,
  ...
}
```

### 调整网格大小

如果游戏界面的网格布局不同，修改 `rows` 和 `cols`：

```json
"items": {
  "rows": 3,
  "cols": 8,
  ...
}
```

## 使用方法

### 1. 自动创建

程序首次启动时，会自动创建 `range.json` 文件，包含默认配置。

### 2. 手动创建

从模板复制配置文件：
```bash
cp range.json.example range.json
```

### 3. 自定义配置

编辑 `range.json` 文件，根据实际游戏界面调整参数：
1. 测量第一个物品槽的位置（start_x, start_y）
2. 测量物品槽的宽高（width, height）
3. 测量物品槽之间的间距
4. 确认行数和列数
5. 保存文件并重启程序

## 代码使用

### 获取所有物品区域

```python
from core.config import AppConfig

cfg = AppConfig.load()
all_regions = cfg.regions.items.get_all_regions()
for region in all_regions:
    print(f"{region['name']}: x={region['x']}, y={region['y']}")
```

### 获取特定物品区域

```python
# 获取第 0 行第 0 列的物品区域
region = cfg.regions.items.get_region(row=0, col=0)
if region:
    print(f"区域: {region}")
```

## 调试模式

在配置中启用调试模式可以查看详细的识别信息：

1. 打开设置窗口
2. 勾选"启用调试模式"
3. 保存设置

调试模式下，程序会在控制台输出：
- 生成的物品区域列表
- 识别的区域坐标
- 截图保存路径
- OCR 识别结果

## 注意事项

- 所有坐标都是相对于游戏窗口 **client 区域**的
- 配置文件保存在项目根目录
- 不同游戏版本或分辨率可能需要调整配置
- 建议在标准分辨率（1920x1080）下配置
- 修改配置后需要重启程序生效

## 优势

相比手动配置每个物品区域，网格布局配置有以下优势：

1. **配置简洁**：只需 8 个参数代替多个区域的完整定义
2. **易于调整**：统一修改大小、间距，无需逐个调整
3. **自动生成**：系统自动计算所有区域坐标
4. **可扩展**：增加行列即可支持更多物品槽
5. **维护方便**：一个文件管理所有区域配置
