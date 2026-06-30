"""考纲百套卷结构化质检规则。"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import re
import string
from typing import Any

from 生成器.question_types import normalize_question_type

FAILED = "failed"
WARNING = "warning"
PASSED = "passed"

CHOICE_TYPES = {"单项选择题", "多项选择题"}
SUBJECTIVE_TYPES = {"简答题", "计算题", "综合应用题", "分析题", "作图题", "识图题"}
DIFFICULTY_ORDER = {"简单": 0, "适中": 1, "困难": 2}

WEB_RESIDUE_MARKS = [
    "<html",
    "</",
    "http://",
    "https://",
    "www.",
    "点击查看",
    "广告",
    "上一篇",
    "下一篇",
    "扫码",
    "二维码",
    "责任编辑",
    "来源：",
    "收藏",
    "分享",
]

FORMAT_RESIDUE_MARKS = [
    "```",
    "**",
    "\\frac",
    "\\(",
    "\\)",
]

PROHIBITED_ANALYSIS_SYMBOLS = ["→", "↑", "↓", "=>", "≫"]
WASTE_OPTION_TEXTS = {
    "正常",
    "无影响",
    "无变化",
    "不确定",
    "不动",
    "任意",
    "无要求",
    "更省油",
    "更快",
    "更好",
    "装饰",
    "没什么",
    "以上都不是",
    "以上都是",
    "都可以",
    "无法确定",
}
CONNECTOR_MARKS = ["和", "或", "且", "以及", "并且"]
CALCULATION_MARKS = ["=", "＋", "+", "－", "-", "×", "*", "÷", "/", "%", "公式", "代入", "计算", "得"]

# 题型归一化统一委托给 question_types.py（字典精确全字匹配，输出标准全名如"单项选择题"）

_TEMPLATE_PATTERNS = [
    r"下列", r"关于", r"有关", r"对于", r"在.*?中", r"根据.*?可知",
    r"说法", r"表述", r"选项", r"哪一项", r"哪项", r"的是", r"是\s*\(\s*\)",
    r"正确的是", r"错误的是", r"不正确的是", r"不属于", r"属于",
    r"主要", r"基本", r"一般", r"通常", r"应当", r"可以", r"能够", r"需要",
    r"作用", r"原因", r"特点", r"目的", r"要求", r"方法", r"措施",
]

_STOP_WORDS = {
    "下列", "关于", "有关", "对于", "说法", "表述", "选项", "哪一项", "哪项",
    "正确", "错误", "不正确", "属于", "不属于", "主要", "基本", "一般", "通常",
    "应当", "可以", "能够", "需要", "作用", "原因", "特点", "目的", "要求", "方法", "措施",
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def make_issue(code: str, name: str, severity: str, message: str) -> dict[str, str]:
    """构造稳定的结构化质检问题。"""
    return {
        "code": code,
        "name": name,
        "severity": severity,
        "message": message,
    }


def _question_no(question: dict[str, Any], fallback: int | None = None) -> int | None:
    value = question.get("question_no")
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _option_label(option: Any) -> str:
    match = re.match(r"^\s*([A-H])\s*[.、．)]", _clean_text(option), re.I)
    return match.group(1).upper() if match else ""


def _option_text(option: Any) -> str:
    text = _clean_text(option)
    return re.sub(r"^\s*[A-H]\s*[.、．)]\s*", "", text, flags=re.I).strip()


def _options_by_label(options: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    if isinstance(options, dict):
        for key, value in options.items():
            label = _clean_text(key).upper()[:1]
            if label:
                result[label] = _clean_text(value)
        return result
    for option in options or []:
        label = _option_label(option)
        if label:
            result[label] = _option_text(option)
    return result


def _normalize_choice_answer(raw_answer: Any) -> str:
    raw = _clean_text(raw_answer)
    if not raw:
        return ""
    if "√" in raw or re.search(r"\b(对|正确)\b", raw):
        return "√"
    if "×" in raw or raw.lower() == "x" or re.search(r"\b(错|错误)\b", raw):
        return "×"
    upper = raw.upper().strip()
    if re.fullmatch(r"[A-D](?:\s*[,，、/ ]\s*[A-D])*", upper) or re.fullmatch(r"[A-D]{1,4}", upper):
        letters = re.findall(r"[A-D]", upper)
        present = set(letters)
        return "".join(letter for letter in "ABCD" if letter in present)
    return raw


def _answer_letters(answer: str) -> list[str]:
    normalized = _normalize_choice_answer(answer)
    if not normalized or not all(letter in "ABCD" for letter in normalized):
        return []
    return list(normalized)


def _contains_correct_option_text(stem: str, answer: str, options: Any) -> bool:
    option_map = _options_by_label(options)
    compact_stem = re.sub(r"\s+", "", stem)
    for letter in _answer_letters(answer):
        option_text = option_map.get(letter, "")
        compact = re.sub(r"\s+", "", option_text)
        if len(compact) < 6:
            continue
        # 用较长选项文本和 6 字以上连续片段检测，避免答案字母 A/B/C/D 误报。
        fragments = {compact}
        if len(compact) > 12:
            fragments.update(compact[i : i + 8] for i in range(0, len(compact) - 7))
        if any(fragment and fragment in compact_stem for fragment in fragments):
            return True
    return False


def _question_text_chunks(question: dict[str, Any]) -> list[str]:
    chunks = [
        _clean_text(question.get("stem")),
        _clean_text(question.get("answer")),
        _clean_text(question.get("analysis")),
        _clean_text(question.get("raw_text")),
    ]
    chunks.extend(_clean_text(option) for option in question.get("options") or [])
    return chunks


def _has_web_residue(question: dict[str, Any]) -> bool:
    haystack = "\n".join(_question_text_chunks(question)).lower()
    return any(mark.lower() in haystack for mark in WEB_RESIDUE_MARKS)


def _has_format_residue(question: dict[str, Any]) -> bool:
    haystack = "\n".join(_question_text_chunks(question))
    if any(mark in haystack for mark in FORMAT_RESIDUE_MARKS):
        return True
    return bool(re.search(r"\$[^$]+\$", haystack))


def _check_answer_format(qtype: str, answer: str, label: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    normalized = _normalize_choice_answer(answer)
    if qtype == "单项选择题" and (len(normalized) != 1 or normalized not in "ABCD"):
        issues.append(make_issue("invalid_answer_format", "答案格式错误", FAILED, f"{label}单项选择题答案应为 A-D 中的一个字母。"))
    elif qtype == "多项选择题":
        if len(normalized) < 2 or not all(letter in "ABCD" for letter in normalized):
            issues.append(make_issue("invalid_answer_format", "答案格式错误", FAILED, f"{label}多项选择题答案应为 A-D 中至少两个字母。"))
        elif normalized == "ABCD":
            issues.append(make_issue("all_options_correct", "多项选择题全选", FAILED, f"{label}多项选择题答案为 ABCD 全选，需重设至少一个合理错误项。"))
    elif qtype == "判断题" and normalized not in {"√", "×"}:
        issues.append(make_issue("invalid_answer_format", "答案格式错误", FAILED, f"{label}判断题答案应为 √ 或 ×。"))
    return issues


def _check_option_quality(option_map: dict[str, str], label: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if len(option_map) < 4:
        return issues

    option_texts = [option_map[letter] for letter in "ABCD" if option_map.get(letter)]
    lengths = [len(text) for text in option_texts if text]
    if len(lengths) >= 2:
        min_len = max(min(lengths), 1)
        max_len = max(lengths)
        ratio = max_len / min_len
        # 短选项即使存在倍数差异，视觉上也不构成明显失衡。
        if max_len > 5 and ratio > 2.0:
            detail = "，".join(f"{letter}({len(option_map[letter])}字)" for letter in "ABCD" if letter in option_map)
            issues.append(make_issue("option_length_imbalance", "选项长度失衡", FAILED, f"{label}选项最长/最短字数比为 {ratio:.1f}，超过 2.0；{detail}。"))

    for letter, text in option_map.items():
        compact = re.sub(r"\s+", "", text)
        if compact in WASTE_OPTION_TEXTS:
            issues.append(make_issue("waste_option", "废选项", FAILED, f"{label}{letter}选项“{text}”属于无效干扰项。"))

    connector_letters = [
        letter for letter, text in option_map.items()
        if any(mark in text for mark in CONNECTOR_MARKS)
    ]
    if len(connector_letters) == 1:
        issues.append(make_issue("inconsistent_option_structure", "选项结构不一致", WARNING, f"{label}仅{connector_letters[0]}选项含连接词，选项结构可能突出。"))

    return issues


def _looks_calculation_related(qtype: str, stem: str, answer: str) -> bool:
    if qtype == "计算题":
        return True
    text = f"{stem}\n{answer}"
    has_number = bool(re.search(r"\d", text))
    has_operator = any(mark in text for mark in ["+", "-", "×", "÷", "/", "=", "%"])
    has_unit_or_calc_word = bool(re.search(r"计算|求|公式|电阻|电压|功率|速度|转速|传动比|直径|容量|尺寸|Ω|V|A|kW|mm|cm|m/s", text))
    return has_number and (has_operator or has_unit_or_calc_word)


def _check_analysis_quality(qtype: str, stem: str, answer: str, analysis: str, label: str, skip_calculation: bool = False) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for symbol in PROHIBITED_ANALYSIS_SYMBOLS:
        if symbol in analysis:
            issues.append(make_issue("prohibited_analysis_symbol", "解析含禁用符号", WARNING, f"{label}解析中出现禁用符号“{symbol}”。"))
            break
    if not skip_calculation and analysis and _looks_calculation_related(qtype, stem, answer) and not any(mark in analysis for mark in CALCULATION_MARKS):
        issues.append(make_issue("missing_calculation_steps", "解析缺少计算过程", WARNING, f"{label}疑似计算相关题，但解析缺少公式、算式或计算步骤。"))
    return issues


def check_question_structured(
    question: dict[str, Any], plan_context: dict[str, Any] | None = None
) -> list[dict[str, str]]:
    """返回单题结构化质检问题列表。"""
    issues: list[dict[str, str]] = []
    question_no = _question_no(question)
    label = f"第{question_no}题" if question_no is not None else "本题"

    qtype = normalize_question_type(question.get("question_type"))
    stem = _clean_text(question.get("stem"))
    answer = _clean_text(question.get("answer"))
    analysis = _clean_text(question.get("analysis"))
    options = question.get("options") or []
    image_refs = question.get("image_refs") if isinstance(question.get("image_refs"), dict) else {}
    has_visual_object = bool(
        question.get("protected_original_docx_block")
        or any((question.get("image_flags") or {}).values())
        or any(image_refs.get(part) for part in ("stem", "answer", "analysis", "options"))
    )
    # 主观题答案已包含解题过程（文本≥10字 或 答案含图片/公式图）的，不检查解析完整性和计算过程。
    # 带图/公式/OLE 题的短解析无法安全自动修复，允许删除解析占位后交付。
    has_answer_images = bool(image_refs.get("answer") or image_refs.get("options"))
    skip_analysis_checks = has_visual_object or (qtype in SUBJECTIVE_TYPES and (len(answer) >= 10 or has_answer_images))

    if not stem:
        issues.append(make_issue("missing_stem", "缺题干", FAILED, f"{label}缺少题干。"))
    if not answer:
        issues.append(make_issue("missing_answer", "缺答案", FAILED, f"{label}缺少答案。"))
    if not skip_analysis_checks:
        if not analysis:
            issues.append(make_issue("missing_analysis", "缺解析", FAILED, f"{label}缺少解析。"))
        elif len(analysis) <= 10:
            issues.append(make_issue("short_analysis", "解析过短", WARNING, f"{label}解析不超过10字。"))

    if answer:
        issues.extend(_check_answer_format(qtype, answer, label))

    if qtype in CHOICE_TYPES:
        option_map = _options_by_label(options)
        missing = [letter for letter in "ABCD" if letter not in option_map]
        # 原始 DOCX 带图题的选项可能嵌在图片/表格中，拆题 JSON 不一定能解析为 options。
        # 只要保留了真实视觉对象，就不要把结构化 options 为空误判为选项缺失。
        if missing and not has_visual_object:
            issues.append(
                make_issue(
                    "missing_options",
                    "选项缺失",
                    FAILED,
                    f"{label}选择题缺少选项：{', '.join(missing)}。",
                )
            )
        issues.extend(_check_option_quality(option_map, label))
        if stem and answer and _contains_correct_option_text(stem, answer, options):
            issues.append(
                make_issue(
                    "answer_exposure",
                    "答案自暴露",
                    WARNING,
                    f"{label}题干疑似直接包含正确选项内容。",
                )
            )

    if analysis:
        issues.extend(_check_analysis_quality(qtype, stem, answer, analysis, label, skip_calculation=skip_analysis_checks))

    difficulty = _clean_text(question.get("difficulty"))
    if difficulty and difficulty not in DIFFICULTY_ORDER:
        issues.append(make_issue("invalid_difficulty", "难度名称不规范", WARNING, f"{label}难度为“{difficulty}”，应为简单、适中或困难。"))

    if _has_web_residue(question):
        issues.append(make_issue("web_residue", "网页残留", WARNING, f"{label}疑似存在网页残留内容。"))
    if _has_format_residue(question):
        issues.append(make_issue("format_residue", "格式残留", WARNING, f"{label}疑似存在 Markdown 或 LaTeX 残留。"))

    if stem and _IMAGE_REQUIRED_RE.search(stem) and not has_visual_object:
        issues.append(
            make_issue(
                "missing_required_image",
                "缺少必要配图",
                FAILED,
                f"{label}题干含“如图/下图/图示”等配图提示，但未检测到题干、答案或解析中的真实图片对象。",
            )
        )

    if plan_context:
        expected_type = normalize_question_type(plan_context.get("question_type"))
        if expected_type and qtype and expected_type != qtype:
            issues.append(
                make_issue(
                    "wrong_question_type",
                    "题型错误",
                    FAILED,
                    f"{label}题型为“{qtype}”，细目表期望为“{expected_type}”。",
                )
            )

    return issues


def check_question(question: dict[str, Any], plan_context: dict[str, Any] | None = None) -> list[str]:
    """返回单题质检问题名称列表，兼容旧调用。"""
    return [issue["name"] for issue in check_question_structured(question, plan_context)]


def _normalize_stem_for_duplicate(stem: Any) -> str:
    text = _clean_text(stem)
    text = re.sub(r"\s+", "", text)
    return text.translate(str.maketrans("", "", string.punctuation + "，。、；：？！“”‘’（）【】《》…—·"))


def check_duplicate_questions_structured(questions: list[dict[str, Any]]) -> dict[int, list[dict[str, str]]]:
    """按题干确定性检查重复题，返回按题目下标归组的问题。"""
    normalized: list[str] = [_normalize_stem_for_duplicate(q.get("stem")) for q in questions]
    counts = Counter(stem for stem in normalized if stem)
    first_seen: dict[str, int] = {}
    result: dict[int, list[dict[str, str]]] = defaultdict(list)

    for index, stem in enumerate(normalized):
        if not stem or counts[stem] <= 1:
            continue
        question_no = _question_no(questions[index], index + 1)
        if stem not in first_seen:
            first_seen[stem] = index
            continue
        first_no = _question_no(questions[first_seen[stem]], first_seen[stem] + 1)
        result[index].append(
            make_issue(
                "duplicate_question",
                "重复题",
                FAILED,
                f"第{question_no}题题干与第{first_no}题重复。",
            )
        )
        result[first_seen[stem]].append(
            make_issue(
                "duplicate_question",
                "重复题",
                FAILED,
                f"第{first_no}题题干与第{question_no}题重复。",
            )
        )

    return dict(result)


def check_duplicate_questions(questions: list[dict[str, Any]]) -> dict[int, list[str]]:
    """按题干粗略检查重复题，兼容旧调用。"""
    structured = check_duplicate_questions_structured(questions)
    return {index: [issue["name"] for issue in issues] for index, issues in structured.items()}


def _normalize_stem_for_dup(text: Any) -> str:
    text = _clean_text(text)
    text = re.sub(r"^\d+[.．、]\s*", "", text)
    text = re.sub(r"（\s*）", "", text)
    text = re.sub(r"[，,。；;：:？！?、（）()《》<>\[\]【】\s]", "", text)
    for pattern in _TEMPLATE_PATTERNS:
        text = re.sub(pattern, "", text)
    return text.strip()


def _longest_common_substring_len(text_a: str, text_b: str) -> int:
    if not text_a or not text_b:
        return 0
    prev = [0] * (len(text_b) + 1)
    best = 0
    for ca in text_a:
        curr = [0]
        for idx, cb in enumerate(text_b, 1):
            val = prev[idx - 1] + 1 if ca == cb else 0
            curr.append(val)
            if val > best:
                best = val
        prev = curr
    return best


def _keyword_units(text: Any) -> set[str]:
    normalized = _normalize_stem_for_dup(text)
    if len(normalized) < 2:
        return {normalized} if normalized else set()
    units = {normalized[i:i + 2] for i in range(len(normalized) - 1)}
    return {unit for unit in units if unit and unit not in _STOP_WORDS}


def _char_set_similarity(text_a: str, text_b: str) -> float:
    if not text_a or not text_b:
        return 0.0
    set_a = set(text_a)
    set_b = set(text_b)
    shorter = min(len(set_a), len(set_b))
    if shorter == 0:
        return 0.0
    return len(set_a & set_b) / shorter


def _keyword_similarity(text_a: Any, text_b: Any) -> float:
    units_a = _keyword_units(text_a)
    units_b = _keyword_units(text_b)
    shorter = min(len(units_a), len(units_b))
    if shorter == 0:
        return 0.0
    return len(units_a & units_b) / shorter


def _is_duplicate_stem_pair(text_a: Any, text_b: Any) -> tuple[bool, float, str]:
    norm_a = _normalize_stem_for_dup(text_a)
    norm_b = _normalize_stem_for_dup(text_b)
    if not norm_a or not norm_b:
        return False, 0.0, "核心题干为空"

    shorter_len = min(len(norm_a), len(norm_b))
    phrase_len = _longest_common_substring_len(norm_a, norm_b)
    phrase_score = phrase_len / max(shorter_len, 1)
    keyword_score = _keyword_similarity(text_a, text_b)
    char_score = _char_set_similarity(norm_a, norm_b)
    score = max(phrase_score, keyword_score, char_score)

    if phrase_len >= 8 and phrase_score >= 0.60:
        return True, score, f"连续相同片段{phrase_len}字"
    if keyword_score >= 0.75 and char_score >= 0.60:
        return True, score, "核心关键词高度重合"
    if char_score >= 0.90 and shorter_len >= 10:
        return True, score, "去模板后题干高度相似"
    return False, score, "未达到重复阈值"


# ====== 增强检测: 数字归一化 + 答案交叉 + 知识点密度 ======

def _normalize_numbers(text: str) -> str:
    """将数字、单位值归一化为占位符 #N，消除数字替换题的文字差异。"""
    if not text:
        return ""
    # 数字+单位（10Ω, 20V, 5A, 100kΩ, 3.3V...）
    text = re.sub(r'\d+\.?\d*\s*[ΩVAWHzμkM%℃]', '#N', text)
    # 纯数字（整数/小数）
    text = re.sub(r'\d+\.?\d*', '#N', text)
    return text


