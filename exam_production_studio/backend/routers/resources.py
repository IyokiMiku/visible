"""资源上传/状态（阶段七，设计文档 §5.1）。"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

import db
from engine import repo
from ._common import fail, ok

router = APIRouter(prefix="/api/projects", tags=["resources"])


@router.post("/{project_id}/resources")
async def upload_resource(project_id: str, kind: str = Form("其他"), file: UploadFile = File(...)):
    row = repo.get_project(project_id)
    if not row:
        return fail("项目不存在", status=404)
    from engine.context import ProjectContext
    ctx = ProjectContext.from_row(row)
    sub = {"考纲": "考纲", "教材": "教材", "真题": "真题", "模板": "模板", "规划表": "规划表"}.get(kind, "其他")
    dest_dir = ctx.input_dir(sub)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / file.filename
    dest.write_bytes(await file.read())
    rid = repo.new_id("res_")
    db.execute(
        "INSERT INTO resources (id, project_id, kind, filename, path, status) VALUES (?,?,?,?,?,?)",
        (rid, project_id, kind, file.filename, str(dest), "imported"))
    return ok({"id": rid, "kind": kind, "filename": file.filename, "status": "imported"})


@router.get("/{project_id}/resources")
def list_resources(project_id: str):
    return ok(db.query("SELECT * FROM resources WHERE project_id=?", (project_id,)))
