from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any

import requests

from services.ocr.base_ocr import IOcrEngine, OcrResult


@dataclass(frozen=True)
class BaiduOcrConfig:
    api_key: str
    secret_key: str
    # 标准版（够用、便宜、快）；你后续想用高精度我也给了接口名
    api_name: str = "general_basic"  # general_basic / accurate_basic
    timeout_sec: float = 15.0
    max_retries: int = 2
    backoff_sec: float = 0.6
    debug_mode: bool = False  # 调试模式


class BaiduOcrEngine(IOcrEngine):
    """
    百度OCR接入（自动token缓存）：
    - 获取access_token: https://aip.baidubce.com/oauth/2.0/token
    - OCR识别: https://aip.baidubce.com/rest/2.0/ocr/v1/{api_name}
    文档：ai.baidu.com / cloud.baidu.com OCR
    """

    def __init__(self, cfg: BaiduOcrConfig):
        self._cfg = cfg
        self._token: str | None = None
        self._token_expire_at: float = 0.0  # epoch seconds

    def recognize(self, image_path: str) -> OcrResult:
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
                # 百度错误结构：error_code / error_msg
                if "error_code" in j:
                    # token 失效常见：110/111 等（有时会出现）
                    # 这里遇到错误就清 token 重试一次
                    last_err = f"百度OCR错误 {j.get('error_code')}: {j.get('error_msg')}"
                    if attempt < self._cfg.max_retries:
                        self._token = None
                        self._token_expire_at = 0.0
                        time.sleep(self._cfg.backoff_sec * (attempt + 1))
                        continue
                    return OcrResult(ok=False, raw=j, error=last_err)

                text = self._parse_words_result(j)
                return OcrResult(ok=True, text=text, raw=j)

            except Exception as e:
                last_err = str(e)
                if attempt < self._cfg.max_retries:
                    time.sleep(self._cfg.backoff_sec * (attempt + 1))
                    continue
                return OcrResult(ok=False, error=f"百度OCR请求失败：{last_err}")

        return OcrResult(ok=False, error=f"百度OCR失败：{last_err or 'unknown'}")

    # ---------------- token ----------------

    def _get_access_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expire_at:
            return self._token

        if self._cfg.debug_mode:
            print(f"[BaiduOcr] 获取 Access Token:")
            print(f"  API Key: {self._cfg.api_key[:10]}... (长度: {len(self._cfg.api_key)})")
            print(f"  Secret Key: {self._cfg.secret_key[:10]}... (长度: {len(self._cfg.secret_key)})")

        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self._cfg.api_key,
            "client_secret": self._cfg.secret_key,
        }
        resp = requests.get(url, params=params, timeout=self._cfg.timeout_sec)

        if self._cfg.debug_mode:
            print(f"  响应状态码: {resp.status_code}")

        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")

        j = resp.json()
        token = j.get("access_token")
        expires_in = j.get("expires_in")  # 秒
        if not token or not expires_in:
            raise RuntimeError(f"token返回异常：{json.dumps(j, ensure_ascii=False)[:300]}")

        # 提前 60 秒过期，避免边界问题
        self._token = token
        self._token_expire_at = time.time() + int(expires_in) - 60

        if self._cfg.debug_mode:
            print(f"  Token 获取成功: {token[:20]}...{token[-20:]}")

        return token

    # ---------------- helpers ----------------

    @staticmethod
    def _read_base64(path: str) -> str:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def _parse_words_result(j: dict[str, Any]) -> str:
        # 标准通用：words_result: [{"words": "..."}...]
        arr = j.get("words_result")
        if not isinstance(arr, list):
            return ""
        parts = []
        for it in arr:
            if isinstance(it, dict) and isinstance(it.get("words"), str):
                parts.append(it["words"])
        return "\n".join(parts).strip()
