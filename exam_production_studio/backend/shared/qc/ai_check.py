"""AI 深度质检：判断整卷内容与主题/知识点的相符程度（A9）。

best-effort：LLM 未配置或调用/解析失败时返回空列表，绝不阻塞流程。
只判断「内容是否切题」，不评价难度/格式（那些由本地规则负责）。
"""
from __future__ import annotations

import json
import re

from engine.drivers.base import PaperQuestions, QCIssue
from shared.ai import complete, is_configured

_MAX_QUESTIONS = 60      # 送检题量上限，避免超长 prompt
_STEM_CLIP = 200         # 单题题干截断长度


def _parse_json(raw: str) -> dict | None:
    """从模型输出里提取 JSON（容忍 ```json 代码围栏与前后噪声）。"""
    if not raw:
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except (ValueError, TypeError):
            return None


def ai_theme_check(qs: PaperQuestions, topic: str, *, course: str = "") -> list[QCIssue]:
    """返回整卷与主题相符性问题（QCIssue 列表）。未配置/失败返回 []。"""
    if not is_configured() or not qs.questions or not str(topic or "").strip():
        return []

    lines = []
    for q in qs.questions[:_MAX_QUESTIONS]:
        stem = str(q.stem or "").strip().replace("\n", " ")[:_STEM_CLIP]
        lines.append(f"{q.number}. [{q.qtype}] {stem}")

    system = ("你是严格的试卷命题质检专家。只判断题目内容是否与给定主题/知识范围相符，"
              "不要评价难度、格式、答案对错。")
    user = (
        f"主题/知识范围：{topic}\n"
        f"课程：{course}\n\n"
        f"本卷题目：\n" + "\n".join(lines) + "\n\n"
        "请判断整卷及各题是否与该主题相符。只返回 JSON，不要解释：\n"
        '{"overall":"相符|部分不符|不符","issues":[{"question_no":题号数字或null,"detail":"简述不符原因"}]}\n'
        "整卷完全相符时 issues 为空数组。"
    )

    try:
        raw = complete(user, system=system, temperature=0.1, max_tokens=1500)
    except Exception:  # noqa: BLE001 — best-effort，任何异常都跳过
        return []

    data = _parse_json(raw)
    if not isinstance(data, dict):
        return []

    result: list[QCIssue] = []
    valid_nos = {q.number for q in qs.questions}
    raw_issues = data.get("issues") or []
    if isinstance(raw_issues, list):
        for it in raw_issues:
            if not isinstance(it, dict):
                continue
            detail = str(it.get("detail") or "").strip()
            if not detail:
                continue
            qno = it.get("question_no")
            if isinstance(qno, int) and qno in valid_nos:
                result.append(QCIssue(scope="单题", type="内容与主题不符", severity="警告",
                                      question_no=qno, detail=detail))
            else:
                result.append(QCIssue(scope="全卷", type="内容与主题不符", severity="警告",
                                      detail=detail))

    overall = str(data.get("overall") or "").strip()
    if overall and overall != "相符" and not result:
        sev = "警告" if overall == "不符" else "信息"
        result.append(QCIssue(scope="全卷", type="整卷与主题相符性", severity=sev,
                              detail=f"AI 判断：{overall}"))
    return result
