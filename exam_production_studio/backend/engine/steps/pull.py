"""拉题 + AI 补题步骤（阶段五 steps/pull，设计文档 §3.3/§6.4）。

学科网拉题为主，不足 AI 补题；仍不足/低信度 → 待确认(AI_GENERATE)。
双析卷 needed = plan × 2（由 ctx.pull_multiplier 决定）。
"""
from __future__ import annotations

from typing import Any, Callable

from engine import registry, repo
from engine.drivers.base import PaperQuestions, Question
from shared.ai import ai_fill as default_fill
from shared.xueke_api import pull_for_plan


def build_paper_plan(ctx, paper_no: int) -> dict[str, Any]:
    paper = repo.get_paper(ctx.project_id, paper_no) or {}
    mode = registry.get(ctx.paper_type)
    vc = ctx.volume_config or mode.default_volume_config
    by_type = {t: int(c.get("count", 0)) for t, c in (vc.get("by_type") or {}).items()}
    return {
        "paper_no": paper_no,
        "topic": paper.get("topic") or ctx.course,
        "point_name": paper.get("point_name") or paper.get("topic") or "",
        "kpoint_id": paper.get("kpoint_id", ""),
        "difficulty": vc.get("difficulty", {"easy": 80, "medium": 10, "hard": 10}),
        "by_type": by_type,
    }


def produce_questions(
    ctx, paper_no: int, fill_impl: Callable | None = None
) -> tuple[PaperQuestions, list[dict[str, Any]]]:
    fill_impl = fill_impl or default_fill
    plan = build_paper_plan(ctx, paper_no)
    multiplier = ctx.pull_multiplier()
    needed = {t: c * multiplier for t, c in plan["by_type"].items() if c > 0}
    if not needed:  # 兜底：至少出一题
        needed = {"单项选择题": 5 * multiplier}

    reviews: list[dict[str, Any]] = []

    pulled = pull_for_plan(ctx, plan, needed)
    pulled_qs: list[Question] = list(pulled.questions) if pulled.ok else []
    have_by_type: dict[str, int] = {}
    for q in pulled_qs:
        have_by_type[q.qtype] = have_by_type.get(q.qtype, 0) + 1

    shortfall = {t: max(0, n - have_by_type.get(t, 0)) for t, n in needed.items()}
    filled: list[Question] = []
    if any(v > 0 for v in shortfall.values()):
        filled = fill_impl(ctx, plan, shortfall, start_number=len(pulled_qs) + 1)

    questions = pulled_qs + filled
    # 重新编号
    for i, q in enumerate(questions, 1):
        q.number = i

    # 待确认判定：仍不足，或存在低信度 AI 占位题
    final_by_type: dict[str, int] = {}
    for q in questions:
        final_by_type[q.qtype] = final_by_type.get(q.qtype, 0) + 1
    still_short = {t: n - final_by_type.get(t, 0) for t, n in needed.items() if n - final_by_type.get(t, 0) > 0}
    low_conf = [q.number for q in questions if q.source == "ai" and q.confidence < ctx.confidence_threshold()]

    if not pulled.ok and pulled.note:
        # 学科网未命中（含无凭据），且走了 AI 补题
        if low_conf or still_short:
            reviews.append({
                "type": "AI_GENERATE", "paper_no": paper_no, "confidence": 0.0,
                "payload": {"reason": pulled.note, "ai_questions": low_conf,
                            "still_short": still_short},
            })
    elif low_conf or still_short:
        reviews.append({
            "type": "AI_GENERATE", "paper_no": paper_no,
            "confidence": min([0.0] + [q.confidence for q in questions if q.number in low_conf]),
            "payload": {"ai_questions": low_conf, "still_short": still_short},
        })

    pq = PaperQuestions(paper_no=paper_no, questions=questions,
                        meta={"topic": plan["topic"], "needed": needed,
                              "pulled_note": pulled.note})
    return pq, reviews
