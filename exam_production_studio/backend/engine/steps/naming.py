"""确认命名步骤（阶段五 steps/naming）。

写入 exam_type_name（项目表），供命名/标题使用。
"""
from __future__ import annotations

from typing import Any

from engine import repo


def confirm_naming(ctx, exam_info: dict[str, Any] | None = None) -> None:
    exam_info = exam_info or {}
    name = exam_info.get("exam_type_name") or ctx.exam_type_name or "高职分类考试"
    ctx.exam_type_name = name
    repo.update_project_field(ctx.project_id, "exam_type_name", name)
