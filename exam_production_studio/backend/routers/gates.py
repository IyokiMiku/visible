"""闸门读写接口（F2）：闸门1 结构化目录、闸门2 规划表行的读取/保存。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from engine import gates
from ._common import fail, load_ctx, ok

router = APIRouter(prefix="/api/projects", tags=["gates"])


@router.get("/{project_id}/gate/toc")
def gate_get_toc(project_id: str):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    return ok({"tocs": gates.get_toc(ctx)})


@router.post("/{project_id}/gate/toc")
def gate_save_toc(project_id: str, payload: dict[str, Any] = Body(...)):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    textbook = payload.get("textbook", "")
    return ok({"path": gates.save_toc(ctx, textbook, payload)})


@router.get("/{project_id}/gate/planning")
def gate_get_planning(project_id: str):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    return ok(gates.get_planning(ctx))


@router.post("/{project_id}/gate/planning")
def gate_save_planning(project_id: str, payload: dict[str, Any] = Body(...)):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    rows = payload.get("rows") or []
    force = bool(payload.get("force"))
    result = gates.save_planning(ctx, rows, force=force)
    return ok(result)
