"""Textbook TOC OCR, parsing, and textbook path helpers."""

import json
import os
import re
import sys
from pathlib import Path

from plan_modules.config import BASE_DIR, safe_path_part as _safe_path_part


_PUBLISHER_SHORT = {
    "高等教育出版社": "高教", "高教版": "高教", "高教": "高教",
    "机械工业出版社": "机工", "机工版": "机工", "机工": "机工",
    "人民邮电出版社": "人邮", "人邮版": "人邮", "人邮": "人邮",
    "重庆大学出版社": "重大", "重大版": "重大", "重大": "重大",
}


def parse_pages_list(pages_str, default_end=None):
    """解析页码范围，如 1,3,5-8；不传且给定 default_end 时默认前 default_end 页。"""
    if not pages_str:
        if default_end is None:
            return []
        return list(range(1, default_end + 1))
    pages = []
    for part in str(pages_str).split(","):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(\d+)\s*[-~]\s*(\d+)$", part)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            pages.extend(range(min(start, end), max(start, end) + 1))
        else:
            try:
                pages.append(int(part))
            except ValueError:
                pass
    return sorted(set(p for p in pages if p > 0))


def prompt_toc_pages_for_textbook(pdf_path):
    """交互询问单本教材的目录页范围。"""
    while True:
        print(f"请输入《{Path(pdf_path).stem}》目录所在页码范围（如 1-3 或 2,4-6）：")
        pages_input = input("> ").strip()
        pages = parse_pages_list(pages_input)
        if pages:
            return pages
        print("页码范围不能为空，且需包含有效正整数页码。")



def parse_textbook_filename(path):
    """从教材 PDF 文件名中提取书名、出版社简称、版次。"""
    stem = Path(path).stem
    name = stem
    publisher = ""
    edition = ""

    m = re.search(r"(.+?)[（(]([^）)]*?)(高教|机工|人邮|重大|[^）)]{2,8}出版社)?(?:版)?[·•\s_-]*第\s*(\d+)\s*版[^）)]*[）)]", stem)
    if m:
        name = m.group(1).strip()
        raw_pub = (m.group(2) or m.group(3) or "").strip(" ·•_-版")
        publisher = _PUBLISHER_SHORT.get(raw_pub, raw_pub[:2] if raw_pub else "")
        edition = m.group(4)
    else:
        m = re.search(r"(.+?)[（(]([^）)]+)[）)]", stem)
        if m:
            name = m.group(1).strip()
            inside = m.group(2)
            pub_m = re.search(r"(高教|机工|人邮|重大|[一-龥]+出版社)", inside)
            ed_m = re.search(r"第\s*(\d+)\s*版", inside)
            if pub_m:
                raw_pub = pub_m.group(1)
                publisher = _PUBLISHER_SHORT.get(raw_pub, raw_pub[:2])
            if ed_m:
                edition = ed_m.group(1)

    name = re.sub(r"[（(].*$", "", name).strip()
    return {"name": name or stem, "publisher": publisher or "待填", "edition": int(edition) if str(edition).isdigit() else "待填", "path": str(path)}



def _textbook_info_line(textbook):
    edition = textbook.get("edition", "待填")
    if isinstance(edition, int):
        edition_text = f"第{edition}版"
    elif str(edition).isdigit():
        edition_text = f"第{edition}版"
    else:
        edition_text = "第待填版"
    return f"参考教材：《{textbook.get('name', '待填写')}》{textbook.get('publisher', '待填')}{edition_text}"


def _clean_toc_title(text):
    text = re.sub(r"\.{2,}\s*\d+\s*$", "", text)
    text = re.sub(r"[·•]{2,}\s*\d+\s*$", "", text)
    text = re.sub(r"\s+\d+\s*$", "", text)
    text = re.sub(r"^(第[一二三四五六七八九十百\d]+[章节篇项目]|项目[一二三四五六七八九十\d]+|任务[一二三四五六七八九十\d]+|\d+(?:[．.]\d+)*|[一二三四五六七八九十]+[、.．])\s*", "", text)
    text = re.sub(r"^(学习任务|任务|项目|知识点|单元|模块)\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ：:.-—_\t")
    return text


def make_theme_from_toc(title):
    theme = _clean_toc_title(title)
    theme = re.sub(r"(的)?(概念|知识|方法|原理|定义|概述|基础|简介)$", "", theme)
    theme = theme.replace(" ", "")
    return theme[:12] or title.strip()[:12]



