# 服务器识别功能文档

## 功能概述

从游戏日志中识别玩家信息和服务器类型（永久区/赛季区/专家区），用于区分不同服务器的兑换日志。

## 服务器类型

### 支持的服务器类型

| 服务器类型 | 枚举值 | Season ID | 说明 |
|---|---|---|---|
| 永久区 | `PERMANENT_ZONE` | 1 | 永久服务器 |
| 赛季区 | `SEASON_ZONE` | 1201 | 赛季服务器 |
| 专家区 | `EXPERT_ZONE` | 1231 | 专家服务器 |
| 未知 | `UNKNOWN` | 其他 | 未知服务器，默认使用赛季区配置 |

### 显示标签

- 永久区: "永久区"
- 赛季区: "赛季区"
- 专家区: "专家区"
- 未知: "未知区服"

## 日志格式

### 玩家信息日志格式

```
[Game] +player+
[Game] +player+Name[玩家名]
[Game] +player+SeasonId[赛季ID]
```

### 连接关闭日志格式

```
[Game] NetGame CloseConnect
```

### 示例日志

```
[2026.02.14-10.30.00:111][902]GameLog: Display: [Game] +player+
[2026.02.14-10.30.00:222][902]GameLog: Display: [Game] +player+Name[Player123]
[2026.02.14-10.30.00:333][902]GameLog: Display: [Game] +player+SeasonId[1201]
```

## 实现细节

### 文件结构

```
domain/models/
  ├── season.py              # 服务器类型枚举和映射
  └── player_info.py         # 玩家信息数据模型

services/
  ├── season_resource_service.py  # 服务器资源服务
  └── game_log_parser_service.py  # 日志解析服务（已更新）
```

### 核心类

#### 1. `SeasonServerType` (枚举)

```python
class SeasonServerType(Enum):
    UNKNOWN = 0
    PERMANENT_ZONE = 1  # 永久区
    SEASON_ZONE = 2  # 赛季区
    EXPERT_ZONE = 3  # 专家区
```

#### 2. `PlayerInfo` (数据类)

```python
@dataclass
class PlayerInfo:
    name: str  # 玩家名
    season_id: int | None = None  # 赛季ID
    season_type: SeasonServerType = SeasonServerType.UNKNOWN
    timestamp: datetime | None = None
```

#### 3. `SeasonResourceService` (服务类)

功能：
- 根据赛季ID加载对应服务器的配置
- 管理不同服务器的数据文件路径
- 提供服务器切换通知
- 维护当前服务器状态

方法：
- `load_for_season(season_id: int) -> SeasonLoadResult`: 为指定赛季加载配置
- `get_current_season_info() -> SeasonInfoSnapshot`: 获取当前赛季信息
- `get_season_label() -> str`: 获取当前服务器的显示标签
- `get_data_file_path(file_type: str) -> str`: 获取数据文件路径

#### 4. `GameLogParserService` (已更新)

新增功能：
- 识别玩家信息（`+player+` 日志）
- 识别服务器类型（`SeasonId`）
- 监听连接关闭事件（`NetGame CloseConnect`）
- 切换服务器时自动更新配置

新增方法：
- `_parse_player_info(log_line: LogLine)`: 解析玩家信息
- `get_player_info() -> Optional[PlayerInfo]`: 获取当前玩家信息
- `get_season_info() -> SeasonInfoSnapshot`: 获取当前服务器信息
- `get_season_label() -> str`: 获取服务器显示标签

### 正则表达式

```python
# 玩家信息开始
PLAYER_INFO_START_PATTERN = re.compile(r"^\+player\+")

# 玩家名
PLAYER_NAME_PATTERN = re.compile(r"\+(?:player\+)?Name\s*\[([^\]]*)\]")

# 赛季ID
PLAYER_SEASON_ID_PATTERN = re.compile(r"\+(?:player\+)?SeasonId\s*\[([^\]]*)\]")

# 连接关闭
CONNECTION_CLOSED_PATTERN = re.compile(r"\[Game\]\s+NetGame\s+CloseConnect")
```

## 使用示例

### 基本使用

```python
from services.game_log_parser_service import GameLogParserService

# 创建解析器
parser = GameLogParserService()

# 解析新事件
buy_events, refresh_events = parser.parse_new_events()

# 获取玩家信息
player_info = parser.get_player_info()
if player_info:
    print(f"玩家: {player_info.name}")
    print(f"服务器: {player_info.season_type}")
    print(f"赛季ID: {player_info.season_id}")

# 获取服务器信息
season_info = parser.get_season_info()
print(f"当前服务器: {season_info.season_type}")

# 获取服务器标签
season_label = parser.get_season_label()
print(f"服务器标签: {season_label}")
```

### 在兑换日志中使用

```python
from services.game_log_parser_service import GameLogParserService
from domain.models.season import SeasonServerType

parser = GameLogParserService()

# 解析日志并获取服务器信息
parser.parse_new_events()
player_info = parser.get_player_info()

if player_info:
    # 根据服务器类型区分日志
    if player_info.season_type == SeasonServerType.PERMANENT_ZONE:
        # 永久区兑换日志
        log_file = "exchange_log_permanent.json"
    elif player_info.season_type == SeasonServerType.SEASON_ZONE:
        # 赛季区兑换日志
        log_file = "exchange_log_season.json"
    elif player_info.season_type == SeasonServerType.EXPERT_ZONE:
        # 专家区兑换日志
        log_file = "exchange_log_expert.json"
    else:
        # 未知服务器，使用赛季区默认配置
        log_file = "exchange_log_season.json"
    
    # 保存兑换日志到对应的文件
    save_exchange_log(log_file, exchange_data)
```

## 测试

运行测试脚本验证功能：

```bash
python test_season_parser.py
```

测试内容：
- 玩家信息开始识别
- 玩家名提取
- 赛季ID提取
- 服务器类型解析
- 连接关闭检测

## 数据文件路径

根据服务器类型，数据文件会保存到不同的目录：

```
PermanentZone/
  ├── price_equipment_permanent.json
  ├── price_skill_permanent.json
  ├── price_consumable_permanent.json
  └── exchange_log_permanent.json

SeasonZone/
  ├── price_equipment_season.json
  ├── price_skill_season.json
  ├── price_consumable_season.json
  └── exchange_log_season.json

ExpertZone/
  ├── price_equipment_expert.json
  ├── price_skill_expert.json
  ├── price_consumable_expert.json
  └── exchange_log_expert.json
```

## 服务器切换处理

当检测到玩家信息变化时：

1. 保存当前服务器的状态
2. 切换到新服务器
3. 加载新服务器的配置
4. 更新数据文件路径
5. 重置背包状态

## 注意事项

1. **首次启动**：会跳到日志文件末尾，只监控新日志
2. **服务器切换**：会在连接关闭时重置玩家信息
3. **未知服务器**：收到未知 SeasonId 时，默认使用赛季区配置
4. **并发安全**：如需多线程支持，请在 `SeasonResourceService` 中添加锁机制

## 参考资料

- GameLogMonitor 项目: `D:\GameLogMonitor`
- 关键文件:
  - `Services/Configuration/SeasonResourceService.cs`
  - `Parsers/PlayerInfoParser.cs`
  - `Core/Handlers/PlayerInfoHandler.cs`
  - `Utils/SeasonDisplayHelper.cs`
