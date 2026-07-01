"""质检规则（shared/qc）——对齐考纲百套卷新版规则。

接收 ctx + 题目，产出结构化问题（QCIssue，含稳定 code）与评分。
字符串 issues 由 QCIssue 派生以向后兼容。公式源码（$...$/{{math:}}）视为合法内容，不做残留清理。
"""
from __future__ import annotations

import re
from collections import Counter

from engine.drivers.base import PaperQuestions, QCIssue, QCResult
from .dedup import is_duplicate_stem_pair, normalize_stem_exact

_PASS_SCORE = 90.0
_SEVERITY_PENALTY = {"严重": 15.0, "警告": 5.0, "信息": 0.0}

CHOICE_TYPES = {"单项选择题", "多项选择题"}
JUDGE_TYPE = "判断题"
SUBJECTIVE_TYPES = {"简答题", "计算题", "综合应用题", "分析题", "作图题", "识图题", "简答作图题"}
DIFFICULTY_ORDER = {"简单", "适中", "困难"}

_BANNED = ["→", "↑", "↓", "=>", "≫"]
_WASTE_WORDS = {
    "正常", "无影响", "无变化", "不确定", "不动", "任意", "无要求",
    "更省油", "更快", "更好", "装饰", "没什么",
    "以上都不是", "以上都是", "都可以", "无法确定",
}
_CONNECTOR_MARKS = ["和", "或", "且", "以及", "并且"]
_CALC_MARKS = ["=", "＋", "+", "－", "-", "×", "*", "÷", "/", "%", "公式", "代入", "计算", "得"]
_WEB_RESIDUE_MARKS = [
    "<html", "</", "http://", "https://", "www.", "点击查看", "广告",
    "上一篇", "下一篇", "扫码", "二维码", "责任编辑", "来源：", "收藏", "分享",
]
_IMAGE_REQUIRED_RE = re.compile(
    r"(如图(?:所示)?|下图|图中|图示|根据(?:下)?图|由(?:下)?图|见图|观察(?:下)?图|"
    r"所示(?:电路|结构|波形|曲线|图形)|(?:电路|结构|波形|曲线|图形)如图)"
)

# code → 是否属于“格式类”（用于 format_ok 判定）
_FORMAT_CODES = {"option_length_imbalance", "invalid_answer_format", "missing_options"}


# ---------- 基础工具 ----------
def _clean(v) -> str:
    return str(v or "").strip()


def _opt_len(opt: str) -> int:
    return len(re.sub(r"\s", "", opt))


def _fmt_dist(dist: dict[str, int]) -> str:
    return "，".join(f"{k}={dist.get(k, 0)}" for k in "ABCD")


def _normalize_choice_answer(raw) -> str:
    """规范化选择/判断答案：√/× 或按 ABCD 顺序去重的字母串；无法识别返回原文。"""
    raw = _clean(raw)
    if not raw:
        return ""
    if "√" in raw or re.search(r"(对|正确)", raw):
        return "√"
    if "×" in raw or raw.lower() == "x" or re.search(r"(错|错误)", raw):
        return "×"
    upper = raw.upper()
    if re.fullmatch(r"[A-D](?:\s*[,，、/ ]\s*[A-D])*", upper) or re.fullmatch(r"[A-D]{1,4}", upper):
        present = set(re.findall(r"[A-D]", upper))
        return "".join(letter for letter in "ABCD" if letter in present)
    return raw


def _answer_letters(answer) -> list[str]:
    normalized = _normalize_choice_answer(answer)
    if not normalized or not all(c in "ABCD" for c in normalized):
        return []
    return list(normalized)


def _option_map(options) -> dict[str, str]:
    """studio 选项为纯文本列表，按下标映射到 A/B/C/D…。空选项忽略。"""
    result: dict[str, str] = {}
    for i, opt in enumerate(options or []):
        text = _clean(opt)
        if text:
            result[chr(ord("A") + i)] = text
    return result


def _has_visual(q) -> bool:
    if getattr(q, "stem_images", None):
        return True
    for imgs in getattr(q, "option_images", None) or []:
        if imgs:
            return True
    return False


def _looks_calculation(qtype: str, stem: str, answer: str) -> bool:
    if qtype == "计算题":
        return True
    text = f"{stem}\n{answer}"
    has_number = bool(re.search(r"\d", text))
    has_operator = any(m in text for m in ["+", "-", "×", "÷", "/", "=", "%"])
    has_unit = bool(re.search(r"计算|求|公式|电阻|电压|功率|速度|转速|传动比|直径|容量|尺寸|Ω|V|A|kW|mm|cm|m/s", text))
    return has_number and (has_operator or has_unit)


