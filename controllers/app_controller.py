import os
import time

from core.config import AppConfig
from services.game_binder import GameBinder
from services.process_watcher import ProcessWatcher
from services.capture_service import CaptureService
from services.ocr.base_ocr import IOcrEngine
from services.overlay.overlay_service import OverlayService, OverlayTextItem


class AppController:
    """控制器：业务流程与 UI 交互的中枢。"""

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

        # 余额识别区域配置（多个备用区域，依次尝试）
        balance_regions = [
            # 区域1: 根据用户提供的位置 x=279, y=21, 扩大
            {
                'x': 250,
                'y': 10,
                'width': 100,
                'height': 50,
                'name': '原位置扩大'
            },
            # 区域2: 根据识别到的位置 x=31, y=14, 扩大
            {
                'x': 20,
                'y': 5,
                'width': 80,
                'height': 40,
                'name': '新位置扩大'
            },
            # 区域3: 顶部更大区域
            {
                'x': 0,
                'y': 0,
                'width': 200,
                'height': 80,
                'name': '顶部大区域'
            },
        ]

        balance_value = "--"

        for idx, region in enumerate(balance_regions):
            if self._cfg.ocr.debug_mode:
                print(f"\n[余额识别] 尝试区域 {idx + 1}/{len(balance_regions)} ({region['name']}): x={region['x']}, y={region['y']}, width={region['width']}, height={region['height']}")

            # 截取余额区域
            balance_out_path = os.path.join(os.getcwd(), f"captures/last_balance_{idx}.png")
            cap = self._capture.capture_region_once(bound.hwnd, balance_out_path, region, timeout_sec=2.5)

            if not cap.ok or not cap.path:
                if self._cfg.ocr.debug_mode:
                    print(f"[余额识别] 截图失败: {cap.error}")
                continue

            if self._cfg.ocr.debug_mode:
                print(f"[余额识别] 截图已保存到: {balance_out_path}")

            # 识别余额
            r = self._ocr.recognize(cap.path)
            if r.ok and r.text:
                # 提取数字作为余额
                temp_balance = self._extract_balance(r.text)

                if self._cfg.ocr.debug_mode:
                    print(f"[余额识别] 原始识别: {repr(r.text)}")
                    print(f"[余额识别] 提取余额: {temp_balance}")
                    if r.raw and 'words_result' in r.raw:
                        print(f"[余额识别] OCR原始响应:")
                        for word_idx, word in enumerate(r.raw['words_result'][:3]):
                            print(f"    [{word_idx}] {word}")

                # 如果成功提取到数字，就使用这个结果
                if temp_balance != "--":
                    balance_value = temp_balance
                    break
            else:
                if self._cfg.ocr.debug_mode:
                    print(f"[余额识别] 识别失败: {r.error if r.error else '未识别到文字'}")

        # 更新UI
        self._ui.update_balance(balance_value)

        if self._cfg.ocr.debug_mode and balance_value == "--":
            print(f"\n[余额识别] 所有区域尝试失败，无法识别余额")

        # A：截 client 区域（用于OCR/Overlay对齐）
        out_path = os.path.join(os.getcwd(), "captures", "last_client.png")
        cap = self._capture.capture_client_once(bound.hwnd, out_path, timeout_sec=2.5)

        if not cap.ok or not cap.path:
            self._ui.show_info(f"截图失败：{cap.error}")
            return

        # 云OCR
        r = self._ocr.recognize(cap.path)
        if not r.ok:
            self._ui.show_info(f"OCR失败：{r.error}")
            return

        # 显示识别文本和坐标信息
        if r.text:
            # 创建或更新overlay
            if not self._overlay.is_visible():
                self._overlay.create_overlay(bound.hwnd)

            # 转换OCR结果为overlay文本项
            text_items = []
            if r.words:
                for word in r.words:
                    text_item = OverlayTextItem(
                        text=word.text,
                        x=word.x,
                        y=word.y,
                        width=word.width,
                        height=word.height,
                        color="#00FF00",
                        font_size=14,
                    )
                    text_items.append(text_item)

                # 在overlay上显示文本
                self._overlay.show_texts(text_items)

                # 在控制台输出坐标信息
                if self._cfg.ocr.debug_mode:
                    print("\n[Overlay] 识别到的文本及坐标信息:")
                    for word in r.words:
                        print(f"  文本: {word.text}")
                        print(f"  位置: x={word.x}, y={word.y}, width={word.width}, height={word.height}")
                        print(f"  边界: ({word.x}, {word.y}) - ({word.x + word.width}, {word.y + word.height})")
            else:
                self._overlay.close()
                self._ui.show_info(r.text)
        else:
            self._overlay.close()
            self._ui.show_info("未识别到文字")

    def _extract_balance(self, text: str) -> str:
        """从识别的文本中提取余额数字"""
        import re
        # 匹配连续的数字
        numbers = re.findall(r'\d+', text)
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

    def on_balance_detect_click(self):
        """单独的余额识别按钮（可选）"""
        bound = self._binder.bound
        if not bound:
            self._ui.show_info("未绑定游戏窗口，无法识别。")
            return

        # 余额识别区域
        balance_region = {
            'x': 250,
            'y': 10,
            'width': 100,
            'height': 50
        }

        if self._cfg.ocr.debug_mode:
            print(f"\n[余额识别（单独）] 截图区域: x={balance_region['x']}, y={balance_region['y']}, width={balance_region['width']}, height={balance_region['height']}")

        # 先保存完整client区域用于对比
        full_client_path = os.path.join(os.getcwd(), "captures", "last_client_full.png")
        full_cap = self._capture.capture_client_once(bound.hwnd, full_client_path, timeout_sec=2.5)

        if self._cfg.ocr.debug_mode:
            print(f"[余额识别（单独）] 完整client区域已保存到: {full_client_path}")

        balance_out_path = os.path.join(os.getcwd(), "captures", "last_balance.png")
        cap = self._capture.capture_region_once(bound.hwnd, balance_out_path, balance_region, timeout_sec=2.5)

        if not cap.ok or not cap.path:
            self._ui.show_info(f"截图失败：{cap.error}")
            return

        if self._cfg.ocr.debug_mode:
            print(f"[余额识别（单独）] 余额区域已保存到: {balance_out_path}")

        r = self._ocr.recognize(cap.path)
        if r.ok and r.text:
            balance_value = self._extract_balance(r.text)
            self._ui.update_balance(balance_value)

            if self._cfg.ocr.debug_mode:
                print(f"\n[余额识别（单独）] 原始识别: {repr(r.text)}")
                print(f"[余额识别（单独）] 提取余额: {balance_value}")
                if r.raw and 'words_result' in r.raw:
                    print(f"[余额识别（单独）] OCR原始响应:")
                    for idx, word in enumerate(r.raw['words_result'][:3]):
                        print(f"    [{idx}] {word}")
        else:
            if self._cfg.ocr.debug_mode:
                print(f"[余额识别（单独）] 识别失败: {r.error if r.error else '未识别到文字'}")
                if r.raw:
                    print(f"[余额识别（单独）] 原始响应: {r.raw}")
            self._ui.show_info(f"余额识别失败: {r.error if r.error else '未识别到文字'}")

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

            # 保存到文件
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