def _parse_toc_line(line):
    raw = line.strip()
    if not raw or raw in ("目录", "CONTENTS", "Contents"):
        return None
    raw = re.sub(r"\s+", " ", raw)
    raw = re.sub(r"[.·•…]{2,}", " ", raw)
    m_page = re.search(r"(?:\s|^)(\d{1,4})\s*$", raw)
    page = int(m_page.group(1)) if m_page else None
    text = re.sub(r"\s+\d{1,4}\s*$", "", raw).strip()

    chapter_patterns = [
        r"^(第[一二三四五六七八九十百\d]+[章篇])\s+(.+)$",
        r"^(项目[一二三四五六七八九十\d]+)\s+(.+)$",
        r"^(模块[一二三四五六七八九十\d]+)\s+(.+)$",
    ]
    for pat in chapter_patterns:
        m = re.match(pat, text)
        if m:
            return {"kind": "chapter", "title": f"{m.group(1)} {m.group(2).strip()}", "page": page}

    section_patterns = [
        r"^(\d+[．.]\d+(?:[．.]\d+)*)\s*(.+)$",
        r"^(任务[一二三四五六七八九十\d]+)\s+(.+)$",
        r"^([一二三四五六七八九十]+[、.．])\s*(.+)$",
        r"^(\d+[、.．])\s*(.+)$",
    ]
    for pat in section_patterns:
        m = re.match(pat, text)
        if m and len(m.group(2).strip()) >= 2:
            return {"kind": "section", "title": f"{m.group(1)} {m.group(2).strip()}", "page": page}
    return None


def parse_toc_text(toc_text):
    """将教材目录 OCR 文本解析为章/节/主题列表。"""
    items = []
    current_chapter = ""
    seen = set()
    for line in toc_text.splitlines():
        parsed = _parse_toc_line(line)
        if not parsed:
            continue
        title = parsed["title"]
        if parsed["kind"] == "chapter":
            current_chapter = title
            continue
        key = (current_chapter, title)
        if key in seen:
            continue
        seen.add(key)
        theme = make_theme_from_toc(title)
        if len(theme) < 2:
            continue
        items.append({
            "id": f"toc-{len(items) + 1}",
            "chapter": current_chapter or "教材目录",
            "section": title,
            "theme": theme,
            "page": parsed.get("page"),
        })
    return items