def _is_number_substitute_pair(text_a: str, text_b: str) -> tuple[bool, str]:
    """检测两题是否为纯数字替换题——题干结构相同，仅数值不同。"""
    n_a = _normalize_numbers(_normalize_stem_for_dup(text_a))
    n_b = _normalize_numbers(_normalize_stem_for_dup(text_b))
    if not n_a or not n_b or len(n_a) < 10 or len(n_b) < 10:
        return False, ""
    # 要求#N出现至少2次（说明确实有数字被替换了）
    if n_a.count('#N') < 2 or n_b.count('#N') < 2:
        return False, ""
    # 归一化后完全相同 → 纯数字替换
    if n_a == n_b:
        return True, f"数字替换题（数值不同，结构相同）"
    # 归一化后相似度>0.95
    longer = max(len(n_a), len(n_b))
    common = _longest_common_substring_len(n_a, n_b)
    if common / max(longer, 1) > 0.95:
        return True, f"疑似数字替换题（结构相似度{common/longer:.0%}）"
    return False, ""


def _check_answer_stem_leak(
    loaded_a: list[dict], loaded_b: list[dict],
    label_a: str, label_b: str,
) -> list[dict]:
    """检测A卷答案是否出现在B卷题干中（答案泄露）。"""
    issues: list[dict] = []
    for idx_a, qa in enumerate(loaded_a):
        answer = str(qa.get("answer", "")).strip()
        if not answer or len(answer) < 2:
            continue
        qno_a = qa.get("question_no") or idx_a + 1
        for idx_b, qb in enumerate(loaded_b):
            stem = str(qb.get("stem", "") or "")
            if not stem:
                continue
            qno_b = qb.get("question_no") or idx_b + 1
            # 答案文本直接出现在另卷题干中
            if answer in stem:
                issues.append(make_issue(
                    "answer_stem_leak", "答案泄露",
                    WARNING,
                    f"{label_a}第{qno_a}题答案({answer[:20]})出现在{label_b}第{qno_b}题题干中",
                ))
    return issues


