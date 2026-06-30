"""映射表生成（阶段四 shared/ai，源 generate_mapping 去硬编码）。

考点/教材主题 → kpointId。产出 生产规划/{课程}_映射表.xlsx。
有学科网凭据时尝试用 kpoint_resolver 解析 kpointId；否则留空并标低信度。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook

_HEADERS = ["序号", "主题/考点", "知识点", "kpointId", "置信度", "来源"]


def generate_mapping(ctx, plan_rows: list[dict[str, Any]] | None = None) -> Path:
    out_dir = ctx.dir("生产规划")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ctx.course or '课程'}_映射表.xlsx"

    rows = plan_rows or []
    # 尝试解析 kpointId（有凭据时）
    resolver = None
    try:
        from shared.xueke_api import kpoint_resolver as _kr  # noqa
        resolver = _kr
    except Exception:
        resolver = None

    wb = Workbook()
    ws = wb.active
    ws.title = "映射表"
    ws.append(_HEADERS)

    if not rows:
        rows = [{"topic": ctx.course or "示例主题", "point_name": ""}]

    for i, r in enumerate(rows, 1):
        topic = r.get("topic") or r.get("paper_name") or r.get("point_name") or ""
        point = r.get("point_name") or topic
        kpoint_id = r.get("kpoint_id") or ""
        conf = r.get("confidence")
        if conf is None:
            conf = 1.0 if kpoint_id else 0.0
        source = "resolver" if kpoint_id else "unresolved"
        if not kpoint_id and resolver is not None and hasattr(resolver, "resolve"):
            try:
                kpoint_id, conf = resolver.resolve(ctx, point)  # type: ignore
            except Exception:
                pass
        ws.append([i, topic, point, kpoint_id, conf, source])

    wb.save(str(out_path))
    return out_path
