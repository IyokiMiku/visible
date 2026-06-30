"""逐卷质检步骤（阶段五 steps/qc）。

跑质检规则 + 写报告 + 落库 quality_summary；不通过返回需人工审核标记。
"""
from __future__ import annotations

from typing import Any

from engine import repo
from engine.drivers.base import PaperQuestions, QCResult
from shared.qc import run_quality_checks, write_report, append_error_report


def qc(ctx, paper_no: int, qs: PaperQuestions) -> tuple[QCResult, list[dict[str, Any]]]:
    result = run_quality_checks(ctx, qs)
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