def _check_kpoint_density(
    loaded_a: list[dict], loaded_b: list[dict],
    label_a: str, label_b: str,
) -> list[dict]:
    """检测同一知识点在两卷中是否被过度考查（密度过高）。"""
    from collections import Counter

    def collect_kpoints(loaded):
        kp: list[str] = []
        for q in loaded:
            kp_ids = q.get("_kpoint_ids") or q.get("kpointIds") or []
            if isinstance(kp_ids, str):
                kp_ids = [x.strip() for x in kp_ids.split(",") if x.strip()]
            for kid in kp_ids:
                kp.append(str(kid))
        return Counter(kp)

    ca = collect_kpoints(loaded_a)
    cb = collect_kpoints(loaded_b)

    issues: list[dict] = []
    all_kids = set(ca.keys()) | set(cb.keys())
    for kid in all_kids:
        count_a = ca.get(kid, 0)
        count_b = cb.get(kid, 0)
        total = count_a + count_b
        # 同一知识点在两卷中出现9次以上
        if total >= 9:
            issues.append(make_issue(
                "kpoint_density_high", "跨卷知识点密度过高",
                WARNING,
                f"kpoint {kid[-6:]} 在{label_a}(×{count_a})和{label_b}(×{count_b})共出现{total}次",
            ))
    return issues