def _has_web_residue(q) -> bool:
    haystack = "\n".join([_clean(q.stem), _clean(q.answer), _clean(q.analysis),
                          *[_clean(o) for o in (q.options or [])]]).lower()
    return any(m.lower() in haystack for m in _WEB_RESIDUE_MARKS)


def _contains_correct_option_text(stem: str, answer: str, option_map: dict[str, str]) -> bool:
    compact_stem = re.sub(r"\s+", "", stem)
    for letter in _answer_letters(answer):
        compact = re.sub(r"\s+", "", option_map.get(letter, ""))
        if len(compact) < 6:
            continue
        fragments = {compact}
        if len(compact) > 12:
            fragments.update(compact[i:i + 8] for i in range(0, len(compact) - 7))
        if any(f and f in compact_stem for f in fragments):
            return True
    return False


# ---------- 单题检查 ----------
def _check_question(q) -> list[QCIssue]:
    issues: list[QCIssue] = []
    n = q.number
    qtype = _clean(q.qtype)
    stem = _clean(q.stem)
    answer = _clean(q.answer)
    analysis = _clean(q.analysis)
    has_visual = _has_visual(q)
    skip_analysis = has_visual or (qtype in SUBJECTIVE_TYPES and len(answer) >= 10)

    if not stem:
        issues.append(QCIssue(scope="单题", code="missing_stem", type="缺题干",
                              severity="严重", question_no=n, detail="该题缺少题干"))
    if not answer:
        issues.append(QCIssue(scope="单题", code="missing_answer", type="缺答案",
                              severity="严重", question_no=n, detail="该题缺少【答案】"))
    if not skip_analysis:
        if not analysis:
            issues.append(QCIssue(scope="单题", code="missing_analysis", type="缺解析",
                                  severity="严重", question_no=n, detail="该题缺少【解析】"))
        elif len(analysis) <= 10:
            issues.append(QCIssue(scope="单题", code="short_analysis", type="解析过短",
                                  severity="警告", question_no=n, detail=f"解析不超过10字（{len(analysis)}字）"))

    # 答案格式
    if answer:
        normalized = _normalize_choice_answer(answer)
        if qtype == "单项选择题" and (len(normalized) != 1 or normalized not in "ABCD"):
            issues.append(QCIssue(scope="单题", code="invalid_answer_format", type="答案格式错误",
                                  severity="严重", question_no=n, detail="单项选择题答案应为 A-D 中的一个字母"))
        elif qtype == "多项选择题":
            if len(normalized) < 2 or not all(c in "ABCD" for c in normalized):
                issues.append(QCIssue(scope="单题", code="invalid_answer_format", type="答案格式错误",
                                      severity="严重", question_no=n, detail="多项选择题答案应为 A-D 中至少两个字母"))
            elif normalized == "ABCD":
                issues.append(QCIssue(scope="单题", code="all_options_correct", type="多项选择题全选",
                                      severity="严重", question_no=n, detail="答案为 ABCD 全选，需重设至少一个合理错误项"))
        elif qtype == JUDGE_TYPE and normalized not in {"√", "×"}:
            issues.append(QCIssue(scope="单题", code="invalid_answer_format", type="答案格式错误",
                                  severity="严重", question_no=n, detail="判断题答案应为 √ 或 ×"))

    # 选择题选项质量
    if qtype in CHOICE_TYPES:
        option_map = _option_map(q.options)
        missing = [L for L in "ABCD" if L not in option_map]
        if missing and not has_visual:
            issues.append(QCIssue(scope="单题", code="missing_options", type="选项缺失",
                                  severity="严重", question_no=n, detail=f"选择题缺少选项：{', '.join(missing)}"))
        texts = [option_map[L] for L in "ABCD" if option_map.get(L)]
        lengths = [len(t) for t in texts if t]
        if len(lengths) >= 2:
            max_len, min_len = max(lengths), max(min(lengths), 1)
            if max_len > 5 and max_len / min_len > 2.0:
                issues.append(QCIssue(scope="单题", code="option_length_imbalance", type="选项长度失衡",
                                      severity="严重", question_no=n,
                                      detail=f"选项最长/最短字数比 {max_len/min_len:.1f} > 2.0"))
        for letter, text in option_map.items():
            if re.sub(r"\s+", "", text) in _WASTE_WORDS:
                issues.append(QCIssue(scope="单题", code="waste_option", type="废选项",
                                      severity="严重", question_no=n, detail=f'{letter}选项"{text}"属于无效干扰项'))
        connector_letters = [L for L, t in option_map.items() if any(m in t for m in _CONNECTOR_MARKS)]
        if len(connector_letters) == 1:
            issues.append(QCIssue(scope="单题", code="inconsistent_option_structure", type="选项结构不一致",
                                  severity="警告", question_no=n,
                                  detail=f"仅 {connector_letters[0]} 选项含连接词，选项结构可能突出"))
        if stem and answer and _contains_correct_option_text(stem, answer, option_map):
            issues.append(QCIssue(scope="单题", code="answer_exposure", type="答案自暴露",
                                  severity="警告", question_no=n, detail="题干疑似直接包含正确选项内容"))

    # 解析质量
    if analysis:
        for sym in _BANNED:
            if sym in analysis:
                issues.append(QCIssue(scope="单题", code="prohibited_analysis_symbol", type="解析含禁用符号",
                                      severity="警告", question_no=n, detail=f'解析中出现禁用符号"{sym}"'))
                break
        if not skip_analysis and _looks_calculation(qtype, stem, answer) and not any(m in analysis for m in _CALC_MARKS):
            issues.append(QCIssue(scope="单题", code="missing_calculation_steps", type="解析缺少计算过程",
                                  severity="警告", question_no=n, detail="疑似计算题，但解析缺少公式/算式/计算步骤"))

    # 难度名称
    difficulty = _clean(q.difficulty)
    if difficulty and difficulty not in DIFFICULTY_ORDER:
        issues.append(QCIssue(scope="单题", code="invalid_difficulty", type="难度名称不规范",
                              severity="警告", question_no=n, detail=f'难度为"{difficulty}"，应为简单/适中/困难'))

    # 网页残留
    if _has_web_residue(q):
        issues.append(QCIssue(scope="单题", code="web_residue", type="网页残留",
                              severity="警告", question_no=n, detail="疑似存在网页残留内容"))

    # 缺必要配图
    if stem and _IMAGE_REQUIRED_RE.search(stem) and not has_visual:
        issues.append(QCIssue(scope="单题", code="missing_required_image", type="缺少必要配图",
                              severity="严重", question_no=n,
                              detail='题干含"如图/下图/图示"等提示，但未检测到题干/选项图片'))

    # AI 占位题（studio 特有）
    if q.source == "ai" and q.confidence <= 0.0:
        issues.append(QCIssue(scope="单题", code="ai_placeholder", type="AI占位题待确认",
                              severity="严重", question_no=n, detail="未配置LLM的AI占位题，需人工确认"))

    return issues


