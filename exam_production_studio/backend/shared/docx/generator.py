"""组卷底层（阶段四 shared/docx，源 docx_utils1/docx_generation 去硬编码）。

按 ctx + 类型模板生成 docx：三行标题、选项表、答案/解析红字。
variant='解析版' 含答案解析；'原卷版' 不含。
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

from engine.drivers.base import PaperQuestions
from . import naming

RED = RGBColor(0xFF, 0x00, 0x00)


def _set_margins(doc: Document) -> None:
    for section in doc.sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.18)
        section.right_margin = Cm(3.18)


def _add_title(doc: Document, lines: list[str]) -> None:
    for ln in lines:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(ln)
        run.bold = True
        run.font.size = Pt(14)


def _add_type_header(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(12)


_CN_NUM = "一二三四五六七八九十"


def generate_docx(
    ctx,
    qs: PaperQuestions,
    *,
    variant: str = "解析版",
    paper_name: str = "",
    paper_subtype: str = "考点训练卷",
    suffix: str = "",
    topic: str = "",
    out_dir: Path | None = None,
) -> Path:
    """生成单份 docx，返回路径。"""
    out_dir = out_dir or ctx.dir("生成结果")
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = naming.build_filename(
        ctx, qs.paper_no, paper_name=paper_name, variant=variant,
        paper_subtype=paper_subtype, suffix=suffix, topic=topic,
    )
    out_path = out_dir / f"{fname}.docx"

    doc = Document()
    _set_margins(doc)
    _add_title(doc, naming.build_title_lines(
        ctx, qs.paper_no, paper_name=paper_name, paper_subtype=paper_subtype,
        suffix=suffix, topic=topic,
    ))
    doc.add_paragraph()

    # 按题型分组保持顺序
    grouped: dict[str, list] = {}
    order: list[str] = []
    for q in qs.questions:
        if q.qtype not in grouped:
            grouped[q.qtype] = []
            order.append(q.qtype)
        grouped[q.qtype].append(q)

    show_answer = variant == "解析版"
    seq = 1
    for ti, qtype in enumerate(order):
        cn = _CN_NUM[ti] if ti < len(_CN_NUM) else str(ti + 1)
        _add_type_header(doc, f"{cn}、{qtype}")
        for q in grouped[qtype]:
            doc.add_paragraph(f"{seq}. {q.stem}")
            if q.options:
                for oi, opt in enumerate(q.options):
                    letter = chr(ord("A") + oi)
                    doc.add_paragraph(f"{letter}. {opt}")
            if show_answer:
                pa = doc.add_paragraph()
                ra = pa.add_run(f"【答案】{q.answer}")
                ra.font.color.rgb = RED
                px = doc.add_paragraph()
                rx = px.add_run(f"【解析】{q.analysis}")
                rx.font.color.rgb = RED
            seq += 1

    doc.save(str(out_path))
    return out_path
