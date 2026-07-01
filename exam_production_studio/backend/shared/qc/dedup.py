"""题干查重算法（移植自一课一练 check.py）。

对两道题的题干做去模板归一化后，用「最长连续公共片段 + 核心关键词相似度 +
去模板字符集合相似度」三路判定是否疑似重复。studio 已有结构化题干，直接传文本即可。
"""
from __future__ import annotations

import re
import string

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


_EXACT_PUNCT = string.punctuation + "，。、；：？！“”‘’（）【】《》…—·"


def normalize_stem_exact(text: str) -> str:
    """精确重复归一化：仅去空白与标点，保留全部文字（用于判定完全相同题干）。"""
    t = str(text or "")
    t = re.sub(r"\s+", "", t)
    return t.translate(str.maketrans("", "", _EXACT_PUNCT))


def _normalize_stem_for_dup(text: str) -> str:
    """去掉出题模板词和标点，保留核心知识词用于模糊查重。"""
    if not text:
        return ""
    text = re.sub(r"^\d+[\.．、]\s*", "", text)
    text = re.sub(r"（\s*）", "", text)
    text = re.sub(r"[，,。；;：:？！?、（）()《》<>\[\]【】\s]", "", text)
    for pattern in _TEMPLATE_PATTERNS:
        text = re.sub(pattern, "", text)
    return text.strip()


def _longest_common_substring_len(text_a: str, text_b: str) -> int:
    """最长连续公共片段长度。"""
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


def _keyword_units(text: str) -> set:
    """用去模板后的连续二字片段近似表示核心关键词。"""
    text = _normalize_stem_for_dup(text)
    if len(text) < 2:
        return {text} if text else set()
    units = {text[i:i + 2] for i in range(len(text) - 1)}
    return {u for u in units if u and u not in _STOP_WORDS}


def _char_set_similarity(text_a: str, text_b: str) -> float:
    """字符集合相似度：共同字符数 ÷ 较短文本字符数。"""
    if not text_a or not text_b:
        return 0.0
    set_a, set_b = set(text_a), set(text_b)
    shorter = min(len(set_a), len(set_b))
    if shorter == 0:
        return 0.0
    return len(set_a & set_b) / shorter


def _keyword_similarity(text_a: str, text_b: str) -> float:
    """核心关键词相似度：共同关键词片段数 ÷ 较少关键词片段数。"""
    units_a, units_b = _keyword_units(text_a), _keyword_units(text_b)
    shorter = min(len(units_a), len(units_b))
    if shorter == 0:
        return 0.0
    return len(units_a & units_b) / shorter


def is_duplicate_stem_pair(text_a: str, text_b: str) -> tuple[bool, float, str]:
    """判断两道题题干是否重复：连续短语 + 关键词相似度 + 去模板字符相似度。"""
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
