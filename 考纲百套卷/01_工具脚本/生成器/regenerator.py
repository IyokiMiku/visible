"""不合格题目修复与重生成模块。"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import random
import re
from typing import Any, Callable

from .prompts import build_regenerate_question_prompt
from .question_types import normalize_question_type


@dataclass
class RegenerationResult:
    """题目修复结果。"""

    original: dict[str, Any]
    regenerated: dict[str, Any] | None
    issues: list[str]
    status: str
    message: str = ""


def needs_regeneration(issues: list[str]) -> bool:
    """判断质检问题是否需要 AI 修复或重生成。"""
    hard_keywords = [
        "缺答案",
        "缺解析",
        "解析过短",
        "乱码",
        "选项缺失",
        "选项长度失衡",
        "废选项",
        "答案格式错误",
        "多选题全选",
        "解析含禁用符号",
        "解析缺少计算过程",
        "知识点不匹配",
        "重复",
        "题型错误",
        "答案自暴露",
        "答案分布失衡",
    ]
    text = "\n".join(issues)
    return any(keyword in text for keyword in hard_keywords)


def fix_answer_distribution(questions: list[dict[str, Any]], max_swaps: int = 5) -> bool:
    """本地修复答案分布失衡：将答案频率最高的选项与频率最低的选项互换。

    循环执行，每次互换一对选项，直到分布满足要求（≤40% 且 ≥15%）或达到 max_swaps。

    Returns:
        True 如果执行了至少一次互换
    """
    fixed_any = False

    for _ in range(max_swaps):
        # 1. 统计单选答案分布
        single_qa: list[tuple[int, dict[str, Any], str]] = []
        for i, q in enumerate(questions):
            qt = normalize_question_type(q.get("question_type") or q.get("_question_type") or "")
            ans = str(q.get("answer", "")).strip().upper()
            if qt == "单项选择题" and len(ans) == 1 and ans in "ABCD" and not q.get("protected_original_docx_block"):
                single_qa.append((i, q, ans))

        if not single_qa:
            break

        dist = Counter(ans for _, _, ans in single_qa)
        total = len(single_qa)

        max_letter = max("ABCD", key=lambda l: dist.get(l, 0))
        min_letter = min("ABCD", key=lambda l: dist[l] if dist[l] > 0 else float("inf"))
        max_cnt = dist.get(max_letter, 0)
        min_cnt = dist.get(min_letter, 0)

        # 检查是否需要修复
        over = max_cnt / total > 0.40 if total > 0 else False
        under = any(
            dist.get(l, 0) > 0 and dist[l] / total < 0.15
            for l in "ABCD"
        ) if total >= 8 else False

        if not over and not under:
            break

        # 2. 找到答案为 max_letter 的题目，随机选一题
        candidates = [(i, q, a) for i, q, a in single_qa if a == max_letter]
        if not candidates:
            break

        fix_idx, fix_q, _fix_ans = random.choice(candidates)

        # 3. 找出 max_letter 和 min_letter 选项索引并互换内容
        options = list(fix_q.get("options", []))
        if len(options) < 2:
            continue

        opt_max_idx = opt_min_idx = -1
        for oi, opt_text in enumerate(options):
            m = re.match(r"([A-H])[.、．)]", str(opt_text).strip(), re.I)
            if m:
                label = m.group(1).upper()
                if label == max_letter:
                    opt_max_idx = oi
                elif label == min_letter:
                    opt_min_idx = oi

        if opt_max_idx == -1 or opt_min_idx == -1:
            continue

        max_text = re.sub(r"^[A-H][.、．)]\s*", "", str(options[opt_max_idx]).strip(), flags=re.I)
        min_text = re.sub(r"^[A-H][.、．)]\s*", "", str(options[opt_min_idx]).strip(), flags=re.I)
        options[opt_max_idx] = f"{max_letter}. {min_text}"
        options[opt_min_idx] = f"{min_letter}. {max_text}"
        fix_q["options"] = options
        fix_q["answer"] = min_letter
        fixed_any = True

    return fixed_any


def _strip_json_fence(text: str) -> str:
    text = str(text or "").strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.S | re.I)
    return fence.group(1).strip() if fence else text


def parse_regeneration_output(output: dict[str, Any] | str) -> dict[str, Any] | None:
    """从模型输出中提取单题 JSON 对象。"""
    if isinstance(output, dict):
        data = output
    else:
        text = _strip_json_fence(str(output or ""))
        candidates = [text]
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            candidates.append(text[start : end + 1])

        data = None
        for candidate in candidates:
            try:
                data = json.loads(candidate)
                break
            except json.JSONDecodeError:
                continue
        if not isinstance(data, dict):
            return None

    if isinstance(data.get("question"), dict):
        data = data["question"]
    if isinstance(data.get("regenerated"), dict):
        data = data["regenerated"]
    return data if isinstance(data, dict) else None


def _normalize_options(options: Any) -> list[str]:
    if isinstance(options, dict):
        result = []
        for label in sorted(options):
            value = str(options[label] or "").strip()
            if value:
                result.append(f"{str(label).upper()[:1]}. {value}")
        return result
    result = []
    for option in options or []:
        text = str(option or "").strip()
        if text:
            result.append(text)
    return result


_IMMUTABLE_DOCX_METADATA_KEYS = (
    "source_docx_path",
    "source_path",
    "source_paragraph_indices",
    "source_body_indices",
    "original_docx_body_indices",
    "original_docx_body_range",
    "stem_paragraph_indices",
    "answer_paragraph_indices",
    "analysis_paragraph_indices",
    "image_flags",
    "image_refs",
    "protected_original_docx_block",
    "protection_reason",
    "has_original_docx_images",
    "original_docx_image_refs",
)


def _question_has_original_docx_images(question: dict[str, Any]) -> bool:
    if question.get("has_original_docx_images"):
        return True
    refs = question.get("image_refs") or {}
    return any(refs.get(part) for part in ("stem", "answer", "analysis"))


def _preserve_original_docx_metadata(original: dict[str, Any], question: dict[str, Any]) -> None:
    for key in _IMMUTABLE_DOCX_METADATA_KEYS:
        if key in original:
            question[key] = original[key]
    if _question_has_original_docx_images(original):
        question["has_original_docx_images"] = True


def normalize_regenerated_question(original: dict[str, Any], repaired: dict[str, Any]) -> dict[str, Any]:
    """补齐修复题字段，保证可替换到 questions 列表。"""
    question = dict(original)
    for key in ["question_type", "stem", "answer", "analysis", "knowledge_points", "difficulty", "raw_text"]:
        if key in repaired and repaired[key] not in (None, ""):
            question[key] = repaired[key]
    if "options" in repaired:
        question["options"] = _normalize_options(repaired.get("options"))

    question["question_no"] = original.get("question_no")
    question["heading"] = repaired.get("heading") or original.get("heading", "")
    question["status"] = "repaired"
    question["issues"] = []
    question["issue_details"] = []
    question["fix_type"] = repaired.get("fix_type") or ("text_only_preserve_images" if _question_has_original_docx_images(original) else "auto")
    _preserve_original_docx_metadata(original, question)
    _normalize_judge_answer(question)
    return question


def _normalize_judge_answer(question: dict[str, Any]) -> None:
    """判断题答案统一为 √ / ×。"""
    qt = str(question.get("question_type", "")).strip()
    if "判断" not in qt:
        return
    ans = str(question.get("answer", "")).strip().upper()
    mapping = {"A": "√", "B": "×", "正确": "√", "对": "√", "TRUE": "√",
               "错误": "×", "错": "×", "FALSE": "×", "√": "√", "×": "×"}
    if ans in mapping:
        question["answer"] = mapping[ans]


def normalize_all_judge_answers(questions: list[dict[str, Any]]) -> None:
    """批量规范化判断题答案，并修正题型错误（有A-D选项→单项选择题）。"""
    import re
    for q in questions:
        qtype = normalize_question_type(q.get("_question_type") or q.get("question_type") or "")
        if qtype == "判断题":
            options = q.get("options") or []
            if isinstance(options, str):
                options = re.split(r"(?=[A-H][.、．)])", options)
                options = [o.strip() for o in options if o.strip()]
            if isinstance(options, list) and len(options) >= 4:
                # 判断题却有A-D选项 → 修正为单项选择题
                labels = [re.match(r"([A-D])[.、．)]", str(o), re.I) for o in options[:4]]
                if all(m and m.group(1) for m in labels):
                    q["_question_type"] = "单项选择题"
                    q["question_type"] = "单项选择题"
                    print(f"  → 自动修正题型：第{q.get('question_no','?')}题 判断题→单项选择题（检测到A-D选项）")
                    continue
        _normalize_judge_answer(q)


def regenerate_question(
    question: dict[str, Any],
    issues: list[str],
    plan_context: dict[str, Any],
    spec_text: str,
    llm_call: Callable[[str], dict[str, Any] | str],
) -> RegenerationResult:
    """调用外部模型接口修复/重生成单题。

    llm_call 由主流程注入，可复用 config_io.py 中的模型调用能力。
    """
    if question.get("protected_original_docx_block") and not _question_has_original_docx_images(question):
        return RegenerationResult(question, question, issues, "skipped", "题目含受保护对象但缺少可复制图片元数据，跳过自动重生成")

    if not needs_regeneration(issues):
        return RegenerationResult(question, question, issues, "skipped", "质检问题不需要重生成")

    prompt = build_regenerate_question_prompt(question, issues, plan_context, spec_text)
    MAX_RETRIES = 2
    for attempt in range(MAX_RETRIES + 1):  # 共 3 次尝试（首次 + 2 次重试）
        try:
            output = llm_call(prompt)
        except Exception as exc:  # pragma: no cover
            if attempt < MAX_RETRIES:
                continue
            return RegenerationResult(question, None, issues, "failed", str(exc))

        parsed = parse_regeneration_output(output)
        if parsed:
            return RegenerationResult(question, normalize_regenerated_question(question, parsed), issues, "success")

        if attempt < MAX_RETRIES:
            print(f"  第{question.get('question_no','?')}题 JSON 解析失败，重试第 {attempt + 1} 次...")

    return RegenerationResult(question, None, issues, "failed", f"模型输出经 {MAX_RETRIES + 1} 次尝试仍无法解析为题目 JSON")
