"""待确认队列（阶段七，设计文档 §5.3）。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from engine import repo, review
from ._common import fail, ok

router = APIRouter(prefix="/api/projects", tags=["review"])


class ConfirmIn(BaseModel):
    decision: dict[str, Any] | None = None


@router.get("/{project_id}/reviews")
def list_reviews(project_id: str, status: str = "pending"):
    items = review.pending(project_id) if status == "pending" else repo.all_reviews(project_id)
    return ok(items)


@router.post("/{project_id}/reviews/{review_id}/confirm")
def confirm_review(project_id: str, review_id: str, body: ConfirmIn | None = None):
    item = review.confirm(review_id, body.decision if body else None)
    if not item:
        return fail("待确认项不存在", status=404)
    return ok(item)


@router.post("/{project_id}/reviews/{review_id}/return")
def return_review(project_id: str, review_id: str):
    item = review.return_item(review_id)
    if not item:
        return fail("待确认项不存在", status=404)
    return ok(item)
