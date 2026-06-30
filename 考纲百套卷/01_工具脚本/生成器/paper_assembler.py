"""将结构化题目重新组装为解析版试卷文本。"""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
import re
from typing import Any

from .paths import FINAL_TEXT_DIR

CN_NUMBERS = "一二三四五六七八九十"
from .question_types import TYPE_ORDER as QUESTION_TYPE_ORDER, normalize_question_type, type_display_name


def _safe_output_name(text: Any) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", str(text or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned or "未命名"


def _paper_output_group(paper: Any) -> str:
    meta = getattr(paper, "meta", None)
    province = getattr(meta, "province", "") if meta else ""
    exam_category = getattr(meta, "exam_category", "") if meta else ""
    return _safe_output_name(" ".join(part for part in [province, exam_category] if part).strip() or "未分类")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_heading(heading: Any, qtype: Any, index: int) -> str:
    text = _clean_text(heading)
    # 标准章节标题（如"一、单项选择题"）按实际分组序号重编号
    if text and re.match(r'^[一二三四五六七八九十]、', text):
        name = type_display_name(normalize_question_type(qtype)) or "其他题"
        number = CN_NUMBERS[index] if 0 <= index < len(CN_NUMBERS) else str(index + 1)
        return f"{number}、{name}"
    if text:
        return text
    name = type_display_name(normalize_question_type(qtype)) or "其他题"
    number = CN_NUMBERS[index] if 0 <= index < len(CN_NUMBERS) else str(index + 1)
    return f"{number}、{name}"


def _summary_number(value: Any) -> int | None:
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    if not match:
        return None
    number = float(match.group(0))
    return int(number) if number.is_integer() else number


def _format_section_score_summary(count: Any, score_per: Any, subtotal: Any) -> str:
    count_no = _summary_number(count)
    score_no = _summary_number(score_per)
    subtotal_no = _summary_number(subtotal)
    if count_no is None or score_no is None:
        return ""
    if subtotal_no is None:
        subtotal_no = count_no * score_no
    return f"本大题共{count_no}小题，每题{score_no}分，共{subtotal_no}分"


def _question_type_summaries(paper: Any) -> dict[str, dict[str, Any]]:
    meta = getattr(paper, "meta", None)
    summaries = getattr(meta, "question_type_summaries", {}) or {}
    course = _clean_text(getattr(paper, "module", ""))
    rows = summaries.get(course) or []
    return {normalize_question_type(row.get("type")): row for row in rows}


def _heading_with_score_summary(heading: str, qtype: Any, items: list[dict[str, Any]], paper: Any) -> str:
    if re.search(r"本大题共\d+小题，每题\d+分，共\d+分", heading):
        return heading

    summary = _question_type_summaries(paper).get(normalize_question_type(qtype))
    if summary:
        score_text = _format_section_score_summary(summary.get("count"), summary.get("score_per"), summary.get("subtotal"))
        if score_text:
            return f"{heading}（{score_text}）"

    score_per = _summary_number(items[0].get("score_per") if items else None)
    if score_per is not None:
        subtotal = len(items) * score_per
        return f"{heading}（本大题共{len(items)}小题，每题{score_per}分，共{subtotal}分）"
    return heading


def _heading_key(question: dict[str, Any]) -> tuple[str, str]:
    heading = _clean_text(question.get("heading"))
    qtype = normalize_question_type(question.get("question_type")) or "其他题"
    # 多项选择题但答案为单字母 → 实际是单选题（AI 误标）
    if qtype == "多项选择题" and question.get("answer", "").strip() in {"A", "B", "C", "D", "√", "×"}:
        qtype = "单项选择题"
    # heading 统一清空：中文数字章节标题 / 裸题型名 → 归并到空 heading
    if heading and (
        re.match(r'^[一二三四五六七八九十]、', heading) or
        normalize_question_type(heading)
    ):
        heading = ""
    return heading, qtype


def _ordered_groups(questions: list[dict[str, Any]]) -> OrderedDict[tuple[str, str], list[dict[str, Any]]]:
    groups: OrderedDict[tuple[str, str], list[dict[str, Any]]] = OrderedDict()
    for question in questions:
        groups.setdefault(_heading_key(question), []).append(question)

    # 全部 heading 都是中文数字开头（如一、二、）的标准章节标题 → 按题型排序
    all_standard = all(key[0] and re.match(r'^[一二三四五六七八九十]、', key[0]) for key in groups)
    if any(key[0] for key in groups) and not all_standard:
        return groups

    ordered: OrderedDict[tuple[str, str], list[dict[str, Any]]] = OrderedDict()
    order = {qtype: idx for idx, qtype in enumerate(QUESTION_TYPE_ORDER)}
    for key, items in sorted(groups.items(), key=lambda pair: order.get(pair[0][1], len(order))):
        ordered[key] = items
    return ordered