_MATH_MARKER_RE = re.compile(
    r"\$[^$]{1,200}\$|\\\([^)]{1,200}\\\)|\\\[[\s\S]{1,500}?\\\]|"
    r"\{\{?math:.*?\}\}?|\\(?:frac|sqrt|sum|int|lim|sin|cos|tan|log|ln|Omega|rho|times|cdot|Delta|alpha|beta|gamma)\b(?:\s*\{[^{}]*\})*",
    re.DOTALL,
)

_TEXT_FORMULA_RE = re.compile(
    r"(?:[A-Za-zα-ωΑ-ΩηρΩ][\wα-ωΑ-ΩηρΩ_]*|[一-鿿]{1,8})\s*="
    r"\s*[^，。；;、\n]{1,80}(?:[+＋\-－×*÷/^=]|\d|Ω|V|A|W|Hz|r/min|N|Pa|MPa|mm|cm|m|%)"
)

_FORMULA_UNIT_RE = re.compile(r"(r/min|MPa|kΩ|MΩ|mA|kW|Ω|Hz|Pa|mm|cm|%)", re.I)

_IMAGE_TOKEN_RE = re.compile(r"\[(?:图片|图|image|img)\]|<img\b|!\[[^\]]*\]\([^)]*\)", re.I)
_IMAGE_REQUIRED_RE = re.compile(
    r"(如图(?:所示)?|下图|图中|图示|根据(?:下)?图|由(?:下)?图|见图|观察(?:下)?图|"
    r"所示(?:电路|结构|波形|曲线|图形)|(?:电路|结构|波形|曲线|图形)如图)",
    re.I,
)


