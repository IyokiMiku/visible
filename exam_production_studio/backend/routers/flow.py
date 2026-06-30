"""流程执行（阶段七，设计文档 §5.2）。"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from engine import registry, repo, runner
from ._common import fail, ok

router = APIRouter(prefix="/api/projects", tags=["flow"])


class RerunIn(BaseModel):
    node: str
    paper_no: int | None = None


@router.get("/{project_id}/flow")
def get_flow(project_id: str):
    row = repo.get_project(project_id)
    if not row:
        return fail("项目不存在", status=404)
    mode = registry.get(row["paper_type"])
    from engine.drivers import get_driver
    from engine.context import ProjectContext
    driver = get_driver(ProjectContext.from_row(row))
    run = repo.latest_run(project_id)
    papers = repo.get_papers(project_id)
    return ok({
        "flow_nodes": driver.flow_nodes,
        "status": row["status"],
        "current_node": run["current_node"] if run else "",
        "progress": run["progress"] if run else 0,
        "papers": [{"paper_no": p["paper_no"], "status": p["status"]} for p in papers],
        "pending_reviews": len(repo.pending_reviews(project_id)),
    })


@router.post("/{project_id}/flow/start")
def start_flow(project_id: str):
    if not repo.get_project(project_id):
        return fail("项目不存在", status=404)
    rid = runner.start(project_id)
    return ok({"run_id": rid})


@router.post("/{project_id}/flow/pause")
def pause_flow(project_id: str):
    runner.pause(project_id)
    return ok({"paused": True})


@router.post("/{project_id}/flow/resume")
def resume_flow(project_id: str):
    rid = runner.resume(project_id)
    return ok({"run_id": rid})


@router.post("/{project_id}/flow/rerun")
def rerun_flow(project_id: str, body: RerunIn):
    rid = runner.rerun(project_id, body.node, body.paper_no)
    return ok({"run_id": rid})


@router.get("/{project_id}/flow/logs")
def flow_logs(project_id: str, limit: int = 500):
    return ok(repo.get_logs(project_id, limit))
