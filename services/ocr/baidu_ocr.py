"""百度OCR服务实现 - 实现IOcrService接口"""
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any

import requests

from services.interfaces import IOcrService, OcrResult


@dataclass(frozen=True)
class BaiduOcrConfig:
    """百度OCR配置"""
    api_key: str
    secret_key: str
    # 标准版（够用、便宜、快）；高精度：accurate
    api_name: str = "general_basic"
    timeout_sec: float = 15.0
    max_retries: int = 2
    backoff_sec: float = 0.6
    debug_mode: bool = False  # 调试模式


class BaiduOcrEngine(IOcrService):
    """
    百度OCR接入（自动token缓存）
    - 获取access_token: https://aip.baidubce.com/oauth/2.0/token
    - OCR识别: https://aip.baidubce.com/rest/2.0/ocr/v1/{api_name}
    文档：ai.baidu.com / cloud.baidu.com OCR
    """

    def __init__(self, cfg: BaiduOcrConfig):
        self._cfg = cfg
        self._token: str | None = None
        self._token_expire_at: float = 0.0  # epoch seconds

    def recognize(self, image_path: str) -> OcrResult:
        """识别图片中的文字

        Args:
            image_path: 图片路径

        Returns:
            OCR识别结果
        """
        try:
            img_b64 = self._read_base64(image_path)
        except Exception as e:
            return OcrResult(ok=False, error=f"读取图片失败：{e}")

        try:
            token = self._get_access_token()
        except Exception as e:
            return OcrResult(ok=False, error=f"获取百度token失败：{e}")

        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/{self._cfg.api_name}?access_token={token}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        # 百度OCR是 x-www-form-urlencoded，image=base64（不是json）
        # 可加参数：detect_direction、paragraph、probability 等
        data = {
            "image": img_b64,
            "detect_direction": "true",
        }

        last_err = None
        for attempt in range(self._cfg.max_retries + 1):
            try:
                resp = requests.post(url, headers=headers, data=data, timeout=self._cfg.timeout_sec)
                if resp.status_code != 200:
                    last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
                    raise RuntimeError(last_err)

                j = resp.json()

                # 调试输出原始数据
                if self._cfg.debug_mode:
                    print(f"\n[BaiduOcr] 原始响应数据:")
                    print(f"  API类型: {self._cfg.api_name}")
                    print(f"  识别结果数量: {len(j.get('words_result', []))}")
                    if j.get('words_result'):
                        print(f"  第一个结果: {json.dumps(j['words_result'][0], ensure_ascii=False, indent=2)}")

                # 百度错误结构：error_code / error_msg
                if "error_code" in j:
                    # token 失效常见：110/111 等
                    # 这里遇到错误就清 token 重试一次
                    last_err = f"百度OCR错误 {j.get('error_code')}: {j.get('error_msg')}"
                    if attempt < self._cfg.max_retries:
                        self._token = None
                        self._token_expire_at = 0.0
                        time.sleep(self._cfg.backoff_sec * (attempt + 1))
                        continue
                    return OcrResult(ok=False, raw=j, error=last_err)

                text, words_list = self._parse_words_result(j)
                return OcrResult(ok=True, text=text, words=words_list, raw=j)

            except Exception as e:
                last_err = str(e)
                if attempt < self._cfg.max_retries:
                    time.sleep(self._cfg.backoff_sec * (attempt + 1))
                    continue
                return OcrResult(ok=False, error=f"百度OCR请求失败：{last_err}")

        return OcrResult(ok=False, error=f"百度OCR失败：{last_err or 'unknown'}")

    def _get_access_token(self) -> str:
        """获取access_token，自动缓存"""
        now = time.time()
        if self._token and now < self._token_expire_at:
            return self._token

        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self._cfg.api_key,
            "client_secret": self._cfg.secret_key
        }

        resp = requests.get(url, params=params, timeout=self._cfg.timeout_sec)
        if resp.status_code != 200:
            raise RuntimeError(f"获取token失败: HTTP {resp.status_code}")

        j = resp.json()
        if "access_token" not in j:
            raise RuntimeError(f"获取token失败: 响应无access_token: {j}")

        # 缓存token，提前60秒过期
        self._token = j["access_token"]
        expires_in = j.get("expires_in", 2592000)  # 默认30天
        self._token_expire_at = now + expires_in - 60

        return self._token

    def _read_base64(self, image_path: str) -> str:
        """读取图片并转为base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _parse_words_result(self, j: dict) -> tuple[str, list[Any]]:
        """解析百度OCR返回的words_result

        Args:
            j: 百度OCR返回的JSON

        Returns:
            (text, words_list): 完整文本和文字块列表
        """
        words_result = j.get("words_result", [])

        # 提取完整文本
        text_lines = [item.get("words", "") for item in words_result]
        text = "\n".join(text_lines)

        # 提取文字块（带位置信息）
        from domain.models import OcrWordResult

        words_list = []
        for item in words_result:
            location = item.get("location", {})
            words_list.append(OcrWordResult(
                text=item.get("words", ""),
                x=location.get("left", 0),
                y=location.get("top", 0),
                width=location.get("width", 0),
                height=location.get("height", 0),
                raw=item
            ))

        return text, words_list
