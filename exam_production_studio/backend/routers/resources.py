"""资源上传/状态（阶段七，设计文档 §5.1）。"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

import db
from engine import repo
from ._common import fail, ok

router = APIRouter(prefix="/api/projects", tags=["resources"])

# 各资源类型允许的文件扩展名白名单（后端强校验，前端拦截可被绕过）。
_DOC_EXTS = {".pdf", ".doc", ".docx"}
ALLOWED_EXTS: dict[str, set[str]] = {
    "考纲": _DOC_EXTS,
    "教材": _DOC_EXTS,
    "真题": _DOC_EXTS,
    "模板": {".doc", ".docx"},
    "规划表": {".xlsx", ".xls"},
}
# 类型未知时的兜底：允许常见文档格式。
_DEFAULT_EXTS = _DOC_EXTS | {".xlsx", ".xls"}


def _allowed_exts(kind: str) -> set[str]:
    return ALLOWED_EXTS.get(kind, _DEFAULT_EXTS)


@router.post("/{project_id}/resources")
async def upload_resource(project_id: str, kind: str = Form("其他"), file: UploadFile = File(...)):
    row = repo.get_project(project_id)
    if not row:
        return fail("项目不存在", status=404)
    ext = Path(file.filename or "").suffix.lower()
    allowed = _allowed_exts(kind)
    if ext not in allowed:
        return fail(f"「{kind}」不支持该文件类型（{ext or '未知'}），仅允许：{'、'.join(sorted(allowed))}")
    from engine.context import ProjectContext
    ctx = ProjectContext.from_row(row)
    sub = {"考纲": "考纲", "教材": "教材", "真题": "真题", "模板": "模板", "规划表": "规划表"}.get(kind, "其他")
    dest_dir = ctx.input_dir(sub)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / file.filename
    dest.write_bytes(await file.read())
    # 同类型同文件名视为覆盖（更新已有记录），否则新增（支持一个类型多份文件）。
    existing = db.query_one(
        "SELECT id FROM resources WHERE project_id=? AND kind=? AND filename=?",
        (project_id, kind, file.filename))
    if existing:
        rid = existing["id"]
        db.execute("UPDATE resources SET path=?, status=? WHERE id=?", (str(dest), "imported", rid))
    else:
        rid = repo.new_id("res_")
        db.execute(
            "INSERT INTO resources (id, project_id, kind, filename, path, status) VALUES (?,?,?,?,?,?)",
            (rid, project_id, kind, file.filename, str(dest), "imported"))
    return ok({"id": rid, "kind": kind, "filename": file.filename, "status": "imported"})


@router.get("/{project_id}/resources")
def list_resources(project_id: str):
    return ok(db.query("SELECT * FROM resources WHERE project_id=?", (project_id,)))


@router.delete("/{project_id}/resources/{resource_id}")
def delete_resource(project_id: str, resource_id: str):
    row = db.query_one(
        "SELECT * FROM resources WHERE id=? AND project_id=?", (resource_id, project_id))
    if not row:
        return fail("资源不存在", status=404)
    path = row.get("path")
    if path:
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass
    db.execute("DELETE FROM resources WHERE id=?", (resource_id,))
    return ok({"deleted": resource_id})