def _normalize_formula_text(formula: str) -> str:
    """公式指纹归一化：保留结构/单位，弱化变量名、中文量名和数值差异。"""
    text = _clean_text(formula)
    text = re.sub(r"^\$|\$$|^\\\(|\\\)$|^\\\[|\\\]$", "", text)
    text = re.sub(r"^\{\{?math:|\}\}?$", "", text, flags=re.I)
    text = text.replace("\\left", "").replace("\\right", "")
    text = text.replace("＋", "+").replace("－", "-").replace("×", "*").replace("÷", "/")
    text = text.replace("＝", "=").replace("^", "^")
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"\d+(?:\.\d+)?", "#N", text)
    text = _FORMULA_UNIT_RE.sub(lambda m: f"#U{m.group(1).lower()}#", text)
    text = re.sub(r"(?<!#U)[a-zA-Zα-ωΑ-Ωηρ](?:_\{?[^{}]+\}?|\^\{?[^{}]+\}?)*", "#V", text)
    text = re.sub(r"[一-鿿]{1,8}(?==|[+\-*/])", "#C", text)
    return text


def _formula_candidates(text: str) -> list[str]:
    candidates = [match.group(0) for match in _MATH_MARKER_RE.finditer(text)]
    candidates.extend(match.group(0) for match in _TEXT_FORMULA_RE.finditer(text))
    return candidates


