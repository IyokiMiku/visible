#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
textbook_toc_scanner.py
=======================
扫描版教材PDF目录提取工具
支持：扫描版（图像型）PDF → OCR文字提取 → 目录结构整理 → Markdown输出

依赖：
    pip install pymupdf pytesseract Pillow
    Tesseract OCR 需单独安装：
      Windows: winget install --id UB-Mannheim.TesseractOCR
      Linux:   sudo apt install tesseract-ocr tesseract-ocr-chi-sim
    中文语言包 chi_sim.traineddata 需放入：
      Windows: C:/Program Files/Tesseract-OCR/tessdata/
      或通过 --tessdata 参数指定自定义路径

用法示例：
    # 基本用法（自动检测目录页并输出）
    python textbook_toc_scanner.py 电工技术.pdf

    # 指定多本书（批量）
    python textbook_toc_scanner.py 书1.pdf 书2.pdf 书3.pdf

    # 指定扫描页范围（默认前20页）
    python textbook_toc_scanner.py 电工技术.pdf --pages 2-15

    # 指定自定义 tessdata 路径
    python textbook_toc_scanner.py 电工技术.pdf --tessdata /path/to/tessdata

    # 指定输出文件
    python textbook_toc_scanner.py 书1.pdf 书2.pdf --output 目录汇总.md

    # 仅渲染图像（不OCR，用于调试）
    python textbook_toc_scanner.py 电工技术.pdf --render-only --out-dir ./images
