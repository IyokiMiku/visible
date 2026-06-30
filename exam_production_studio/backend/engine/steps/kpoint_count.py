"""知识点数量文档步骤（阶段五 steps/kpoint_count）。

- 考纲/双析：学科网题量统计（无凭据时基于规划生成占位统计）。
- 一课一练：教材目录本地 OCR 扫描。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from engine import repo
from shared.ocr import scan_textbook_toc


def kpoint_count(ctx, rows: list[dict[str, Any]] | None = None) -> Path:
    if ctx.paper_type == "yikeyilian":
        return scan_textbook_toc(ctx)

    rows = rows or repo.get_papers(ctx.project_id)
    out_dir = ctx.dir("知识点数量")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ctx.course or '课程'}_知识点题目数量.md"
    lines = [f"# {ctx.course or '课程'} 知识点题目数量统计", "",
             "> 学科网题量统计（未配置凭据时为基于规划的占位统计）。", "",
             "| 序号 | 知识点 | 主题 | 预估题量 |", "|---|---|---|---|"]
    for r in rows:
        point = r.get("point_name") or r.get("topic") or ""
        topic = r.get("topic") or ""
        lines.append(f"| {r.get('paper_no')} | {point} | {topic} | 待统计 |")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
