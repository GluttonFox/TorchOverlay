from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from PIL import Image, ImageDraw, ImageFont

@dataclass
class OcrBox:
    text: str
    left: int
    top: int
    width: int
    height: int

def parse_baidu_boxes(ocr_json: dict[str, Any]) -> list[OcrBox]:
    boxes: list[OcrBox] = []
    arr = ocr_json.get("words_result", [])
    if not isinstance(arr, list):
        return boxes

    for it in arr:
        if not isinstance(it, dict):
            continue
        text = (it.get("words") or "").strip()
        loc = it.get("location")
        if not text or not isinstance(loc, dict):
            continue
        boxes.append(
            OcrBox(
                text=text,
                left=int(loc.get("left", 0)),
                top=int(loc.get("top", 0)),
                width=int(loc.get("width", 0)),
                height=int(loc.get("height", 0)),
            )
        )
    return boxes

def annotate_image(input_path: str, output_path: str, boxes: list[OcrBox]) -> None:
    im = Image.open(input_path).convert("RGB")
    draw = ImageDraw.Draw(im)

    # 字体：优先用系统字体；找不到就用默认（默认对中文可能不好看，但能跑通）
    try:
        font = ImageFont.truetype("msyh.ttc", 16)  # 微软雅黑
    except Exception:
        font = ImageFont.load_default()

    for b in boxes:
        x1, y1 = b.left, b.top
        x2, y2 = b.left + b.width, b.top + b.height

        # 画框
        draw.rectangle([x1, y1, x2, y2], width=2)

        # 画文字（放在框上方，防止遮挡）
        text_y = max(0, y1 - 18)
        draw.text((x1, text_y), b.text, font=font)

    im.save(output_path)
