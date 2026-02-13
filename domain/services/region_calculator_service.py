"""区域计算领域服务 - 负责识别区域的计算"""
from domain.models.region import Region


class RegionCalculatorService:
    """区域计算服务 - 从 config.py 拆分出来"""

    # 基准分辨率
    BASE_WIDTH = 1920
    BASE_HEIGHT = 1080

    def calculate_for_resolution(
        self,
        client_width: int,
        client_height: int
    ) -> tuple[Region, list[Region]]:
        """根据分辨率计算识别区域

        Args:
            client_width: 窗口client区域宽度
            client_height: 窗口client区域高度

        Returns:
            (balance_region, item_regions): 余额区域和物品区域列表
        """
        # 计算缩放比例
        scale_x = client_width / self.BASE_WIDTH
        scale_y = client_height / self.BASE_HEIGHT

        # 创建余额区域
        balance_region = self._create_balance_region(scale_x, scale_y)

        # 创建物品区域
        item_regions = self._create_item_regions(scale_x, scale_y)

        return balance_region, item_regions

    def calculate_combined_region(self, *regions: Region) -> Region:
        """计算包含所有区域的最小边界框

        Args:
            *regions: 可变数量的区域

        Returns:
            合并后的区域
        """
        if not regions:
            return Region(name="empty", x=0, y=0, width=0, height=0)

        min_x = min(r.x for r in regions)
        min_y = min(r.y for r in regions)
        max_x = max(r.x + r.width for r in regions)
        max_y = max(r.y + r.height for r in regions)

        return Region(
            name="combined",
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y
        )

    def _create_balance_region(self, scale_x: float, scale_y: float) -> Region:
        """创建余额区域

        Args:
            scale_x: x方向缩放比例
            scale_y: y方向缩放比例

        Returns:
            余额区域
        """
        # 基准余额区域坐标
        base_balance = {
            "name": "余额区域",
            "x": 1735,
            "y": 36,
            "width": 100,
            "height": 40
        }

        return Region(
            name=base_balance["name"],
            x=int(base_balance["x"] * scale_x),
            y=int(base_balance["y"] * scale_y),
            width=int(base_balance["width"] * scale_x),
            height=int(base_balance["height"] * scale_y)
        )

    def _create_item_regions(self, scale_x: float, scale_y: float) -> list[Region]:
        """创建物品区域

        Args:
            scale_x: x方向缩放比例
            scale_y: y方向缩放比例

        Returns:
            物品区域列表
        """
        # 基准物品区域网格参数
        base_items = {
            "start_x": 423,
            "start_y": 157,
            "width": 200,
            "height": 200,
            "horizontal_spacing": 10,
            "vertical_spacing": 10,
            "rows": 2,
            "cols": 6
        }

        # 生成物品区域（第1行6列，第2行2列）
        item_regions = []
        for row in range(base_items["rows"]):
            cols_in_row = 2 if row == 1 else 6
            for col in range(cols_in_row):
                x = int((base_items["start_x"] + col * (base_items["width"] + base_items["horizontal_spacing"])) * scale_x)
                y = int((base_items["start_y"] + row * (base_items["height"] + base_items["vertical_spacing"])) * scale_y)
                width = int(base_items["width"] * scale_x)
                height = int(base_items["height"] * scale_y)

                item_regions.append(Region(
                    name=f"item_r{row}_c{col}",
                    x=x,
                    y=y,
                    width=width,
                    height=height
                ))

        return item_regions
