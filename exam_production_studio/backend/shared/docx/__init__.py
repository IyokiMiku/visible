"""shared/docx：组卷底层（命名 + 三行标题 + 生成）。"""
from .naming import build_filename, build_title_lines
from .generator import generate_docx

__all__ = ["build_filename", "build_title_lines", "generate_docx"]
