"""人工确认队列（阶段五 engine/review，设计文档 §3.5）。

类型：AI_MATCH / AI_GENERATE / RULE_CONFLICT / QC_FAIL。
低于信度阈值或质检不过 → 生成 review_items(pending) 并使流程暂停。
"""
from __future__ import annotations

from typing import Any

from engine import repo

VALID_TYPES = {"AI_MATCH", "AI_GENERATE", "RULE_CONFLICT", "QC_FAIL", "CONTENT_REVIEW"}


def enqueue(ctx, run_id: str, node: str, rtype: str, paper_no: int | None,
            confidence: float, payload: dict[str, Any]) -> str:
    if rtype not in VALID_TYPES:
        raise ValueError(f"未知待确认类型: {rtype}")
    return repo.enqueue_review(ctx.project_id, run_id, node, rtype, paper_no, confidence, payload)


def pending(project_id: str) -> list[dict[str, Any]]:
    return repo.pending_reviews(project_id)


def has_pending(project_id: str) -> bool:
    return len(repo.pending_reviews(project_id)) > 0


def confirm(review_id: str, decision: dict[str, Any] | None = None) -> dict[str, Any] | None:
    item = repo.get_review(review_id)
    if not item:
        return None
    repo.set_review_status(review_id, "confirmed")
    return repo.get_review(review_id)


def return_item(review_id: str) -> dict[str, Any] | None:
    item = repo.get_review(review_id)
    if not item:
        return None
    repo.set_review_status(review_id, "returned")
    return repo.get_review(review_id)
