"""预留视觉 OCR 接口（阶段四 shared/ocr）。

读 settings.vision；未启用则抛 VisionNotEnabled（明确"未启用"）。
"""
from __future__ import annotations

from typing import Any

import config


class VisionNotEnabled(RuntimeError):
    """视觉模型未启用。"""


def vision_ocr(images: list[Any], cfg: dict[str, Any] | None = None) -> str:
    cfg = cfg or config.get_vision_config()
    if not cfg.get("enabled"):
        raise VisionNotEnabled("视觉 OCR 未启用（请在全局设置配置并启用 VISION_*）")
    # TODO(接入): 调用视觉模型完成图片 OCR。
    raise VisionNotEnabled("视觉 OCR 已配置但尚未接入实现")
