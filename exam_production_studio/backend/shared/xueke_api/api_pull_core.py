"""学科网拉题核心（接入：源 学科网API拉题移植版/api_pull_core.py 去硬编码）。

改造：
- 修复失效 import（`学科网API拉题移植版.*` → 同包相对导入）。
- 去除本地题库文件读写/错题索引/CLI；只负责"按 课程/知识点/题型 拉够候选题并返回内存列表"。
"""
from __future__ import annotations

import random
import re
from typing import Any, Sequence

from .html_content_converter import convert_answer_html
from .query_questions import build_payload, query as api_query

# 流程题型 → API section_type；倍率沿用原工具
SECTION_TYPE_MAP = {
    "choice": {"multiplier": 3, "mode": "random"},
    "fill": {"multiplier": 3, "mode": "random"},
    "judge": {"multiplier": 3, "mode": "random"},
    "short_answer": {"multiplier": 5, "mode": "random"},
    "calc": {"multiplier": 5, "mode": "scan"},
}

REJECT_ANSWER_PATTERNS = [re.compile(r"^\s*略\s*$"), re.compile(r"^\s*$"), re.compile(r"^<[^>]+>\s*$")]


def clean_html(html_text: Any) -> str:
    if not html_text:
        return ""
    text = str(html_text)
    text = re.sub(r"<img[^>]*>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = (text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))
    return re.sub(r"\s+", " ", text).strip()


def has_img(html_text: Any) -> bool:
    return bool(html_text and re.search(r"<img\b", str(html_text), flags=re.I))


def validate_question(q: dict[str, Any], section_type: str) -> tuple[bool, str]:
    if q.get("status") is not None and q.get("status") != 1:
        return False, "status != 1"
    if not q.get("kpointIds"):
        return False, "kpointIds 为空"
    if q.get("difficulty") is None:
        return False, "difficulty 缺失"
    answer_raw = q.get("answer", "") or ""
    if isinstance(answer_raw, dict):
        answer_raw = answer_raw.get("stem", "") or ""
    answer_text = convert_answer_html(answer_raw).strip() or clean_html(answer_raw)
    if any(p.match(answer_text) for p in REJECT_ANSWER_PATTERNS) and not has_img(answer_raw):
        return False, f"答案无效: {answer_text[:20]!r}"
    stem_text = clean_html(q.get("stem", "") or "")
    if len(stem_text) < 2 and not has_img(q.get("stem", "") or ""):
        return False, "题干极短且无图"
    if section_type == "choice" and not re.match(r"^[A-D]\s*$", answer_text):
        return False, f"选择题答案非 A-D: {answer_text[:20]!r}"
    return True, ""


def pull_page(
    *, course_id: int | None, kpoint_ids: Sequence[Any] | None, type_ids: Sequence[Any],
    page_index: int, page_size: int, cookie: str, app_key: str, sign: str,
) -> list[dict[str, Any]]:
    payload = build_payload(
        course_id=course_id, kpoint_ids=list(kpoint_ids) if kpoint_ids else None,
        type_ids=list(type_ids), page_size=page_size, page_index=page_index, bank_ids=None,
    )
    result = api_query(payload, app_key=app_key, sign=sign, cookie=cookie)
    if result is None or not result.get("valid"):
        err = result.get("error", "无响应") if isinstance(result, dict) else "无响应"
        raise RuntimeError(f"学科网 API 调用失败: {err}")
    return result.get("result", {}).get("list", []) or []


def _dedup_extend(collected: list, existing_ids: set, rows: list) -> list:
    new_rows = [q for q in rows if str(q.get("questionId", "")) not in existing_ids]
    for q in new_rows:
        existing_ids.add(str(q.get("questionId", "")))
    collected.extend(new_rows)
    return new_rows


def pull_questions(
    *, course_id: int | None, kpoint_ids: Sequence[Any] | None, type_ids: Sequence[Any],
    section_type: str, needed: int, cookie: str, app_key: str, sign: str,
) -> list[dict[str, Any]]:
    """为单一题型拉够候选题（按倍率多拉），返回校验通过的题目行列表。"""
    cfg = SECTION_TYPE_MAP.get(section_type, SECTION_TYPE_MAP["choice"])
    target = max(needed * cfg["multiplier"], needed)
    page_size = 100 if cfg["mode"] == "scan" else min(max(target, 60), 100)
    existing_ids: set[str] = set()
    collected: list[dict[str, Any]] = []

    if cfg["mode"] == "scan":
        empty = 0
        for page in range(1, 21):
            rows = pull_page(course_id=course_id, kpoint_ids=kpoint_ids, type_ids=type_ids,
                             page_index=page, page_size=page_size, cookie=cookie, app_key=app_key, sign=sign)
            if not rows:
                empty += 1
                if empty >= 2:
                    break
                continue
            empty = 0
            if not _dedup_extend(collected, existing_ids, rows):
                break
            if len(rows) < page_size or len(collected) >= target:
                break
    else:
        tried: set[int] = set()
        for lo, hi in ((1, 20), (1, 11), (1, 6)):
            cands = [p for p in range(lo, hi + 1) if p not in tried]
            for page in random.sample(cands, min(3, len(cands))):
                tried.add(page)
                rows = pull_page(course_id=course_id, kpoint_ids=kpoint_ids, type_ids=type_ids,
                                 page_index=page, page_size=page_size, cookie=cookie, app_key=app_key, sign=sign)
                _dedup_extend(collected, existing_ids, rows)
                if len(collected) >= target:
                    break
            if len(collected) >= target:
                break

    valid = [q for q in collected if validate_question(q, section_type)[0]]
    return valid[:target]
