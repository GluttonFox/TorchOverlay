"""兑换记录领域模型"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExchangeRecord:
    """兑换记录（验证通过的购买）"""
    timestamp: datetime  # 购买时间
    item_name: str  # 物品名称
    item_id: int  # 物品ID
    item_quantity: str  # 物品数量（OCR识别的原始文本，如"x5"）
    original_price: float  # 原价
    converted_price: float  # 折后价
    profit: float  # 利润
    gem_cost: int  # 实际消耗的神威辉石数量
    ocr_timestamp: datetime  # OCR识别时间
    log_timestamp: datetime  # 日志记录时间
    verified: bool = True  # 已验证通过

    def to_dict(self) -> dict:
        """转换为字典格式用于JSON存储"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'item_name': self.item_name,
            'item_id': self.item_id,
            'item_quantity': self.item_quantity,
            'original_price': self.original_price,
            'converted_price': self.converted_price,
            'profit': self.profit,
            'gem_cost': self.gem_cost,
            'ocr_timestamp': self.ocr_timestamp.isoformat() if self.ocr_timestamp else None,
            'log_timestamp': self.log_timestamp.isoformat(),
            'verified': self.verified
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ExchangeRecord':
        """从字典创建对象"""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            item_name=data['item_name'],
            item_id=data['item_id'],
            item_quantity=data['item_quantity'],
            original_price=data['original_price'],
            converted_price=data['converted_price'],
            profit=data['profit'],
            gem_cost=data['gem_cost'],
            ocr_timestamp=datetime.fromisoformat(data['ocr_timestamp']) if data.get('ocr_timestamp') else None,
            log_timestamp=datetime.fromisoformat(data['log_timestamp']),
            verified=data.get('verified', True)
        )


@dataclass
class OcrRecognitionRecord:
    """OCR识别记录（所有识别结果）"""
    timestamp: datetime
    item_name: str
    item_id: int | None = None  # 物品ID（通过ItemPriceService查询）
    item_quantity: str = ""
    original_price: float = 0.0
    converted_price: float = 0.0
    profit: float = 0.0
    gem_cost: str = ""  # OCR识别的价格（字符串格式）
    verified: bool = False
    verified_by_event_id: str | None = None
    expire_time: datetime | None = None

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'item_name': self.item_name,
            'item_id': self.item_id,
            'item_quantity': self.item_quantity,
            'original_price': self.original_price,
            'converted_price': self.converted_price,
            'profit': self.profit,
            'gem_cost': self.gem_cost,
            'verified': self.verified,
            'verified_by_event_id': self.verified_by_event_id,
            'expire_time': self.expire_time.isoformat() if self.expire_time else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'OcrRecognitionRecord':
        """从字典创建对象"""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            item_name=data['item_name'],
            item_id=data.get('item_id'),  # 兼容旧数据
            item_quantity=data['item_quantity'],
            original_price=data['original_price'],
            converted_price=data['converted_price'],
            profit=data['profit'],
            gem_cost=data['gem_cost'],
            verified=data.get('verified', False),
            verified_by_event_id=data.get('verified_by_event_id'),
            expire_time=datetime.fromisoformat(data['expire_time']) if data.get('expire_time') else None
        )
