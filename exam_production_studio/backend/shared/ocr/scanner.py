"""教材目录扫描（阶段四 shared/ocr，阶段 A 增强）。

按 PDF 类型分支：
- 文字版：优先 PDF 内置书签(TOC)，否则抽取目录页文本层；
- 图片版：渲染目录页为图 → 视觉 OCR（vision_ocr）；未启用视觉时回退文本层并标注。

两分支统一产出结构化 ``toc_structured.json``（供阶段 C/D 消费），并保留 md（人工阅读/向后兼容）。
"""
from __future__ import annotations

from pathlib import Path

from shared.ocr import toc_structured as ts
from shared.ocr.pdf_type import IMAGE, detect_pdf_type
from shared.ocr.vision import VisionNotEnabled, render_pdf_pages, vision_ocr

_TOC_PAGES = 12  # 目录页默认扫描范围（前 N 页）


def _find_pdfs(ctx) -> list[Path]:
    in_dir = ctx.input_dir()
    if not in_dir.exists():
        return []
    return sorted(in_dir.rglob("*.pdf"))


def _text_pages(doc, pages: int) -> str:
    parts: list[str] = []
    for i in range(min(pages, doc.page_count)):
        t = doc.load_page(i).get_text("text").strip()
        if t:
            parts.append(t)
    return "\n".join(parts)


def _structured_dir(ctx) -> Path:
    return ctx.dir("教材目录扫描")


def _build_structured_for_pdf(pdf: Path, ctx) -> tuple[ts.StructuredToc, list[str]]:
    """对单本教材 PDF 产出结构化目录 + 供 md 展示的行。返回 (structured, md_lines)。"""
    import fitz  # pymupdf

    md_lines: list[str] = [f"## {pdf.name}"]
    detect = detect_pdf_type(pdf)
    md_lines.append(f"> 类型判定：{detect.kind}（{detect.reason}）")

    structured = ts.StructuredToc(textbook=pdf.stem, source_pdf=pdf.name, pdf_kind=detect.kind)
    doc = fitz.open(str(pdf))
    try:
        bookmarks = doc.get_toc() or []
        if bookmarks:
            # 书签最可靠、不依赖页面文本层，优先采用（图片版也可能带人工书签）
            structured.nodes = ts.build_from_bookmarks(bookmarks)
            md_lines.append("> 来源：PDF 内置书签。")
        elif detect.kind == IMAGE:
            # 图片版：渲染目录页 → 视觉 OCR
            try:
                imgs = render_pdf_pages(pdf, range(min(_TOC_PAGES, doc.page_count)))
                ocr_text = vision_ocr(imgs) if imgs else ""
                structured.nodes = ts.build_from_text(ocr_text)
                md_lines.append("> 视觉 OCR 完成。")
            except VisionNotEnabled as e:
                # 回退文本层（扫描件通常抽不到，node 可能为空，交由闸门1人工补充）
                structured.nodes = ts.build_from_text(_text_pages(doc, _TOC_PAGES))
                structured.pdf_kind = "image(fallback_text)"
                md_lines.append(f"> 视觉 OCR 未启用（{e}），已回退文本层，建议人工补充目录。")
        else:
            structured.nodes = ts.build_from_text(_text_pages(doc, _TOC_PAGES))
            md_lines.append("> 来源：目录页文本层。")
    finally:
        doc.close()

    for n in structured.nodes:
        indent = "  " * (max(1, n.level) - 1)
        page = f"（p{n.page}）" if n.page else ""
        md_lines.append(f"{indent}- {n.title}{page}")
    md_lines.append("")
    return structured, md_lines


def scan_textbook_toc(ctx, pdf_path: Path | None = None) -> Path:
    """扫描教材目录，产出 md（返回值）+ 每本教材的 toc_structured.json。"""
    out_dir = _structured_dir(ctx)
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
        import fitz  # noqa: F401  仅用于探测依赖是否就绪
    except Exception as e:  # noqa: BLE001
        lines += [f"> 本地扫描依赖未就绪：{e}", ""]
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return out_path

    for pdf in pdfs:
        structured, md_lines = _build_structured_for_pdf(Path(pdf), ctx)
        lines += md_lines
        # 每本教材单独落一个结构化 json（供阶段 C/D 消费、闸门1 编辑）
        sub = out_dir / Path(pdf).stem
        ts.save_structured(sub / ts.STRUCTURED_FILENAME, structured)

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def load_structured_tocs(ctx) -> list[ts.StructuredToc]:
    """读取本项目已产出的全部 toc_structured.json（供规划生成消费）。"""
    out_dir = _structured_dir(ctx)
    if not out_dir.exists():
        return []
    result: list[ts.StructuredToc] = []
    for jf in sorted(out_dir.rglob(ts.STRUCTURED_FILENAME)):
        st = ts.load_structured(jf)
        if st and st.nodes:
            result.append(st)
    return result
