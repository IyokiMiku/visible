"""质量摘要 / 质检报告（阶段七，设计文档 §5.4）。"""
from __future__ import annotations

from fastapi import APIRouter

from engine import repo
from ._common import fail, load_ctx, ok

router = APIRouter(prefix="/api/projects", tags=["qc"])


@router.get("/{project_id}/quality")
def quality(project_id: str):
    rows = repo.get_quality(project_id)
    if not rows:
        return ok({"papers": [], "summary": {}})
    n = len(rows)
    summary = {
        "avg_score": round(sum(r["score"] for r in rows) / n, 1),
        "adopted": sum(r["adopted"] for r in rows),
        "ai_filled": sum(r["ai_filled"] for r in rows),
        "manual_confirmed": sum(r["manual_confirmed"] for r in rows),
        "coverage": round(sum(r["coverage"] for r in rows) / n, 3),
        "completeness": round(sum(r["completeness"] for r in rows) / n, 3),
        "papers": n,
    }
    return ok({"papers": rows, "summary": summary})


@router.get("/{project_id}/qc/reports")
def qc_reports(project_id: str):
    papers = repo.get_papers(project_id)
    pending = [p for p in papers if p["status"] == "pending_review"]
    return ok([{"paper_no": p["paper_no"], "status": p["status"],
                "report": p["qc_report_path"]} for p in pending])


@router.get("/{project_id}/qc/reports/{paper_no}")
def qc_report(project_id: str, paper_no: int):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    path = ctx.dir("质检报告") / f"第{paper_no}卷_质检报告.md"
    if not path.exists():
        return fail("报告不存在", status=404)
    return ok({"paper_no": paper_no, "markdown": path.read_text(encoding="utf-8")})