# ---------- 全卷检查 ----------
def _answer_distribution_issues(qs: PaperQuestions) -> list[QCIssue]:
    issues: list[QCIssue] = []
    singles, multis = [], []
    for q in qs.questions:
        if "选择" not in q.qtype:
            continue
        a = _normalize_choice_answer(q.answer)
        if q.qtype == "单项选择题" and len(a) == 1 and a in "ABCD":
            singles.append(a)
        elif q.qtype == "多项选择题" and len(a) >= 2 and all(c in "ABCD" for c in a):
            multis.append(a)

    if singles:
        dist = Counter(singles)
        dist_text = _fmt_dist(dist)
        total = len(singles)
        max_letter = max("ABCD", key=lambda L: dist.get(L, 0))
        max_count = dist.get(max_letter, 0)
        over_max = False
        if max_count / total > 0.40:
            over_max = True
            issues.append(QCIssue(scope="全卷", code="single_answer_over_max", type="答案分布失衡", severity="严重",
                                  detail=f"单选答案分布 {dist_text}；{max_letter} 占比 {max_count/total:.0%}，超过 40%"))
        if total >= 8:
            for L in "ABCD":
                c = dist.get(L, 0)
                if 0 < c / total < 0.15:
                    issues.append(QCIssue(scope="全卷", code="single_answer_below_min", type="答案分布失衡", severity="严重",
                                          detail=f"单选答案分布 {dist_text}；{L} 占比 {c/total:.0%}，低于 15%"))
        if total > 5 and max_count > total * 0.5 and not over_max:
            issues.append(QCIssue(scope="全卷", code="single_answer_distribution", type="答案分布失衡", severity="警告",
                                  detail=f"单选答案分布 {dist_text}；{max_letter} 占比 {max_count/total:.0%}，超过 50%"))
        if not any(i.code.startswith("single_answer") for i in issues):
            issues.append(QCIssue(scope="全卷", code="single_answer_info", type="答案分布", severity="信息",
                                  detail=f"单选答案分布 {dist_text}"))

    if multis:
        dist = Counter(c for a in multis for c in a)
        total = len(multis)
        dist_text = _fmt_dist(dist)
        max_count = max(dist.get(L, 0) for L in "ABCD")
        min_count = min(dist.get(L, 0) for L in "ABCD")
        if total > 2 and (max_count == total or min_count == 0):
            issues.append(QCIssue(scope="全卷", code="multi_answer_distribution", type="多选答案分布不均", severity="警告",
                                  detail=f"多选答案分布 {dist_text}；存在选项总是或从未作为正确项"))
        else:
            issues.append(QCIssue(scope="全卷", code="multi_answer_info", type="多选答案分布", severity="信息",
                                  detail=f"多选答案分布 {dist_text}"))
    return issues


