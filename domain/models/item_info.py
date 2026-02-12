"""物品信息领域模型"""
from dataclasses import dataclass


@dataclass
class ItemInfo:
    """物品信息"""
    index: int
    region_name: str
    name: str
    quantity: str
    price: str
    is_sold_out: bool = False

    @property
    def is_valid(self) -> bool:
        """检查物品信息是否有效"""
        return self.name != "--" and self.name.strip()

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'index': self.index,
            'region_name': self.region_name,
            'name': self.name,
            'quantity': self.quantity,
            'price': self.price,
            'is_sold_out': self.is_sold_out
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ItemInfo':
        """从字典创建"""
        return cls(
            index=data['index'],
            region_name=data['region_name'],
            name=data['name'],
            quantity=data['quantity'],
            price=data['price'],
            is_sold_out=data.get('is_sold_out', False)
        )
