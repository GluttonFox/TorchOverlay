"""测试服务器识别功能"""
import re

# 测试正则表达式
PLAYER_INFO_START_PATTERN = re.compile(r"^\+player\+")
PLAYER_NAME_PATTERN = re.compile(r"\+(?:player\+)?Name\s*\[([^\]]*)\]")
PLAYER_SEASON_ID_PATTERN = re.compile(r"\+(?:player\+)?SeasonId\s*\[([^\]]*)\]")
CONNECTION_CLOSED_PATTERN = re.compile(r"\[Game\]\s+NetGame\s+CloseConnect")

# 测试日志行
test_lines = [
    # 玩家信息开始
    "[2026.02.14-10.30.00:111][902]GameLog: Display: [Game] +player+",
    
    # 玩家名
    "[2026.02.14-10.30.00:222][902]GameLog: Display: [Game] +player+Name[Player123]",
    
    # 赛季ID（赛季区）
    "[2026.02.14-10.30.00:333][902]GameLog: Display: [Game] +player+SeasonId[1201]",
    
    # 另一个玩家的信息（永久区）
    "[2026.02.14-11.00.00:111][902]GameLog: Display: [Game] +player+",
    "[2026.02.14-11.00.00:222][902]GameLog: Display: [Game] +player+Name[Player456]",
    "[2026.02.14-11.00.00:333][902]GameLog: Display: [Game] +player+SeasonId[1]",
    
    # 专家区
    "[2026.02.14-12.00.00:111][902]GameLog: Display: [Game] +player+",
    "[2026.02.14-12.00.00:222][902]GameLog: Display: [Game] +player+Name[Player789]",
    "[2026.02.14-12.00.00:333][902]GameLog: Display: [Game] +player+SeasonId[1231]",
    
    # 连接关闭
    "[2026.02.14-13.00.00:111][902]GameLog: Display: [Game] NetGame CloseConnect",
]

# 赛季ID映射
SEASON_ID_MAPPING = {
    1: "永久区",
    1201: "赛季区",
    1231: "专家区",
}

def resolve_season_type(season_id: int) -> str:
    """根据赛季ID解析服务器类型"""
    return SEASON_ID_MAPPING.get(season_id, "未知区服")

print("=" * 80)
print("测试服务器识别功能")
print("=" * 80)

player_name = None
player_season_id = None

for line in test_lines:
    print(f"\n原始日志: {line}")
    
    # 检查玩家信息开始
    if PLAYER_INFO_START_PATTERN.search(line):
        print(f"  ✓ 玩家信息开始")
        player_name = None
        player_season_id = None
    
    # 提取玩家名
    if player_name is None:
        name_match = PLAYER_NAME_PATTERN.search(line)
        if name_match:
            player_name = name_match.group(1).strip()
            print(f"  ✓ 玩家名: {player_name}")
    
    # 提取赛季ID
    if player_season_id is None:
        season_match = PLAYER_SEASON_ID_PATTERN.search(line)
        if season_match:
            season_id_str = season_match.group(1).strip()
            try:
                player_season_id = int(season_id_str)
                season_type = resolve_season_type(player_season_id)
                print(f"  ✓ 赛季ID: {player_season_id} ({season_type})")
                
                # 显示完整的玩家信息
                print(f"\n  完整玩家信息:")
                print(f"    玩家名: {player_name}")
                print(f"    赛季ID: {player_season_id}")
                print(f"    服务器类型: {season_type}")
            except ValueError:
                print(f"  ✗ 无法解析赛季ID: {season_id_str}")
    
    # 检查连接关闭
    if CONNECTION_CLOSED_PATTERN.search(line):
        print(f"  ✓ 检测到断开连接")
        player_name = None
        player_season_id = None

print("\n" + "=" * 80)
print("测试完成！")
print("=" * 80)
