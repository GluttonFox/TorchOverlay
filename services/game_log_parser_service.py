"""游戏日志解析服务 - 解析UE_game.log中的购买和刷新事件

基于 GameLogMonitor 项目的正确日志格式解析：
- 物品更新: ItemChange@ Update Id=xxx BagNum=xxx in PageId=xxx SlotId=xxx
- 物品添加: ItemChange@ Add Id=xxx BagNum=xxx in PageId=xxx SlotId=xxx
- 物品删除: ItemChange@ Delete Id=xxx in PageId=xxx SlotId=xxx
"""
import re
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass

from core.logger import get_logger
from domain.models.buy_event import BuyEvent
from domain.models.refresh_event import RefreshEvent
from domain.models.item_update import ItemChange, UpdateItemInfo, AddItemInfo, DeleteItemInfo
from domain.models.player_info import PlayerInfo
from services.inventory_state_manager import InventoryStateManager, GEM_BASE_ID
from services.season_resource_service import SeasonResourceService

logger = get_logger(__name__)


@dataclass
class LogLine:
    """日志行解析结果"""
    timestamp: datetime
    content: str
    raw_line: str


class GameLogParserService:
    """游戏日志解析服务
    
    核心功能：
    1. 解析游戏日志文件中的物品变化事件
    2. 识别购买、刷新等操作
    3. 维护背包状态，追踪物品数量变化
    """

    # 正则表达式模式
    ITEM_UPDATE_PATTERN = re.compile(
        r"ItemChange@\s+Update\s+Id=([^\s]+)\s+BagNum=(\d+)\s+in\s+PageId=(-?\d+)\s+SlotId=(\d+)"
    )
    ITEM_ADD_PATTERN = re.compile(
        r"ItemChange@\s+Add\s+Id=([^\s]+)\s+BagNum=(\d+)\s+in\s+PageId=(\d+)\s+SlotId=(\d+)"
    )
    ITEM_DELETE_PATTERN = re.compile(
        r"ItemChange@\s+Delete\s+Id=([^\s]+)\s+in\s+PageId=(\d+)\s+SlotId=(\d+)"
    )
    
    # 事件边界模式
    EVENT_START_PATTERN = re.compile(r"ItemChange@\s+ProtoName=(\w+)\s+start")
    EVENT_END_PATTERN = re.compile(r"ItemChange@\s+ProtoName=(\w+)\s+end")
    
    # 成功标志
    BUY_SUCCESS_PATTERN = re.compile(r"Func_Common_BuySuccess")
    REFRESH_SUCCESS_PATTERN = re.compile(r"Func_Vendor_refreshSuccess")
    
    # 背包初始化进度
    LOAD_PROGRESS_PATTERN = re.compile(r"LoadUILogicProgress=(\d+)")
    
    # 玩家信息模式
    PLAYER_INFO_START_PATTERN = re.compile(r"^\+player\+")
    PLAYER_NAME_PATTERN = re.compile(r"\+(?:player\+)?Name\s*\[([^\]]*)\]")
    PLAYER_SEASON_ID_PATTERN = re.compile(r"\+(?:player\+)?SeasonId\s*\[([^\]]*)\]")
    
    # 连接关闭模式
    CONNECTION_CLOSED_PATTERN = re.compile(r"\[Game\]\s+NetGame\s+CloseConnect")
    
    # 支持的事件类型
    SUPPORTED_EVENTS = {
        'BuyVendorGoods',  # 购买商店物品
        'RefreshVendorShop',  # 刷新商店
        'Push2',  # 物品推送/副本结算
        'ResetItemsLayout',  # 背包重排
        'PickItems',  # 拾取物品
        'ExchangeItem',  # 交换物品
        'OpenRewardBox',  # 打开奖励箱
        'ReCostItem',  # 重新消耗物品
    }

    def __init__(self, game_log_path: str | None = None):
        """初始化日志解析服务

        Args:
            game_log_path: 游戏日志文件路径，如果为None则使用默认路径
        """
        self.game_log_path = game_log_path or self._get_default_log_path()
        self._last_position = 0  # 上次读取位置
        self._last_size = 0  # 上次文件大小
        self._initialized = False  # 服务是否已初始化

        # 背包状态管理器
        self._inventory_manager = InventoryStateManager()

        # 服务器资源服务
        self._season_service = SeasonResourceService()

        # 当前事件上下文
        self._current_event = None  # EventContext 对象
        self._last_event = None  # 上一个事件上下文（用于跨事件配对）

        # Update 记录缓存（用于基于时间戳配对）
        # 存储最近的所有 Update 记录，格式: {timestamp: UpdateItemInfo}
        self._update_records_cache: Dict[datetime, dict] = {}

        # 玩家信息
        self._player_name: Optional[str] = None
        self._player_season_id: Optional[int] = None

    def _get_default_log_path(self) -> str:
        """获取默认的游戏日志路径"""
        return r"D:\TapTap\PC Games\172664\UE_game.log"

    def parse_new_events(self) -> tuple[List[BuyEvent], List[RefreshEvent]]:
        """解析新的日志事件（从上次读取位置开始）
        
        Returns:
            (购买事件列表, 刷新事件列表)
        """
        if not os.path.exists(self.game_log_path):
            logger.warning(f"游戏日志文件不存在: {self.game_log_path}")
            return [], []

        try:
            with open(self.game_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 检查文件是否被重置
                current_size = os.path.getsize(self.game_log_path)
                if current_size < self._last_size:
                    logger.info("日志文件已被重置，从头开始读取")
                    self._last_position = 0
                    self._inventory_manager.reset_backpack_initialized()
                self._last_size = current_size

                # 首次启动，跳到文件末尾
                if not self._initialized:
                    logger.info("首次启动，跳到日志文件末尾，只监控新日志")
                    self._last_position = current_size
                    self._initialized = True
                    return [], []

                # 跳转到上次读取位置
                f.seek(self._last_position)

                buy_events = []
                refresh_events = []
                
                for line in f:
                    # 更新读取位置（通过行长度）
                    self._last_position += len(line.encode('utf-8'))
                    
                    parsed = self._parse_log_line(line)
                    if not parsed:
                        continue

                    # 处理日志行（捕获异常，确保不会因为单行解析失败而中断）
                    try:
                        self._process_log_line(parsed, buy_events, refresh_events)
                    except Exception as e:
                        logger.error(f"处理日志行时发生错误: {e}", exc_info=True)
                        # 继续处理下一行

                # 文件结束时，如果有未完成的事件，强制结束
                if self._current_event:
                    logger.warning(f"文件结束，强制关闭未完成事件: {self._current_event.event_type}")
                    self._finalize_event(buy_events, refresh_events)

                return buy_events, refresh_events

        except Exception as e:
            logger.error(f"解析日志失败: {e}", exc_info=True)
            return [], []

    def _process_log_line(self, log_line: LogLine, 
                         buy_events: List[BuyEvent], 
                         refresh_events: List[RefreshEvent]) -> None:
        """处理单行日志
        
        Args:
            log_line: 解析后的日志行
            buy_events: 购买事件列表（输出参数）
            refresh_events: 刷新事件列表（输出参数）
        """
        content = log_line.content
        
        # 0. 检查连接关闭
        if self.CONNECTION_CLOSED_PATTERN.search(content):
            # logger.debug("检测到断开连接事件，重置玩家状态")
            self._player_name = None
            self._player_season_id = None
            self._inventory_manager.reset_backpack_initialized()
        
        # 1. 识别玩家信息
        self._parse_player_info(log_line)
        
        # 2. 检查背包初始化进度
        self._check_load_progress(log_line)
        
        # 3. 解析物品变化
        item_change = self._parse_item_change(log_line)
        if item_change:
            self._inventory_manager.apply_item_change(item_change)
            # 如果有当前事件，记录变更
            if self._current_event:
                self._current_event.add_change(item_change)
        
        # 4. 检测事件开始
        event_start = self.EVENT_START_PATTERN.search(content)
        if event_start:
            event_type = event_start.group(1)
            if event_type in self.SUPPORTED_EVENTS:
                self._start_event(event_type, log_line.timestamp)
        
        # 5. 检测事件结束
        event_end = self.EVENT_END_PATTERN.search(content)
        if event_end:
            event_type = event_end.group(1)
            if self._current_event and self._current_event.event_type == event_type:
                self._end_event(log_line.timestamp)
                self._finalize_event(buy_events, refresh_events)
        
        # 6. 检测成功标志
        self._check_success_flags(log_line)

    def _check_load_progress(self, log_line: LogLine) -> None:
        """检查背包初始化进度
        
        Args:
            log_line: 日志行
        """
        progress_match = self.LOAD_PROGRESS_PATTERN.search(log_line.content)
        if progress_match:
            progress = int(progress_match.group(1))
            # logger.debug(f"加载进度: {progress}")
            print(f"[日志解析] 加载进度: {progress}")
            
            if progress == 2:
                # 开始加载背包物品
                logger.info("开始加载背包物品")
                print(f"[日志解析] 开始加载背包物品")
            elif progress == 3:
                # 背包加载完成
                if not self._inventory_manager.is_backpack_initialized:
                    self._inventory_manager.mark_backpack_initialized()
                    logger.info("背包初始化完成")
                    
                    # 输出背包物品列表
                    items = self._inventory_manager.get_all_items()
                    print(f"[日志解析] 背包初始化完成，物品数量: {len(items)}")
                    
                    # 输出神威辉石数量
                    gem_num = self._inventory_manager.get_item_num(GEM_BASE_ID)
                    print(f"[日志解析] 神威辉石数量: {gem_num}")
                    
                    # 输出前10个物品
                    item_list = list(items.items())[:10]
                    for base_id, record in item_list:
                        print(f"[日志解析]   物品: {base_id}, 数量: {record.bag_num}")
                    
                    if len(items) > 10:
                        print(f"[日志解析]   ... 还有 {len(items) - 10} 个物品")

    
    def _parse_player_info(self, log_line: LogLine) -> None:
        """解析玩家信息
        
        Args:
            log_line: 日志行
        """
        content = log_line.content
        
        # 检查是否是玩家信息开始
        if self.PLAYER_INFO_START_PATTERN.search(content):
            # logger.debug("检测到玩家信息开始")
            self._player_name = None
            self._player_season_id = None
        
        # 提取玩家名
        if self._player_name is None:
            name_match = self.PLAYER_NAME_PATTERN.search(content)
            if name_match:
                self._player_name = name_match.group(1).strip()
                logger.info(f"检测到玩家名: {self._player_name}")
        
        # 提取赛季ID
        if self._player_season_id is None:
            season_match = self.PLAYER_SEASON_ID_PATTERN.search(content)
            if season_match:
                season_id_str = season_match.group(1).strip()
                try:
                    self._player_season_id = int(season_id_str)
                    logger.info(f"检测到赛季ID: {self._player_season_id}")
                    
                    # 加载对应服务器的配置
                    season_load_result = self._season_service.load_for_season(self._player_season_id)
                    if season_load_result.season_changed:
                        logger.info(f"服务器已切换: {season_load_result.previous_season} -> {season_load_result.current_season}")
                except ValueError:
                    logger.warning(f"无法解析赛季ID: {season_id_str}")

    def _parse_item_change(self, log_line: LogLine) -> Optional[ItemChange]:
        """解析物品变更

        Args:
            log_line: 日志行

        Returns:
            ItemChange对象，如果没有匹配返回None
        """
        content = log_line.content

        # 尝试匹配 Update
        match = self.ITEM_UPDATE_PATTERN.search(content)
        if match:
            item_id = match.group(1)
            bag_num = int(match.group(2))
            page_id = int(match.group(3))
            slot_id = int(match.group(4))
            base_id = self._extract_base_id(item_id)

            # logger.debug(f"[物品更新] {base_id}: 数量={bag_num}, 页面={page_id}, 槽位={slot_id}")
            print(f"[物品更新] {base_id}: 数量={bag_num}, 页面={page_id}, 槽位={slot_id}")

            # 存储 Update 记录到缓存（用于时间戳配对）
            self._update_records_cache[log_line.timestamp] = {
                'base_id': base_id,
                'item_id': item_id,
                'bag_num': bag_num,
                'page_id': page_id,
                'slot_id': slot_id,
                'raw_line': log_line.raw_line
            }
            # logger.debug(f"  [缓存] 添加 Update 记录: {base_id}, 时间戳={log_line.timestamp.strftime('%H:%M:%S.%f')}, 当前缓存数={len(self._update_records_cache)}")

            # 清理旧的缓存记录（只保留最近 10 秒的记录）
            self._cleanup_old_update_records()

            return ItemChange(
                item_id=item_id,
                base_id=base_id,
                page_id=page_id,
                slot_id=slot_id,
                timestamp=log_line.timestamp,
                change_type='update',
                bag_num=bag_num,
                raw_line=log_line.raw_line
            )

        # 尝试匹配 Add
        match = self.ITEM_ADD_PATTERN.search(content)
        if match:
            item_id = match.group(1)
            bag_num = int(match.group(2))
            page_id = int(match.group(3))
            slot_id = int(match.group(4))
            base_id = self._extract_base_id(item_id)

            # logger.debug(f"[物品添加] {base_id}: 数量={bag_num}, 页面={page_id}, 槽位={slot_id}")
            print(f"[物品添加] {base_id}: 数量={bag_num}, 页面={page_id}, 槽位={slot_id}")

            return ItemChange(
                item_id=item_id,
                base_id=base_id,
                page_id=page_id,
                slot_id=slot_id,
                timestamp=log_line.timestamp,
                change_type='add',
                bag_num=bag_num,
                raw_line=log_line.raw_line
            )

        # 尝试匹配 Delete
        match = self.ITEM_DELETE_PATTERN.search(content)
        if match:
            item_id = match.group(1)
            page_id = int(match.group(2))
            slot_id = int(match.group(3))
            base_id = self._extract_base_id(item_id)

            # logger.debug(f"[物品删除] {base_id}: 页面={page_id}, 槽位={slot_id}")
            print(f"[物品删除] {base_id}: 页面={page_id}, 槽位={slot_id}")

            return ItemChange(
                item_id=item_id,
                base_id=base_id,
                page_id=page_id,
                slot_id=slot_id,
                timestamp=log_line.timestamp,
                change_type='delete',
                raw_line=log_line.raw_line
            )

        return None

    @staticmethod
    def _extract_base_id(item_id: str) -> str:
        """从物品ID中提取基础ID
        
        物品ID格式: BaseId_InstanceId
        例如: 5210_12345 -> 5210
        
        Args:
            item_id: 完整的物品ID
            
        Returns:
            基础ID
        """
        if '_' in item_id:
            return item_id.split('_')[0]
        return item_id

    def _start_event(self, event_type: str, timestamp: datetime) -> None:
        """开始一个新事件

        Args:
            event_type: 事件类型
            timestamp: 开始时间戳
        """
        # 如果有未完成的事件，强制结束
        if self._current_event:
            logger.warning(f"强制结束未完成事件: {self._current_event.event_type}")
            print(f"[日志解析] 强制结束未完成事件: {self._current_event.event_type}")

        # 创建新事件
        snapshot = self._inventory_manager.create_snapshot()
        instance_snapshot = self._inventory_manager.create_instance_snapshot()
        self._current_event = EventContext(
            event_type=event_type,
            start_time=timestamp,
            snapshot=snapshot,
            instance_snapshot=instance_snapshot
        )

        # logger.info(f"========== 检测到事件开始: {event_type} ({timestamp.strftime('%H:%M:%S.%f')}) ==========")
        print(f"[日志解析] ========== 检测到事件开始: {event_type} ({timestamp.strftime('%H:%M:%S.%f')}) ==========")

        # 输出背包快照
        # logger.debug(f"  背包快照: {snapshot}")
        print(f"[日志解析]   背包快照: {len(snapshot)} 个物品")

        # 输出神威辉石数量
        gem_num = snapshot.get(GEM_BASE_ID, 0)
        print(f"[日志解析]   神威辉石: {gem_num}")

    def _end_event(self, timestamp: datetime) -> None:
        """结束当前事件
        
        Args:
            timestamp: 结束时间戳
        """
        if self._current_event:
            self._current_event.end_time = timestamp

            # logger.info(f"========== 检测到事件结束: {self._current_event.event_type} ({timestamp.strftime('%H:%M:%S.%f')}) ==========")
            print(f"[日志解析] ========== 检测到事件结束: {self._current_event.event_type} ({timestamp.strftime('%H:%M:%S.%f')}) ==========")

            # 输出事件内的变更数
            change_count = self._current_event.get_change_count()
            # logger.debug(f"  事件内变更数: {change_count}")
            print(f"[日志解析]   事件内变更数: {change_count} (更新: {len(self._current_event.item_updates)}, 添加: {len(self._current_event.item_adds)}, 删除: {len(self._current_event.item_deletes)})")


    def _check_success_flags(self, log_line: LogLine) -> None:
        """检查操作成功标志
        
        Args:
            log_line: 日志行
        """
        if not self._current_event:
            return
        
        content = log_line.content
        
        if self._current_event.event_type == 'BuyVendorGoods':
            if self.BUY_SUCCESS_PATTERN.search(content):
                self._current_event.success = True
                logger.info(f"  - 购买成功！")
        
        elif self._current_event.event_type == 'RefreshVendorShop':
            if self.REFRESH_SUCCESS_PATTERN.search(content):
                self._current_event.success = True
                logger.info(f"  - 刷新成功！")

    def _cleanup_old_update_records(self) -> None:
        """清理旧的 Update 记录缓存（只保留最近 10 秒的记录）"""
        now = datetime.now()
        old_timestamps = []

        for timestamp in list(self._update_records_cache.keys()):
            if (now - timestamp).total_seconds() > 10:
                old_timestamps.append(timestamp)

        for timestamp in old_timestamps:
            del self._update_records_cache[timestamp]

        if old_timestamps:
            # logger.debug(f"清理了 {len(old_timestamps)} 条旧的 Update 记录")
            pass

    def _finalize_event(self, buy_events: List[BuyEvent],
                        refresh_events: List[RefreshEvent]) -> None:
        """完成事件处理

        参考 GameLogMonitor 的实现，识别移动操作（ResetItemsLayout, MoveWareHouseItems2）

        Args:
            buy_events: 购买事件列表
            refresh_events: 刷新事件列表
        """
        if not self._current_event:
            return

        event = self._current_event
        event_type = event.event_type

        # 识别移动操作（ResetItemsLayout, MoveWareHouseItems2）
        self._identify_move_operation(event)

        logger.info(f"========== 处理事件: {event_type}, success={event.success} ==========")

        # 对于购买事件，使用基于时间戳的 Update 配对逻辑
        if event_type == 'BuyVendorGoods':
            # 检查是否有物品变化（更新、添加或删除）
            has_changes = (len(event.item_updates) > 0 or
                         len(event.item_adds) > 0 or
                         len(event.item_deletes) > 0)

            if has_changes or event.success:
                self._process_buy_event_with_update_pairing(event, buy_events)
            else:
                logger.info("  没有检测到物品变化，跳过购买事件")

        elif event_type == 'RefreshVendorShop' and event.success:
            self._process_refresh_event(event, refresh_events)

        logger.info(f"========== 事件结束 ==========")

        # 保存上一个事件（用于跨事件配对）
        if event_type in ['Push2', 'BuyVendorGoods']:
            self._last_event = event
            # logger.debug(f"  保存上一个事件: {event_type}, 变更数={event.get_change_count()}")

        # 清空事件上下文
        self._current_event = None

    def _identify_move_operation(self, event: 'EventContext') -> None:
        """识别移动操作（参考 GameLogMonitor 的 MoveWareHouseItems2Parser）

        移动操作的判断条件：
        1. 物品在 ItemDeletes 和 ItemAdds/ItemUpdates 中都出现
        2. 物品的 PageId 不同

        Args:
            event: 事件上下文
        """
        if event.event_type not in ('ResetItemsLayout', 'MoveWareHouseItems2'):
            return

        # 收集删除的物品ID
        delete_item_ids = set()
        for delete in event.item_deletes:
            delete_item_ids.add(delete.item_id)

        # 收集添加/更新的物品ID
        add_update_item_ids = set()
        for add in event.item_adds:
            add_update_item_ids.add(add.item_id)
        for update in event.item_updates:
            add_update_item_ids.add(update.item_id)

        # 识别移动的物品（在删除和添加/更新中都出现）
        moved_item_ids = set()

        # 检查添加的物品是否是移动的
        for add in event.item_adds:
            if add.item_id in delete_item_ids:
                # 找到对应的删除记录
                for delete in event.item_deletes:
                    if delete.item_id == add.item_id:
                        if delete.page_id != add.page_id:
                            moved_item_ids.add(add.item_id)
                        break

        # 检查更新的物品是否是移动的
        for update in event.item_updates:
            if update.item_id in delete_item_ids:
                # 找到对应的删除记录
                for delete in event.item_deletes:
                    if delete.item_id == update.item_id:
                        if delete.page_id != update.page_id:
                            moved_item_ids.add(update.item_id)
                        break

        if moved_item_ids:
            # 标记为移动操作
            event.metadata['IsMoveOperation'] = True
            event.metadata['MovedItemIds'] = list(moved_item_ids)
            logger.info(f"  识别到移动操作: {len(moved_item_ids)} 个物品")
            # print(f"[日志解析]  识别到移动操作: {len(moved_item_ids)} 个物品")
        else:
            event.metadata['IsMoveOperation'] = False
            event.metadata['MovedItemIds'] = []

    def _process_buy_event_with_update_pairing(self, event: 'EventContext', buy_events: List[BuyEvent]) -> None:
        """处理购买事件（基于 Update 时间戳配对）

        配对逻辑：
        1. 从 BuyVendorGoods 事件中找到 5210（神威辉石）的 Update 记录
        2. 计算出神威辉石的消耗量
        3. 从 _update_records_cache 中查找时间戳最相近的其他物品 Update 记录
        4. 计算出该物品的增加数量
        5. 创建 BuyEvent（不验证是否匹配，交给 ExchangeVerificationService 处理）

        Args:
            event: BuyVendorGoods 事件上下文
            buy_events: 购买事件列表
        """
        logger.info(f"  尝试基于 Update 时间戳配对")

        # 从 BuyVendorGoods 事件中找到 5210 的 Update 记录
        gem_update = None
        gem_cost = 0
        gem_update_timestamp = None

        for update in event.item_updates:
            if update.base_id == GEM_BASE_ID:
                gem_update = update
                gem_update_timestamp = update.timestamp

                # 计算神威辉石消耗（使用事件开始时的实例快照）
                original_quantity = event.instance_snapshot.get(update.item_id, 0)
                gem_cost = abs(update.bag_num - original_quantity)
                logger.info(f"  找到神威辉石 Update: item_id={update.item_id}, 原始={original_quantity}, 新={update.bag_num}, 消耗={gem_cost}")
                break

        if not gem_update or gem_cost <= 0:
            # logger.debug("  未能提取神威辉石消耗，跳过配对")
            # print(f"[购买事件配对]  警告: 未能提取神威辉石消耗")
            return

        # 优先检查事件内的 Add 记录（购买的物品通常是新添加的）
        if event.item_adds:
            # 使用第一个 Add 记录作为购买的物品
            add_item = event.item_adds[0]
            item_base_id = add_item.base_id
            item_quantity = add_item.bag_num or 1

            logger.info(f"  使用事件内的 Add 记录: 物品={item_base_id}, 数量={item_quantity}")
            # print(f"[购买事件配对]  ✓ 找到 Add 记录: 物品={item_base_id}, 数量={item_quantity}")

            # 创建购买事件
            buy_event = self._create_buy_event(
                item_id=int(item_base_id),
                gem_cost=gem_cost,
                timestamp=event.end_time or gem_update_timestamp,
                quantity=item_quantity
            )

            if buy_event:
                buy_events.append(buy_event)
                logger.info(f"✓ 创建购买事件: {buy_event.item_name} x{buy_event.item_quantity}, 消耗神威辉石: {buy_event.gem_cost}")
                # print(f"[购买事件配对]  ✓ 创建购买事件: {buy_event.item_name} x{buy_event.item_quantity}, 消耗神威辉石: {buy_event.gem_cost}")
            return

        # 如果没有 Add 记录，从缓存中查找时间戳最相近的其他物品 Update 记录
        if not gem_update_timestamp:
            logger.warning("  神威辉石 Update 没有时间戳，无法配对")
            # print(f"[购买事件配对]  警告: 神威辉石 Update 没有时间戳")
            return

        # 尝试从缓存查找
        matched_item_update = self._find_nearest_item_update(gem_update_timestamp, GEM_BASE_ID)

        # 如果缓存中找不到，尝试使用事件内的其他 Update 记录
        if not matched_item_update and len(event.item_updates) > 1:
            logger.info("  缓存中未找到，尝试使用事件内的其他 Update 记录")
            for update in event.item_updates:
                if update.base_id != GEM_BASE_ID:
                    # 使用第一个非神威辉石的 Update 记录
                    matched_item_update = {
                        'base_id': update.base_id,
                        'item_id': update.item_id,
                        'bag_num': update.bag_num,
                        'timestamp': update.timestamp
                    }
                    logger.info(f"  使用事件内的 Update 记录: 物品={update.base_id}, 数量={update.bag_num}")
                    # print(f"[购买事件配对]  ✓ 找到事件内 Update: 物品={update.base_id}, 数量={update.bag_num}")
                    break

        # 如果事件内也找不到，尝试使用上一个事件（如 Push2）中的物品变更
        if not matched_item_update and self._last_event:
            logger.info(f"  事件内未找到，尝试使用上一个事件: {self._last_event.event_type}")
            # 优先使用 Update 记录
            for update in self._last_event.item_updates:
                if update.base_id != GEM_BASE_ID:
                    # 计算增加数量
                    original_quantity = self._last_event.instance_snapshot.get(update.item_id, 0)
                    increased_quantity = update.bag_num - original_quantity

                    if increased_quantity > 0:
                        matched_item_update = {
                            'base_id': update.base_id,
                            'item_id': update.item_id,
                            'bag_num': update.bag_num,
                            'timestamp': update.timestamp,
                            'increased_quantity': increased_quantity  # 保存增加的数量
                        }
                        logger.info(f"  使用上一个事件的 Update 记录: 物品={update.base_id}, 增加了{increased_quantity}个")
                        # print(f"[购买事件配对]  ✓ 找到上一个事件 Update: 物品={update.base_id}, 增加了{increased_quantity}个")
                        break

        if not matched_item_update:
            logger.warning("  未能找到购买的物品记录")
            # print(f"[购买事件配对]  警告: 未能找到购买的物品记录")
            return

        if not matched_item_update:
            logger.warning("  未找到匹配的物品 Update 记录")
            # print(f"[购买事件配对]  警告: 未找到匹配的物品 Update 记录")
            return

        # 从匹配的 Update 中提取物品信息
        item_base_id = matched_item_update['base_id']
        item_id_str = matched_item_update['item_id']
        item_timestamp = matched_item_update['timestamp']
        bag_num = matched_item_update['bag_num']

        # 计算物品增加数量
        # 如果是从上一个事件获取的，直接使用保存的 increased_quantity
        if 'increased_quantity' in matched_item_update:
            item_quantity = matched_item_update['increased_quantity']
        else:
            # 使用事件开始时的实例快照计算
            original_quantity = event.instance_snapshot.get(item_id_str, 0)
            item_quantity = bag_num - original_quantity

        logger.info(f"  匹配的物品 Update: ID={item_base_id}, 时间={item_timestamp.strftime('%H:%M:%S.%f')}, 原始={original_quantity}, 新={bag_num}, 增加={item_quantity}")
        logger.info(f"  时间差: {abs((item_timestamp - gem_update_timestamp).total_seconds()):.3f}秒")
        # print(f"[购买事件配对]  ✓ 找到匹配: 物品={item_base_id}, 数量={item_quantity}, 时间差={abs((item_timestamp - gem_update_timestamp).total_seconds()):.3f}秒")

        if item_quantity <= 0:
            # logger.debug(f"  物品数量未增加（数量={item_quantity}），跳过")
            # print(f"[购买事件配对]  警告: 物品数量未增加（数量={item_quantity}）")
            return

        # 创建购买事件（不验证是否匹配，交给 ExchangeVerificationService 处理）
        buy_event = self._create_buy_event(
            item_id=int(item_base_id),
            gem_cost=gem_cost,
            timestamp=event.end_time or gem_update_timestamp,
            quantity=item_quantity
        )

        if buy_event:
            buy_events.append(buy_event)
            logger.info(f"✓ 创建购买事件: {buy_event.item_name} x{buy_event.item_quantity}, 消耗神威辉石: {buy_event.gem_cost}")
            # print(f"[购买事件配对]  ✓ 创建购买事件: {buy_event.item_name} x{buy_event.item_quantity}, 消耗神威辉石: {buy_event.gem_cost}")

    def _find_nearest_item_update(self, target_timestamp: datetime, exclude_base_id: str) -> Optional[dict]:
        """查找时间戳最相近的 Update 记录（排除指定物品）

        时间戳范围限制：目标时间戳 ± 10 毫秒

        Args:
            target_timestamp: 目标时间戳（神威辉石 Update 的时间戳）
            exclude_base_id: 要排除的物品基础ID（如神威辉石）

        Returns:
            匹配的 Update 记录，如果没有返回 None
        """
        # 时间戳范围：目标时间戳 ± 100 毫秒
        time_range_ms = 0.100  # 100 毫秒 = 0.100 秒
        min_timestamp = target_timestamp - timedelta(seconds=time_range_ms)
        max_timestamp = target_timestamp + timedelta(seconds=time_range_ms)

        # logger.debug(f"  时间戳查找范围: {min_timestamp.strftime('%H:%M:%S.%f')} ~ {max_timestamp.strftime('%H:%M:%S.%f')}")
        # logger.debug(f"  缓存中共有 {len(self._update_records_cache)} 条 Update 记录")

        best_match = None
        min_time_diff = float('inf')

        for timestamp, record in self._update_records_cache.items():
            # 排除指定物品
            if record['base_id'] == exclude_base_id:
                continue

            # 检查是否在时间戳范围内（± 10 毫秒）
            if not (min_timestamp <= timestamp <= max_timestamp):
                # logger.debug(f"  跳过 Update: 物品={record['base_id']}, 时间戳={timestamp.strftime('%H:%M:%S.%f')}（超出范围）")
                continue

            # 计算时间差
            time_diff = abs((timestamp - target_timestamp).total_seconds())

            # logger.debug(f"  检查 Update: 物品={record['base_id']}, 时间戳={timestamp.strftime('%H:%M:%S.%f')}, 时间差={time_diff*1000:.3f}毫秒")

            # 找到时间差最小的记录
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                best_match = record
                best_match['timestamp'] = timestamp
                # logger.debug(f"    找到更好的匹配: 物品={record['base_id']}, 时间差={time_diff*1000:.3f}毫秒")

        if best_match:
            logger.info(f"  ✓ 找到最佳匹配: 物品={best_match['base_id']}, 时间差={min_time_diff*1000:.3f}毫秒")
        else:
            # logger.warning(f"  ✗ 未找到在时间范围内的 Update 记录")
            # 输出缓存中的所有记录用于调试
            # logger.debug(f"  缓存中的所有记录（前5条）：")
            # for idx, (timestamp, record) in enumerate(list(self._update_records_cache.items())[:5]):
            #     time_diff = abs((timestamp - target_timestamp).total_seconds())
            #     logger.debug(f"    [{idx}] 物品={record['base_id']}, 时间戳={timestamp.strftime('%H:%M:%S.%f')}, 时间差={time_diff*1000:.3f}毫秒")
            pass

        return best_match

    def _process_buy_event(self, event: 'EventContext', buy_events: List[BuyEvent]) -> None:
        """处理购买事件

        参考 GameLogMonitor 的实现，不使用快照，而是直接基于事件内的 Update/Add/Delete 操作计算变化

        Args:
            event: 事件上下文
            buy_events: 购买事件列表
        """
        logger.info(f"  事件内变更数: {event.get_change_count()} (更新: {len(event.item_updates)}, 添加: {len(event.item_adds)}, 删除: {len(event.item_deletes)})")

        # 检查是否是移动操作
        is_move_operation = event.metadata.get('IsMoveOperation', False)
        moved_item_ids = event.metadata.get('MovedItemIds', [])

        if is_move_operation:
            logger.info("  检测到移动操作，跳过购买事件处理")
            # print(f"[购买事件]  检测到移动操作，跳过")
            return

        # 收集所有消耗和获得的物品
        spent_items = []  # 消耗的物品列表
        gained_items = []  # 获得的物品列表

        # 处理 Update 操作（参考 GameLogMonitor 的 ItemInventoryHandler）
        for update in event.item_updates:
            base_id = update.base_id
            item_id = update.item_id  # 使用完整的 item_id

            # 跳过移动物品
            if item_id in moved_item_ids:
                # logger.debug(f"  跳过移动物品: {base_id}({item_id})")
                continue

            # 从事件快照中获取该实例的原始数量
            original_quantity = event.instance_snapshot.get(item_id, 0)

            # 计算变化（参考 GameLogMonitor: current - original）
            new_quantity = update.bag_num
            delta = new_quantity - original_quantity

            # logger.debug(f"  Update操作: {base_id}({item_id}), 原始={original_quantity}, 新={new_quantity}, 变化={delta}")

            if delta < 0:
                # 物品消耗
                spent_items.append({
                    'base_id': base_id,
                    'delta': delta,
                    'quantity': abs(delta)
                })
                logger.info(f"    - {base_id}: {abs(delta)} (delta={delta})")
                # if base_id == GEM_BASE_ID:
                #     print(f"[购买事件]    ✓ 神威辉石消耗: {abs(delta)}")
            elif delta > 0:
                # 物品增加
                gained_items.append({
                    'base_id': base_id,
                    'delta': delta,
                    'quantity': delta
                })
                logger.info(f"    + {base_id}: {delta} (delta={delta})")
                # if base_id != GEM_BASE_ID:
                #     print(f"[购买事件]    ✓ 物品: {base_id}, 数量: {delta}")
        
        # 处理 Add 操作
        for add in event.item_adds:
            base_id = add.base_id
            item_id = add.item_id
            quantity = add.bag_num or 1

            # 跳过移动物品
            if item_id in moved_item_ids:
                # logger.debug(f"  跳过移动物品: {base_id}({item_id})")
                continue

            # Add 操作表示物品增加
            gained_items.append({
                'base_id': base_id,
                'delta': quantity,
                'quantity': quantity
            })
            logger.info(f"    + {base_id}: {quantity} (Add)")
            # if base_id != GEM_BASE_ID:
            #     print(f"[购买事件]    ✓ 物品: {base_id}, 数量: {quantity}")

        # 处理 Delete 操作
        for delete in event.item_deletes:
            base_id = delete.base_id
            item_id = delete.item_id  # 使用完整的 item_id

            # 跳过移动物品
            if item_id in moved_item_ids:
                # logger.debug(f"  跳过移动物品: {base_id}({item_id})")
                continue

            # 从事件快照中获取该实例的原始数量
            original_quantity = event.instance_snapshot.get(item_id, 0)

            # Delete 操作表示物品全部删除
            delta = -original_quantity
            spent_items.append({
                'base_id': base_id,
                'delta': delta,
                'quantity': abs(delta)
            })
            logger.info(f"    - {base_id}: {abs(delta)} (Delete)")
        
        logger.info(f"  消耗的物品: {len(spent_items)} 个")
        logger.info(f"  获得的物品: {len(gained_items)} 个")
        
        # 从消耗中找神威辉石
        gem_cost = 0
        for item in spent_items:
            if item['base_id'] == GEM_BASE_ID:
                gem_cost = item['quantity']
                logger.info(f"  检测到神威辉石消耗: {gem_cost}")
                # print(f"[购买事件]  检测到神威辉石消耗: {gem_cost}")
                break
        
        if gem_cost > 0:
            # 过滤掉神威辉石
            non_gem_gained = [item for item in gained_items if item['base_id'] != GEM_BASE_ID]
            
            if non_gem_gained:
                # 有物品增加，使用第一个增加的物品
                first_gained = non_gem_gained[0]
                buy_event = self._create_buy_event(
                    item_id=int(first_gained['base_id']),
                    gem_cost=gem_cost,
                    timestamp=event.end_time,
                    quantity=first_gained['quantity']
                )
                if buy_event:
                    buy_events.append(buy_event)
                    logger.info(f"✓ 创建购买事件: {buy_event.item_name} x{buy_event.item_quantity}, 消耗神威辉石: {buy_event.gem_cost}")
                    # print(f"[购买事件]  ✓ 创建购买事件: {buy_event.item_name} x{buy_event.item_quantity}, 消耗神威辉石: {buy_event.gem_cost}")
            else:
                # 没有物品增加（可能是消耗型物品或特殊情况）
                logger.info(f"没有检测到物品增加，检查是否有其他变化")
                # print(f"[购买事件]  没有检测到物品增加，检查其他变化")

                # 检查 item_updates 中是否有非神威辉石物品的更新
                for update in event.item_updates:
                    base_id = update.base_id
                    item_id = update.item_id

                    # 跳过移动物品
                    if item_id in moved_item_ids:
                        continue

                    if update.base_id != GEM_BASE_ID:
                        # 计算这个物品的 delta
                        original_quantity = event.instance_snapshot.get(item_id, 0)
                        delta = update.bag_num - original_quantity

                        logger.info(f"  候选物品（从更新中）: {base_id}({item_id}), 原始={original_quantity}, 新={update.bag_num}, 变化={delta}")

                        # 情况1：数量增加（delta > 0）- 正常的购买
                        if delta > 0:
                            buy_event = self._create_buy_event(
                                item_id=int(update.base_id),
                                gem_cost=gem_cost,
                                timestamp=event.end_time,
                                quantity=delta
                            )
                            if buy_event:
                                buy_events.append(buy_event)
                                logger.info(f"✓ 创建购买事件（数量增加）: {buy_event.item_name} x{buy_event.item_quantity}, 消耗神威辉石: {buy_event.gem_cost}")
                                # print(f"[购买事件]  ✓ 创建购买事件（数量增加）: {buy_event.item_name} x{buy_event.item_quantity}, 消耗神威辉石: {buy_event.gem_cost}")
                            break

                        # 情况2：数量减少（delta < 0）- 可能是消耗型物品被错误识别
                        # 这种情况下，购买数量 = abs(delta)（实际增加的数量）
                        elif delta < 0:
                            # 物品数量减少，但这是购买事件，说明可能记录有误
                            # 尝试使用 abs(delta) 作为购买数量
                            bought_quantity = abs(delta)
                            buy_event = self._create_buy_event(
                                item_id=int(update.base_id),
                                gem_cost=gem_cost,
                                timestamp=event.end_time,
                                quantity=bought_quantity
                            )
                            if buy_event:
                                buy_events.append(buy_event)
                                logger.info(f"✓ 创建购买事件（消耗型，数量={bought_quantity}）: {buy_event.item_name} x{buy_event.item_quantity}, 消耗神威辉石: {buy_event.gem_cost}")
                                # print(f"[购买事件]  ✓ 创建购买事件（消耗型，数量={bought_quantity}）: {buy_event.item_name} x{buy_event.item_quantity}, 消耗神威辉石: {buy_event.gem_cost}")
                            break
                else:
                    # 无法识别购买的物品，但仍然记录神威辉石消耗
                    logger.warning(f"无法识别购买的物品，但记录了神威辉石消耗: {gem_cost}")
                    # print(f"[购买事件]  警告: 无法识别购买的物品，但记录了神威辉石消耗: {gem_cost}")
        else:
            logger.warning(f"未能识别购买事件（没有检测到神威辉石消耗）")
            # print(f"[购买事件]  警告: 未能识别购买事件（没有检测到神威辉石消耗）")

    def _process_refresh_event(self, event: 'EventContext',
                              refresh_events: List[RefreshEvent]) -> None:
        """处理刷新事件

        参考 GameLogMonitor 的实现，不使用快照，而是直接基于事件内的 Update/Delete 操作计算变化

        Args:
            event: 事件上下文
            refresh_events: 刷新事件列表
        """
        logger.info(f"  事件内变更数: {event.get_change_count()} (更新: {len(event.item_updates)}, 添加: {len(event.item_adds)}, 删除: {len(event.item_deletes)})")

        # 收集所有消耗的物品
        spent_items = []

        # 处理 Update 操作
        for update in event.item_updates:
            base_id = update.base_id
            item_id = update.item_id  # 使用完整的 item_id

            # 从事件快照中获取该实例的原始数量
            original_quantity = event.instance_snapshot.get(item_id, 0)

            # 计算变化
            new_quantity = update.bag_num
            delta = new_quantity - original_quantity

            if delta < 0:
                # 物品消耗
                spent_items.append({
                    'base_id': base_id,
                    'delta': delta,
                    'quantity': abs(delta)
                })
                logger.info(f"    - {base_id}: {abs(delta)} (delta={delta})")

        # 处理 Delete 操作
        for delete in event.item_deletes:
            base_id = delete.base_id
            item_id = delete.item_id  # 使用完整的 item_id

            # 从事件快照中获取该实例的原始数量
            original_quantity = event.instance_snapshot.get(item_id, 0)

            # Delete 操作表示物品全部删除
            delta = -original_quantity
            spent_items.append({
                'base_id': base_id,
                'delta': delta,
                'quantity': abs(delta)
            })
            logger.info(f"    - {base_id}: {abs(delta)} (Delete)")

        # 从消耗中找神威辉石
        gem_cost = 50  # 默认值
        for item in spent_items:
            if item['base_id'] == GEM_BASE_ID:
                gem_cost = item['quantity']
                logger.info(f"  检测到神威辉石消耗: {gem_cost}")
                # print(f"[刷新事件]  检测到神威辉石消耗: {gem_cost}")
                break
        
        refresh_event = RefreshEvent(
            timestamp=event.end_time,
            gem_cost=gem_cost,
            log_context={'snapshot': event.snapshot, 'changes': spent_items}
        )
        refresh_events.append(refresh_event)
        logger.info(f"✓ 创建刷新事件: 消耗神威辉石: {gem_cost}, 时间: {refresh_event.timestamp.strftime('%H:%M:%S')}")

    def _create_buy_event(self, item_id: int, gem_cost: int, 
                         timestamp: datetime, quantity: int) -> Optional[BuyEvent]:
        """创建购买事件
        
        Args:
            item_id: 物品ID
            gem_cost: 消耗的神威辉石数量
            timestamp: 时间戳
            quantity: 物品数量
            
        Returns:
            BuyEvent对象，如果创建失败返回None
        """
        try:
            # 尝试从item.json中查找名称
            item_name = f"Item_{item_id}"
            
            item_json_path = os.path.join(os.path.dirname(__file__), '..', 'item.json')
            if os.path.exists(item_json_path):
                import json
                with open(item_json_path, 'r', encoding='utf-8') as f:
                    item_data = json.load(f)
                    if str(item_id) in item_data:
                        item_name = item_data[str(item_id)].get('Name', f"Item_{item_id}")
            
            return BuyEvent(
                timestamp=timestamp,
                item_id=item_id,
                item_name=item_name,
                item_quantity=quantity,
                gem_cost=gem_cost,
                log_context={}
            )
        except Exception as e:
            logger.error(f"创建购买事件失败: {e}", exc_info=True)
            return None

    def _parse_log_line(self, line: str) -> Optional[LogLine]:
        """解析单行日志
        
        Args:
            line: 日志行文本
            
        Returns:
            解析后的LogLine对象，如果解析失败返回None
        """
        if not line.strip() or '[Game]' not in line:
            return None

        try:
            # 提取时间戳: [2026.02.13-08.23.26:996]
            time_match = re.search(r'\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}:\d{3})\]', line)
            if time_match:
                timestamp_str = time_match.group(1)
                timestamp = datetime.strptime(timestamp_str, '%Y.%m.%d-%H.%M.%S:%f')

                # 提取[Game]后面的内容
                game_match = re.search(r'\[Game\]\s*(.*)', line)
                if game_match:
                    content = game_match.group(1).strip()
                    return LogLine(timestamp=timestamp, content=content, raw_line=line)

        except (ValueError, IndexError) as e:
            # logger.debug(f"解析日志行失败: {line[:100]}, 错误: {e}")
            pass

        return None

    def reset_position(self) -> None:
        """重置读取位置，从头开始读取日志"""
        self._last_position = 0
        self._last_size = 0
        self._inventory_manager.reset_backpack_initialized()
        self._update_records_cache.clear()  # 清理 Update 记录缓存
        self._player_name = None
        self._player_season_id = None
        logger.info("日志读取位置和背包状态已重置")
    
    def get_player_info(self) -> Optional[PlayerInfo]:
        """获取当前玩家信息
        
        Returns:
            PlayerInfo对象，如果未获取到玩家信息返回None
        """
        if self._player_name is None:
            return None
        
        season_info = self._season_service.get_current_season_info()
        
        return PlayerInfo(
            name=self._player_name,
            season_id=self._player_season_id,
            season_type=season_info.season_type,
            timestamp=None
        )
    
    def get_season_info(self):
        """获取当前服务器信息
        
        Returns:
            SeasonInfoSnapshot对象
        """
        return self._season_service.get_current_season_info()
    
    def get_season_label(self) -> str:
        """获取当前服务器的显示标签
        
        Returns:
            服务器标签，如"赛季区"、"永久区"等
        """
        return self._season_service.get_season_label()


class EventContext:
    """事件上下文

    参考 GameLogMonitor 的设计，使用三个独立列表存储不同类型的物品变更：
    - ItemUpdates: 物品更新（数量变化）
    - ItemAdds: 物品添加
    - ItemDeletes: 物品删除
    """

    def __init__(self, event_type: str, start_time: datetime, snapshot: Dict[str, int], instance_snapshot: Dict[str, int] = None):
        self.event_type = event_type  # 事件类型
        self.start_time = start_time  # 开始时间
        self.end_time: Optional[datetime] = None  # 结束时间
        self.snapshot = snapshot  # 事件开始时的背包快照（累加后的base_id）
        self.instance_snapshot = instance_snapshot or {}  # 事件开始时的物品实例快照（精确的item_id）

        # 物品变更列表（参考 GameLogMonitor 的设计）
        self.item_updates: list = []  # 物品更新
        self.item_adds: list = []  # 物品添加
        self.item_deletes: list = []  # 物品删除

        self.success = False  # 操作是否成功
        self.metadata: Dict = {}  # 元数据（用于标记移动操作等）
    
    def add_change(self, change: ItemChange) -> None:
        """添加物品变更到事件
        
        根据 change_type 自动添加到对应的列表：
        - 'update' -> item_updates
        - 'add' -> item_adds
        - 'delete' -> item_deletes
        
        Args:
            change: 物品变更信息
        """
        if change.change_type == 'update':
            self.item_updates.append(change)
        elif change.change_type == 'add':
            self.item_adds.append(change)
        elif change.change_type == 'delete':
            self.item_deletes.append(change)
    
    def add_update(self, change: ItemChange) -> None:
        """添加物品更新
        
        Args:
            change: 物品变更信息
        """
        self.item_updates.append(change)
    
    def add_add(self, change: ItemChange) -> None:
        """添加物品添加
        
        Args:
            change: 物品变更信息
        """
        self.item_adds.append(change)
    
    def add_delete(self, change: ItemChange) -> None:
        """添加物品删除
        
        Args:
            change: 物品变更信息
        """
        self.item_deletes.append(change)
    
    @property
    def changes(self) -> list:
        """获取所有变更（兼容性属性）"""
        return self.item_updates + self.item_adds + self.item_deletes
    
    def get_change_count(self) -> int:
        """获取总变更数量"""
        return len(self.item_updates) + len(self.item_adds) + len(self.item_deletes)