def _option_lines(options: Any) -> list[str]:
    if isinstance(options, dict):
        options = [f"{label}. {_clean_text(options[label])}" for label in sorted(options) if _clean_text(options[label])]

    result: list[str] = []
    normalized: list[str] = []
    for option in options or []:
        text = _clean_text(option)
        if not text:
            continue
        match = re.match(r"^([A-H])\s*[.、．)]\s*(.+)", text, re.I)
        if match:
            normalized.append(f"{match.group(1).upper()}. {match.group(2).strip()}")
        else:
            normalized.append(text)

    # 选项布局：≤5字全单行，其他两两配对，用 Tab 分隔使 DOCX 表格可多列渲染
    if len(normalized) == 4 and all(len(opt) <= 5 for opt in normalized):
        result.append("\t\t".join(normalized))
    else:
        for i in range(0, len(normalized), 2):
            if i + 1 < len(normalized):
                result.append(f"{normalized[i]}\t\t{normalized[i + 1]}")
            else:
                result.append(normalized[i])
    return result


def _strip_image_placeholders(value: Any) -> str:
    return re.sub(r"\s*(?:\[图片\]|【图片】)\s*", "", _clean_text(value)).strip()


def _strip_leading_question_numbers(text: Any) -> str:
    cleaned = _clean_text(text)
    while True:
        stripped = re.sub(r"^\s*\d+\s*[.、．)）]\s*", "", cleaned).strip()
        if stripped == cleaned:
            return cleaned
        cleaned = stripped


def _stem_from_raw_text(raw_text: Any) -> str:
    for line in str(raw_text or "").splitlines():
        cleaned = _strip_image_placeholders(line)
        if not cleaned or cleaned.startswith(("【答案】", "【解析】", "【详解】", "【分析】")):
            continue
        return _strip_leading_question_numbers(cleaned)
    return ""


def _question_stem(question: dict[str, Any]) -> str:
    stem = _strip_image_placeholders(question.get("stem"))
    if not stem:
        stem = _stem_from_raw_text(question.get("raw_text"))
    return _strip_leading_question_numbers(stem)


def _analysis_text(value: Any, stem: Any = "") -> str:
    text = _strip_image_placeholders(value)
    stem_text = _strip_leading_question_numbers(_strip_image_placeholders(stem))
    if stem_text and text.startswith(stem_text):
        text = text[len(stem_text):].strip()
    while True:
        cleaned = re.sub(r"^【(?:解析|详解|分析)】\s*", "", text).strip()
        if cleaned == text:
            return text
        text = cleaned


_STUB_ANALYSIS_RE = re.compile(r"^(?:略|无|—|－－|--|\.|。)?\s*$")


def _has_visual_object(question: dict[str, Any]) -> bool:
    image_refs = question.get("image_refs") if isinstance(question.get("image_refs"), dict) else {}
    return bool(
        question.get("protected_original_docx_block")
        or any((question.get("image_flags") or {}).values())
        or any(image_refs.get(part) for part in ("stem", "answer", "analysis", "options"))
    )


def _should_emit_analysis(question: dict[str, Any], analysis: str) -> bool:
    text = str(analysis or "").strip()
    if not text or _STUB_ANALYSIS_RE.match(text):
        return False
    if _has_visual_object(question) and len(text) <= 10:
        return False
    return True


def _question_lines(question: dict[str, Any], display_no: int) -> list[str]:
    stem = _question_stem(question)
    lines = [f"{display_no}. {stem}".rstrip()]
    lines.extend(_option_lines(question.get("options")))
    lines.append(f"【答案】{_strip_image_placeholders(question.get('answer'))}")
    analysis = _analysis_text(question.get('analysis'), stem)
    if _should_emit_analysis(question, analysis):
        lines.append(f"【解析】{analysis}")
    return lines


def assemble_analysis_paper_text(questions: list[dict[str, Any]], paper: Any = None) -> str:
    """将题目结构确定性组装成解析版试卷文本。"""
    groups = _ordered_groups(questions)
    lines: list[str] = []
    display_no = 1
    prev_heading = ""
    for group_index, ((heading, qtype), items) in enumerate(groups.items()):
        section_heading = _normalize_heading(heading, qtype, group_index)
        # 跳过与前一组相同的标题（如 单选题 中的 多项选择题 误标为同 heading）
        if section_heading == prev_heading:
            # 合并到上一组，不重复输出标题
            pass
        else:
            if lines:
                lines.append("")
            lines.append(_heading_with_score_summary(section_heading, qtype, items, paper))
            lines.append("")
        prev_heading = section_heading
        for question in items:
            lines.extend(_question_lines(question, display_no))
            lines.append("")
            display_no += 1
    return "\n".join(lines).strip() + "\n"


def write_analysis_text(paper: Any, questions: list[dict[str, Any]], output_dir: str | Path | None = None) -> Path:
    """写出解析版原始文本，供 DOCX 生成使用。"""
    root = Path(output_dir) if output_dir else FINAL_TEXT_DIR
    output_path = root / _paper_output_group(paper) / f"{getattr(paper, 'paper_label', '第x卷')}_解析版.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(assemble_analysis_paper_text(questions, paper), encoding="utf-8")
    return output_path
