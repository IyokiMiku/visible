"""文件命名与三行标题（阶段四 shared/docx，去硬编码：按 ctx + 类型模板）。

命名为示意实现，最终以各类型模板/编写规范为准（设计文档 §10.4）。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from engine import registry


def _fmt(template: str, values: dict[str, Any]) -> str:
    safe: defaultdict[str, str] = defaultdict(str)
    safe.update({k: ("" if v is None else str(v)) for k, v in values.items()})
    try:
        return template.format_map(safe).strip()
    except Exception:
        return template


def build_filename(
    ctx,
    paper_no: int,
    *,
    paper_name: str = "",
    variant: str = "解析版",
    paper_subtype: str = "考点训练卷",
    suffix: str = "",
    topic: str = "",
) -> str:
    """生成 docx 文件名（不含扩展名）。"""
    mode = registry.get(ctx.paper_type)
    values = {
        "vol": paper_no,
        "paper_name": paper_name or topic or ctx.course,
        "topic": topic or paper_name or ctx.course,
        "paper_subtype": paper_subtype,
        "suffix": suffix,
        "variant": variant,
        "course": ctx.course,
        "province": ctx.province,
        "exam_type_name": ctx.exam_type_name,
        "exam_category": ctx.exam_category,
        "textbook": ctx.textbook,
        "edition": ctx.edition,
    }
    name = _fmt(mode.name_template, values) if mode.name_template else (
        f"第{paper_no}卷 {paper_name or ctx.course}（{variant}）"
    )
    # 清理 Windows 文件名非法字符
    for ch in '\\/:*?"<>|':
        name = name.replace(ch, "")
    return name


def build_title_lines(
    ctx,
    paper_no: int,
    *,
    paper_name: str = "",
    paper_subtype: str = "考点训练卷",
    suffix: str = "",
    topic: str = "",
) -> list[str]:
    """三行标题，按类型组织。"""
    t = ctx.paper_type
    if t == "yikeyilian":
        return [
            f"{ctx.province} 一课一练".strip(),
            f"《{ctx.textbook}》 {ctx.edition}".strip(),
            f"第{paper_no}练 {topic or paper_name}".strip(),
        ]
    if t == "shuangxi":
        return [
            f"{ctx.province}（{ctx.exam_type_name}）考点双析卷".strip(),
            f"第{paper_no}卷 {paper_name or topic} {suffix}".strip(),
            f"《{ctx.course}》{ctx.exam_category}".strip(),
        ]
    # kaogang_100 默认
    return [
        f"{ctx.province}（{ctx.exam_type_name}）考纲百套卷".strip(),
        f"第{paper_no}卷 {paper_name or topic}".strip(),
        f"{paper_subtype}《{ctx.course}》{ctx.exam_category}".strip(),
    ]
