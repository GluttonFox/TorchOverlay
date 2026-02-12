"""测试夹具和Mock工具"""
import pytest
from pathlib import Path

from core.config import AppConfig, OcrConfig


@pytest.fixture
def sample_config():
    """示例配置fixture"""
    return AppConfig(
        app_title_prefix="TorchOverlay",
        keywords=("火炬之光", "火炬之光无限"),
        watch_interval_ms=1000,
        elevated_marker="管理员",
        ocr=OcrConfig(
            api_key="test_api_key",
            secret_key="test_secret_key",
            api_name="accurate",
            timeout_sec=5.0,
            max_retries=3,
            debug_mode=False
        ),
        last_price_update=None,
        enable_tax_calculation=False,
        mystery_gem_mode="min"
    )


@pytest.fixture
def temp_output_dir(tmp_path: Path):
    """临时输出目录fixture"""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return str(output_dir)


@pytest.fixture
def sample_image_path(tmp_path: Path):
    """示例图片路径fixture"""
    # 创建一个测试图片
    from PIL import Image
    import numpy as np
    
    # 创建一个简单的测试图片
    img_array = np.ones((100, 100, 3), dtype=np.uint8) * 255
    img = Image.fromarray(img_array)
    image_path = tmp_path / "test_image.png"
    img.save(str(image_path))
    return str(image_path)
