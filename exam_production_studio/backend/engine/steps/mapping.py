"""映射表步骤（阶段五 steps/mapping）。

考点/教材主题 → kpointId（kpoint_resolver 本地树匹配 + AI 兜底），落库到 papers.kpoint_id，
写映射表 xlsx；低于信度阈值（默认 0.85）的卷进入待确认(AI_MATCH)。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from engine import repo
from shared.ai import generate_mapping
from shared.xueke_api import kpoint_resolver


def gen_mapping(ctx, rows: list[dict[str, Any]] | None = None) -> tuple[Path, list[dict[str, Any]]]:
    rows = rows or repo.get_papers(ctx.project_id)
    threshold = ctx.confidence_threshold()
    plan_rows: list[dict[str, Any]] = []
    low_conf: list[dict[str, Any]] = []

    for r in rows:
        pno = r.get("paper_no")
        point = r.get("point_name") or r.get("topic") or ""
        kid = r.get("kpoint_id") or ""
        conf = 1.0 if kid else 0.0
        if not kid:
            kid, conf = kpoint_resolver.resolve(ctx, point)
        if kid:
            repo.update_paper(ctx.project_id, pno, kpoint_id=kid)
        plan_rows.append({"topic": r.get("topic"), "point_name": point,
                          "kpoint_id": kid, "confidence": round(conf, 2)})
        if not kid or conf < threshold:
            low_conf.append({"paper_no": pno, "point_name": point, "confidence": round(conf, 2)})

    path = generate_mapping(ctx, plan_rows)
    return path, low_conf
