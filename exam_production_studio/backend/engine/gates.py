"""两道人工确认闸门的读写后端（F2）。

- 闸门1（读取结果）：读取/保存结构化教材目录 toc_structured.json（可编辑、可增条目）；
- 闸门2（生成结果）：读取/保存规划表行（可编辑、可增条目），保存时重渲染 xlsx 并重落库。

前端（F3）据此做“简略展示 + 行内编辑 + 新增条目 + 确认/回退”。这里只保证后端写回与重渲染。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from engine import repo
from shared.ocr import load_structured_tocs
from shared.ocr import toc_structured as ts
from shared.planning import kaogang as kg
from shared.planning import validate
from shared.planning import yikeyilian as yy


# ---------------- 闸门1：结构化目录 ----------------
def get_toc(ctx) -> list[dict[str, Any]]:
    return [st.to_dict() for st in load_structured_tocs(ctx)]


def save_toc(ctx, textbook: str, payload: dict[str, Any]) -> str:
    """保存编辑后的结构化目录（含新增条目）到对应教材的 toc_structured.json。"""
    structured = ts.structured_from_dict(payload)
    if not structured.textbook:
        structured.textbook = textbook
    out_dir = ctx.dir("教材目录扫描") / (textbook or structured.textbook or "教材")
    path = ts.save_structured(out_dir / ts.STRUCTURED_FILENAME, structured)
    return str(path)


# ---------------- 闸门2：规划表行 ----------------
def get_planning(ctx) -> dict[str, Any]:
    """返回规划表行的简略视图（供闸门2 编辑）。

    考纲百套卷：仅返回考点训练卷行供人工编辑；专题卷/综合卷由考点行派生，保存时自动重建。
    """
    papers = repo.get_papers(ctx.project_id)
    if ctx.paper_type == "kaogang_100":
        papers = [p for p in papers
                  if (p.get("meta") or {}).get("paper_subtype", p.get("paper_type")) == "考点训练卷"]
    rows = []
    for p in papers:
        meta = p.get("meta") or {}
        rows.append({
            "paper_no": p.get("paper_no"),
            "topic": p.get("topic"), "point_name": p.get("point_name"),
            "level": meta.get("level", ""),
            "course": meta.get("course", "") or p.get("module", ""),
            "unit_name": meta.get("unit_name", ""), "chapter_name": meta.get("chapter_name", ""),
            "theme": meta.get("theme", ""), "syllabus_no": meta.get("syllabus_no", ""),
        })
    return {"paper_type": ctx.paper_type, "rows": rows}


def _validate_rows(ctx, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if ctx.paper_type == "yikeyilian":
        return validate.validate_yikeyilian(rows).to_dict()
    if ctx.paper_type == "shuangxi":
        return validate.validate_shuangxi(rows).to_dict()
    if ctx.paper_type == "kaogang_100":
        return validate.validate_kaogang(rows).to_dict()
    return {"blocked": False, "issues": []}


def save_planning(ctx, rows: list[dict[str, Any]], *, force: bool = False) -> dict[str, Any]:
    """保存编辑后的规划行：先补卷号→校验（硬拦截可 force=人工确认放行）→重落库 + 重渲染。"""
    # 先补卷号/层级号（校验依赖 paper_no 连续性），再校验
    kaogang_total = 0
    if ctx.paper_type == "yikeyilian":
        from shared.planning.llm_gen import assign_yikeyilian_numbers
        assign_yikeyilian_numbers(rows)
    elif ctx.paper_type == "shuangxi":
        for i, r in enumerate(rows, 1):
            r["paper_no"] = i  # 内容序号 seq
    elif ctx.paper_type == "kaogang_100":
        summary = kg.arrange_volume_numbers(rows)
        kaogang_total = summary.get("total_volumes") or len(rows)

    vres = _validate_rows(ctx, rows)
    if vres["blocked"] and not force:
        return {"saved": False, "validation": vres}

    out_dir = ctx.dir("生产规划")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = None
    if ctx.paper_type == "yikeyilian":
        title = f"{ctx.province}{ctx.exam_category}《一课一练》考点规划表 v1"
        out = out_dir / f"{ctx.province}{ctx.exam_category}_{ctx.textbook or ctx.course}_一课一练考点规划表.xlsx"
        path = str(yy.render_8col(rows, title=title,
                                  config_line="题型：见各行 | 难度：80:10:10",
                                  textbook_line=f"参考教材：《{ctx.textbook}》{ctx.edition}", out_path=out))
        persist = [dict(r, paper_subtype="一课一练", status="planned", original_paper_no=r.get("paper_no")) for r in rows]
    elif ctx.paper_type == "shuangxi":
        from shared.planning import shuangxi as sx
        out = out_dir / f"{ctx.province}_{ctx.exam_category}_{ctx.course or '课程'}_考点双析卷规划表.xlsx"
        path = str(sx.render_9col(rows, title=f"{ctx.province}{ctx.exam_category}《考点双析卷》考点规划表 v1",
                                  config_line="题型：见各行 | 难度：80:10:10", out_path=out))
        persist = [dict(r, paper_subtype="考点双析卷", status="planned", original_paper_no=r.get("paper_no")) for r in rows]
    elif ctx.paper_type == "kaogang_100":
        from engine.steps.planning import build_kaogang_papers
        out = out_dir / f"{ctx.province}_{ctx.exam_category}_考点规划总表.xlsx"
        path = str(kg.render_10col(rows, title=f"《{ctx.province}{ctx.exam_category}》系列卷考点规划总表（百套卷）",
                                   subtitle=f"《{ctx.province}{ctx.exam_category}》系列卷考点规划总表",
                                   out_path=out))
        # 由编辑后的考点行重建三类卷（专题/综合派生），并按全局卷号范围筛选
        diff = (ctx.volume_config or {}).get("difficulty", {"easy": 80, "medium": 10, "hard": 10})
        selected = set(ctx.selected_papers(kaogang_total) or range(1, kaogang_total + 1))
        persist = [p for p in build_kaogang_papers(rows, diff) if (p.get("paper_no") or 0) in selected]
    else:
        persist = rows
    repo.replace_papers(ctx.project_id, persist)
    return {"saved": True, "validation": vres, "path": path}
