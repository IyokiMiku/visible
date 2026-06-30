"""细目表步骤（阶段五 steps/mesh，仅考纲百套卷）。

依据规划生成 专题训练卷_*.docx / 课程综合卷_*.docx 的细目表占位。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document

from engine import repo


def gen_mesh(ctx, rows: list[dict[str, Any]] | None = None) -> list[Path]:
    rows = rows or repo.get_papers(ctx.project_id)
    out_dir = ctx.dir("生产规划") / "细目表"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for kind in ("专题训练卷", "课程综合卷"):
        doc = Document()
        doc.add_paragraph(f"{ctx.course} {kind} 细目表").runs[0].bold = True
        table = doc.add_table(rows=1, cols=4)
        hdr = table.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text = "序号", "知识点", "题型", "题量"
        for r in rows:
            cells = table.add_row().cells
            cells[0].text = str(r.get("paper_no", ""))
            cells[1].text = str(r.get("point_name") or r.get("topic") or "")
            cells[2].text = "综合"
            cells[3].text = "待定"
        p = out_dir / f"{kind}_{ctx.course or '课程'}.docx"
        doc.save(str(p))
        paths.append(p)
    return paths
