"""从 PDF 提取文本保存为参考资料 txt 文件

使用方法：
  # 提取真题
  python 01_工具脚本/资料提取/extract_ref.py --pdf "2024年真题.pdf" --type exam --output "03_项目数据/参考资料/真题/重庆市机械加工类_2024真题.txt"

  # 提取教材（全书）
  python 01_工具脚本/资料提取/extract_ref.py --pdf "教材.pdf" --type textbook --output "03_项目数据/参考资料/教材/机械基础.txt"

  # 提取教材（指定页码范围，对应某章节）
  python 01_工具脚本/资料提取/extract_ref.py --pdf "教材.pdf" --type textbook --pages 45-78 --output "03_项目数据/参考资料/教材/机械基础_第3章_材料与选用.txt"

  # 批量提取目录下所有 PDF
  python 01_工具脚本/资料提取/extract_ref.py --dir "真题PDF目录/" --type exam --output-dir "03_项目数据/参考资料/真题/"
"""

import argparse
import os
import re
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def extract_pdf_text(pdf_path, pages=None):
    """从 PDF 提取文本

    Args:
        pdf_path: PDF 文件路径
        pages: 可选的页码范围元组 (start, end)，1-based 闭区间
    Returns:
        提取的文本字符串
    """
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            if pages:
                start, end = pages
                start = max(1, start) - 1
                end = min(total_pages, end)
                page_range = range(start, end)
            else:
                page_range = range(total_pages)

            for i in page_range:
                page_text = pdf.pages[i].extract_text()
                if page_text:
                    text += page_text + "\n"
    except ImportError:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            if pages:
                start, end = pages
                start = max(1, start) - 1
                end = min(total_pages, end)
                page_range = range(start, end)
            else:
                page_range = range(total_pages)

            for i in page_range:
                page_text = reader.pages[i].extract_text()
                if page_text:
                    text += page_text + "\n"
        except ImportError:
            print("错误：需要安装 pdfplumber 或 PyPDF2")
            print("  pip install pdfplumber")
            sys.exit(1)

    return _clean_text(text)


def _clean_text(text):
    """清理提取的文本：去除页码标记、多余空行等"""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # 跳过纯页码行
        if re.match(r'^\d+$', stripped):
            continue
        # 跳过 PDF 页分隔标记
        if re.match(r'^-+\s*\d+\s*(of|/)\s*\d+\s*-+$', stripped):
            continue
        cleaned.append(line)

    # 合并连续空行为单个空行
    result = []
    prev_empty = False
    for line in cleaned:
        if not line.strip():
            if not prev_empty:
                result.append("")
            prev_empty = True
        else:
            result.append(line)
            prev_empty = False

    return "\n".join(result).strip()


def split_by_chapters(text):
    """将教材文本按章节拆分

    识别的章节标题格式：
      - "第X章 xxx" / "第一章 xxx"
      - "1. xxx" / "1．xxx"（顶格，非缩进的考点行）
    Returns:
        [(chapter_title, chapter_text), ...]
    """
    lines = text.split("\n")
    chapters = []
    current_title = "全文"
    current_lines = []

    chapter_pattern = re.compile(
        r'^(第[一二三四五六七八九十百\d]+[章节篇])\s*(.+)'
        r'|^(\d+)[．.]\s*([^\s（(了解理解掌握熟悉能会认识].{2,})'
    )

    for line in lines:
        stripped = line.strip()
        m = chapter_pattern.match(stripped)
        if m:
            # 保存上一章
            if current_lines:
                chapters.append((current_title, "\n".join(current_lines)))
            # 新章节
            if m.group(1):
                current_title = f"{m.group(1)} {m.group(2)}"
            else:
                current_title = f"{m.group(3)}．{m.group(4)}"
            current_lines = [stripped]
        else:
            current_lines.append(line)

    if current_lines:
        chapters.append((current_title, "\n".join(current_lines)))

    return chapters


