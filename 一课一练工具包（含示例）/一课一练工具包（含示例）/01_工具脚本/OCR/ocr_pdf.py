"""图片型 PDF 本地 OCR 工具

用途：
  将扫描版/图片型 PDF 按页转为图片，并用 RapidOCR 本地识别为 txt/json/md。
  OCR 结果建议只作为“人工摘录真题样本”的辅助，不建议直接作为最终知识依据。

使用示例：
  python ocr_pdf.py --pdf "../真题PDF/2024年真题.pdf" --output-dir "output/2024真题"
  python ocr_pdf.py --pdf "../真题PDF/2024年真题.pdf" --pages 1,3,5-8 --output-dir "output/抽样"
  python ocr_pdf.py --pdf "../真题PDF/2024年真题.pdf" --pages 1-5 --export-only
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def parse_pages_arg(pages_str):
    """解析页码范围，如 '1,3,5-8' → [1,3,5,6,7,8]。"""
    if not pages_str:
        return []
    pages = []
    for part in pages_str.split(","):
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


def export_pdf_pages(pdf_path, output_dir, pages=None, zoom=2.0):
    """将 PDF 指定页导出为 PNG。返回 [(page_num, image_path), ...]。"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("错误：缺少 PyMuPDF，请先安装：pip install pymupdf")
        sys.exit(1)

    pdf_path = Path(pdf_path)
    pages_dir = Path(output_dir) / "pages"
    os.makedirs(pages_dir, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    if not pages:
        pages = list(range(1, total_pages + 1))

    exported = []
    matrix = fitz.Matrix(zoom, zoom)
    for page_num in pages:
        if page_num < 1 or page_num > total_pages:
            print(f"  跳过无效页码: {page_num}")
            continue
        page = doc[page_num - 1]
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image_path = pages_dir / f"page_{page_num:03d}.png"
        pix.save(str(image_path))
        exported.append((page_num, image_path))
        print(f"  导出第 {page_num}/{total_pages} 页: {image_path}")

    doc.close()
    return exported


def load_ocr_engine():
    """加载 RapidOCR 引擎。"""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        print("错误：缺少 rapidocr-onnxruntime，请先安装：pip install rapidocr-onnxruntime")
        sys.exit(1)
    return RapidOCR()


def _json_safe_box(box):
    """将 RapidOCR 可能返回的 numpy 坐标转换为可写入 JSON 的普通列表。"""
    try:
        if hasattr(box, "tolist"):
            return box.tolist()
        return [[float(x), float(y)] for x, y in box]
    except Exception:
        return box


def _normalize_ocr_result(raw_result):
    """兼容 RapidOCR 不同版本的返回结构，统一为行列表。"""
    # 常见返回：result, elapse = engine(image_path)
    if isinstance(raw_result, tuple) and len(raw_result) >= 1:
        raw_result = raw_result[0]
    if raw_result is None:
        return []

    lines = []
    for item in raw_result:
        # 常见 item: [box, text, score]
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        box = item[0]
        text = item[1]
        score = item[2] if len(item) > 2 else None
        if not text:
            continue
        lines.append({
            "box": _json_safe_box(box),
            "text": str(text).strip(),
            "score": float(score) if isinstance(score, (int, float)) else None,
        })
    return lines


def _box_xy(box):
    """取 OCR 框左上角近似坐标，用于排序。"""
    try:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        return min(xs), min(ys)
    except Exception:
        return 0, 0


def sort_ocr_lines(lines):
    """按从上到下、从左到右排序 OCR 行。"""
    return sorted(lines, key=lambda item: (_box_xy(item.get("box"))[1], _box_xy(item.get("box"))[0]))


def lines_to_text(lines, min_score=0.0):
    """将 OCR 行转换为纯文本。"""
    parts = []
    for item in lines:
        score = item.get("score")
        if score is not None and score < min_score:
            continue
        text = item.get("text", "").strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def run_ocr(image_entries, output_dir, min_score=0.0):
    """对页面图片执行 OCR，并输出 json/txt/combined。"""
    engine = load_ocr_engine()
    output_dir = Path(output_dir)
    json_dir = output_dir / "json"
    txt_dir = output_dir / "txt"
    os.makedirs(json_dir, exist_ok=True)
    os.makedirs(txt_dir, exist_ok=True)

    combined_txt_parts = []
    combined_md_parts = []

    for page_num, image_path in image_entries:
        print(f"  OCR 第 {page_num} 页...")
        try:
            raw = engine(str(image_path))
            lines = sort_ocr_lines(_normalize_ocr_result(raw))
            page_text = lines_to_text(lines, min_score=min_score)
        except Exception as e:
            print(f"    ! OCR 第 {page_num} 页失败，已跳过：{e}")
            lines = []
            page_text = ""

        json_path = json_dir / f"page_{page_num:03d}.json"
        txt_path = txt_dir / f"page_{page_num:03d}.txt"

        json_path.write_text(json.dumps({
            "page": page_num,
            "image": str(image_path),
            "lines": lines,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        txt_path.write_text(page_text + "\n", encoding="utf-8")

        combined_txt_parts.append(page_text)
        combined_md_parts.append(f"\n\n## 第 {page_num} 页\n\n{page_text}")
        print(f"    → {txt_path} ({len(page_text)} 字)")

    combined_txt = "\n\n".join(part for part in combined_txt_parts if part.strip()).strip()
    combined_md = "\n".join(combined_md_parts).strip()
    (output_dir / "combined.txt").write_text(combined_txt + "\n", encoding="utf-8")
    (output_dir / "combined.md").write_text(combined_md + "\n", encoding="utf-8")
    print(f"\n已生成合并文本：{output_dir / 'combined.txt'}")
    print(f"已生成带页码文本：{output_dir / 'combined.md'}")


def main():
    parser = argparse.ArgumentParser(description="图片型 PDF 本地 OCR 工具")
    parser.add_argument("--pdf", required=True, help="PDF 文件路径")
    parser.add_argument("--output-dir", "-o", help="输出目录，默认 output/PDF文件名")
    parser.add_argument("--pages", help="页码范围，如 1,3,5-8；不填则处理全部页")
    parser.add_argument("--zoom", type=float, default=2.0, help="PDF 转图片倍率，默认 2.0；识别差可试 3.0")
    parser.add_argument("--min-score", type=float, default=0.0, help="过滤低置信度文本，默认不过滤")
    parser.add_argument("--export-only", action="store_true", help="只导出页面图片，不执行 OCR")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"错误：PDF 文件不存在：{pdf_path}")
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else Path("output") / pdf_path.stem
    os.makedirs(output_dir, exist_ok=True)

    pages = parse_pages_arg(args.pages)
    print(f"PDF: {pdf_path}")
    print(f"输出目录: {output_dir}")
    if pages:
        print(f"处理页码: {pages}")
    else:
        print("处理页码: 全部")

    image_entries = export_pdf_pages(pdf_path, output_dir, pages=pages, zoom=args.zoom)
    if args.export_only:
        print("\n已按 --export-only 仅导出图片，未执行 OCR。")
        return

    run_ocr(image_entries, output_dir, min_score=args.min_score)


if __name__ == "__main__":
    main()
