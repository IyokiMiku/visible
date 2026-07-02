"""考纲百套卷映射表（D4）：考点训练卷 AI 分层匹配 + 专题/综合卷代码聚合。

规则（对齐《考纲百套卷 规划表编写说明》§五）：
- 仅考点训练卷需要逐行匹配（L3 叶子→L2 父，禁 L1，禁跨课程/跨专题）；
- 匹配不上标 `AI生成`；
- 专题训练卷 = 其下考点卷 ID 并集去重（`聚合`）；
- 课程综合卷 = 该课程全部考点卷 ID 并集去重（`聚合`）；
- A 列必须覆盖全部试卷（考点卷 + 专题卷 + 综合卷）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font

HEADERS = ["试卷序号", "知识点 ID", "映射方式", "备注"]


def _dedup(ids: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def build_mapping_rows(kp_rows: list[dict[str, Any]], *, course_name_of=None,
                       resolver=None) -> list[dict[str, Any]]:
    """由考点训练卷行构造完整映射行（考点卷匹配 + 专题/综合卷聚合）。

    kp_rows：parse_10col/arrange 后的考点卷行（含 course/theme/paper_no/theme_vol_no/course_vol_range/point_name/knowledge）。
    resolver：签名 (text, course)->(ids, method)，默认用 kpoint_resolver.resolve_layered。
    course_name_of：可选映射「规划课程名 → 知识树课程名」；默认恒等。
    """
    if resolver is None:
        from shared.xueke_api.kpoint_resolver import resolve_layered as resolver
    course_name_of = course_name_of or (lambda c: c)

    rows: list[dict[str, Any]] = []
    # 1) 考点训练卷：逐行分层匹配（不跨课程——用本行 course 的知识树）
    by_theme: dict[tuple, list[int]] = {}
    by_course: dict[str, list[int]] = {}
    for r in kp_rows:
        text = r.get("knowledge") or r.get("point_name") or ""
        ids, method = resolver(text, course_name_of(r.get("course", "")))
        rows.append({
            "vol": f"第{r['paper_no']}卷", "ids": ids, "method": method,
            "remark": "" if ids else "知识树无匹配节点",
            "_sort": r["paper_no"],
        })
        # 聚合累积（禁跨课程/跨专题：键含 course）
        by_theme.setdefault((r.get("course", ""), r.get("theme", ""), r.get("theme_vol_no")), []).extend(ids)
        by_course.setdefault(r.get("course", ""), []).extend(ids)

    # 2) 专题训练卷（聚合去重）
    for (course, theme, tvol), ids in by_theme.items():
        if not tvol:
            continue
        rows.append({"vol": f"第{tvol}卷", "ids": _dedup(ids), "method": "聚合",
                     "remark": f"聚合自专题「{theme}」考点卷", "_sort": tvol})

    # 3) 课程综合卷（每课程综合卷区间共享同一并集）
    course_ranges: dict[str, tuple[int, int]] = {}
    for r in kp_rows:
        rng = r.get("course_vol_range")
        if rng:
            course_ranges[r.get("course", "")] = tuple(rng)
    for course, (lo, hi) in course_ranges.items():
        ids = _dedup(by_course.get(course, []))
        vol = f"第{lo}-{hi}卷" if hi > lo else f"第{lo}卷"
        rows.append({"vol": vol, "ids": ids, "method": "聚合",
                     "remark": f"聚合自课程「{course}」全部考点卷", "_sort": lo})

    rows.sort(key=lambda x: x["_sort"])
    return rows


def render_mapping(rows: list[dict[str, Any]], out_path: str | Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "知识点映射"
    for c, h in enumerate(HEADERS, 1):
        cell = ws.cell(1, c, h)
        cell.font = Font(name="微软雅黑", bold=True)
    unmatched: list[str] = []
    for r in rows:
        ids = r.get("ids") or []
        ws.append([r["vol"], ",".join(str(i) for i in ids), r["method"], r.get("remark", "")])
        if r["method"] == "AI生成":
            unmatched.append(r["vol"])
    if unmatched:
        ws.append([])
        ws.append(["# 未匹配列表", "、".join(unmatched)])
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out))
    return out
