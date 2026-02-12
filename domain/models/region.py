"""识别区域领域模型"""
from dataclasses import dataclass


@dataclass
class Region:
    """识别区域"""
    name: str
    x: int
    y: int
    width: int
    height: int

    def contains_point(self, x: int, y: int) -> bool:
        """检查点是否在区域内

        Args:
            x: x坐标
            y: y坐标

        Returns:
            是否在区域内
        """
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)

    def contains_center(self, x: int, y: int, width: int, height: int) -> bool:
        """检查矩形中心点是否在区域内

        Args:
            x: 左上角x坐标
            y: 左上角y坐标
            width: 宽度
            height: 高度

        Returns:
            中心点是否在区域内
        """
        center_x = x + width / 2
        center_y = y + height / 2
        return self.contains_point(center_x, center_y)

    def get_bounding_box(self) -> dict:
        """获取边界框字典

        Returns:
            {x, y, width, height}
        """
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height
        }
