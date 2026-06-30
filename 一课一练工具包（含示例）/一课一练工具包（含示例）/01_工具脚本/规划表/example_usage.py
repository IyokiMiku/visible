#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
example_usage.py
================
textbook_toc_scanner 使用示例

运行前请确保：
  1. 已安装 pymupdf / pytesseract / Pillow
  2. 已安装 Tesseract OCR
  3. chi_sim.traineddata 语言包已就位
"""

from textbook_toc_scanner import scan_single, scan_multiple

# ────────────────────────────────────────────────
# 示例 1：扫描单本教材
# ────────────────────────────────────────────────

# 修改这里为你的 PDF 路径和 tessdata 路径
PDF_1 = r"C:/Users/zxxk/Desktop/wyy/03_项目数据/参考资料/教材/重庆市/电气技术类/电工技术基础与技能（高教版 第3版）周邵敏.pdf"
TESSDATA = r"C:/Users/zxxk/WorkBuddy/2026-06-13-09-31-51/tessdata"

print("【示例1】扫描单本教材")
md = scan_single(
    pdf_path=PDF_1,
    tessdata_dir=TESSDATA,
    pages="2-20",       # 扫描前20页（一般目录在前10页内）
    dpi=2.5,            # 分辨率倍率，越高越慢但识别更准
    output="电工技术目录.md",  # 输出文件（不指定则打印到屏幕）
    verbose=True,        # 显示详细进度
)

# ────────────────────────────────────────────────
# 示例 2：批量扫描三本教材
# ────────────────────────────────────────────────

BASE_DIR = r"C:/Users/zxxk/Desktop/wyy/03_项目数据/参考资料/教材/重庆市/电气技术类"

BOOKS = [
    f"{BASE_DIR}/电子技术基础与技能.pdf",
    f"{BASE_DIR}/电机与电气控制技术（高教版）第4版 赵承荻.pdf",
    f"{BASE_DIR}/电工技术基础与技能（高教版 第3版）周邵敏.pdf",
]

print("\n【示例2】批量扫描三本教材")
md_all = scan_multiple(
    pdf_paths=BOOKS,
    tessdata_dir=TESSDATA,
    pages="2-20",
    dpi=2.5,
    output="三本教材目录汇总.md",
    verbose=False,
)

print("\n✅ 所有教材扫描完成！")

# ────────────────────────────────────────────────
# 示例 3：生成结构化目录缓存（供 generate_plan.py 直接复用）
# ────────────────────────────────────────────────

# 会在 output_dir 下生成 toc_raw.txt / toc_raw_by_page.md /
# toc_structured.json / toc_detected_pages.json / toc.md
from textbook_toc_scanner import scan_textbook_toc_structured

structured = scan_textbook_toc_structured(
    pdf_path=PDF_1,
    tessdata_dir=TESSDATA,
    pages="2-20",
    dpi=2.5,
    output_dir="教材OCR缓存/电工技术基础与技能",
    layout="auto",       # auto / single / double
    preprocess=False,    # 扫描质量差时可改为 True
    verbose=True,
)
print(f"结构化目录条目数：{len(structured['entries'])}")

# ────────────────────────────────────────────────
# 示例 4：一步生成教材目录驱动规划表（命令行）
# ────────────────────────────────────────────────

print(r'''
【示例4】规划表生成命令：
python generate_plan.py ^
  --pdf "2025年重庆市高等职业教育分类考试专业综合理论测试 电气技术类考试说明.pdf" ^
  --title "重庆市电气技术类" ^
  --textbook-driven ^
  --toc-pages 2-20 ^
  --ocr-engine auto ^
  --toc-dpi 2.5 ^
  --tessdata "C:/Users/zxxk/WorkBuddy/2026-06-13-09-31-51/tessdata"
''')
