"""OCR识别流程服务 - 统一处理OCR识别业务流程"""
from typing import Optional, Callable
from core.logger import get_logger
from domain.models import Region
from services.interfaces import ICaptureService, IOcrService


logger = get_logger(__name__)


class RecognitionFlowService:
    """OCR识别流程服务 - 封装完整的识别流程"""

    def __init__(
        self,
        capture_service: ICaptureService,
        ocr_service: IOcrService,
        text_parser,
        region_calculator,
        debug_callback: Optional[Callable] = None
    ):
        """初始化识别流程服务

        Args:
            capture_service: 截图服务
            ocr_service: OCR服务
            text_parser: 文本解析服务
            region_calculator: 区域计算服务
            debug_callback: 调试回调函数
        """
        self._capture = capture_service
        self._ocr = ocr_service
        self._text_parser = text_parser
        self._region_calculator = region_calculator
        self._debug_callback = debug_callback or (lambda *args, **kwargs: None)

    def execute_recognition_flow(
        self,
        hwnd: int,
        client_width: int,
        client_height: int
    ) -> dict:
        """执行完整的OCR识别流程

        Args:
            hwnd: 窗口句柄
            client_width: 客户区域宽度
            client_height: 客户区域高度

        Returns:
            识别结果字典，包含：
            - balance_value: 余额
            - item_results: 物品识别结果列表
            - success: 是否成功
            - error: 错误信息（如果失败）
        """
        result = {
            'balance_value': '--',
            'item_results': [],
            'success': False,
            'error': None
        }

        try:
            # 1. 计算识别区域
            balance_region, item_regions = self._region_calculator.calculate_for_resolution(
                client_width, client_height
            )

            # 2. 计算合并区域
            combined_region = self._region_calculator.calculate_combined_region(
                balance_region, *item_regions
            )

            self._debug_callback(
                f"[识别流程] 合并区域: x={combined_region.x}, y={combined_region.y}, "
                f"width={combined_region.width}, height={combined_region.height}"
            )
            self._debug_callback(f"[识别流程] 窗口分辨率: {client_width}x{client_height}")

            # 3. 截取合并区域
            from core.paths import ProjectPaths
            combined_out_path = ProjectPaths.get_capture_path("last_combined.png")

            cap = self._capture.capture_region(
                hwnd,
                combined_out_path,
                combined_region.get_bounding_box(),
                timeout_sec=2.5,
                preprocess=False
            )

            if not cap.ok or not cap.path:
                result['error'] = "截图失败，无法识别。"
                return result

            self._debug_callback(f"[识别流程] 截图已保存到: {combined_out_path}")

            # 4. OCR识别
            ocr_result = self._ocr.recognize(cap.path)
            if not ocr_result.ok:
                result['error'] = f"OCR识别失败: {ocr_result.error}"
                return result

            self._debug_callback(f"[识别流程] 原始识别文本: {repr(ocr_result.text)}")
            if ocr_result.words:
                self._debug_callback(f"[识别流程] 识别到 {len(ocr_result.words)} 个文字块")

            # 5. 分配识别结果
            balance_value, item_results = self._allocate_recognition_results(
                ocr_result.words,
                combined_region,
                balance_region,
                item_regions
            )

            result['balance_value'] = balance_value
            result['item_results'] = item_results
            result['success'] = True

            if balance_value == '--':
                self._debug_callback("[识别流程] 余额识别失败")

            return result

        except Exception as e:
            logger.error(f"OCR识别流程异常: {e}", exc_info=True)
            result['error'] = f"OCR识别流程异常: {e}"
            return result

    def _allocate_recognition_results(
        self,
        words: list,
        combined_region: Region,
        balance_region: Region,
        item_regions: list[Region]
    ) -> tuple[str, list[dict]]:
        """根据位置信息分配OCR识别结果

        Args:
            words: OCR识别的文字块列表
            combined_region: 合并区域
            balance_region: 余额区域
            item_regions: 物品区域列表

        Returns:
            (余额值, 物品识别结果列表)
        """
        balance_value = "--"
        item_results = []

        if not words:
            return balance_value, item_results

        for word in words:
            # 计算文字块在合并区域中的绝对位置
            word_x = word.x + combined_region.x
            word_y = word.y + combined_region.y

            # 检查是否在余额区域内
            if balance_region.contains_center(word_x, word_y, word.width, word.height):
                balance_text = word.text
                balance_value = self._text_parser.extract_balance(balance_text)
                self._debug_callback(
                    f"[识别流程] 文字块归属余额: {repr(balance_text)} -> 余额: {balance_value}"
                )
            else:
                # 检查是否在某个物品区域内
                for item_idx, item_region in enumerate(item_regions):
                    if item_region.contains_center(word_x, word_y, word.width, word.height):
                        item_results.append({
                            'index': item_idx,
                            'text': word.text,
                            'region_name': item_region.name
                        })
                        self._debug_callback(
                            f"[识别流程] 文字块归属物品区域{item_idx + 1}({item_region.name}): {repr(word.text)}"
                        )
                        break

        return balance_value, item_results
