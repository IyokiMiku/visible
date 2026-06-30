"""规划表步骤（阶段五 steps/planning）。

source='upload'：解析上传的规划表 xlsx；否则本地合成（OCR/默认）。
产出 生产规划/{规划表}.xlsx，并把卷落库 papers。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook

from engine import registry, repo

_PLAN_HEADERS = ["序号", "卷号", "试卷主题", "考纲知识点", "卷型", "难度", "套数"]


def _find_uploaded_plan(ctx) -> Path | None:
    in_dir = ctx.input_dir()
    if not in_dir.exists():
        return None
    xlsxs = [p for p in in_dir.rglob("*.xlsx") if "映射" not in p.name]
    return xlsxs[0] if xlsxs else None


def _parse_uploaded(path: Path) -> list[dict[str, Any]]:
    wb = load_workbook(str(path), data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h).strip() if h is not None else "" for h in next(rows_iter, [])]
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows_iter, 1):
        cells = {headers[j] if j < len(headers) else f"c{j}": row[j] for j in range(len(row))}
        topic = str(cells.get("试卷主题") or cells.get("主题") or cells.get("试卷名称") or f"主题{i}").strip()
        point = str(cells.get("考纲知识点") or cells.get("知识点") or topic).strip()
        out.append({"paper_no": i, "topic": topic, "point_name": point})
    return out


def _subtype(ctx) -> str:
    return {"yikeyilian": "一课一练", "shuangxi": "考点训练卷"}.get(ctx.paper_type, "考点训练卷")


def _synthesize(ctx, total_hint: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(1, total_hint + 1):
        rows.append({
            "paper_no": i,
            "topic": f"{ctx.course or '课程'} 第{i}{'练' if ctx.paper_type == 'yikeyilian' else '卷'}主题",
            "point_name": f"{ctx.course or '课程'}知识点{i}",
        })
    return rows


def gen_planning(ctx, source: str = "ocr") -> tuple[Path, list[dict[str, Any]]]:
    mode = registry.get(ctx.paper_type)
    diff = (ctx.volume_config or mode.default_volume_config).get("difficulty", {"easy": 80, "medium": 10, "hard": 10})

    uploaded = _find_uploaded_plan(ctx) if source == "upload" else None
    if uploaded:
        base_rows = _parse_uploaded(uploaded)
    else:
        base_rows = None

    total = len(base_rows) if base_rows else 3
    selected = ctx.selected_papers(total)
    if not selected:  # 'all'
        selected = list(range(1, total + 1))

    if base_rows:
        by_no = {r["paper_no"]: r for r in base_rows}
        rows = [by_no.get(n, {"paper_no": n, "topic": f"主题{n}", "point_name": ""}) for n in selected]
        # 重排卷号为连续
        for idx, r in enumerate(rows, 1):
            r["paper_no"] = idx
    else:
        synth = _synthesize(ctx, max(selected))
        rows = [synth[n - 1] for n in selected]
        for idx, r in enumerate(rows, 1):
            r["paper_no"] = idx

    for r in rows:
        r.setdefault("paper_subtype", _subtype(ctx))
        r["difficulty"] = diff
        r["status"] = "planned"

    # 写 xlsx
    out_dir = ctx.dir("生产规划")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ctx.course or '课程'}_规划表.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "规划表"
    ws.append(_PLAN_HEADERS)
    for r in rows:
        ws.append([r["paper_no"], r["paper_no"], r["topic"], r["point_name"],
                   r["paper_subtype"], "简单80/适中10/困难10", 1])
    wb.save(str(out_path))

    repo.replace_papers(ctx.project_id, rows)
    return out_path, rows