def ocr_textbook_toc(pdf_path, pages, output_dir, reuse=True, engine="auto", tessdata_dir=None,
                     dpi=2.5, layout="auto", preprocess=False, keep_images=False):
    """OCR 教材目录页，优先使用目录专用扫描器，缓存 toc_raw/toc_structured 并返回文本。"""
    output_dir = Path(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    raw_path = output_dir / "toc_raw.txt"
    structured_path = output_dir / "toc_structured.json"
    if reuse and structured_path.exists() and raw_path.exists() and raw_path.read_text(encoding="utf-8", errors="ignore").strip():
        return raw_path.read_text(encoding="utf-8", errors="ignore")
    if reuse and raw_path.exists() and raw_path.read_text(encoding="utf-8", errors="ignore").strip():
        return raw_path.read_text(encoding="utf-8", errors="ignore")

    engine = (engine or "auto").lower()
    if engine in ("auto", "tesseract"):
        try:
            from textbook_toc_scanner import scan_textbook_toc_structured
            print(f"  使用 Tesseract 目录专用 OCR: {Path(pdf_path).name} 页码 {pages}")
            result = scan_textbook_toc_structured(
                pdf_path,
                pages=pages,
                tessdata_dir=tessdata_dir,
                dpi=dpi,
                output_dir=output_dir,
                reuse=False,
                keep_images=keep_images,
                layout=layout,
                preprocess=preprocess,
                verbose=False,
            )
            text = raw_path.read_text(encoding="utf-8", errors="ignore") if raw_path.exists() else "\n\n".join(result.get("page_texts", {}).values())
            raw_path.write_text(text, encoding="utf-8")
            return text
        except Exception as e:
            if engine == "tesseract":
                print(f"错误：Tesseract 目录 OCR 失败：{e}")
                sys.exit(1)
            print(f"  Tesseract 目录 OCR 不可用，回退 RapidOCR：{e}")

    ocr_dir = BASE_DIR / "01_工具脚本" / "OCR"
    if str(ocr_dir) not in sys.path:
        sys.path.insert(0, str(ocr_dir))
    try:
        from ocr_pdf import export_pdf_pages, run_ocr
    except ImportError:
        print("错误：无法导入 OCR/ocr_pdf.py")
        sys.exit(1)

    print(f"  OCR 教材目录页: {Path(pdf_path).name} 页码 {pages}")
    try:
        image_entries = export_pdf_pages(pdf_path, output_dir, pages=pages, zoom=dpi)
        run_ocr(image_entries, output_dir, min_score=0.0)
    except SystemExit:
        raise
    except Exception as e:
        print(f"错误：教材目录 OCR 失败：{e}")
        sys.exit(1)

    combined = output_dir / "combined.txt"
    text = combined.read_text(encoding="utf-8", errors="ignore") if combined.exists() else ""
    raw_path.write_text(text, encoding="utf-8")
    return text


def convert_scanner_entries_to_toc_items(entries):
    """将 textbook_toc_scanner 的结构化 entries 转为 generate_plan 的 toc_items。"""
    items = []
    current_chapter = "教材目录"
    seen = set()
    for entry in entries or []:
        level = int(entry.get("level") or 0)
        title = str(entry.get("title") or "").strip()
        if not title:
            continue
        if level == 1:
            current_chapter = title
            continue
        key = (current_chapter, title)
        if key in seen:
            continue
        seen.add(key)
        theme = make_theme_from_toc(title)
        if len(theme) < 2:
            continue
        items.append({
            "id": f"toc-{len(items) + 1}",
            "chapter": current_chapter,
            "section": title,
            "theme": theme,
            "page": entry.get("book_page"),
            "source_page": entry.get("source_page"),
            "raw_line": entry.get("raw_line", ""),
        })
    return items


def load_structured_toc_items(ocr_dir):
    """读取增强 OCR 产出的 toc_structured.json，并转为 toc_items。"""
    structured_path = Path(ocr_dir) / "toc_structured.json"
    if not structured_path.exists():
        return []
    try:
        data = json.loads(structured_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    entries = data.get("entries", [])
    return convert_scanner_entries_to_toc_items(entries)


def _resolve_textbook_pdfs(args, province, category):
    if args.textbook_pdf:
        return [Path(args.textbook_pdf)]
    candidates = []
    if args.textbook_dir:
        candidates.append(Path(args.textbook_dir))
    if province and category:
        # 双击交互时按标题前缀优先查找：03_项目数据/参考资料/教材/省份/考类
        candidates.append(BASE_DIR / "03_项目数据" / "参考资料" / "教材" / province / category)
        candidates.append(BASE_DIR / "03_项目数据" / "教材" / province / category)
    for directory in candidates:
        if directory.exists():
            pdfs = sorted(p for p in directory.glob("*.pdf") if not p.name.startswith("~"))
            if pdfs:
                return pdfs
    return []


def _warn_missing_textbook_pdfs(expected_textbooks, pdfs):
    """提示考纲参考教材与实际教材 PDF 数量/名称不一致。"""
    if not expected_textbooks:
        return

    found = [parse_textbook_filename(p) for p in pdfs]
    found_names = [tb.get("name", "") for tb in found]
    missing = []
    for expected in expected_textbooks:
        expected_name = expected.get("name", "")
        if not expected_name:
            continue
        matched = any(
            expected_name in found_name or found_name in expected_name
            for found_name in found_names
            if found_name
        )
        if not matched:
            missing.append(expected)

    if len(pdfs) != len(expected_textbooks) or missing:
        print("\n警告：考试说明中的参考教材与当前教材 PDF 不完全一致。")
        print(f"  考试说明参考教材：{len(expected_textbooks)} 本；当前找到教材 PDF：{len(pdfs)} 本")
        if found:
            print("  已找到教材 PDF：")
            for tb in found:
                print(f"    - 《{tb.get('name', '未知教材')}》{tb.get('publisher', '待填')}第{tb.get('edition', '待填')}版")
        if missing:
            print("  可能缺失教材 PDF：")
            for tb in missing:
                print(f"    - 《{tb.get('name', '未知教材')}》{tb.get('publisher', '待填')}第{tb.get('edition', '待填')}版")
        print("  如需生成三本书对应的三个规划表，请把缺失教材 PDF 放入 --textbook-dir 指定目录。")



def _match_course_name(textbook, courses):
    name = textbook.get("name", "")
    for course in courses:
        if name and (name in course["name"] or course["name"] in name):
            return course["name"]
    return ""


def _default_ocr_dir(args, province, category, textbook):
    if args.ocr_output_dir:
        return Path(args.ocr_output_dir)
    return BASE_DIR / "03_项目数据" / "参考资料" / "教材OCR" / _safe_path_part(province or "未分类") / _safe_path_part(category or "未分类") / _safe_path_part(textbook.get("name", "教材"))

