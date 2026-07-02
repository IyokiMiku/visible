"""规划表行 JSON 契约（CD1）：约束 LLM 输出结构，供 prompt 与校验共用。

两套：
- yikeyilian 8 列考点行；
- kaogang 10 列考点行（+ 映射由代码聚合）。
LLM 只输出 JSON 数组，字段与枚举如下；渲染/卷号/映射由代码保证。
"""
from __future__ import annotations

from typing import Any

LEVELS = ["极重要", "重要", "标准"]

# 一课一练：LLM 输出的一行
YIKEYILIAN_ROW_SCHEMA = {
    "type": "object",
    "required": ["unit_name", "chapter_name", "topic", "point_name", "level"],
    "properties": {
        "unit_name": {"type": "string", "description": "一级标题（单元/章），如「第1章 电路的基本概念」"},
        "chapter_name": {"type": "string", "description": "二级标题（章/节），如「一、电路基础知识」"},
        "topic": {"type": "string", "description": "试卷主题（C列），≤10 汉字、去动词"},
        "point_name": {"type": "string", "description": "考纲知识点原文（B列），末尾不带句号"},
        "level": {"enum": LEVELS, "description": "掌握→极重要(拆2行) / 理解应用→重要 / 了解→标准"},
        "qtype": {"type": "string"},
        "syllabus_no": {"type": "string", "description": "考纲标号，如 课程1§3(2)"},
    },
}

# 考纲百套卷：LLM 输出的一行（考点训练卷）
KAOGANG_ROW_SCHEMA = {
    "type": "object",
    "required": ["course", "theme", "point_name", "knowledge"],
    "properties": {
        "course": {"type": "string", "description": "A 知识模块/课程名"},
        "theme": {"type": "string", "description": "B 专题名称（考纲一级标题），≤15字"},
        "point_name": {"type": "string", "description": "C 考点名称（可作卷名），≤15字，覆盖2-5个知识点"},
        "knowledge": {"type": "string", "description": "D 考点内容，多个知识点以换行分隔，每条 1. 了解/理解/掌握 开头，末尾无句号"},
    },
}


def _s(v: Any) -> str:
    return str(v).strip() if v is not None else ""


def normalize_yikeyilian_row(d: dict[str, Any]) -> dict[str, Any]:
    """把 LLM 输出的一课一练行归一化为内部 row（补层级号占位，供后续编号/渲染）。"""
    return {
        "unit_name": _s(d.get("unit_name")),
        "chapter_name": _s(d.get("chapter_name")),
        "topic": _s(d.get("topic")),
        "point_name": _strip_end_period(_s(d.get("point_name"))),
        "level": _s(d.get("level")) or "标准",
        "qtype": _s(d.get("qtype")),
        "syllabus_no": _s(d.get("syllabus_no")),
    }


def normalize_kaogang_row(d: dict[str, Any]) -> dict[str, Any]:
    return {
        "course": _s(d.get("course")),
        "theme": _s(d.get("theme")),
        "point_name": _s(d.get("point_name")),
        "knowledge": "\n".join(_strip_end_period(ln.strip())
                               for ln in _s(d.get("knowledge")).splitlines() if ln.strip()),
    }


def _strip_end_period(s: str) -> str:
    return s.rstrip().rstrip("。.．").rstrip()
