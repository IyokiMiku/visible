"""项目 CRUD + 产品名预览（阶段七，设计文档 §5.1）。"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

import db
from engine import registry, repo
from engine.context import ProjectContext
from shared.docx import build_filename
from ._common import fail, ok

router = APIRouter(prefix="/api/projects", tags=["projects"])

_JSON_FIELDS = {"volume_config", "output_versions", "ai_options"}


class ProjectIn(BaseModel):
    name: str = ""
    paper_type: str
    province: str = ""
    exam_category: str = ""
    course: str = ""
    textbook: str = ""
    edition: str = ""
    exam_type_name: str = "高职分类考试"
    paper_range: str = "all"
    plan_source: str = "ocr"
    volume_config: dict[str, Any] | None = None
    output_versions: list[str] | None = None
    ai_options: dict[str, Any] | None = None


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for f in _JSON_FIELDS:
        if isinstance(out.get(f), str) and out[f]:
            try:
                out[f] = json.loads(out[f])
            except ValueError:
                pass
    return out


@router.get("")
def list_projects():
    return ok([_serialize(r) for r in db.query("SELECT * FROM projects ORDER BY created_at DESC")])


@router.post("")
def create_project(body: ProjectIn):
    try:
        mode = registry.get(body.paper_type)
    except KeyError:
        return fail(f"未知试卷类型: {body.paper_type}")
    pid = repo.new_id("prj_")
    vc = body.volume_config or mode.default_volume_config
    ov = body.output_versions or ["原卷版", "解析版"]
    ai = body.ai_options or {"match": True, "summary": True, "fill": True,
                             "match_threshold": 0.85, "max_fix_rounds": 2}
    name = body.name or f"{mode.display_name}_{body.province}_{body.course}".strip("_")
    db.execute(
        "INSERT INTO projects (id,name,paper_type,province,exam_category,course,textbook,edition,"
        "exam_type_name,name_template,volume_config,paper_range,plan_source,output_versions,ai_options,status,created_at,updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (pid, name, body.paper_type, body.province, body.exam_category, body.course, body.textbook,
         body.edition, body.exam_type_name, mode.name_template,
         json.dumps(vc, ensure_ascii=False), body.paper_range, body.plan_source,
         json.dumps(ov, ensure_ascii=False), json.dumps(ai, ensure_ascii=False),
         "ready", repo.now(), repo.now()))
    return ok(_serialize(repo.get_project(pid)))


@router.get("/{project_id}")
def get_project(project_id: str):
    row = repo.get_project(project_id)
    if not row:
        return fail("项目不存在", status=404)
    return ok(_serialize(row))


@router.put("/{project_id}")
def update_project(project_id: str, body: ProjectIn):
    if not repo.get_project(project_id):
        return fail("项目不存在", status=404)
    fields = body.model_dump()
    for f in _JSON_FIELDS:
        if fields.get(f) is not None:
            fields[f] = json.dumps(fields[f], ensure_ascii=False)
        else:
            fields.pop(f, None)
    sets = ",".join(f"{k}=?" for k in fields)
    db.execute(f"UPDATE projects SET {sets}, updated_at=? WHERE id=?",
               list(fields.values()) + [repo.now(), project_id])
    return ok(_serialize(repo.get_project(project_id)))


@router.delete("/{project_id}")
def delete_project(project_id: str):
    db.execute("DELETE FROM projects WHERE id=?", (project_id,))
    for t in ("papers", "runs", "flow_logs", "review_items", "quality_summary"):
        db.execute(f"DELETE FROM {t} WHERE project_id=?", (project_id,))
    return ok({"deleted": project_id})


@router.get("/{project_id}/name-preview")
def name_preview(project_id: str):
    row = repo.get_project(project_id)
    if not row:
        return fail("项目不存在", status=404)
    ctx = ProjectContext.from_row(row)
    sample = build_filename(ctx, 1, paper_name=ctx.course or "示例主题", variant="解析版",
                            suffix="教师讲解卷" if ctx.paper_type == "shuangxi" else "",
                            topic=ctx.course or "示例主题")
    total = None
    try:
        total = len(ctx.selected_papers()) or None
    except ValueError:
        pass
    return ok({"preview": sample, "paper_count": total})
