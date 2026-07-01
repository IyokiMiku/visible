"""逐卷质检步骤（阶段五 steps/qc）。

跑质检规则 + 写报告 + 落库 quality_summary；不通过返回需人工审核标记。
"""
from __future__ import annotations

from typing import Any

from engine import repo
from engine.drivers.base import PaperQuestions, QCResult
from shared.qc import run_quality_checks, write_report, append_error_report
from shared.qc.ai_check import ai_theme_check

_SEVERITY_PENALTY = {"严重": 15.0, "警告": 5.0, "信息": 0.0}
_PASS_SCORE = 90.0


def _merge_ai_issues(ctx, result: QCResult, qs: PaperQuestions) -> None:
    """把 AI 相符性问题并入质检结果并重算评分/结论（best-effort，异常已在内部吞掉）。"""
    topic = qs.meta.get("topic") or getattr(ctx, "course", "")
    ai_issues = ai_theme_check(qs, topic, course=getattr(ctx, "course", ""))
    if not ai_issues:
        return
    result.structured = list(result.structured) + ai_issues
    result.issues = [i.to_text() for i in result.structured]
    penalty = min(100.0, sum(_SEVERITY_PENALTY.get(i.severity, 0.0) for i in result.structured))
    result.score = max(0.0, 100.0 - penalty)
    has_placeholder = any(i.code == "ai_placeholder" for i in result.structured)
    result.passed = result.score >= _PASS_SCORE and not has_placeholder


def qc(ctx, paper_no: int, qs: PaperQuestions) -> tuple[QCResult, list[dict[str, Any]]]:
    result = run_quality_checks(ctx, qs)
    _merge_ai_issues(ctx, result, qs)
    report_path = write_report(ctx, result)
    result.report_path = report_path
    if not result.passed:
        append_error_report(ctx, paper_no, result.issues)

    repo.save_quality(ctx.project_id, paper_no, {
        "score": result.score,
        "adopted": qs.adopted,
        "ai_filled": qs.ai_filled,
        "manual_confirmed": 0,
        "format_ok": result.format_ok,
        "completeness": result.completeness,
        "coverage": result.coverage,
        "ai_risk": result.ai_risk,
        "suggestion": "可交付" if result.passed else "建议人工复核后交付",
    })

    reviews: list[dict[str, Any]] = []
    if not result.passed:
        reviews.append({
            "type": "QC_FAIL", "paper_no": paper_no, "confidence": result.score / 100.0,
            "payload": {"score": result.score, "issues": result.issues,
                        "report": str(report_path)},
        })
    return result, reviews
