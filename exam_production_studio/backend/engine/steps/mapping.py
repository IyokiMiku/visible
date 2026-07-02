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


def _dedup_ids(ids: list[Any]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _gen_mapping_kaogang(ctx, rows: list[dict[str, Any]]) -> tuple[Path, list[dict[str, Any]]]:
    """考纲百套卷映射表（D4）：考点卷分层匹配 + 专题/综合卷聚合。

    逐卷解析 kpointId 并落库 papers（kpoint_id 单值 + meta.kpoint_ids 列表），供拉题按卷取题源；
    聚合卷（专题/综合）由 meta.agg_texts 独立解析并集去重，不依赖底层考点卷是否在选区内。
    """
    from shared.planning.kaogang_mapping import render_mapping
    from shared.xueke_api.kpoint_resolver import resolve_layered

    map_rows: list[dict[str, Any]] = []
    low_conf: list[dict[str, Any]] = []
    for r in rows:
        meta = r.get("meta") or {}
        pno = r.get("paper_no")
        course = meta.get("course") or r.get("module") or ctx.course or ""
        if meta.get("is_aggregate"):
            all_ids: list[Any] = []
            for t in meta.get("agg_texts") or []:
                text = t.get("knowledge") or t.get("point_name") or ""
                ids, _m = resolve_layered(text, t.get("course") or course)
                all_ids.extend(ids)
            ids = _dedup_ids(all_ids)
            method = "聚合"
            src = "专题" if meta.get("agg_kind") == "theme" else "课程"
            remark = f"聚合自{src}「{meta.get('theme') or course}」考点卷" + ("" if ids else "（无匹配）")
        else:
            text = meta.get("knowledge") or r.get("point_name") or meta.get("point_name") or r.get("topic") or ""
            ids, method = resolve_layered(text, course)
            remark = "" if ids else "知识树无匹配节点"
        repo.update_paper(ctx.project_id, pno,
                          kpoint_id=(str(ids[0]) if ids else ""),
                          kpoint_ids=[str(i) for i in ids])
        map_rows.append({"vol": f"第{pno}卷", "ids": ids, "method": method,
                         "remark": remark, "_sort": pno or 0})
        if method == "AI生成":
            low_conf.append({"paper_no": pno, "point_name": remark, "confidence": 0.0})

    map_rows.sort(key=lambda x: x["_sort"])
    out_dir = ctx.dir("生产规划")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ctx.province}_{ctx.exam_category}_映射表.xlsx"
    render_mapping(map_rows, out_path)
    from engine import archive
    archive.export_planning_artifact(ctx, out_path)
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