"""

import os
import sys
import re
import json
import argparse
import shutil
import tempfile
import subprocess
from pathlib import Path

# ──────────────────────────────────────────────
# 依赖检查
# ──────────────────────────────────────────────

def check_dependencies():
    """检查并提示缺失的依赖"""
    missing = []

    try:
        import fitz  # PyMuPDF
    except ImportError:
        missing.append("pymupdf (pip install pymupdf)")

    try:
        import pytesseract
    except ImportError:
        missing.append("pytesseract (pip install pytesseract)")

    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow (pip install Pillow)")

    if missing:
        print("❌ 缺少以下依赖，请先安装：")
        for m in missing:
            print(f"   pip install {m.split(' ')[0]}")
        sys.exit(1)

    # 检查 Tesseract 可执行文件
    tess_path = find_tesseract()
    if not tess_path:
        print("❌ 未找到 Tesseract 可执行文件。")
        print("   Windows 安装：winget install --id UB-Mannheim.TesseractOCR")
        print("   Linux 安装：sudo apt install tesseract-ocr tesseract-ocr-chi-sim")
        sys.exit(1)

    return tess_path


def find_tesseract():
    """自动查找 Tesseract 可执行文件路径"""
    # 常见安装路径
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    # 尝试 PATH 中查找
    found = shutil.which("tesseract")
    if found:
        return found

    return None


# ──────────────────────────────────────────────
# PDF 页面渲染
# ──────────────────────────────────────────────

def render_pdf_pages(pdf_path, page_range, out_dir, dpi_scale=2.5):
    """
    将 PDF 指定页范围渲染为 PNG 图像。

    Args:
        pdf_path:   PDF 文件路径
        page_range: tuple(start, end)，基于1的页码，包含端点
        out_dir:    输出目录
        dpi_scale:  渲染倍率（建议 2.0~3.0，越高越清晰但越慢）

    Returns:
        list: 渲染出的 PNG 文件路径列表（按页码顺序）
    """
    import fitz

    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    start_page = max(1, page_range[0])
    end_page = min(total_pages, page_range[1])

    mat = fitz.Matrix(dpi_scale, dpi_scale)
    rendered = []

    print(f"  📄 渲染第 {start_page}~{end_page} 页（共 {total_pages} 页）")
    for i in range(start_page - 1, end_page):  # fitz 索引从0开始
        page = doc[i]
        pix = page.get_pixmap(matrix=mat)
        img_path = os.path.join(out_dir, f"page_{i+1:03d}.png")
        pix.save(img_path)
        rendered.append(img_path)

    doc.close()
    return rendered


# ──────────────────────────────────────────────
# OCR 文字识别
# ──────────────────────────────────────────────

def ocr_image(img_path, tesseract_cmd, tessdata_dir=None, lang="chi_sim"):
    """
    对单张 PNG 图像进行 OCR 识别，返回识别文字。

    Args:
        img_path:      图像文件路径
        tesseract_cmd: tesseract 可执行文件路径
        tessdata_dir:  自定义 tessdata 目录（可为 None 表示使用系统默认）
        lang:          OCR 语言（默认中文简体 chi_sim）

    Returns:
        str: 识别出的文字
    """
    import pytesseract
    from PIL import Image

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    img = Image.open(img_path)

    # 设置 tessdata 路径（通过环境变量）
    env_backup = os.environ.get("TESSDATA_PREFIX")
    if tessdata_dir:
        os.environ["TESSDATA_PREFIX"] = tessdata_dir

    try:
        config = "--oem 3 --psm 6"
        text = pytesseract.image_to_string(img, lang=lang, config=config)
    finally:
        # 恢复环境变量
        if tessdata_dir:
            if env_backup is None:
                os.environ.pop("TESSDATA_PREFIX", None)
            else:
                os.environ["TESSDATA_PREFIX"] = env_backup

    return text.strip()


def _preprocess_image_file(img_path, output_path=None):
    """对扫描图做轻量增强：灰度、对比度增强、二值化。返回增强图路径。"""
    from PIL import Image, ImageEnhance

    src = Path(img_path)
    if output_path is None:
        output_path = src.with_name(src.stem + "_preprocessed.png")
    img = Image.open(src).convert("L")
    img = ImageEnhance.Contrast(img).enhance(1.6)
    img = img.point(lambda p: 255 if p > 180 else 0)
    img.save(output_path)
    return str(output_path)


def _ocr_image_double_column(img_path, tesseract_cmd, tessdata_dir=None, lang="chi_sim", preprocess=False):
    """将页面按左右两栏裁切后 OCR，按左栏→右栏拼接文本。"""
    from PIL import Image

    img = Image.open(img_path)
    width, height = img.size
    overlap = max(10, width // 80)
    mid = width // 2
    crops = [
        (0, 0, min(width, mid + overlap), height),
        (max(0, mid - overlap), 0, width, height),
    ]
    parts = []
    with tempfile.TemporaryDirectory(prefix="toc_cols_") as tmp:
        for idx, box in enumerate(crops, 1):
            crop_path = os.path.join(tmp, f"col_{idx}.png")
            img.crop(box).save(crop_path)
            ocr_path = _preprocess_image_file(crop_path) if preprocess else crop_path
            parts.append(ocr_image(ocr_path, tesseract_cmd, tessdata_dir, lang))
    return "\n".join(p for p in parts if p.strip()).strip()


def _looks_like_double_column(img_path):
    """保守判断页面是否可能为双栏目录。"""
    try:
        from PIL import Image
        img = Image.open(img_path)
        width, height = img.size
        return width / max(height, 1) > 0.72
    except Exception:
        return False


def ocr_image_for_toc(img_path, tesseract_cmd, tessdata_dir=None, lang="chi_sim", layout="single", preprocess=False):
    """目录 OCR：支持可选图片增强与单双栏处理。"""
    layout = (layout or "single").lower()
    work_path = _preprocess_image_file(img_path) if preprocess else img_path

    if layout == "double":
        return _ocr_image_double_column(img_path, tesseract_cmd, tessdata_dir, lang, preprocess)

    single_text = ocr_image(work_path, tesseract_cmd, tessdata_dir, lang)
    if layout == "auto" and _looks_like_double_column(img_path):
        double_text = _ocr_image_double_column(img_path, tesseract_cmd, tessdata_dir, lang, preprocess)
        # 选择更像目录、且有效行更多的结果。
        single_score = score_toc_page(single_text)
        double_score = score_toc_page(double_text)
        single_lines = len([l for l in single_text.splitlines() if l.strip()])
        double_lines = len([l for l in double_text.splitlines() if l.strip()])
        if double_score > single_score or (double_score == single_score and double_lines > single_lines * 1.15):
            return double_text
    return single_text.strip()


def check_tessdata(tessdata_dir, lang="chi_sim"):
    """检查指定 tessdata 目录中是否包含指定语言包"""
    if tessdata_dir:
        traineddata = os.path.join(tessdata_dir, f"{lang}.traineddata")
        if os.path.isfile(traineddata):
            return True
        return False

    # 检查系统默认路径
    default_dirs = [
        r"C:\Program Files\Tesseract-OCR\tessdata",
        r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
        "/usr/share/tesseract-ocr/4.00/tessdata",
        "/usr/share/tessdata",
    ]
    for d in default_dirs:
        if os.path.isfile(os.path.join(d, f"{lang}.traineddata")):
            return True

    return False


# ──────────────────────────────────────────────
# 目录页检测
# ──────────────────────────────────────────────

# 目录页的关键词特征
TOC_KEYWORDS = [
    "目录", "contents", "CONTENTS",
    "第.*章", "第.*节", "单元", "模块",
    "chapter", "unit", "section",
    r"\d+\.\d+",          # 如 "1.1" "2.3"
    r"…+\s*\d+",          # 省略号后跟页码
    r"\.\s*\d{1,3}\s*$",  # 行末有页码
]

# 正文页的反向排除词（出现这些说明已是正文）
CONTENT_ANTI_KEYWORDS = [
    "例题", "【例】", "解：", "解题",
    "实验步骤", "操作步骤",
    r"图\s*\d+[-—]\d+",   # 如"图1-1"正文图注
    r"表\s*\d+[-—]\d+",   # 如"表2-3"
]

TOC_SCORE_THRESHOLD = 3   # 达到该分数才认为是目录页


def score_toc_page_detail(text):
    """给页面文字打分并返回详细构成，便于诊断目录页检测。"""
    detail = {
        "keyword_score": 0,
        "page_number_score": 0,
        "short_line_score": 0,
        "anti_score": 0,
        "total": 0,
        "matched_keywords": [],
        "matched_anti_keywords": [],
        "page_num_lines": 0,
        "short_lines": 0,
        "line_count": 0,
        "is_toc": False,
    }
    if not text or len(text.strip()) < 20:
        return detail

    lines = text.split("\n")
    detail["line_count"] = len(lines)

    for kw in TOC_KEYWORDS:
        for line in lines:
            if re.search(kw, line):
                detail["keyword_score"] += 1
                detail["matched_keywords"].append(kw)
                break

    page_num_lines = sum(1 for l in lines if re.search(r'\d{1,3}\s*$', l.strip()))
    detail["page_num_lines"] = page_num_lines
    if page_num_lines > 3:
        detail["page_number_score"] = 2

    short_lines = sum(1 for l in lines if 5 < len(l.strip()) < 40)
    detail["short_lines"] = short_lines
    if lines and short_lines > len(lines) * 0.5:
        detail["short_line_score"] = 1

    for anti in CONTENT_ANTI_KEYWORDS:
        if re.search(anti, text):
            detail["anti_score"] -= 2
            detail["matched_anti_keywords"].append(anti)

    detail["total"] = (
        detail["keyword_score"]
        + detail["page_number_score"]
        + detail["short_line_score"]
        + detail["anti_score"]
    )
    detail["is_toc"] = detail["total"] >= TOC_SCORE_THRESHOLD
    return detail


def score_toc_page(text):
    """
    给页面文字打分，判断是否为目录页。
    返回分数（越高越可能是目录）。
    """
    return score_toc_page_detail(text)["total"]


# ──────────────────────────────────────────────
# 目录结构解析
# ──────────────────────────────────────────────

def _extract_trailing_page(line):
    """提取目录行末页码，并返回去页码后的文本。"""
    raw = line.strip()
    m = re.search(r'[\s\.·•…]+(\d{1,4})\s*$', raw)
    page = int(m.group(1)) if m else None
    clean = re.sub(r'[\s\.·•…]+\d{1,4}\s*$', '', raw).strip()
    return clean, page


def _is_noise_toc_line(clean):
    """过滤页眉页脚、水印、版权、纯符号等非目录行。"""
    if not clean or len(clean) < 2:
        return True
    if re.match(r'^[\d\s\.\-\/]+$', clean):
        return True
    noise_patterns = [
        r'扫描全能王', r'CamScanner', r'版权所有', r'责任编辑', r'出版社',
        r'ISBN', r'定价', r'印刷', r'版次', r'开本', r'字数', r'网址',
        r'^第\s*\d+\s*页$', r'^[-—_]+$',
    ]
    return any(re.search(p, clean, re.I) for p in noise_patterns)


def _has_toc_shape(line, had_page=False):
    """判断一行是否具备目录条目的形态特征。"""
    patterns = [
        r'^(预备知识|绪论|附录)',
        r'^(第[一二三四五六七八九十百\d]+[章节篇])',
        r'^(单元[一二三四五六七八九十\d]+)',
        r'^(模块[一二三四五六七八九十\d]+)',
        r'^(项目[一二三四五六七八九十\d]+)',
        r'^(任务[一二三四五六七八九十\d]+)',
        r'^\d+[．.]\d+',
        r'^[一二三四五六七八九十]+[、．.]\s*\S',
        r'^(相关技能|实训|技术与应用|拓宽知识|应知应会|练习与考工模拟)',
    ]
    return had_page or any(re.search(p, line) for p in patterns)


def parse_toc_structure_with_pages(page_texts):
    """逐页解析 OCR 文本，保留每条目录项来源 PDF 页码和书内页码。"""
    entries = []
    for source_page, text in sorted(page_texts.items(), key=lambda kv: int(kv[0])):
        for raw_line in text.split("\n"):
            raw_line = raw_line.strip()
            clean, book_page = _extract_trailing_page(raw_line)
            clean = re.sub(r'\s+', ' ', clean).strip()
            if _is_noise_toc_line(clean):
                continue
            if not _has_toc_shape(clean, had_page=book_page is not None):
                continue
            level = detect_level(clean)
            if level > 0:
                entries.append({
                    "level": level,
                    "title": clean,
                    "source_page": int(source_page),
                    "book_page": book_page,
                    "raw_line": raw_line,
                })
    return entries


def parse_toc_structure(ocr_texts):
    """
    从多页 OCR 文字中解析出目录的层级结构。

    Args:
        ocr_texts: list of str，各目录页的 OCR 识别文字

    Returns:
        list of dict: [{"level": 1, "title": "第1章 直流电路"}, ...]
    """
    page_texts = {idx + 1: text for idx, text in enumerate(ocr_texts)}
    entries = parse_toc_structure_with_pages(page_texts)
    return [{"level": e["level"], "title": e["title"]} for e in entries]


def detect_level(line):
    """
    根据行的格式判断目录层级。
    返回：1（一级）、2（二级）、3（三级）、0（忽略）
    """
    # 一级标题特征
    level1_patterns = [
        r'^(预备知识|绪论|附录)',
        r'^(第[一二三四五六七八九十百\d]+[章节篇])',
        r'^(单元[一二三四五六七八九十\d]+)',
        r'^(模块[一二三四五六七八九十\d]+)',
        r'^(项目[一二三四五六七八九十\d]+)',
        r'^(任务[一二三四五六七八九十\d]+)',
        r'^(UNIT|Chapter|MODULE)\s*\d*',
        r'^[一二三四五六七八九十]+[、．.]\s*\S',  # 一、二、等大纲
    ]

    # 二级标题特征
    level2_patterns = [
        r'^\d+\.\d+\s+\S',          # 1.1 标题
        r'^[（(]\d+[）)]\s+\S',      # (1) 标题
        r'^[①②③④⑤⑥⑦⑧⑨⑩]',        # 带圈数字
        r'^\s+(相关技能|实训|技术与应用|拓宽知识|应知应会)',
    ]

    # 三级标题特征
    level3_patterns = [
        r'^\s{2,}[\u4e00-\u9fff]',   # 缩进的中文
        r'^\s+\d+\.\d+\.\d+',        # 1.1.1 格式
        r'^\s+[▪●■•]\s+',            # 项目符号
    ]

    for pat in level1_patterns:
        if re.match(pat, line):
            return 1

    for pat in level2_patterns:
        if re.match(pat, line):
            return 2

    for pat in level3_patterns:
        if re.match(pat, line):
            return 3

    # 默认：含有中文且长度适中的行视为二级
    if re.search(r'[\u4e00-\u9fff]', line) and 4 <= len(line) <= 50:
        return 2

    return 0  # 忽略


# ──────────────────────────────────────────────
# Markdown 输出
# ──────────────────────────────────────────────

def entries_to_markdown(book_name, entries):
    """将解析结果转为 Markdown 格式"""
    lines = [f"## {book_name}\n"]
    current_h2 = None

    for entry in entries:
        title = entry["title"]
        level = entry["level"]

        if level == 1:
            lines.append(f"\n### {title}")
            current_h2 = title
        elif level == 2:
            lines.append(f"- {title}")
        elif level == 3:
            lines.append(f"  - {title}")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# 核心流程
# ──────────────────────────────────────────────

def scan_textbook(pdf_path, tesseract_cmd, tessdata_dir=None,
                  page_range=(2, 20), dpi_scale=2.5,
                  work_dir=None, keep_images=False, verbose=False):
    """
    完整扫描一本教材的目录。

    Args:
        pdf_path:      PDF 文件路径
        tesseract_cmd: Tesseract 可执行路径
        tessdata_dir:  自定义 tessdata 路径（含 chi_sim.traineddata）
        page_range:    扫描页范围 (start, end)，基于1的页码
        dpi_scale:     渲染分辨率倍率（2.0~3.0）
        work_dir:      临时图像目录（None 则自动创建临时目录）
        keep_images:   是否保留渲染的 PNG 图像
        verbose:       是否输出详细日志

    Returns:
        dict: {
            "book_name": str,
            "toc_pages": list of int,     # 检测到的目录页码
            "ocr_texts": dict,            # {页码: OCR文字}
            "entries": list of dict,      # 解析出的目录条目
            "markdown": str,              # Markdown 格式输出
        }
    """
    book_name = Path(pdf_path).stem
    print(f"\n{'='*60}")
    print(f"📚 处理：{book_name}")
    print(f"{'='*60}")

    # 创建临时目录
    auto_tmp = work_dir is None
    if auto_tmp:
        work_dir = tempfile.mkdtemp(prefix="toc_scan_")

    try:
        # ── Step 1: 渲染 PDF 页面为图像 ──
        print(f"🖼  渲染页面（×{dpi_scale} 分辨率）...")
        images = render_pdf_pages(
            pdf_path,
            page_range=page_range,
            out_dir=work_dir,
            dpi_scale=dpi_scale
        )

        # ── Step 2: OCR 识别所有渲染页 ──
        print(f"🔍 OCR 识别（共 {len(images)} 页）...")
        ocr_results = {}

        for img_path in images:
            page_num = int(re.search(r'page_(\d+)', img_path).group(1))
            if verbose:
                print(f"  → 识别第 {page_num} 页...")
            try:
                text = ocr_image(img_path, tesseract_cmd, tessdata_dir)
                ocr_results[page_num] = text
            except Exception as e:
                if verbose:
                    print(f"  ⚠️  第 {page_num} 页 OCR 失败: {e}")
                ocr_results[page_num] = ""

        # ── Step 3: 检测目录页 ──
        print("📋 检测目录页...")
        toc_pages = []
        for page_num, text in sorted(ocr_results.items()):
            score = score_toc_page(text)
            if verbose:
                print(f"  第 {page_num} 页：得分 {score}")
            if score >= TOC_SCORE_THRESHOLD:
                toc_pages.append(page_num)
                if verbose:
                    print(f"  ✅ 第 {page_num} 页识别为目录页（得分={score}）")

        if not toc_pages:
            # 如果没有检测到目录，降低阈值重试
            print("  ⚠️  未检测到目录页，降低阈值重试...")
            for page_num, text in sorted(ocr_results.items()):
                score = score_toc_page(text)
                if score >= 1:
                    toc_pages.append(page_num)

        print(f"  📌 目录页：{toc_pages}")

        # ── Step 4: 解析目录结构 ──
        toc_texts = [ocr_results[p] for p in toc_pages if p in ocr_results]
        entries = parse_toc_structure(toc_texts)

        # ── Step 5: 生成 Markdown ──
        markdown = entries_to_markdown(book_name, entries)

        print(f"✅ 完成：识别到 {len(entries)} 个目录条目")

        return {
            "book_name": book_name,
            "toc_pages": toc_pages,
            "ocr_texts": ocr_results,
            "entries": entries,
            "markdown": markdown,
        }

    finally:
        # 清理临时目录
        if auto_tmp and not keep_images:
            shutil.rmtree(work_dir, ignore_errors=True)
        elif keep_images:
            print(f"📁 渲染图像保存在：{work_dir}")


def _page_range_from_pages(pages):
    """兼容 '2-20'、'2,4-6'、列表等页码输入，返回连续扫描范围。"""
    if isinstance(pages, tuple):
        return pages
    if isinstance(pages, list):
        nums = [int(p) for p in pages if int(p) > 0]
        return (min(nums), max(nums)) if nums else (2, 20)
    text = str(pages or "2-20")
    nums = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part or "~" in part:
            bits = re.split(r"[-~]", part, maxsplit=1)
            if len(bits) == 2 and bits[0].strip().isdigit() and bits[1].strip().isdigit():
                start, end = int(bits[0]), int(bits[1])
                nums.extend(range(min(start, end), max(start, end) + 1))
        elif part.isdigit():
            nums.append(int(part))
    return (min(nums), max(nums)) if nums else (2, 20)


def _write_structured_outputs(output_dir, result):
    """写出 OCR 缓存和校对产物。"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_page_texts = result.get("page_texts", {})
    page_texts = {int(k): v for k, v in raw_page_texts.items()}
    toc_pages = {int(p) for p in result.get("toc_pages", [])}
    raw_parts = [page_texts[p] for p in sorted(page_texts) if p in toc_pages and page_texts[p].strip()]
    if not raw_parts:
        raw_parts = [page_texts[p] for p in sorted(page_texts) if page_texts[p].strip()]
    (output_dir / "toc_raw.txt").write_text("\n\n".join(raw_parts).strip() + "\n", encoding="utf-8")

    by_page = []
    for page_num in sorted(page_texts):
        marker = "（目录页）" if page_num in toc_pages else ""
        by_page.append(f"## PDF 第 {page_num} 页{marker}\n\n{page_texts[page_num].strip()}")
    (output_dir / "toc_raw_by_page.md").write_text("\n\n".join(by_page).strip() + "\n", encoding="utf-8")
    (output_dir / "toc_structured.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "toc_detected_pages.json").write_text(json.dumps(result.get("page_scores", []), ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "toc.md").write_text(result.get("markdown", "") + "\n", encoding="utf-8")


def scan_textbook_toc_structured(pdf_path, pages="2-20", tessdata_dir=None, dpi=2.5,
                                 output_dir=None, reuse=True, keep_images=False,
                                 layout="auto", preprocess=False, verbose=False,
                                 lang="chi_sim"):
    """扫描教材目录并输出结构化结果，供规划表生成器直接复用。"""
    output_dir = Path(output_dir) if output_dir else None
    structured_path = output_dir / "toc_structured.json" if output_dir else None
    if reuse and structured_path and structured_path.exists():
        try:
            data = json.loads(structured_path.read_text(encoding="utf-8"))
            if data.get("entries"):
                if verbose:
                    print(f"  复用结构化目录缓存：{structured_path}")
                return data
        except Exception:
            pass

    tess_cmd = find_tesseract()
    if not tess_cmd:
        raise RuntimeError("未找到 Tesseract 可执行文件")
    if not check_tessdata(tessdata_dir, lang):
        raise RuntimeError(f"未找到 {lang}.traineddata 语言包")

    book_name = Path(pdf_path).stem
    auto_tmp = output_dir is None
    work_dir = tempfile.mkdtemp(prefix="toc_scan_") if auto_tmp else str(output_dir / "pages")
    page_range = _page_range_from_pages(pages)

    try:
        print(f"\n{'='*60}\n📚 处理：{book_name}\n{'='*60}")
        print(f"🖼  渲染页面（×{dpi} 分辨率）...")
        images = render_pdf_pages(pdf_path, page_range=page_range, out_dir=work_dir, dpi_scale=dpi)

        print(f"🔍 OCR 识别（共 {len(images)} 页，layout={layout}）...")
        page_texts = {}
        page_scores = []
        for img_path in images:
            page_num = int(re.search(r'page_(\d+)', img_path).group(1))
            if verbose:
                print(f"  → 识别第 {page_num} 页...")
            try:
                text = ocr_image_for_toc(img_path, tess_cmd, tessdata_dir, lang=lang, layout=layout, preprocess=preprocess)
            except Exception as e:
                if verbose:
                    print(f"  ⚠️  第 {page_num} 页 OCR 失败: {e}")
                text = ""
            page_texts[page_num] = text
            detail = score_toc_page_detail(text)
            detail["page"] = page_num
            page_scores.append(detail)

        print("📋 检测目录页...")
        toc_pages = [d["page"] for d in page_scores if d.get("is_toc")]
        if not toc_pages:
            print("  ⚠️  未检测到目录页，降低阈值重试...")
            toc_pages = [d["page"] for d in page_scores if d.get("total", 0) >= 1]
        if not toc_pages:
            toc_pages = sorted(page_texts)
        if verbose:
            for d in page_scores:
                print(f"  第 {d['page']} 页：得分 {d.get('total', 0)}")
        print(f"  📌 目录页：{toc_pages}")

        toc_page_texts = {p: page_texts[p] for p in toc_pages if p in page_texts}
        entries = parse_toc_structure_with_pages(toc_page_texts)
        markdown = entries_to_markdown(book_name, entries)
        result = {
            "book_name": book_name,
            "toc_pages": toc_pages,
            "page_texts": {str(k): v for k, v in page_texts.items()},
            "page_scores": page_scores,
            "entries": entries,
            "markdown": markdown,
            "settings": {
                "pages": pages,
                "dpi": dpi,
                "layout": layout,
                "preprocess": preprocess,
                "lang": lang,
            },
        }
        if output_dir:
            _write_structured_outputs(output_dir, result)
        print(f"✅ 完成：识别到 {len(entries)} 个目录条目")
        return result
    finally:
        if auto_tmp and not keep_images:
            shutil.rmtree(work_dir, ignore_errors=True)


# ──────────────────────────────────────────────
# 批量处理 + 输出
# ──────────────────────────────────────────────

def batch_scan(pdf_paths, tesseract_cmd, tessdata_dir=None,
               page_range=(2, 20), dpi_scale=2.5,
               output_path=None, keep_images=False,
               images_dir=None, verbose=False):
    """
    批量处理多本教材，汇总输出。

    Args:
        pdf_paths:    PDF 文件路径列表
        output_path:  输出 Markdown 文件路径（None 则打印到屏幕）
        images_dir:   保存渲染图像的根目录（None 则不保留）
        其余参数：同 scan_textbook()

    Returns:
        str: 完整 Markdown 文字
    """
    all_results = []

    for pdf_path in pdf_paths:
        if not os.path.isfile(pdf_path):
            print(f"❌ 文件不存在：{pdf_path}")
            continue

        # 为每本书分配图像目录
        book_name = Path(pdf_path).stem
        if keep_images and images_dir:
            work_dir = os.path.join(images_dir, book_name)
            os.makedirs(work_dir, exist_ok=True)
        else:
            work_dir = None

        result = scan_textbook(
            pdf_path,
            tesseract_cmd=tesseract_cmd,
            tessdata_dir=tessdata_dir,
            page_range=page_range,
            dpi_scale=dpi_scale,
            work_dir=work_dir,
            keep_images=keep_images,
            verbose=verbose,
        )
        all_results.append(result)

    # 汇总 Markdown
    header = "# 教材目录整理\n\n> 由 textbook_toc_scanner.py 自动生成（OCR识别，可能存在误差）\n"
    body = "\n\n---\n\n".join(r["markdown"] for r in all_results)
    full_md = header + "\n\n---\n\n" + body + "\n"

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_md)
        print(f"\n📝 目录已保存到：{output_path}")
    else:
        print("\n" + "="*60)
        print(full_md)

    return full_md


