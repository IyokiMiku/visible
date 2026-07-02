"""PDF 类型判定（阶段 A1）。

区分「文字版 PDF」（有可抽取文本层）与「图片版 PDF」（扫描件，无文本层，需 OCR）。
判定方式：逐页取文本层，统计前若干页可见字符量；低于阈值判为图片版。

无 PyMuPDF 依赖时保守判为文字版（回退到文本层抽取，不至于误触发昂贵的视觉 OCR）。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

TEXT = "text"
IMAGE = "image"

# 每页可见字符数达到该值即视为“该页有文本层”。目录页文字通常不密，取值偏低。
_PER_PAGE_MIN_CHARS = 50
# 采样页中「有文本层的页」占比达到该值即判为文字版。
_TEXT_PAGE_RATIO = 0.5


@dataclass
class PdfTypeResult:
    kind: str                    # TEXT | IMAGE
    sampled_pages: int
    text_pages: int
    total_chars: int
    reason: str = ""

    @property
    def is_text(self) -> bool:
        return self.kind == TEXT

    @property
    def is_image(self) -> bool:
        return self.kind == IMAGE


def _visible_chars(text: str) -> int:
    """去掉空白后的可见字符数。"""
    return len("".join(text.split()))


def detect_pdf_type(
    pdf_path: str | Path,
    *,
    sample_pages: int = 5,
    per_page_min_chars: int = _PER_PAGE_MIN_CHARS,
    text_page_ratio: float = _TEXT_PAGE_RATIO,
) -> PdfTypeResult:
    """判定 PDF 为文字版还是图片版。

    - 采样前 ``sample_pages`` 页；
    - 单页可见字符 ≥ ``per_page_min_chars`` 记为「有文本层」；
    - 有文本层页占比 ≥ ``text_page_ratio`` → 文字版，否则图片版。
    """
    path = Path(pdf_path)
    if not path.exists():
        return PdfTypeResult(TEXT, 0, 0, 0, reason="文件不存在，保守按文字版处理")

    try:
        import fitz  # pymupdf
    except Exception as e:  # noqa: BLE001
        return PdfTypeResult(TEXT, 0, 0, 0, reason=f"PyMuPDF 不可用（{e}），保守按文字版处理")

    try:
        doc = fitz.open(str(path))
    except Exception as e:  # noqa: BLE001
        return PdfTypeResult(TEXT, 0, 0, 0, reason=f"打开 PDF 失败（{e}），保守按文字版处理")

    try:
        n = min(sample_pages, doc.page_count)
        text_pages = 0
        total_chars = 0
        for i in range(n):
            chars = _visible_chars(doc.load_page(i).get_text("text"))
            total_chars += chars
            if chars >= per_page_min_chars:
                text_pages += 1
        if n == 0:
            return PdfTypeResult(IMAGE, 0, 0, 0, reason="空文档")
        ratio = text_pages / n
        kind = TEXT if ratio >= text_page_ratio else IMAGE
        reason = f"采样{n}页，有文本层{text_pages}页（占比{ratio:.0%}），共{total_chars}字符"
        return PdfTypeResult(kind, n, text_pages, total_chars, reason=reason)
    finally:
        doc.close()
