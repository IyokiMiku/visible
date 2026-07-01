"""文件命名与三行标题（阶段四 shared/docx，去硬编码：按 ctx + 类型模板）。

命名为示意实现，最终以各类型模板/编写规范为准（设计文档 §10.4）。
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from engine import registry

# 编写说明模板文件名（位于 configs/{type}/ 下，可在专属配置页编辑，全局生效）。
NOTE_TEMPLATE_FILENAME = "编写说明.tpl.txt"

# 各类型默认编写说明模板串（占位符用 {province} 等，按 \n 分段）。
# 当 configs/{type}/编写说明.tpl.txt 不存在时回退到此处，保证旧行为。
DEFAULT_NOTE_TEMPLATES: dict[str, str] = {
    "yikeyilian": (
        "编写说明：考虑到中职学生普遍基础知识相对薄弱的情况，我们依据支架式教学理念，"
        "精心编制了{province}（{exam_type_name}）《{textbook}》（{edition}）一课一练。"
        "专辑里的每一份练习，都与课堂所授知识点紧密相关，题目围绕课堂所学知识点呈现。"
        "目的在于激发学生的学习兴趣，培养他们的学习自觉性，帮助学生扎实掌握课程的基本概念与基本方法。\n"
        "本练习是第{vol}练，内容围绕《{textbook}》中的{paper_name}范围编写。"
    ),
    "kaogang_100": (
        "{province}《{exam_category}考纲百套卷》，依据考纲编写。"
        "本专辑围绕考纲要求，采用三阶递进式训练体系编写：基础层拆解考点为微目标，"
        "巩固层强化知识交叉与场景关联，应用层聚焦综合提升。\n"
        "本试卷是第{vol}卷{paper_subtype}，按《{course}》中的{paper_name}范围和要求编写。"
    ),
    "shuangxi": (
        "编写说明：依据{province}（{exam_type_name}）考试要求，围绕《{course}》相关课程内容编制考点双析卷。"
        "专辑里的每一份试卷，都与考纲知识点紧密相关，题目围绕应掌握的知识和能力呈现。\n"
        "本试卷是第{vol}卷，内容涵盖{paper_name}。"
    ),
}


def _fmt(template: str, values: dict[str, Any]) -> str:
    safe: defaultdict[str, str] = defaultdict(str)
    safe.update({k: ("" if v is None else str(v)) for k, v in values.items()})
    try:
        return template.format_map(safe).strip()
    except Exception:
        return template


def note_template_path(paper_type: str) -> Path:
    """编写说明模板文件路径（configs/{type}/编写说明.tpl.txt）。"""
    return registry.CONFIGS_DIR / paper_type / NOTE_TEMPLATE_FILENAME


def load_note_template(paper_type: str) -> str:
    """读取编写说明模板串；文件不存在时回退默认模板。"""
    path = note_template_path(paper_type)
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            pass
    return DEFAULT_NOTE_TEMPLATES.get(paper_type, DEFAULT_NOTE_TEMPLATES["yikeyilian"])


def build_editorial_note(
    ctx,
    paper_no: int,
    *,
    paper_name: str = "",
    paper_subtype: str = "考点训练卷",
    topic: str = "",
    knowledge_scope: str = "",
    template: str | None = None,
) -> str:
    """按类型模板生成编写说明文本（多段以 \\n 分隔），供蓝框渲染使用。

    template 非 None 时用其作为模板（用于预览未保存的草稿）；否则读取
    configs/{type}/编写说明.tpl.txt（不存在则回退默认模板）。
    """
    try:
        display_name = registry.get(ctx.paper_type).display_name
    except Exception:
        display_name = ctx.paper_type
    name = paper_name or topic or ctx.course
    values = {
        "vol": paper_no,
        "paper_name": name,
        "topic": topic or name,
        "paper_subtype": paper_subtype,
        "knowledge_scope": knowledge_scope or name,
        "course": ctx.course,
        "province": ctx.province,
        "exam_type_name": ctx.exam_type_name,
        "exam_category": ctx.exam_category,
        "textbook": ctx.textbook,
        "edition": ctx.edition,
        "series_name": display_name,
        "display_name": display_name,
    }
    tpl = template if template is not None else load_note_template(ctx.paper_type)
    return _fmt(tpl, values)


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
        header = str(ctx.exam_type_name or "").strip()
        name = paper_name or topic
        return [
            header.strip(),
            f"《{ctx.course}》　考点双析卷　第{paper_no}卷".strip(),
            f"{name}　　{suffix}".strip(),
        ]
    # kaogang_100 默认
    return [
        f"{ctx.province}（{ctx.exam_type_name}）考纲百套卷".strip(),
        f"第{paper_no}卷 {paper_name or topic}".strip(),
        f"{paper_subtype}《{ctx.course}》{ctx.exam_category}".strip(),
    ]