def _duplicate_issues(qs: PaperQuestions) -> list[QCIssue]:
    """题干重复两级：精确相同=严重，模糊疑似=警告。"""
    issues: list[QCIssue] = []
    qlist = qs.questions
    exact_keys = [normalize_stem_exact(q.stem) for q in qlist]
    for a in range(len(qlist)):
        for b in range(a + 1, len(qlist)):
            na, nb = qlist[a].number, qlist[b].number
            if exact_keys[a] and exact_keys[a] == exact_keys[b]:
                issues.append(QCIssue(scope="全卷", code="duplicate_question", type="重复题", severity="严重",
                                      related_nos=[na, nb], detail=f"第{na}题与第{nb}题题干完全重复"))
                continue
            dup, score, reason = is_duplicate_stem_pair(_clean(qlist[a].stem), _clean(qlist[b].stem))
            if dup:
                issues.append(QCIssue(scope="全卷", code="similar_question", type="疑似重复题", severity="警告",
                                      related_nos=[na, nb],
                                      detail=f"第{na}题与第{nb}题题干疑似重复（{reason}，相似度={score:.0%}）"))
    return issues


def _question_count_issue(qs: PaperQuestions) -> list[QCIssue]:
    """题量与规划不符：以 meta.needed 的合计为期望题量。"""
    needed = qs.meta.get("needed") or {}
    expected = sum(int(v) for v in needed.values()) if needed else 0
    actual = len(qs.questions)
    if expected > 0 and actual != expected:
        return [QCIssue(scope="全卷", code="question_count_mismatch", type="题量与规划不符", severity="严重",
                        detail=f"规划要求 {expected} 题，实际 {actual} 题")]
    return []


def run_quality_checks(ctx, qs: PaperQuestions) -> QCResult:
    total = len(qs.questions)
    if total == 0:
        empty = QCIssue(scope="全卷", code="no_questions", type="无题目", severity="严重", detail="试卷无题目")
        return QCResult(paper_no=qs.paper_no, score=0.0, passed=False,
                        issues=[empty.to_text()], structured=[empty],
                        completeness=0.0, coverage=0.0, format_ok=False, ai_risk="高")

    issues: list[QCIssue] = []
    for q in qs.questions:
        issues.extend(_check_question(q))
    issues.extend(_answer_distribution_issues(qs))
    issues.extend(_duplicate_issues(qs))
    issues.extend(_question_count_issue(qs))

    # 指标
    missing = {i.question_no for i in issues if i.code in ("missing_answer", "missing_analysis") and i.question_no}
    completeness = 1.0 - (len(missing) / total)
    coverage = len({q.kpoint for q in qs.questions if q.kpoint}) / total if total else 0.0
    ai_placeholder = any(i.code == "ai_placeholder" for i in issues)
    ai_count = sum(1 for q in qs.questions if q.source == "ai")
    ai_risk = "高" if ai_placeholder else ("中" if ai_count else "低")

    penalty = min(100.0, sum(_SEVERITY_PENALTY.get(i.severity, 0.0) for i in issues))
    score = max(0.0, 100.0 - penalty)
    passed = score >= _PASS_SCORE and not ai_placeholder
    format_ok = not any(i.code in _FORMAT_CODES for i in issues)

    return QCResult(
        paper_no=qs.paper_no, score=score, passed=passed,
        issues=[i.to_text() for i in issues], structured=issues,
        completeness=round(completeness, 3), coverage=round(coverage, 3),
        format_ok=format_ok, ai_risk=ai_risk,
    )
