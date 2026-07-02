"""学科网基础数据（专业大类 → 专业 → 课程目录），供创建向导级联下拉。

数据来自本地 configs/xueke_mapping/专业课程树.json（全国通用静态目录）；
可用 `python -m shared.xueke_api.refresh_profession_tree` 重新抓取覆盖。
"""
from __future__ import annotations

from fastapi import APIRouter

from shared.xueke_api import kpoint_resolver
from ._common import ok

router = APIRouter(prefix="/api/xueke", tags=["xueke"])


@router.get("/tree")
def get_profession_tree():
    """返回整棵「大类 → 专业 → 课程(courseId)」目录，前端本地做级联。"""
    tree = kpoint_resolver.load_profession_tree()
    return ok({"categories": tree.get("categories") or []})