# ──────────────────────────────────────────────
# 命令行入口
# ──────────────────────────────────────────────

def parse_page_range(s):
    """解析页范围字符串，如 '2-20' → (2, 20)"""
    if "-" in s:
        parts = s.split("-")
        return (int(parts[0]), int(parts[1]))
    else:
        return (1, int(s))


def main():
    parser = argparse.ArgumentParser(
        description="扫描版教材PDF目录提取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("pdfs", nargs="+", help="PDF 文件路径（支持多个）")
    parser.add_argument("--pages", default="2-20",
                        help="扫描的页码范围，格式: 起始-结束，默认 2-20")
    parser.add_argument("--tessdata", default=None,
                        help="自定义 tessdata 目录（含 chi_sim.traineddata）")
    parser.add_argument("--output", "-o", default=None,
                        help="输出 Markdown 文件路径（不指定则打印到屏幕）")
    parser.add_argument("--dpi", type=float, default=2.5,
                        help="渲染分辨率倍率（1.0~4.0，默认 2.5）")
    parser.add_argument("--render-only", action="store_true",
                        help="仅渲染图像，不进行 OCR（用于调试）")
    parser.add_argument("--keep-images", action="store_true",
                        help="保留渲染的 PNG 图像文件")
    parser.add_argument("--out-dir", default=None,
                        help="结构化 OCR/图像保存目录；--keep-images 时保存渲染图像")
    parser.add_argument("--layout", choices=["auto", "single", "double"], default="auto",
                        help="目录版面：auto 自动、single 单栏、double 双栏，默认 auto")
    parser.add_argument("--preprocess", action="store_true",
                        help="OCR 前对图片做灰度/对比度/二值化增强")
    parser.add_argument("--no-reuse", action="store_true",
                        help="不复用 out-dir 中已有 toc_structured.json")
    parser.add_argument("--structured", action="store_true",
                        help="输出 toc_raw/toc_structured/toc_detected_pages/toc.md 等结构化产物")
    parser.add_argument("--lang", default="chi_sim",
                        help="OCR 语言代码（默认 chi_sim 中文简体）")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="输出详细日志")

    args = parser.parse_args()

    # 检查依赖
    check_dependencies()
    tess_cmd = find_tesseract()

    # 检查中文语言包
    if not check_tessdata(args.tessdata, args.lang):
        print(f"⚠️  未找到 {args.lang}.traineddata 语言包。")
        if args.tessdata:
            print(f"   请将 {args.lang}.traineddata 放入：{args.tessdata}")
        else:
            print(f"   请将 {args.lang}.traineddata 放入 Tesseract 的 tessdata 目录，")
            print(f"   或通过 --tessdata 参数指定自定义路径。")
            print(f"   下载地址：https://github.com/tesseract-ocr/tessdata/raw/main/{args.lang}.traineddata")
        sys.exit(1)

    page_range = parse_page_range(args.pages)

    # 仅渲染模式
    if args.render_only:
        out_dir = args.out_dir or "./rendered_images"
        for pdf in args.pdfs:
            book_name = Path(pdf).stem
            dir_path = os.path.join(out_dir, book_name)
            os.makedirs(dir_path, exist_ok=True)
            imgs = render_pdf_pages(pdf, page_range, dir_path, args.dpi)
            print(f"✅ {book_name}：渲染 {len(imgs)} 页 → {dir_path}")
        return

    # 批量 OCR + 解析
    if args.structured or args.out_dir or args.layout != "auto" or args.preprocess:
        all_md = []
        for pdf in args.pdfs:
            book_dir = Path(args.out_dir) / Path(pdf).stem if args.out_dir and len(args.pdfs) > 1 else (Path(args.out_dir) if args.out_dir else None)
            result = scan_textbook_toc_structured(
                pdf,
                pages=args.pages,
                tessdata_dir=args.tessdata,
                dpi=args.dpi,
                output_dir=book_dir,
                reuse=not args.no_reuse,
                keep_images=args.keep_images,
                layout=args.layout,
                preprocess=args.preprocess,
                verbose=args.verbose,
                lang=args.lang,
            )
            all_md.append(result["markdown"])
        full_md = "# 教材目录整理\n\n" + "\n\n---\n\n".join(all_md) + "\n"
        if args.output:
            Path(args.output).write_text(full_md, encoding="utf-8")
            print(f"\n📝 目录已保存到：{args.output}")
        else:
            print("\n" + full_md)
        return

    batch_scan(
        pdf_paths=args.pdfs,
        tesseract_cmd=tess_cmd,
        tessdata_dir=args.tessdata,
        page_range=page_range,
        dpi_scale=args.dpi,
        output_path=args.output,
        keep_images=args.keep_images,
        images_dir=args.out_dir,
        verbose=args.verbose,
    )