def parse_pages_arg(pages_str):
    """解析页码范围参数，如 '45-78' → (45, 78)"""
    if not pages_str:
        return None
    m = re.match(r'(\d+)\s*[-~]\s*(\d+)', pages_str)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    # 单页
    try:
        p = int(pages_str)
        return (p, p)
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser(description="从 PDF 提取参考资料文本")
    parser.add_argument("--pdf", "-p", help="单个 PDF 文件路径")
    parser.add_argument("--dir", "-d", help="批量处理：PDF 文件所在目录")
    parser.add_argument("--type", "-t", choices=["exam", "textbook"],
                        default="exam", help="资料类型：exam=真题, textbook=教材")
    parser.add_argument("--pages", help="提取的页码范围（如 45-78）")
    parser.add_argument("--output", "-o", help="输出 txt 文件路径")
    parser.add_argument("--output-dir", help="批量输出目录")
    parser.add_argument("--split-chapters", action="store_true",
                        help="教材模式下按章节拆分为多个文件")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[2]

    if args.dir:
        # 批量模式
        pdf_dir = Path(args.dir)
        if not pdf_dir.exists():
            print(f"错误：目录不存在 {args.dir}")
            sys.exit(1)

        out_dir = Path(args.output_dir) if args.output_dir else base_dir / "03_项目数据" / "参考资料" / ("真题" if args.type == "exam" else "教材")
        os.makedirs(out_dir, exist_ok=True)

        pdfs = list(pdf_dir.glob("*.pdf"))
        print(f"找到 {len(pdfs)} 个 PDF 文件")

        for pdf_file in pdfs:
            print(f"\n处理: {pdf_file.name}")
            text = extract_pdf_text(str(pdf_file))
            out_name = pdf_file.stem + ".txt"
            out_path = out_dir / out_name
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"  → {out_path} ({len(text)} 字)")

    elif args.pdf:
        # 单文件模式
        if not os.path.exists(args.pdf):
            print(f"错误：文件不存在 {args.pdf}")
            sys.exit(1)

        pages = parse_pages_arg(args.pages)
        text = extract_pdf_text(args.pdf, pages)
        print(f"提取文本: {len(text)} 字")

        if args.split_chapters and args.type == "textbook":
            # 按章节拆分
            chapters = split_by_chapters(text)
            out_dir = Path(args.output_dir) if args.output_dir else base_dir / "03_项目数据" / "参考资料" / "教材"
            os.makedirs(out_dir, exist_ok=True)

            pdf_stem = Path(args.pdf).stem
            for i, (title, content) in enumerate(chapters):
                safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:30]
                out_path = out_dir / f"{pdf_stem}_{safe_title}.txt"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  章节 {i+1}: {title} → {out_path.name} ({len(content)} 字)")
        else:
            # 整体输出
            if args.output:
                out_path = Path(args.output)
            else:
                sub = "真题" if args.type == "exam" else "教材"
                out_dir = base_dir / "03_项目数据" / "参考资料" / sub
                os.makedirs(out_dir, exist_ok=True)
                out_path = out_dir / (Path(args.pdf).stem + ".txt")

            os.makedirs(out_path.parent, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"已保存: {out_path} ({len(text)} 字)")

    else:
        # 交互模式
        print("PDF 参考资料提取工具")
        print("=" * 40)
        print("\n请输入 PDF 文件路径：")
        pdf_path = input("> ").strip().strip('"')
        if not os.path.exists(pdf_path):
            print(f"错误：文件不存在")
            sys.exit(1)

        print("\n资料类型：")
        print("  1. 真题")
        print("  2. 教材")
        choice = input("> ").strip()
        ref_type = "textbook" if choice == "2" else "exam"

        pages = None
        if ref_type == "textbook":
            print("\n页码范围（如 45-78，留空提取全部）：")
            pages_str = input("> ").strip()
            pages = parse_pages_arg(pages_str)

        text = extract_pdf_text(pdf_path, pages)
        print(f"\n提取文本: {len(text)} 字")

        sub = "真题" if ref_type == "exam" else "教材"
        out_dir = base_dir / "03_项目数据" / "参考资料" / sub
        os.makedirs(out_dir, exist_ok=True)
        out_path = out_dir / (Path(pdf_path).stem + ".txt")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"已保存: {out_path}")


if __name__ == "__main__":
    main()