def _formula_signature(question: dict[str, Any] | str) -> str:
    """提取题干/选项中的 LaTeX、math 标记或普通文本公式并生成稳定签名。"""
    if isinstance(question, dict):
        chunks = [_clean_text(question.get("stem")), _clean_text(question.get("raw_text")), _clean_text(question.get("analysis"))]
        for option in question.get("options") or []:
            if isinstance(option, dict):
                chunks.append(_clean_text(option.get("text")))
            else:
                chunks.append(_clean_text(option))
        text = "\n".join(chunks)
    else:
        text = _clean_text(question)

    formulas = [_normalize_formula_text(candidate) for candidate in _formula_candidates(text)]
    formulas = [formula for formula in formulas if len(formula) >= 3 and any(op in formula for op in "=+-*/^\\")]
    if not formulas:
        return ""
    payload = "|".join(sorted(set(formulas)))
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def _stem_image_hashes(question: dict[str, Any]) -> set[str]:
    refs = question.get("image_refs") or {}
    stem_refs = refs.get("stem") if isinstance(refs, dict) else []
    hashes: set[str] = set()
    for ref in stem_refs or []:
        if isinstance(ref, dict):
            value = _clean_text(ref.get("sha256"))
            if value:
                hashes.add(value)
    return hashes


def _image_context_signature(question: dict[str, Any]) -> str:
    """为含图题生成签名：优先使用真实图片 hash，缺失时回退到上下文。"""
    stem_hashes = _stem_image_hashes(question)
    if stem_hashes:
        return "hash:" + hashlib.md5("|".join(sorted(stem_hashes)).encode("utf-8")).hexdigest()

    image_parts: list[str] = []

    def add_image(value: Any) -> None:
        if isinstance(value, dict):
            image_parts.append("|".join(_clean_text(value.get(key)) for key in ("url", "width", "height", "sha256") if value.get(key)))
        elif value:
            image_parts.append(_clean_text(value))

    for img in question.get("stem_images") or question.get("images") or []:
        add_image(img)
    option_images = question.get("option_images") or {}
    if isinstance(option_images, dict):
        for images in option_images.values():
            if isinstance(images, list):
                for img in images:
                    add_image(img)
            else:
                add_image(images)
    for option in question.get("options") or []:
        if isinstance(option, dict):
            images = option.get("images") or option.get("image") or []
            if isinstance(images, list):
                for img in images:
                    add_image(img)
            else:
                add_image(images)

    text = "\n".join(_question_text_chunks(question))
    has_image_marker = bool(_IMAGE_TOKEN_RE.search(text))
    if not image_parts and not has_image_marker:
        return ""

    context = _normalize_stem_for_dup(text)
    context = _normalize_numbers(context)
    context = re.sub(r"[A-H][.、．)]", "", context)
    payload = "|".join(sorted(image_parts)) + "||" + context[:160]
    return "ctx:" + hashlib.md5(payload.encode("utf-8")).hexdigest()


def _check_formula_signature_pair(
    question_a: dict[str, Any], question_b: dict[str, Any],
) -> tuple[bool, str]:
    sig_a = _formula_signature(question_a)
    sig_b = _formula_signature(question_b)
    if not sig_a or sig_a != sig_b:
        return False, ""
    return True, "公式指纹相同"


def _check_image_context_signature_pair(
    question_a: dict[str, Any], question_b: dict[str, Any],
) -> tuple[bool, str]:
    sig_a = _image_context_signature(question_a)
    sig_b = _image_context_signature(question_b)
    if not sig_a or sig_a != sig_b:
        return False, ""
    if sig_a.startswith("hash:"):
        return True, "图片素材哈希相同"
    return True, "图表/图片上下文签名相同"


