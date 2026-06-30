"""奇偶分卷步骤（阶段五 steps/split，仅考点双析卷）。

翻转规则（设计文档 §3.4）：偶数题→教师讲解卷、奇数题→学生练习卷；
教师卷号=seq×2-1、学生卷号=seq×2。每卷出 解析版+原卷版，共 4 份。
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from engine.drivers.base import PaperQuestions
from shared.docx import generate_docx


def split_odd_even(ctx, seq: int, qs: PaperQuestions) -> dict[str, PaperQuestions]:
    even_qs = [deepcopy(q) for q in qs.questions if q.number % 2 == 0]  # 偶 → 教师
    odd_qs = [deepcopy(q) for q in qs.questions if q.number % 2 == 1]   # 奇 → 学生
    for i, q in enumerate(even_qs, 1):
        q.number = i
    for i, q in enumerate(odd_qs, 1):
        q.number = i
    teacher = PaperQuestions(paper_no=seq * 2 - 1, questions=even_qs, meta=dict(qs.meta))
    student = PaperQuestions(paper_no=seq * 2, questions=odd_qs, meta=dict(qs.meta))
    return {"teacher": teacher, "student": student}


def assemble_split(ctx, seq: int, qs: PaperQuestions, *, paper_name: str = "") -> list[Path]:
    parts = split_odd_even(ctx, seq, qs)
    paper_name = paper_name or qs.meta.get("topic") or ctx.course
    paths: list[Path] = []
    for role, suffix in (("teacher", "教师讲解卷"), ("student", "学生练习卷")):
        pq = parts[role]
        for variant in (ctx.output_versions or ["原卷版", "解析版"]):
            p = generate_docx(ctx, pq, variant=variant, paper_name=paper_name,
                              suffix=suffix, topic=paper_name)
            paths.append(p)
    return paths
