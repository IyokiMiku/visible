"""组卷步骤（阶段五 steps/assemble，考纲/一课一练 ×1）。

按 output_versions 生成 解析版/原卷版 docx，写入 生成结果/。
"""
from __future__ import annotations

from pathlib import Path

from engine import repo
from engine.drivers.base import PaperQuestions
from shared.docx import generate_docx


def assemble(ctx, paper_no: int, qs: PaperQuestions, *, suffix: str = "") -> list[Path]:
    paper = repo.get_paper(ctx.project_id, paper_no) or {}
    paper_name = paper.get("topic") or qs.meta.get("topic") or ctx.course
    paper_subtype = paper.get("paper_type") or "考点训练卷"
    paths: list[Path] = []
    for variant in (ctx.output_versions or ["原卷版", "解析版"]):
        p = generate_docx(ctx, qs, variant=variant, paper_name=paper_name,
                          paper_subtype=paper_subtype, suffix=suffix, topic=paper_name)
        paths.append(p)
    return paths
