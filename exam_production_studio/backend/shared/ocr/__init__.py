"""shared/ocr：PDF 类型判定 + 教材目录扫描（文字层/视觉 OCR）+ 结构化目录。"""
from .pdf_type import IMAGE, TEXT, detect_pdf_type
from .scanner import load_structured_tocs, scan_textbook_toc
from .toc_structured import StructuredToc, TocNode, load_structured, save_structured
from .vision import VisionNotEnabled, render_pdf_pages, vision_ocr

__all__ = [
    "scan_textbook_toc", "load_structured_tocs",
    "detect_pdf_type", "TEXT", "IMAGE",
    "vision_ocr", "render_pdf_pages", "VisionNotEnabled",
    "StructuredToc", "TocNode", "load_structured", "save_structured",
]
