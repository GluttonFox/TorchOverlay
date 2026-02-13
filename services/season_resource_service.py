"""服务器资源服务 - 管理不同服务器的配置和数据"""
import os
from typing import Optional, Dict
from dataclasses import dataclass

from core.logger import get_logger
from domain.models.season import SeasonServerType, resolve_season_type

logger = get_logger(__name__)


@dataclass
class SeasonInfoSnapshot:
    """赛季信息快照"""
    season_id: Optional[int]
    season_type: SeasonServerType
    is_recognized: bool  # 是否被识别（unknown但使用了默认配置）


@dataclass
class SeasonLoadResult:
    """赛季加载结果"""
    season_changed: bool  # 服务器是否改变
    previous_season: SeasonServerType
    current_season: SeasonServerType
    is_recognized: bool


class SeasonResourceService:
    """服务器资源服务
    
    功能：
    1. 根据赛季ID加载对应服务器的配置
    2. 管理不同服务器的数据文件路径
    3. 提供服务器切换通知
    """
    
    # 赛季ID常量
    PERMANENT_ZONE_ID = 1
    SEASON_ZONE_ID = 1201
    EXPERT_ZONE_ID = 1231
    
    def __init__(self, base_dir: str | None = None):
        """初始化服务器资源服务
        
        Args:
            base_dir: 基础目录，如果为None则使用项目根目录
        """
        self._base_dir = base_dir or os.path.dirname(os.path.dirname(__file__))
        self._current_season: SeasonServerType = SeasonServerType.UNKNOWN
        self._current_season_id: Optional[int] = None
        self._is_recognized = False
        self._lock = None  # 如果需要多线程支持，可以使用 threading.Lock()
        
        logger.info("服务器资源服务已初始化")
    
    def load_for_season(self, season_id: int) -> SeasonLoadResult:
        """为指定赛季加载配置
        
        Args:
            season_id: 赛季ID
            
        Returns:
            赛季加载结果
        """
        resolved_season = resolve_season_type(season_id)
        
        previous_season = self._current_season
        is_recognized = resolved_season != SeasonServerType.UNKNOWN
        target_season = is_recognized or SeasonServerType.SEASON_ZONE
        
        if not is_recognized:
            logger.info(f"收到未知 SeasonId={season_id}，将沿用赛季服配置")
        
        # 检查是否需要切换
        if (self._current_season == target_season and 
            self._current_season_id == season_id and 
            self._is_recognized == is_recognized):
            # logger.debug(f"赛区未变化，跳过数据加载: {target_season}")
            return SeasonLoadResult(
                season_changed=False,
                previous_season=previous_season,
                current_season=self._current_season,
                is_recognized=self._is_recognized
            )
        
        # 切换服务器
        self._current_season_id = season_id
        self._current_season = target_season
        self._is_recognized = is_recognized
        
        logger.info(f"已切换到 {target_season} (SeasonId={season_id})")
        
        return SeasonLoadResult(
            season_changed=True,
            previous_season=previous_season,
            current_season=self._current_season,
            is_recognized=self._is_recognized
        )
    
    def get_current_season_info(self) -> SeasonInfoSnapshot:
        """获取当前赛季信息
        
        Returns:
            赛季信息快照
        """
        return SeasonInfoSnapshot(
            season_id=self._current_season_id,
            season_type=self._current_season,
            is_recognized=self._is_recognized
        )
    
    def get_season_label(self) -> str:
        """获取当前服务器的显示标签
        
        Returns:
            服务器标签，如"赛季区"、"永久区"等
        """
        return str(self._current_season)
    
    def is_season_loaded(self) -> bool:
        """检查是否已加载赛季配置
        
        Returns:
            如果已加载返回True
        """
        return self._current_season != SeasonServerType.UNKNOWN
    
    def get_data_file_path(self, file_type: str) -> str:
        """获取当前服务器的数据文件路径
        
        Args:
            file_type: 文件类型，如 'price_equipment', 'price_skill', 'price_consumable'
            
        Returns:
            文件绝对路径
        """
        # 根据服务器类型构建路径
        season_dir = {
            SeasonServerType.PERMANENT_ZONE: "PermanentZone",
            SeasonServerType.SEASON_ZONE: "SeasonZone",
            SeasonServerType.EXPERT_ZONE: "ExpertZone"
        }.get(self._current_season, "SeasonZone")
        
        filename = f"{file_type}.json"
        return os.path.join(self._base_dir, season_dir, filename)
    
    def reset(self) -> None:
        """重置服务到初始状态"""
        self._current_season = SeasonServerType.UNKNOWN
        self._current_season_id = None
        self._is_recognized = False
        logger.info("服务器资源服务已重置")
