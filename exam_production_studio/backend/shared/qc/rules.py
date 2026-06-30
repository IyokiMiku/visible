"""质检规则（阶段四 shared/qc，源 质检/rules + quality 去硬编码子集）。

接收 ctx + 题目，产出问题列表与评分；据 编写规范 实现可机检的核心规则。
"""
from __future__ import annotations

import re
from typing import Any

from engine.drivers.base import PaperQuestions, QCResult

_BANNED = ["→", "↑", "↓", "=>", "≫"]
_PASS_SCORE = 90.0


def _opt_len(opt: str) -> int:
    return len(re.sub(r"\s", "", opt))


def run_quality_checks(ctx, qs: PaperQuestions) -> QCResult:
    issues: list[str] = []
    total = len(qs.questions)
    if total == 0:
        return QCResult(paper_no=qs.paper_no, score=0.0, passed=False,
                        issues=["试卷无题目"], completeness=0.0, coverage=0.0,
                        format_ok=False, ai_risk="高")

    choice_qs = [q for q in qs.questions if "选择" in q.qtype]
    # 规则1：选择题选项长度比 ≤ 2.0
    for q in choice_qs:
        lens = [_opt_len(o) for o in q.options if o.strip()]
        if len(lens) >= 2 and min(lens) > 0 and max(lens) / min(lens) > 2.0:
            issues.append(f"第{q.number}题：选项长度比 {max(lens)/min(lens):.1f} > 2.0")

    # 规则2：答案/解析完整
    missing_ans = [q.number for q in qs.questions if not str(q.answer).strip()]
    missing_ana = [q.number for q in qs.questions if not str(q.analysis).strip()]
    if missing_ans:
        issues.append(f"缺少【答案】的题：{missing_ans}")
    if missing_ana:
        issues.append(f"缺少【解析】的题：{missing_ana}")

    # 规则3：解析禁用符号
    for q in qs.questions:
        for sym in _BANNED:
            if sym in str(q.analysis):
                issues.append(f"第{q.number}题：解析含禁用符号 {sym}")
                break

    # 规则4：选择题答案为大写字母
    for q in choice_qs:
        if q.answer and not re.fullmatch(r"[A-D]+", str(q.answer).strip()):
            issues.append(f"第{q.number}题：选择题答案 '{q.answer}' 非 A-D")

    # 规则5：AI 占位题（低信度）必须人工确认
    ai_placeholder = [q.number for q in qs.questions if q.source == "ai" and q.confidence <= 0.0]
    if ai_placeholder:
        issues.append(f"含未配置LLM的AI占位题，需人工确认：{ai_placeholder}")

    # 指标
    completeness = 1.0 - (len(set(missing_ans + missing_ana)) / total)
    coverage = len({q.kpoint for q in qs.questions if q.kpoint}) / total if total else 0.0
    ai_count = sum(1 for q in qs.questions if q.source == "ai")
    ai_risk = "高" if ai_placeholder else ("中" if ai_count else "低")

    # 评分：满分100，每条问题扣分
    penalty = min(100.0, len(issues) * 8.0 + len(ai_placeholder) * 5.0)
    score = max(0.0, 100.0 - penalty)
    passed = score >= _PASS_SCORE and not ai_placeholder

    return QCResult(
        paper_no=qs.paper_no, score=score, passed=passed, issues=issues,
        completeness=round(completeness, 3), coverage=round(coverage, 3),
        format_ok=not any("非 A-D" in i or "长度比" in i for i in issues),
        ai_risk=ai_risk,
    )
