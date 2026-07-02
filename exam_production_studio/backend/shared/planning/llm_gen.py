"""规划表 LLM 生成编排（CD2 + CD4）。

CD2：把「规范要点 + 文本化样本(few-shot) + 抽取内容」组装成 prompt，调用 shared.ai.llm.call_api，
     解析 LLM 返回的 JSON 行并归一化。
CD4：生成 → 校验（validate）→ 未拦截则渲染（复用 render_8col/render_10col）。

准确性依据用户决策：卷号/映射也交给 LLM，但由校验器（硬拦截）+ 人工闸门把关；
LLM 调用为 API-gated（未配置 key 抛 LLMNotConfigured，由调用方降级到目录驱动合成或提示补数据）。
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable

from shared.planning import schema, validate
from shared.planning import yikeyilian as yy

_JSON_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.S)


# ---------------- prompt 组装 CD2 ----------------
def _toc_to_text(structured_tocs) -> str:
    lines: list[str] = []
    for st in structured_tocs:
        lines.append(f"# 教材：{st.textbook}")
        for n in st.nodes:
            lines.append(f"{'  ' * (max(1, n.level) - 1)}- (L{n.level}) {n.title}")
    return "\n".join(lines)


def _sample_rows_text(sample_rows: list[dict[str, Any]], limit: int = 8) -> str:
    """把样本行转成文本表，作为 few-shot（二进制 xlsx 不能直喂）。"""
    out = []
    for r in sample_rows[:limit]:
        out.append(json.dumps({k: r.get(k) for k in ("unit_name", "chapter_name", "topic", "point_name", "level")},
                              ensure_ascii=False))
    return "\n".join(out)


def build_messages_yikeyilian(*, toc_text: str, syllabus_text: str, sample_text: str) -> list[dict[str, str]]:
    system = (
        "你是一课一练考点规划表生成助手。严格依据《规划表编写说明》：\n"
        "1) 试卷主题(topic)来自教材目录、≤10汉字、去掉掌握/理解/了解等动词；\n"
        "2) 考纲知识点(point_name)取考纲原文、末尾不加句号；\n"
        "3) 级别(level)：掌握→极重要 / 理解或应用→重要 / 了解→标准；\n"
        "4) 一级标题(unit_name)为单元/章，二级标题(chapter_name)为章/节。\n"
        "只输出 JSON 数组，每个元素含 unit_name/chapter_name/topic/point_name/level[/qtype/syllabus_no]。"
        "不要输出解释或多余文字。"
    )
    user = (
        f"【教材目录（结构化）】\n{toc_text}\n\n"
        f"【考纲原文】\n{syllabus_text}\n\n"
        f"【样本行 few-shot（JSON）】\n{sample_text}\n\n"
        "请按上面目录顺序生成规划表行 JSON 数组。"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_messages_kaogang(*, syllabus_text: str, counts_text: str, sample_text: str) -> list[dict[str, str]]:
    system = (
        "你是考纲百套卷考点规划总表生成助手。严格依据《规划表编写说明》：\n"
        "1) A课程/B专题(考纲一级标题≤15字)/C考点名(≤15字,覆盖2-5知识点)/D知识点(考纲原文,每条以 1. 了解/理解/掌握 开头,末尾无句号)；\n"
        "2) 每专题 1~4 个考点；窄考点(题量<80)在内容相近且同专题相邻时合并(≤3)。\n"
        "只输出 JSON 数组，元素含 course/theme/point_name/knowledge。不要输出多余文字。"
    )
    user = (
        f"【考纲原文】\n{syllabus_text}\n\n"
        f"【知识点题目数量（判断窄考点）】\n{counts_text}\n\n"
        f"【样本行 few-shot（JSON）】\n{sample_text}\n\n"
        "请生成考点规划总表的考点训练卷行 JSON 数组（卷号由代码编排，无需输出卷号）。"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ---------------- 解析 LLM 输出 ----------------
def parse_json_rows(text: str) -> list[dict[str, Any]]:
    """从 LLM 文本中提取 JSON 数组。容错去 ```fence```。"""
    t = _JSON_FENCE.sub("", str(text).strip())
    try:
        data = json.loads(t)
    except ValueError:
        m = re.search(r"\[.*\]", t, re.S)  # 兜底截取第一个 JSON 数组
        if not m:
            raise
        data = json.loads(m.group(0))
    if isinstance(data, dict):
        data = data.get("rows") or data.get("data") or [data]
    return [d for d in data if isinstance(d, dict)]


# ---------------- 生成编排 CD2 ----------------
def generate_yikeyilian_rows(*, toc_text: str, syllabus_text: str, sample_text: str,
                             caller: Callable[..., str] | None = None) -> list[dict[str, Any]]:
    """调用 LLM 生成一课一练行并归一化。caller 可注入（测试）；默认 llm.call_api（API-gated）。"""
    if caller is None:
        from shared.ai.llm import call_api as caller  # 未配置 key 时内部抛 LLMNotConfigured
    msgs = build_messages_yikeyilian(toc_text=toc_text, syllabus_text=syllabus_text, sample_text=sample_text)
    raw = caller(msgs, temperature=0.2, max_tokens=4096)
    return [schema.normalize_yikeyilian_row(d) for d in parse_json_rows(raw)]


def generate_kaogang_rows(*, syllabus_text: str, counts_text: str, sample_text: str,
                          caller: Callable[..., str] | None = None) -> list[dict[str, Any]]:
    if caller is None:
        from shared.ai.llm import call_api as caller
    msgs = build_messages_kaogang(syllabus_text=syllabus_text, counts_text=counts_text, sample_text=sample_text)
    raw = caller(msgs, temperature=0.2, max_tokens=4096)
    return [schema.normalize_kaogang_row(d) for d in parse_json_rows(raw)]


# ---------------- 校验 + 渲染 CD4 ----------------
def assign_yikeyilian_numbers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """给一课一练行补 A 序号与单元/章/节号：**按课程分组，进入新课程序号重新从 1 开始**。

    委托 yikeyilian.renumber_by_course（单课程时即全局 1..N）。
    """
    return yy.renumber_by_course(rows)


def validate_and_render_yikeyilian(rows: list[dict[str, Any]], *, title: str, config_line: str,
                                   textbook_line: str, out_path) -> dict[str, Any]:
    """校验 → 未拦截则渲染 8 列 xlsx。返回 {blocked, issues, path}。"""
    assign_yikeyilian_numbers(rows)
    result = validate.validate_yikeyilian(rows)
    path = None
    if not result.blocked:
        path = str(yy.render_8col(rows, title=title, config_line=config_line,
                                  textbook_line=textbook_line, out_path=out_path))
    return {"blocked": result.blocked, "issues": [i.to_dict() for i in result.issues], "path": path}
