"""视觉 OCR（阶段 A3）。

图片版 PDF 的目录页渲染成图后，交给独立配置的视觉模型做 OCR。
- 模型/凭据走独立的 ``VISION_*`` 配置（见 config.get_vision_config），与主 LLM 分离、可插拔；
- 未配置（enabled=False）时抛 VisionNotEnabled，由调用方降级（回退文本层或提示补数据）。

调用采用 OpenAI 兼容的多模态 Chat Completions（content 内嵌 image_url data URL）。
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import config


class VisionNotEnabled(RuntimeError):
    """视觉 OCR 未启用（未配置 VISION_API_KEY）。"""


_OCR_PROMPT = (
    "你是教材目录 OCR 助手。请逐行识别图片中的目录文字，"
    "保留章节层级与顺序，按原文输出为纯文本（每个目录条目一行，可保留页码）。"
    "不要输出解释、不要编造图中没有的内容。"
)


def _to_data_url(image: Any) -> str:
    """把一张图片（bytes / 文件路径 / PIL.Image）转成 data URL。"""
    if isinstance(image, (bytes, bytearray)):
        raw = bytes(image)
    elif isinstance(image, (str, Path)):
        raw = Path(image).read_bytes()
    else:  # 尝试按 PIL.Image 处理
        import io
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        raw = buf.getvalue()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{b64}"


def vision_ocr(images: list[Any], cfg: dict[str, Any] | None = None) -> str:
    """对一组目录页图片做 OCR，返回合并后的纯文本（页间以空行分隔）。

    images 元素可为 PNG 字节 / 文件路径 / PIL.Image。
    """
    cfg = cfg or config.get_vision_config()
    if not cfg.get("enabled"):
        raise VisionNotEnabled("视觉 OCR 未启用（请在全局设置配置并启用 VISION_*）")
    if not cfg.get("model"):
        raise VisionNotEnabled("视觉 OCR 已启用但未指定 VISION_MODEL，请先配置视觉模型")

    from openai import OpenAI

    client = OpenAI(api_key=cfg["api_key"], base_url=cfg.get("base_url") or None)
    out: list[str] = []
    for img in images:
        content = [
            {"type": "text", "text": _OCR_PROMPT},
            {"type": "image_url", "image_url": {"url": _to_data_url(img)}},
        ]
        resp = client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": content}],
            temperature=0.0,
            max_tokens=2048,
        )
        out.append((resp.choices[0].message.content or "").strip())
    return "\n\n".join(t for t in out if t)


def render_pdf_pages(pdf_path: str | Path, pages: range | list[int], *, dpi_scale: float = 2.5) -> list[bytes]:
    """把 PDF 指定页渲染为 PNG 字节列表（供视觉 OCR / 前端预览）。

    pages 为 0-based 页序号集合。PyMuPDF 不可用时返回空列表。
    """
    path = Path(pdf_path)
    if not path.exists():
        return []
    try:
        import fitz  # pymupdf
    except Exception:  # noqa: BLE001
        return []
    imgs: list[bytes] = []
    doc = fitz.open(str(path))
    try:
        mat = fitz.Matrix(dpi_scale, dpi_scale)
        for i in pages:
            if 0 <= i < doc.page_count:
                pix = doc.load_page(i).get_pixmap(matrix=mat)
                imgs.append(pix.tobytes("png"))
    finally:
        doc.close()
    return imgs
