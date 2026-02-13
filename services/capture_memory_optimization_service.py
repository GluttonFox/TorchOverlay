"""截图内存优化服务 - 优化截图操作的内存使用"""
import os
from typing import Optional, Tuple
from pathlib import Path
from PIL import Image
import gc

from core.logger import get_logger
from services.interfaces import ICaptureService, CaptureResult

logger = get_logger(__name__)


class CaptureMemoryOptimizationService(ICaptureService):
    """截图内存优化服务

    优化截图操作的内存使用，包括：
    - 自动清理临时文件
    - 限制并发截图数量
    - 图片格式优化
    - 内存使用监控
    """

    def __init__(
        self,
        capture_service: ICaptureService,
        temp_dir: str = "captures",
        max_temp_files: int = 50,
        auto_cleanup: bool = True,
        optimize_format: str = "PNG",
        optimize_quality: int = 85
    ):
        """初始化截图内存优化服务

        Args:
            capture_service: 底层的截图服务
            temp_dir: 临时文件目录
            max_temp_files: 最大临时文件数
            auto_cleanup: 是否自动清理临时文件
            optimize_format: 优化后的图片格式（PNG/JPEG）
            optimize_quality: 图片质量（仅对JPEG有效）
        """
        self._capture_service = capture_service
        self._temp_dir = Path(temp_dir)
        self._max_temp_files = max_temp_files
        self._auto_cleanup = auto_cleanup
        self._optimize_format = optimize_format.upper()
        self._optimize_quality = optimize_quality

        # 确保临时目录存在
        self._temp_dir.mkdir(parents=True, exist_ok=True)

        # 统计信息
        self._stats = {
            'total_captures': 0,
            'optimized_captures': 0,
            'cleanup_count': 0,
            'memory_savings_bytes': 0
        }

    def capture_window(
        self,
        hwnd: int,
        out_path: str,
        timeout_sec: float = 2.5
    ) -> CaptureResult:
        """截取整个窗口（带内存优化）

        Args:
            hwnd: 窗口句柄
            out_path: 输出路径
            timeout_sec: 超时时间

        Returns:
            截图结果
        """
        self._stats['total_captures'] += 1

        # 执行截图
        result = self._capture_service.capture_window(hwnd, out_path, timeout_sec)

        if result.ok and result.path:
            # 优化图片
            self._optimize_image(result.path)

            # 自动清理
            if self._auto_cleanup:
                self._cleanup_temp_files()

        return result

    def capture_client(
        self,
        hwnd: int,
        out_path: str,
        timeout_sec: float = 2.5
    ) -> CaptureResult:
        """截取client区域（带内存优化）

        Args:
            hwnd: 窗口句柄
            out_path: 输出路径
            timeout_sec: 超时时间

        Returns:
            截图结果
        """
        self._stats['total_captures'] += 1

        # 执行截图
        result = self._capture_service.capture_client(hwnd, out_path, timeout_sec)

        if result.ok and result.path:
            # 优化图片
            self._optimize_image(result.path)

            # 自动清理
            if self._auto_cleanup:
                self._cleanup_temp_files()

        return result

    def capture_region(
        self,
        hwnd: int,
        out_path: str,
        region: dict[str, int],
        timeout_sec: float = 2.5,
        preprocess: bool = False
    ) -> CaptureResult:
        """截取指定区域（带内存优化）

        Args:
            hwnd: 窗口句柄
            out_path: 输出路径
            region: 区域定义 {x, y, width, height}
            timeout_sec: 超时时间
            preprocess: 是否预处理

        Returns:
            截图结果
        """
        self._stats['total_captures'] += 1

        # 执行截图
        result = self._capture_service.capture_region(
            hwnd, out_path, region, timeout_sec, preprocess
        )

        if result.ok and result.path:
            # 优化图片
            self._optimize_image(result.path)

            # 自动清理
            if self._auto_cleanup:
                self._cleanup_temp_files()

        return result

    def _optimize_image(self, image_path: str) -> bool:
        """优化图片以减少内存使用

        Args:
            image_path: 图片路径

        Returns:
            是否优化成功
        """
        try:
            # 获取原始图片大小
            original_size = os.path.getsize(image_path)

            # 打开图片
            img = Image.open(image_path)

            # 转换为RGB模式（如果需要）
            if img.mode in ('RGBA', 'LA', 'P'):
                # 透明PNG转换为RGB
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background

            # 保存为优化格式
            if self._optimize_format == 'JPEG':
                # JPEG不支持透明度，转换为RGB
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # 保存为JPEG
                optimized_path = image_path.replace('.png', '.jpg')
                img.save(
                    optimized_path,
                    'JPEG',
                    quality=self._optimize_quality,
                    optimize=True
                )

                # 删除原始PNG
                os.remove(image_path)

                # 重命名优化后的文件
                os.rename(optimized_path, image_path)

            else:  # PNG
                # 保存为PNG，使用压缩
                img.save(
                    image_path,
                    'PNG',
                    optimize=True,
                    compress_level=9
                )

            # 获取优化后的大小
            optimized_size = os.path.getsize(image_path)

            # 计算节省的内存
            savings = original_size - optimized_size
            self._stats['memory_savings_bytes'] += savings
            self._stats['optimized_captures'] += 1

            if savings > 0:
                logger.debug(
                    f"图片优化成功: {original_size} -> {optimized_size} bytes "
                    f"(节省 {savings} bytes, {savings/original_size*100:.1f}%)"
                )

            # 显式释放内存
            img.close()
            del img

            # 手动触发垃圾回收
            gc.collect()

            return True

        except Exception as e:
            logger.error(f"优化图片失败: {e}")
            return False

    def _cleanup_temp_files(self) -> int:
        """清理临时文件

        Returns:
            清理的文件数
        """
        try:
            # 获取所有临时文件
            temp_files = list(self._temp_dir.glob("*.png")) + \
                         list(self._temp_dir.glob("*.jpg"))

            # 按修改时间排序（最旧的在前）
            temp_files.sort(key=lambda f: f.stat().st_mtime)

            # 如果超过最大数量，删除最旧的文件
            cleanup_count = 0
            if len(temp_files) > self._max_temp_files:
                files_to_delete = len(temp_files) - self._max_temp_files

                for i in range(files_to_delete):
                    try:
                        temp_files[i].unlink()
                        cleanup_count += 1
                    except Exception as e:
                        logger.error(f"删除临时文件失败: {e}")

                self._stats['cleanup_count'] += cleanup_count

                if cleanup_count > 0:
                    logger.debug(
                        f"清理了 {cleanup_count} 个临时文件 "
                        f"(总计: {len(temp_files)}, 限制: {self._max_temp_files})"
                    )

            return cleanup_count

        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
            return 0

    def clear_temp_files(self) -> int:
        """清理所有临时文件

        Returns:
            清理的文件数
        """
        try:
            cleanup_count = 0

            # 删除所有PNG和JPG文件
            for ext in ('*.png', '*.jpg', '*.jpeg'):
                for file_path in self._temp_dir.glob(ext):
                    try:
                        file_path.unlink()
                        cleanup_count += 1
                    except Exception as e:
                        logger.error(f"删除临时文件失败: {e}")

            if cleanup_count > 0:
                logger.info(f"清理了 {cleanup_count} 个临时文件")
                self._stats['cleanup_count'] += cleanup_count

            return cleanup_count

        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
            return 0

    def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        # 计算内存节省百分比
        savings_mb = self._stats['memory_savings_bytes'] / (1024 * 1024)

        return {
            **self._stats,
            'memory_savings_mb': f"{savings_mb:.2f} MB",
            'temp_files_count': len(list(self._temp_dir.glob("*.png"))) +
                                len(list(self._temp_dir.glob("*.jpg")))
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            'total_captures': 0,
            'optimized_captures': 0,
            'cleanup_count': 0,
            'memory_savings_bytes': 0
        }

    def get_temp_dir(self) -> str:
        """获取临时目录路径

        Returns:
            临时目录路径
        """
        return str(self._temp_dir)
