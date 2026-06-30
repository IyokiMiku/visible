"""路由公共：统一响应与上下文构造。"""
from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

from engine import repo
from engine.context import ProjectContext


def ok(data: Any = None, message: str = "ok") -> dict[str, Any]:
    return {"code": 0, "message": message, "data": data}


def fail(message: str, code: int = 1, status: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message, "data": None})


def load_ctx(project_id: str) -> ProjectContext:
    row = repo.get_project(project_id)
    if not row:
        raise KeyError(project_id)
    return ProjectContext.from_row(row)
