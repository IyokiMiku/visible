"""教材目录本地扫描（阶段四 shared/ocr，源 textbook_toc_scanner 去硬编码）。

路径参数化：从 ctx 输入目录读取教材 PDF，结果写项目树 教材目录扫描/。
优先用 PDF 内置书签(TOC)，否则抽取前若干页文本。
"""
from __future__ import annotations

from pathlib import Path


def _find_pdfs(ctx) -> list[Path]:
    in_dir = ctx.input_dir()
    if not in_dir.exists():
        return []
    return sorted(in_dir.rglob("*.pdf"))


def scan_textbook_toc(ctx, pdf_path: Path | None = None) -> Path:
    out_dir = ctx.dir("教材目录扫描")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "_教材目录扫描结果.md"

    pdfs = [pdf_path] if pdf_path else _find_pdfs(ctx)
    pdfs = [p for p in pdfs if p and Path(p).exists()]

    lines: list[str] = [f"# 教材目录扫描结果（{ctx.textbook or ctx.course}）", ""]
    if not pdfs:
        lines += ["> 未找到教材 PDF（请在资源导入页上传），以下为空。", ""]
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return out_path

    try:
        import fitz  # pymupdf
    except Exception as e:
        lines += [f"> 本地 OCR 依赖未就绪：{e}", ""]
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return out_path

    for pdf in pdfs:
        lines.append(f"## {Path(pdf).name}")
        doc = fitz.open(str(pdf))
        toc = doc.get_toc() or []
        if toc:
            for level, title, page in toc:
                indent = "  " * (max(1, level) - 1)
                lines.append(f"{indent}- {title}（p{page}）")
        else:
            # 无书签：抽取前 5 页文本作为目录线索
            for i in range(min(5, doc.page_count)):
                text = doc.load_page(i).get_text("text").strip()
                if text:
                    lines.append(f"### 第{i + 1}页文本片段")
                    lines.append(text[:800])
        doc.close()
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
