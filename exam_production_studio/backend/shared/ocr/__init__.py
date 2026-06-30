"""shared/ocr：教材目录本地扫描 + 预留视觉接口。"""
from .scanner import scan_textbook_toc
from .vision import vision_ocr, VisionNotEnabled

__all__ = ["scan_textbook_toc", "vision_ocr", "VisionNotEnabled"]
