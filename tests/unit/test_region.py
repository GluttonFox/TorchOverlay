"""Region模型测试"""
import pytest

from domain.models.region import Region


class TestRegion:
    """Region模型测试类"""

    def test_create_region(self):
        """测试创建Region"""
        region = Region(
            name="测试区域",
            x=100,
            y=200,
            width=300,
            height=400
        )

        assert region.name == "测试区域"
        assert region.x == 100
        assert region.y == 200
        assert region.width == 300
        assert region.height == 400

    def test_contains_point_inside(self):
        """测试点在区域内"""
        region = Region(name="测试", x=100, y=100, width=200, height=200)

        # 区域内的点
        assert region.contains_point(150, 150)
        assert region.contains_point(100, 100)  # 左上角
        assert region.contains_point(300, 300)  # 右下角
        assert region.contains_point(250, 200)

    def test_contains_point_outside(self):
        """测试点在区域外"""
        region = Region(name="测试", x=100, y=100, width=200, height=200)

        # 区域外的点
        assert not region.contains_point(50, 150)  # 左侧
        assert not region.contains_point(150, 50)  # 上方
        assert not region.contains_point(350, 150)  # 右侧
        assert not region.contains_point(150, 350)  # 下方

    def test_contains_point_boundary(self):
        """测试边界情况"""
        region = Region(name="测试", x=100, y=100, width=200, height=200)

        # 边界上的点应该在区域内
        assert region.contains_point(100, 100)  # 左上角
        assert region.contains_point(299, 100)  # 右上角（不包括300）
        assert region.contains_point(100, 299)  # 左下角（不包括300）
        assert region.contains_point(299, 299)  # 右下角（不包括300）

        # 边界外的点（刚好在边界线上）
        assert not region.contains_point(99, 100)  # 左边界外
        assert not region.contains_point(300, 100)  # 右边界外
        assert not region.contains_point(100, 99)  # 上边界外
        assert not region.contains_point(100, 300)  # 下边界外

    def test_contains_center_inside(self):
        """测试矩形中心在区域内"""
        region = Region(name="测试", x=100, y=100, width=200, height=200)

        # 中心在区域内的矩形
        assert region.contains_center(150, 150, 50, 50)  # 中心(175, 175)
        assert region.contains_center(100, 100, 100, 100)  # 中心(150, 150)

    def test_contains_center_outside(self):
        """测试矩形中心在区域外"""
        region = Region(name="测试", x=100, y=100, width=200, height=200)

        # 中心在区域外的矩形
        assert not region.contains_center(50, 50, 100, 100)  # 中心(100, 100) - 边界上
        assert not region.contains_center(0, 0, 100, 100)  # 中心(50, 50)
        assert not region.contains_center(250, 250, 100, 100)  # 中心(300, 300)

    def test_get_bounding_box(self):
        """测试获取边界框"""
        region = Region(name="测试", x=100, y=200, width=300, height=400)

        bbox = region.get_bounding_box()

        assert bbox['x'] == 100
        assert bbox['y'] == 200
        assert bbox['width'] == 300
        assert bbox['height'] == 400

    def test_zero_size_region(self):
        """测试零大小区域"""
        region = Region(name="测试", x=100, y=100, width=0, height=0)

        # 只有原点在区域内
        assert region.contains_point(100, 100)
        assert not region.contains_point(101, 100)

    def test_negative_coordinates(self):
        """测试负坐标"""
        region = Region(name="测试", x=-100, y=-100, width=200, height=200)

        # 测试包含负坐标的点
        assert region.contains_point(0, 0)  # 中心
        assert region.contains_point(-50, -50)
        assert not region.contains_point(-150, 0)

    def test_large_region(self):
        """测试大区域"""
        region = Region(name="测试", x=0, y=0, width=1920, height=1080)

        # 测试大区域
        assert region.contains_point(960, 540)  # 中心
        assert region.contains_point(0, 0)  # 左上角
        assert region.contains_point(1919, 1079)  # 右下角
        assert not region.contains_point(1920, 1080)  # 边界外
