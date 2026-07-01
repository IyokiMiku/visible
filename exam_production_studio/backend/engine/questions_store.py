"""题目 / 质检结果持久化（路线B · C 阶段）。

每卷落两份 JSON 到 04_生成输出/_题目数据/：
  - 第N卷.json        题目数据（Question 全字段，含图片 local_path）+ 审阅状态
  - 第N卷_质检.json    结构化质检结果（评分 + QCIssue 列表）

供内容审阅界面读取/回写。装配时以 第N卷.json 为准（读人工改后的题目）。
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from engine.drivers.base import PaperQuestions, QCIssue, QCResult, Question

_SUBDIR = "_题目数据"


def _dir(ctx) -> Path:
    d = ctx.dir(_SUBDIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def questions_path(ctx, paper_no: int) -> Path:
    return _dir(ctx) / f"第{paper_no}卷.json"


def qc_path(ctx, paper_no: int) -> Path:
    return _dir(ctx) / f"第{paper_no}卷_质检.json"


# ---------- 题目 ----------
def save_questions(ctx, pq: PaperQuestions, *, review: dict[str, Any] | None = None) -> Path:
    """写题目 JSON。review 为审阅状态（status/confirmed_nos 等），缺省时保留已有值。"""
    path = questions_path(ctx, pq.paper_no)
    existing_review: dict[str, Any] = {}
    if review is None and path.exists():
        try:
            existing_review = (json.loads(path.read_text(encoding="utf-8")) or {}).get("review", {})
        except (ValueError, OSError):
            existing_review = {}
    data = {
        "paper_no": pq.paper_no,
        "meta": pq.meta,
        "questions": [asdict(q) for q in pq.questions],
        "review": review if review is not None else existing_review,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_questions(ctx, paper_no: int) -> PaperQuestions | None:
    path = questions_path(ctx, paper_no)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    questions = [Question(**q) for q in data.get("questions", [])]
    return PaperQuestions(paper_no=data.get("paper_no", paper_no),
                          questions=questions, meta=data.get("meta", {}))


def load_review(ctx, paper_no: int) -> dict[str, Any]:
    path = questions_path(ctx, paper_no)
    if not path.exists():
        return {}
    try:
        return (json.loads(path.read_text(encoding="utf-8")) or {}).get("review", {})
    except (ValueError, OSError):
        return {}


def update_review(ctx, paper_no: int, review: dict[str, Any]) -> None:
    """只更新审阅状态，题目内容保持不变。"""
    pq = load_questions(ctx, paper_no)
    if pq is None:
        return
    save_questions(ctx, pq, review=review)


# ---------- 质检 ----------
def save_qc(ctx, qc: QCResult) -> Path:
    path = qc_path(ctx, qc.paper_no)
    data = {
        "paper_no": qc.paper_no,
        "score": qc.score,
        "passed": qc.passed,
        "completeness": qc.completeness,
        "coverage": qc.coverage,
        "format_ok": qc.format_ok,
        "ai_risk": qc.ai_risk,
        "issues": [asdict(i) for i in qc.structured],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_qc(ctx, paper_no: int) -> dict[str, Any] | None:
    path = qc_path(ctx, paper_no)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def load_qc_issues(ctx, paper_no: int) -> list[QCIssue]:
    data = load_qc(ctx, paper_no)
    if not data:
        return []
    return [QCIssue(**i) for i in data.get("issues", [])]
