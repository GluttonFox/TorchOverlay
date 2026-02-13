"""OCR缓存服务 - 缓存OCR识别结果以提高性能"""
import hashlib
import time
from typing import Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from core.logger import get_logger
from services.interfaces import IOcrService, OcrResult

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    image_hash: str  # 图片的MD5哈希
    result: OcrResult  # OCR结果
    timestamp: float  # 缓存时间戳
    hit_count: int  # 命中次数


class OcrCacheService(IOcrService):
    """OCR缓存服务

    通过缓存OCR识别结果来提高性能，避免重复识别相同的图片。
    """

    def __init__(
        self,
        ocr_service: IOcrService,
        max_cache_size: int = 100,
        cache_ttl_seconds: int = 3600,
        enable_disk_cache: bool = True,
        disk_cache_dir: str = "cache/ocr"
    ):
        """初始化OCR缓存服务

        Args:
            ocr_service: 底层的OCR服务
            max_cache_size: 最大缓存条目数
            cache_ttl_seconds: 缓存过期时间（秒）
            enable_disk_cache: 是否启用磁盘缓存
            disk_cache_dir: 磁盘缓存目录
        """
        self._ocr_service = ocr_service
        self._max_cache_size = max_cache_size
        self._cache_ttl = cache_ttl_seconds
        self._enable_disk_cache = enable_disk_cache
        self._disk_cache_dir = Path(disk_cache_dir)

        # 内存缓存
        self._cache: dict[str, CacheEntry] = {}

        # 统计信息
        self._stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'disk_cache_hits': 0,
            'disk_cache_misses': 0
        }

        # 初始化磁盘缓存目录
        if self._enable_disk_cache:
            self._disk_cache_dir.mkdir(parents=True, exist_ok=True)

    def recognize(self, image_path: str) -> OcrResult:
        """识别图片中的文字（带缓存）

        Args:
            image_path: 图片路径

        Returns:
            OCR识别结果
        """
        self._stats['total_requests'] += 1

        # 计算图片哈希
        image_hash = self._calculate_image_hash(image_path)

        # 检查内存缓存
        if self._check_memory_cache(image_hash):
            self._stats['cache_hits'] += 1
            # logger.debug(f"OCR内存缓存命中: {image_path}")
            return self._cache[image_hash].result

        # 检查磁盘缓存
        if self._enable_disk_cache:
            disk_result = self._check_disk_cache(image_hash)
            if disk_result:
                self._stats['disk_cache_hits'] += 1
                self._stats['cache_misses'] += 1  # 磁盘命中但内存未命中
                # logger.debug(f"OCR磁盘缓存命中: {image_path}")
                # 加入内存缓存
                self._add_to_memory_cache(image_hash, disk_result)
                return disk_result

        # 缓存未命中，执行OCR识别
        self._stats['cache_misses'] += 1
        if self._enable_disk_cache:
            self._stats['disk_cache_misses'] += 1

        # logger.debug(f"OCR缓存未命中，执行识别: {image_path}")
        result = self._ocr_service.recognize(image_path)

        # 只缓存成功的结果
        if result.ok:
            self._add_to_memory_cache(image_hash, result)
            if self._enable_disk_cache:
                self._save_to_disk_cache(image_hash, result)

        return result

    def _calculate_image_hash(self, image_path: str) -> str:
        """计算图片的MD5哈希

        Args:
            image_path: 图片路径

        Returns:
            MD5哈希值
        """
        try:
            # 读取图片文件
            with open(image_path, 'rb') as f:
                image_data = f.read()

            # 计算MD5哈希
            return hashlib.md5(image_data).hexdigest()
        except Exception as e:
            logger.error(f"计算图片哈希失败: {e}")
            return ""

    def _check_memory_cache(self, image_hash: str) -> bool:
        """检查内存缓存

        Args:
            image_hash: 图片哈希

        Returns:
            是否命中缓存
        """
        if image_hash not in self._cache:
            return False

        # 检查是否过期
        entry = self._cache[image_hash]
        if time.time() - entry.timestamp > self._cache_ttl:
            del self._cache[image_hash]
            # logger.debug(f"缓存已过期: {image_hash}")
            return False

        # 更新命中统计
        entry.hit_count += 1
        return True

    def _check_disk_cache(self, image_hash: str) -> Optional[OcrResult]:
        """检查磁盘缓存

        Args:
            image_hash: 图片哈希

        Returns:
            OCR结果，如果未命中则返回None
        """
        cache_file = self._disk_cache_dir / f"{image_hash}.json"

        if not cache_file.exists():
            return None

        try:
            import json
            from services.interfaces import OcrResult, OcrWordResult

            # 读取缓存文件
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # 检查是否过期
            cache_time = cache_data.get('timestamp', 0)
            if time.time() - cache_time > self._cache_ttl:
                # 删除过期的缓存
                cache_file.unlink()
                return None

            # 重建OcrResult对象
            words = []
            for word_data in cache_data.get('words', []):
                words.append(OcrWordResult(
                    text=word_data.get('text', ''),
                    x=word_data.get('x', 0),
                    y=word_data.get('y', 0),
                    width=word_data.get('width', 0),
                    height=word_data.get('height', 0),
                    raw=word_data.get('raw')
                ))

            result = OcrResult(
                ok=cache_data.get('ok', True),
                text=cache_data.get('text'),
                words=words if words else None,
                raw=cache_data.get('raw'),
                error=cache_data.get('error')
            )

            return result

        except Exception as e:
            logger.error(f"读取磁盘缓存失败: {e}")
            return None

    def _add_to_memory_cache(self, image_hash: str, result: OcrResult) -> None:
        """添加到内存缓存

        Args:
            image_hash: 图片哈希
            result: OCR结果
        """
        # 检查缓存大小，如果超过限制则清理
        if len(self._cache) >= self._max_cache_size:
            self._evict_oldest_entries()

        # 添加新条目
        self._cache[image_hash] = CacheEntry(
            image_hash=image_hash,
            result=result,
            timestamp=time.time(),
            hit_count=0
        )

    def _evict_oldest_entries(self, evict_count: Optional[int] = None) -> None:
        """淘汰最旧的缓存条目

        Args:
            evict_count: 要淘汰的条目数，如果为None则淘汰10%
        """
        if evict_count is None:
            evict_count = max(1, len(self._cache) // 10)

        # 按时间戳排序，淘汰最旧的
        entries = sorted(
            self._cache.values(),
            key=lambda x: x.timestamp
        )

        for i in range(min(evict_count, len(entries))):
            entry = entries[i]
            del self._cache[entry.image_hash]

        # logger.debug(f"淘汰了 {evict_count} 个旧缓存条目")

    def _save_to_disk_cache(self, image_hash: str, result: OcrResult) -> None:
        """保存到磁盘缓存

        Args:
            image_hash: 图片哈希
            result: OCR结果
        """
        cache_file = self._disk_cache_dir / f"{image_hash}.json"

        try:
            import json

            # 准备缓存数据
            cache_data = {
                'timestamp': time.time(),
                'ok': result.ok,
                'text': result.text,
                'words': [],
                'raw': result.raw,
                'error': result.error
            }

            # 序列化words
            if result.words:
                for word in result.words:
                    cache_data['words'].append({
                        'text': word.text,
                        'x': word.x,
                        'y': word.y,
                        'width': word.width,
                        'height': word.height,
                        'raw': word.raw
                    })

            # 保存到文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)

        except Exception as e:
            logger.error(f"保存磁盘缓存失败: {e}")

    def clear_cache(self, clear_memory: bool = True, clear_disk: bool = False) -> None:
        """清理缓存

        Args:
            clear_memory: 是否清理内存缓存
            clear_disk: 是否清理磁盘缓存
        """
        if clear_memory:
            self._cache.clear()
            logger.info("内存缓存已清理")

        if clear_disk and self._enable_disk_cache:
            # 删除所有磁盘缓存文件
            for cache_file in self._disk_cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.error(f"删除缓存文件失败: {e}")
            logger.info("磁盘缓存已清理")

    def get_stats(self) -> dict:
        """获取缓存统计信息

        Returns:
            统计信息字典
        """
        total_cache_requests = self._stats['cache_hits'] + self._stats['cache_misses']
        hit_rate = (
            self._stats['cache_hits'] / total_cache_requests * 100
            if total_cache_requests > 0 else 0.0
        )

        return {
            **self._stats,
            'memory_cache_size': len(self._cache),
            'disk_cache_size': len(list(self._disk_cache_dir.glob("*.json")))
            if self._enable_disk_cache else 0,
            'cache_hit_rate': f"{hit_rate:.2f}%"
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'disk_cache_hits': 0,
            'disk_cache_misses': 0
        }

    def cleanup_expired_cache(self) -> int:
        """清理过期的缓存条目

        Returns:
            清理的条目数
        """
        cleaned_count = 0
        current_time = time.time()

        # 清理内存缓存
        expired_hashes = []
        for image_hash, entry in self._cache.items():
            if current_time - entry.timestamp > self._cache_ttl:
                expired_hashes.append(image_hash)

        for image_hash in expired_hashes:
            del self._cache[image_hash]
            cleaned_count += 1

        # 清理磁盘缓存
        if self._enable_disk_cache:
            for cache_file in self._disk_cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)

                    cache_time = cache_data.get('timestamp', 0)
                    if current_time - cache_time > self._cache_ttl:
                        cache_file.unlink()
                        cleaned_count += 1
                except Exception as e:
                    logger.error(f"检查缓存文件失败: {e}")

        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 个过期缓存条目")

        return cleaned_count