# ====== 旧版模糊重复检测 ======
def check_fuzzy_duplicate_questions(questions: list[dict[str, Any]]) -> dict[int, list[dict[str, str]]]:
    """按题干相似度检查疑似重复题，精确重复由 check_duplicate_questions_structured 处理。"""
    result: dict[int, list[dict[str, str]]] = defaultdict(list)
    exact_keys = [_normalize_stem_for_duplicate(q.get("stem")) for q in questions]
    for left in range(len(questions)):
        for right in range(left + 1, len(questions)):
            if not exact_keys[left] or exact_keys[left] == exact_keys[right]:
                continue
            duplicate, score, reason = _is_duplicate_stem_pair(questions[left].get("stem"), questions[right].get("stem"))
            if not duplicate:
                continue
            left_no = _question_no(questions[left], left + 1)
            right_no = _question_no(questions[right], right + 1)
            issue_left = make_issue(
                "similar_question",
                "疑似重复题",
                WARNING,
                f"第{left_no}题与第{right_no}题题干疑似重复（{reason}，相似度={score:.0%}）。",
            )
            issue_right = make_issue(
                "similar_question",
                "疑似重复题",
                WARNING,
                f"第{right_no}题与第{left_no}题题干疑似重复（{reason}，相似度={score:.0%}）。",
            )
            result[left].append(issue_left)
            result[right].append(issue_right)
    return dict(result)


def check_question_number_sequence(
    questions: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], dict[int, list[dict[str, str]]]]:
    """检查题号是否按题目顺序从 1 连续递增。"""
    paper_issues: list[dict[str, str]] = []
    per_question: dict[int, list[dict[str, str]]] = defaultdict(list)
    actual = [_question_no(question) for question in questions]
    expected = list(range(1, len(questions) + 1))

    if actual != expected:
        actual_text = "、".join("?" if value is None else str(value) for value in actual)
        expected_text = "、".join(str(value) for value in expected)
        issue = make_issue(
            "non_continuous_numbering",
            "题号不连续",
            FAILED,
            f"题号应为 {expected_text}，实际为 {actual_text}。",
        )
        paper_issues.append(issue)
        for index, (actual_no, expected_no) in enumerate(zip(actual, expected)):
            if actual_no != expected_no:
                per_question[index].append(
                    make_issue(
                        "non_continuous_numbering",
                        "题号不连续",
                        FAILED,
                        f"当前位置应为第{expected_no}题，实际解析为第{actual_no or '?'}题。",
                    )
                )

    return paper_issues, dict(per_question)


def _build_plan_context_by_question_no(paper: Any) -> dict[int, dict[str, Any]]:
    context: dict[int, dict[str, Any]] = {}
    for row in getattr(paper, "blueprint_rows", []) or []:
        question_no = getattr(row, "question_no", None)
        if question_no is None:
            continue
        context[int(question_no)] = {
            "question_no": question_no,
            "question_type": getattr(row, "question_type", ""),
            "difficulty": getattr(row, "difficulty", ""),
            "content": getattr(row, "content", ""),
            "point_name": getattr(row, "point_name", ""),
            "knowledge_points": getattr(row, "knowledge_point", "") or getattr(row, "content", ""),
            "requirement": getattr(row, "requirement", ""),
            "intent": getattr(row, "intent", ""),
            "paper_type": getattr(row, "paper_type", ""),
            "paper_label": getattr(row, "paper_label", ""),
            "module": getattr(row, "module", ""),
            "topic": getattr(row, "topic", ""),
            "province": getattr(row, "province", ""),
            "raw": getattr(row, "raw", {}),
        }
    return context


def _difficulty_for_question(question: dict[str, Any], plan_context: dict[str, Any] | None = None) -> str:
    value = _clean_text(question.get("difficulty"))
    if value:
        return value
    if plan_context:
        return _clean_text(plan_context.get("difficulty"))
    return ""