# ──────────────────────────────────────────────
# 作为模块调用的便捷函数
# ──────────────────────────────────────────────

def scan_single(pdf_path, tessdata_dir=None, pages="2-20",
                dpi=2.5, output=None, verbose=False):
    """
    便捷函数：扫描单本教材目录并返回 Markdown 字符串。

    示例：
        from textbook_toc_scanner import scan_single
        md = scan_single("电工技术.pdf", tessdata_dir="./tessdata")
        print(md)
    """
    check_dependencies()
    tess_cmd = find_tesseract()
    if not tess_cmd:
        raise RuntimeError("Tesseract not found. Install it first.")

    page_range = parse_page_range(pages)
    result = scan_textbook(
        pdf_path,
        tesseract_cmd=tess_cmd,
        tessdata_dir=tessdata_dir,
        page_range=page_range,
        dpi_scale=dpi,
        verbose=verbose,
    )

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(result["markdown"])
        print(f"📝 已保存：{output}")

    return result["markdown"]


def scan_multiple(pdf_paths, tessdata_dir=None, pages="2-20",
                  dpi=2.5, output=None, verbose=False):
    """
    便捷函数：扫描多本教材并汇总输出。

    示例：
        from textbook_toc_scanner import scan_multiple
        books = ["电工技术.pdf", "电子技术.pdf", "电机技术.pdf"]
        md = scan_multiple(books, tessdata_dir="./tessdata", output="目录.md")
    """
    check_dependencies()
    tess_cmd = find_tesseract()
    if not tess_cmd:
        raise RuntimeError("Tesseract not found. Install it first.")

    page_range = parse_page_range(pages)
    return batch_scan(
        pdf_paths=pdf_paths,
        tesseract_cmd=tess_cmd,
        tessdata_dir=tessdata_dir,
        page_range=page_range,
        dpi_scale=dpi,
        output_path=output,
        verbose=verbose,
    )


if __name__ == "__main__":
    main()
