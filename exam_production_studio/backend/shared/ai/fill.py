"""AI 补题统一入口 ai_fill（阶段四 shared/ai，设计文档 §6.4）。

- 已配置 LLM：调用 LLM 按缺口生成，并解析为 Question。
- 退化为占位题（标记 source='ai'、低信度=0.0）的三种情形，占位题文案会区分原因：
  1) 未配置 LLM；2) AI 补题调用失败（如超时/网络，附具体错误）；3) AI 返回为空或无法解析。
  保证流程可离线跑通，并由上层据信度/数量决定是否进入待确认队列（AI_GENERATE）。
"""
from __future__ import annotations

import re
from typing import Any

from engine.drivers.base import Question
from shared.xueke_api import kpoint_resolver
from . import llm
from .prompts import build_generation_prompt

_TYPE_HEADER = re.compile(r"^[一二三四五六七八九十]+、\s*(.+?)\s*$")
_Q_START = re.compile(r"^\s*(\d+)\s*[\.、]\s*(.*)$")
_OPTION = re.compile(r"^([A-DＡ-Ｄ])[\.\．、]\s*(.+)$")
_ANSWER = re.compile(r"^【答案】\s*(.*)$")
_ANALYSIS = re.compile(r"^【解析】\s*(.*)$")


def parse_paper_text(text: str) -> list[Question]:
    """把"题型标题 + 题号 + 选项 + 【答案】+【解析】"格式解析为 Question 列表。"""
    questions: list[Question] = []
    cur_type = "单项选择题"
    cur: Question | None = None
    mode = None  # None | 'stem' | 'answer' | 'analysis'

    def flush() -> None:
        nonlocal cur
        if cur is not None:
            questions.append(cur)
            cur = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        mh = _TYPE_HEADER.match(line.strip())
        if mh and ("题" in mh.group(1)) and not _Q_START.match(line.strip()):
            flush()
            cur_type = kpoint_resolver.normalize_type_name(mh.group(1).strip())
            continue
        mq = _Q_START.match(line)
        if mq and not _OPTION.match(line.strip()):
            flush()
            cur = Question(number=int(mq.group(1)), qtype=cur_type, stem=mq.group(2).strip(), source="ai")
            mode = "stem"
            continue
        if cur is None:
            continue
        for opt_part in re.split(r"\t+|\s{2,}", line.strip()):
            mo = _OPTION.match(opt_part.strip())
            if mo:
                cur.options.append(mo.group(2).strip())
        if _OPTION.match(line.strip()):
            continue
        ma = _ANSWER.match(line.strip())
        if ma:
            cur.answer = ma.group(1).strip()
            mode = "answer"
            continue
        mx = _ANALYSIS.match(line.strip())
        if mx:
            cur.analysis = mx.group(1).strip()
            mode = "analysis"
            continue
        if mode == "answer":
            cur.answer += line.strip()
        elif mode == "analysis":
            cur.analysis += line.strip()
        elif mode == "stem":
            cur.stem += line.strip()
    flush()
    return questions


_DEFAULT_OPTIONS = {
    "单项选择题": ["待人工核对的占位选项一", "待人工核对的占位选项二", "待人工核对的占位选项三", "待人工核对的占位选项四"],
    "多项选择题": ["待人工核对的占位选项一", "待人工核对的占位选项二", "待人工核对的占位选项三", "待人工核对的占位选项四"],
}


def _synthetic(
    plan: dict[str, Any],
    shortfall: dict[str, int],
    start_number: int,
    reason: str = "未配置 LLM",
    detail: str = "",
) -> list[Question]:
    """生成占位题。reason 区分退化原因（未配置 / 调用失败 / 返回为空），detail 附具体错误。"""
    topic = plan.get("topic") or plan.get("paper_name") or plan.get("point_name") or "本卷主题"
    detail_suffix = f"（{detail}）" if detail else ""
    out: list[Question] = []
    n = start_number
    for qtype, count in shortfall.items():
        for i in range(max(0, count)):
            q = Question(
                number=n,
                qtype=qtype,
                stem=(f"【AI待补·{reason}】关于「{topic}」的{qtype}占位第{i + 1}题"
                      f"（需人工确认或修复后重新生成）"),
                options=list(_DEFAULT_OPTIONS.get(qtype, [])),
                answer="A" if "选择" in qtype else "待补充",
                analysis=f"占位解析：AI 补题退化，原因：{reason}{detail_suffix}，已标记待人工确认。",
                difficulty="简单",
                kpoint=str(plan.get("point_name") or topic),
                source="ai",
                confidence=0.0,
            )
            out.append(q)
            n += 1
    return out


def _err_detail(exc: Exception, limit: int = 120) -> str:
    """把异常压成一行简短描述，供占位题标注（避免把超长堆栈塞进题干）。"""
    msg = f"{type(exc).__name__}: {exc}".replace("\n", " ").strip()
    return msg[:limit]


def ai_fill(ctx, plan: dict[str, Any], shortfall: dict[str, int], start_number: int = 1) -> list[Question]:
    shortfall = {t: int(n) for t, n in shortfall.items() if int(n) > 0}
    if not shortfall:
        return []
    if not llm.is_configured():
        return _synthetic(plan, shortfall, start_number, reason="未配置 LLM")
    try:
        prompt = build_generation_prompt(ctx, plan, shortfall)
        text = llm.complete(prompt, temperature=0.7, max_tokens=4096)
        parsed = parse_paper_text(text)
        if not parsed:
            return _synthetic(plan, shortfall, start_number, reason="AI 返回为空或无法解析")
        for idx, q in enumerate(parsed):
            q.number = start_number + idx
            q.source = "ai"
            q.confidence = max(q.confidence, 0.7)
        return parsed
    except Exception as e:  # noqa: BLE001
        return _synthetic(plan, shortfall, start_number, reason="AI 补题调用失败", detail=_err_detail(e))