def _answer_distribution_issues(questions: list[dict[str, Any]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    single_answers: list[str] = []
    single_indices: list[int] = []  # 记录每道单选的 index
    multi_answers: list[str] = []
    for idx, question in enumerate(questions):
        qtype = normalize_question_type(question.get("question_type"))
        answer = _normalize_choice_answer(question.get("answer"))
        if qtype == "单项选择题" and len(answer) == 1 and answer in "ABCD":
            single_answers.append(answer)
            single_indices.append(idx)
        elif qtype == "多项选择题" and len(answer) >= 2 and all(letter in "ABCD" for letter in answer):
            multi_answers.append(answer)

    if single_answers:
        dist = Counter(single_answers)
        dist_text = "，".join(f"{letter}={dist.get(letter, 0)}" for letter in "ABCD")
        max_count = max(dist.values())
        min_count = min(dist.get(letter, 0) for letter in "ABCD")
        total = len(single_answers)
        max_letter = sorted(dist, key=dist.get, reverse=True)[0]
        min_letter = sorted(dist, key=lambda l: dist.get(l, 0))[0]

        # 检查上限：任一选项占比 > 40%
        if total > 0 and max_count / total > 0.40:
            issues.append(make_issue(
                "single_answer_over_max", "答案分布失衡",
                FAILED,
                f"单选答案分布：{dist_text}；{max_letter} 占比 {max_count / total:.0%}，超过 40%。",
            ))
        # 检查下限：任一选项占比 < 15%（仅当该选项至少有 1 题且总数≥8）
        if total >= 8:
            for letter in "ABCD":
                cnt = dist.get(letter, 0)
                if cnt > 0 and cnt / total < 0.15:
                    issues.append(make_issue(
                        "single_answer_below_min", "答案分布失衡",
                        FAILED,
                        f"单选答案分布：{dist_text}；{letter} 占比 {cnt / total:.0%}，低于 15%。",
                    ))

        # 旧版 50% 阈值保留为 warning（兜底）
        if total > 5 and max_count > total * 0.5:
            # 已由上方 40% 规则覆盖 failed，不再重复报 warning
            if not any(i.get("code") == "single_answer_over_max" for i in issues):
                issues.append(make_issue(
                    "single_answer_distribution", "答案分布失衡",
                    WARNING,
                    f"单选答案分布：{dist_text}；{max_letter} 占比 {max_count / total:.0%}，超过 50%。",
                ))

    if multi_answers:
        dist = Counter(letter for answer in multi_answers for letter in answer)
        total = len(multi_answers)
        dist_text = "，".join(f"{letter}={dist.get(letter, 0)}" for letter in "ABCD")
        max_count = max(dist.get(letter, 0) for letter in "ABCD")
        min_count = min(dist.get(letter, 0) for letter in "ABCD")
        if total > 2 and (max_count == total or min_count == 0):
            issues.append(make_issue("multi_answer_distribution", "多选答案分布不均", WARNING, f"多选答案分布：{dist_text}；存在选项总是或从未作为正确项。"))

    return issues


def _difficulty_issues(
    questions: list[dict[str, Any]], context_by_no: dict[int, dict[str, Any]]
) -> tuple[list[dict[str, str]], dict[int, list[dict[str, str]]]]:
    paper_issues: list[dict[str, str]] = []
    per_question: dict[int, list[dict[str, str]]] = defaultdict(list)
    return paper_issues, dict(per_question)


def check_planned_question_count(
    questions: list[dict[str, Any]],
    planned_total: int,
    score_multiplier: int = 1,
) -> list[dict[str, str]]:
    """检查整卷题量是否符合规划表要求（含半量规则）。"""
    actual = len(questions)
    issues: list[dict[str, str]] = []
    if planned_total <= 0:
        return issues
    if score_multiplier == 2:
        expected = max(1, planned_total // 2)
        if actual != expected:
            issues.append(make_issue(
                "question_count_mismatch", "题量与规划不符",
                FAILED,
                f"触发半量规则（题源<40%），应为 {planned_total}÷2={expected} 题，实际 {actual} 题。",
            ))
    else:
        if actual != planned_total:
            issues.append(make_issue(
                "question_count_mismatch", "题量与规划不符",
                FAILED,
                f"规划表要求 {planned_total} 题，实际 {actual} 题。",
            ))
    return issues


def _status_from_issues(issues: list[dict[str, str]]) -> str:
    if any(issue.get("severity") == FAILED for issue in issues):
        return FAILED
    if issues:
        return WARNING
    return PASSED


def _dedupe_issues(issues: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for issue in issues:
        key = (issue.get("code", ""), issue.get("name", ""), issue.get("message", ""))
        if key in seen:
            continue
        result.append(issue)
        seen.add(key)
    return result


def _stem_preview(stem: Any, limit: int = 80) -> str:
    text = re.sub(r"\s+", " ", _clean_text(stem))
    return text if len(text) <= limit else text[:limit] + "…"


def run_quality_checks(
    paper: Any,
    questions: list[dict[str, Any]],
    planned_total: int = 0,
    score_multiplier: int = 1,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """对整卷结构化题目执行质检。"""
    context_by_no = _build_plan_context_by_question_no(paper)
    paper_issues, numbering_issues = check_question_number_sequence(questions)
    duplicate_issues = check_duplicate_questions_structured(questions)
    fuzzy_duplicate_issues = check_fuzzy_duplicate_questions(questions)
    difficulty_paper_issues, difficulty_question_issues = _difficulty_issues(questions, context_by_no)
    paper_issues.extend(_answer_distribution_issues(questions))
    paper_issues.extend(difficulty_paper_issues)
    paper_issues.extend(check_planned_question_count(questions, planned_total, score_multiplier))

    paper_issues = _dedupe_issues(paper_issues)

    question_reports: list[dict[str, Any]] = []
    for index, question in enumerate(questions):
        question_no = _question_no(question, index + 1)
        plan_context = context_by_no.get(question_no or -1)
        issues: list[dict[str, str]] = []
        issues.extend(check_question_structured(question, plan_context))
        issues.extend(duplicate_issues.get(index, []))
        issues.extend(fuzzy_duplicate_issues.get(index, []))
        issues.extend(numbering_issues.get(index, []))
        issues.extend(difficulty_question_issues.get(index, []))

        issues = _dedupe_issues(issues)
        expected_type = normalize_question_type(plan_context.get("question_type")) if plan_context else ""
        question_reports.append(
            {
                "index": index,
                "question_no": question_no,
                "question_type": normalize_question_type(question.get("question_type")),
                "expected_type": expected_type,
                "status": _status_from_issues(issues),
                "issues": issues,
                "stem_preview": _stem_preview(question.get("stem")),
                "source_path": _clean_text(question.get("source_path")),
            }
        )

    return question_reports, paper_issues
