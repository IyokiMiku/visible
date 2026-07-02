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


def _gen_mapping_kaogang(ctx, rows: list[dict[str, Any]]) -> tuple[Path, list[dict[str, Any]]]:
    """考纲百套卷映射表（D4）：考点卷分层匹配 + 专题/综合卷聚合。"""
    from shared.planning.kaogang_mapping import build_mapping_rows, render_mapping

    kp_rows = []
    for r in rows:
        meta = r.get("meta") or {}
        kp_rows.append({
            "course": meta.get("course") or r.get("module") or ctx.course,
            "theme": meta.get("theme") or "",
            "point_name": meta.get("point_name") or r.get("topic") or "",
            "knowledge": meta.get("knowledge") or r.get("point_name") or "",
            "paper_no": r.get("paper_no"),
            "theme_vol_no": meta.get("theme_vol_no"),
            "course_vol_range": meta.get("course_vol_range"),
        })
    map_rows = build_mapping_rows(kp_rows)
    out_dir = ctx.dir("生产规划")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ctx.province}_{ctx.exam_category}_映射表.xlsx"
    render_mapping(map_rows, out_path)
    from engine import archive
    archive.export_planning_artifact(ctx, out_path)
    # 低信度 = AI生成（未匹配）的考点卷，供人工确认
    low_conf = [{"paper_no": r["_sort"], "point_name": r.get("remark", ""), "confidence": 0.0}
                for r in map_rows if r["method"] == "AI生成"]
    return out_path, low_conf


def gen_mapping(ctx, rows: list[dict[str, Any]] | None = None) -> tuple[Path, list[dict[str, Any]]]:
    rows = rows or repo.get_papers(ctx.project_id)
    # 仅考纲百套卷（10 列总表）走分层聚合映射；双析卷/一课一练逐行匹配（无聚合）
    if ctx.paper_type == "kaogang_100":
        return _gen_mapping_kaogang(ctx, rows)
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
    from engine import archive
    archive.export_planning_artifact(ctx, path)
    return path, low_conf
