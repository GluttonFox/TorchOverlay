import os
import re
import time
from typing import Any

from core.config import AppConfig, get_regions_for_resolution, get_combined_region
from core.paths import ProjectPaths
from services.game_binder import GameBinder
from services.process_watcher import ProcessWatcher
from services.capture_service import CaptureService
from services.ocr.base_ocr import IOcrEngine
from services.overlay.overlay_service import OverlayService, OverlayTextItem
from services.overlay.target_window import get_client_rect_in_screen


class AppController:
    """控制器：业务流程与 UI 交互的中枢。"""

    # 区域数量常量
    TOTAL_ITEM_REGIONS = 8

    # 预编译正则表达式，避免重复编译
    _STUFF_PATTERN = re.compile(r'^(TUFF|STUFF)\s*', re.IGNORECASE)
    _QUANTITY_PATTERN = re.compile(r'X\s*(\d+)', re.IGNORECASE)
    _PRICE_PATTERN = re.compile(r'(\d+)\s*$')
    _NUMBERS_PATTERN = re.compile(r'\d+')

    def __init__(
        self,
        cfg: AppConfig,
        binder: GameBinder,
        watcher: ProcessWatcher,
        capture: CaptureService,
        ocr: IOcrEngine,
        overlay: OverlayService,
    ):
        self._cfg = cfg
        self._binder = binder
        self._watcher = watcher
        self._capture = capture
        self._ocr = ocr
        self._overlay = overlay
        self._ui = None

    def attach_ui(self, ui):
        self._ui = ui

    def _debug_log(self, *args, **kwargs) -> None:
        """调试日志（仅在debug模式下输出）

        Args:
            *args: 打印参数
            **kwargs: 打印关键字参数
        """
        if self._cfg.ocr.debug_mode:
            print(*args, **kwargs)

    def on_window_shown(self):
        self._ensure_bound_or_exit()
        self._schedule_watch()

    def _ensure_bound_or_exit(self):
        while True:
            if self._binder.try_bind():
                self._ui.set_bind_state(self._binder.bound)
                return

            retry = self._ui.ask_bind_retry_or_exit()
            if not retry:
                self._overlay.close()  # 关闭overlay
                self._ui.close()
                return

    def _schedule_watch(self):
        def tick():
            bound = self._binder.bound
            if bound:
                if not self._binder.is_bound_hwnd_valid():
                    self._overlay.close()  # 关闭overlay
                    self._ui.close()
                    return
                if not self._watcher.is_alive(bound):
                    self._overlay.close()  # 关闭overlay
                    self._ui.close()
                    return
            self._ui.schedule(self._watcher.interval_ms, tick)

        self._ui.schedule(self._watcher.interval_ms, tick)

    def on_detect_click(self):
        bound = self._binder.bound
        if not bound:
            self._ui.show_info("未绑定游戏窗口，无法识别。")
            return

        # 获取窗口client区域大小
        client_x, client_y, client_width, client_height = get_client_rect_in_screen(bound.hwnd)

        # 根据分辨率自适应计算识别区域
        balance_region, item_regions = get_regions_for_resolution(client_width, client_height)

        # 计算包含所有区域的合并区域
        combined_region = get_combined_region(balance_region, item_regions)

        self._debug_log(f"\n[OCR优化] 合并区域: x={combined_region['x']}, y={combined_region['y']}, width={combined_region['width']}, height={combined_region['height']}")
        self._debug_log(f"[OCR优化] 窗口分辨率: {client_width}x{client_height}")
        self._debug_log(f"[OCR优化] 包含区域: 余额区域({balance_region['name']}) + {len(item_regions)}个物品区域")

        # 截取合并区域（1次截图）
        combined_out_path = ProjectPaths.get_capture_path("last_combined.png")
        cap = self._capture.capture_region_once(bound.hwnd, combined_out_path, combined_region, timeout_sec=2.5, preprocess=False)

        if not cap.ok or not cap.path:
            self._ui.show_info("截图失败，无法识别。")
            return

        self._debug_log(f"[OCR优化] 截图已保存到: {combined_out_path}")

        # OCR识别（1次调用）
        r = self._ocr.recognize(cap.path)
        if not r.ok:
            self._ui.show_info(f"OCR识别失败: {r.error}")
            return

        self._debug_log(f"[OCR优化] 原始识别文本: {repr(r.text)}")
        if r.words:
            self._debug_log(f"[OCR优化] 识别到 {len(r.words)} 个文字块")

        # 根据位置信息分配结果
        balance_value = "--"
        item_results = []

        if r.words:
            # 遍历所有识别到的文字块
            for word in r.words:
                # 计算文字块在合并区域中的绝对位置
                word_x = word.x + combined_region['x']
                word_y = word.y + combined_region['y']

                # 检查是否在余额区域内
                if self._point_in_region(word_x, word_y, word.width, word.height, balance_region):
                    balance_text = word.text
                    balance_value = self._extract_balance(balance_text)

                    self._debug_log(f"[OCR优化] 文字块归属余额: {repr(balance_text)} -> 余额: {balance_value}")
                else:
                    # 检查是否在某个物品区域内
                    for item_idx, item_region in enumerate(item_regions):
                        if self._point_in_region(word_x, word_y, word.width, word.height, item_region):
                            # 收集该物品区域的所有文字块
                            item_results.append({
                                'index': item_idx,
                                'text': word.text,
                                'region_name': item_region['name']
                            })

                            self._debug_log(f"[OCR优化] 文字块归属物品区域{item_idx + 1}({item_region['name']}): {repr(word.text)}")
                            break

        # 更新UI余额
        self._ui.update_balance(balance_value)

        if balance_value == "--":
            self._debug_log(f"\n[OCR优化] 余额识别失败")

        # 清空表格
        self._ui.clear_items_table()

        # 创建overlay显示区域边框
        if not self._overlay.is_visible():
            self._overlay.create_overlay(bound.hwnd)

        # 在overlay上显示物品识别区域边框
        self._overlay.show_regions(item_regions)

        # 批量添加物品结果到表格
        self._add_item_results_batch(item_results, item_regions)

    def _point_in_region(self, x: int, y: int, width: int, height: int, region: dict[str, Any]) -> bool:
        """判断点/矩形是否在区域内

        Args:
            x: 文字块左上角x坐标
            y: 文字块左上角y坐标
            width: 文字块宽度
            height: 文字块高度
            region: 区域定义 {x, y, width, height}

        Returns:
            是否在区域内
        """
        # 计算文字块的中心点
        center_x = x + width / 2
        center_y = y + height / 2

        # 判断中心点是否在区域内
        region_x = region['x']
        region_y = region['y']
        region_right = region_x + region['width']
        region_bottom = region_y + region['height']

        return (region_x <= center_x <= region_right and
                region_y <= center_y <= region_bottom)

    def _add_item_results_batch(self, item_results: list[dict], item_regions: list[dict[str, Any]]):
        """批量添加物品识别结果到表格

        Args:
            item_results: 文字块结果列表 [{'index', 'text', 'region_name'}, ...]
            item_regions: 物品区域列表
        """
        # 按区域索引分组文字块
        grouped = {}
        for result in item_results:
            idx = result['index']
            if idx not in grouped:
                grouped[idx] = []
            grouped[idx].append(result['text'])

        # 为每个区域生成结果
        for idx, region in enumerate(item_regions):
            if idx in grouped:
                # 合并该区域的所有文字块
                combined_text = ' '.join(grouped[idx])
            else:
                combined_text = "--"

            self._debug_log(f"[物品识别] 区域 {idx + 1} ({region['name']}): 合并文本 = {repr(combined_text)}")

            # 解析物品信息
            item_name, item_quantity, item_price = self._parse_item_info(combined_text)
            self._ui.add_item_result(idx + 1, region['name'], item_name, item_quantity, item_price)

    def _parse_item_info(self, text: str) -> tuple[str, str, str]:
        """解析物品信息，返回 (名称, 数量, 价格)"""
        if text == "--":
            return "--", "--", "--"

        # 将换行符替换为空格，并压缩连续空格
        text = ' '.join(text.split())

        # 去掉开头的 TUFF 或 STUFF 标记（使用预编译正则）
        text = self._STUFF_PATTERN.sub('', text)

        # 检查是否已售罄
        if '已售罄' in text:
            # 提取物品名称（已售罄之前的部分）
            name = text.replace('已售罄', '').strip()
            return name, '已售罄', '0'

        # 查找 "X" 后面的数字作为数量（使用预编译正则）
        quantity_match = self._QUANTITY_PATTERN.search(text)
        if quantity_match:
            quantity = quantity_match.group(1)
            # 去掉数量部分，获取物品名称和价格
            remaining = self._QUANTITY_PATTERN.sub('', text).strip()
        else:
            # 没有显式数量，默认为1
            quantity = '1'
            remaining = text

        # 从剩余文本中提取最后一个数字作为价格（使用预编译正则）
        price_match = self._PRICE_PATTERN.search(remaining)
        if price_match:
            price = price_match.group(1)
            # 去掉价格，获取物品名称
            name = self._PRICE_PATTERN.sub('', remaining).strip()
        else:
            # 没有找到价格
            price = '--'
            name = remaining.strip()

        return name, quantity, price

    def _extract_balance(self, text: str) -> str:
        """从识别的文本中提取余额数字"""
        # 匹配连续的数字（使用预编译正则）
        numbers = self._NUMBERS_PATTERN.findall(text)
        if numbers:
            # 取最长的数字串（最可能是余额）
            balance = max(numbers, key=len)
            # 格式化余额（添加千分位分隔符）
            try:
                num = int(balance)
                return f"{num:,}"
            except ValueError:
                return balance
        return "--"

    def update_config(self, ocr_config, watch_interval_ms: int) -> bool:
        """更新配置"""
        try:
            from core.config import AppConfig, OcrConfig
            from services.ocr.baidu_ocr import BaiduOcrEngine, BaiduOcrConfig

            # 更新配置对象
            self._cfg = AppConfig(
                app_title_prefix=self._cfg.app_title_prefix,
                keywords=self._cfg.keywords,
                watch_interval_ms=watch_interval_ms,
                elevated_marker=self._cfg.elevated_marker,
                ocr=ocr_config,
            )

            # 保存配置文件
            if not self._cfg.save():
                raise Exception("保存配置文件失败")

            # 更新监控间隔
            self._watcher.interval_ms = watch_interval_ms

            # 重新创建OCR引擎（重要：确保新配置生效，包括debug_mode）
            ocr_cfg = BaiduOcrConfig(
                api_key=ocr_config.api_key,
                secret_key=ocr_config.secret_key,
                api_name=ocr_config.api_name,
                timeout_sec=ocr_config.timeout_sec,
                max_retries=ocr_config.max_retries,
                debug_mode=ocr_config.debug_mode,
            )
            self._ocr = BaiduOcrEngine(ocr_cfg)

            return True
        except Exception as e:
            print(f"更新配置失败: {e}")
            return False

    def get_config(self):
        """获取当前配置"""
        return self._cfg
