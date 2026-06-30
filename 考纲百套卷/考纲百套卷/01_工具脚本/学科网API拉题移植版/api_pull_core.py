#!/usr/bin/env python3
"""
学科网 API 拉题核心流程（考纲百套卷独立版）

定位：
- 只负责“按课程 / 知识点 / 题型从 API 拉题、过滤、入本地题库”。
- 不生成试卷、不调用 paper_builder、不接入考纲百套卷主流程。
- 以后要融入流程时，可把本文件中的 pull_for_section / pull_for_plan 迁回生成器。

依赖：仅 Python 标准库 + 同目录 query_questions.py / html_content_converter.py。

典型用法：
  export XKW_COOKIE='浏览器里复制出的 Cookie'
  python api_pull_core.py \
    --course-id 1093 \
    --kpoint-ids 123456,234567 \
    --type-ids 1000001 \
    --section-type choice \
    --needed 20 \
    --bank-dir ./bank/机械制图

输出：
- 本地题库文件：choice.json / fill.json / judge.json / short.json / comp.json
- JSON 为 flat array，按 questionId 去重追加。
"""

from __future__ import annotations

import argparse
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from 学科网API拉题移植版.html_content_converter import convert_answer_html
from 学科网API拉题移植版.query_questions import (
    build_payload,
    query as api_query,
    DEFAULT_APP_KEY,
    DEFAULT_SIGN,
    DEFAULT_COOKIE,
    print_request_snapshot,
    print_response_diagnostics,
)


BANK_FILES = {
    "single_choice": "choice.json",
    "fill_blank": "fill.json",
    "judge": "judge.json",
    "short_answer": "short.json",
    "comprehensive": "comp.json",
}

SECTION_TYPE_MAP = {
    "choice": {"bank_key": "single_choice", "question_type": "single_choice"},
    "fill": {"bank_key": "fill_blank", "question_type": "fill_blank"},
    "judge": {"bank_key": "judge", "question_type": "judge"},
    "short_answer": {"bank_key": "short_answer", "question_type": "short_answer"},
    "calc": {"bank_key": "comprehensive", "question_type": "comprehensive"},
}

REJECT_ANSWER_PATTERNS = [
    re.compile(r"^\s*略\s*$"),
    re.compile(r"^\s*$"),
    re.compile(r"^<[^>]+>\s*$"),
]

JUDGE_STEM_PATTERN = re.compile(r"[（(]\s*[）)]\s*$")
MCQ_ANSWER_PATTERN = re.compile(r"^[A-D]\s*$")


def parse_ids(raw: Optional[str]) -> Optional[List[Any]]:
    """把 1,2,abc 解析为 [1, 2, 'abc']。"""
    if not raw:
        return None
    result: List[Any] = []
    for part in raw.split(','):
        item = part.strip()
        if not item:
            continue
        result.append(int(item) if item.isdigit() else item)
    return result or None


def clean_html(html_text: Any) -> str:
    """轻量纯文本清理，用于校验和题型识别。"""
    if not html_text:
        return ""
    text = str(html_text)
    text = re.sub(r"<img[^>]*>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = (text.replace("&nbsp;", " ")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&amp;", "&"))
    return re.sub(r"\s+", " ", text).strip()


def has_img(html_text: Any) -> bool:
    return bool(html_text and re.search(r"<img\b", str(html_text), flags=re.I))


def load_json_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        result = data.get('result', {})
        if isinstance(result, dict) and isinstance(result.get('list'), list):
            return result['list']
        if isinstance(data.get('list'), list):
            return data['list']
    return []


def load_bank(bank_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    return {key: load_json_list(bank_dir / filename) for key, filename in BANK_FILES.items()}


def _coerce_bool_default_true(value: Any) -> bool:
    """将 selection_blocked 规范为布尔值；缺失默认阻断。"""
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "0", "no", "off")
    return bool(value)


def _errata_question_id(item: Any) -> str:
    """兼容 question_id / questionId 两种错题 ID 字段。"""
    if not isinstance(item, dict):
        return ""
    return str(item.get("question_id") or item.get("questionId") or "").strip()


def _strip_book_title(name: Any) -> str:
    text = str(name or "").strip()
    if text.startswith("《") and text.endswith("》") and len(text) > 2:
        return text[1:-1]
    return text


def _relpath(path: Path, start: Path) -> str:
    try:
        return str(path.resolve().relative_to(start.resolve()))
    except Exception:
        try:
            return str(path.relative_to(start))
        except Exception:
            return str(path)


def _normalize_errata_item(
    item: Any,
    *,
    bank_dir: Optional[Path] = None,
    course_name: Optional[str] = None,
    source_file: str = "",
) -> Optional[Dict[str, Any]]:
    """将一条 _errata.json 记录规范化，供选题阻断和总索引复用。"""
    if not isinstance(item, dict):
        return None

    qid = _errata_question_id(item)
    status = str(item.get("status", "pending") or "pending").strip().lower()
    selection_blocked = _coerce_bool_default_true(item.get("selection_blocked", True))
    is_blocked = status != "ignored" and selection_blocked
    resolved_course = (
        item.get("course_name")
        or item.get("course")
        or course_name
        or _strip_book_title((bank_dir or Path(".")).name)
    )

    return {
        "question_id": qid,
        "course_name": str(resolved_course or "").strip(),
        "question_type": item.get("question_type") or item.get("section_type") or item.get("type") or "",
        "error_type": item.get("error_type") or "other",
        "status": status,
        "selection_blocked": selection_blocked,
        "is_blocked": is_blocked,
        "vol": item.get("vol", item.get("volume", item.get("first_found_volume"))),
        "paper_question_no": item.get("paper_question_no"),
        "description": item.get("description") or "",
        "action_in_paper": item.get("action_in_paper") or "",
        "source_file": source_file,
        "timestamp": item.get("timestamp") or item.get("created_at") or item.get("updated_at") or "",
    }


def load_errata_records(bank_dir: Path) -> List[Dict[str, Any]]:
    """加载并规范化课程题库 _errata.json 记录。"""
    path = bank_dir / "_errata.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    course_name = data.get("course_name") if isinstance(data, dict) else None
    rows = data.get("errata", []) if isinstance(data, dict) else []
    records: List[Dict[str, Any]] = []
    for item in rows:
        record = _normalize_errata_item(item, bank_dir=bank_dir, course_name=course_name, source_file=str(path))
        if record and record.get("question_id"):
            records.append(record)
    return records


def load_errata_ids(bank_dir: Path) -> Set[str]:
    """加载待排除的题库错题 ID 集合。"""
    return {r["question_id"] for r in load_errata_records(bank_dir) if r.get("is_blocked")}


def sync_errata_index(bank_root: Path) -> Tuple[Path, Dict[str, Any]]:
    """扫描全部课程 _errata.json，生成题库根目录 _errata_index.json 总索引。"""
    bank_root = bank_root.resolve()
    if not bank_root.is_dir():
        raise FileNotFoundError(f"题库根目录不存在: {bank_root}")

    records: List[Dict[str, Any]] = []
    invalid_records: List[Dict[str, Any]] = []
    courses: Dict[str, Dict[str, Any]] = {}

    for bank_dir in sorted(p for p in bank_root.iterdir() if p.is_dir()):
        errata_path = bank_dir / "_errata.json"
        if not errata_path.exists():
            continue
        try:
            data = json.loads(errata_path.read_text(encoding="utf-8"))
        except Exception as exc:
            invalid_records.append({"source_file": _relpath(errata_path, bank_root), "reason": f"invalid_json: {exc}"})
            continue
        if not isinstance(data, dict):
            invalid_records.append({"source_file": _relpath(errata_path, bank_root), "reason": "not_object"})
            continue

        course_name = data.get("course_name") or _strip_book_title(bank_dir.name)
        rows = data.get("errata", [])
        if not isinstance(rows, list):
            invalid_records.append({"source_file": _relpath(errata_path, bank_root), "course_name": course_name, "reason": "errata_not_list"})
            rows = []

        stats = courses.setdefault(str(course_name), {
            "bank_dir": _relpath(bank_dir, bank_root),
            "errata_file": _relpath(errata_path, bank_root),
            "records": 0,
            "blocked": 0,
            "unblocked": 0,
            "ignored": 0,
            "blocked_ids": [],
            "by_error_type": {},
            "by_status": {},
        })
        blocked_ids = set(stats["blocked_ids"])

        for item in rows:
            record = _normalize_errata_item(
                item,
                bank_dir=bank_dir,
                course_name=str(course_name),
                source_file=_relpath(errata_path, bank_root),
            )
            if not record or not record.get("question_id"):
                invalid_records.append({
                    "source_file": _relpath(errata_path, bank_root),
                    "course_name": course_name,
                    "reason": "missing_question_id",
                    "raw": item if isinstance(item, dict) else str(item),
                })
                continue

            records.append(record)
            stats["records"] += 1
            status = record.get("status") or "pending"
            error_type = record.get("error_type") or "other"
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            stats["by_error_type"][error_type] = stats["by_error_type"].get(error_type, 0) + 1
            if status == "ignored":
                stats["ignored"] += 1
            elif record.get("is_blocked"):
                stats["blocked"] += 1
                blocked_ids.add(record["question_id"])
            else:
                stats["unblocked"] += 1
        stats["blocked_ids"] = sorted(blocked_ids)

    blocked_total = sum(1 for r in records if r.get("is_blocked"))
    ignored_total = sum(1 for r in records if r.get("status") == "ignored")
    index = {
        "_description": "Generated errata index. Do not edit manually. Source of truth is each course _errata.json.",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "root": str(bank_root),
        "summary": {
            "courses": len(courses),
            "records": len(records),
            "blocked": blocked_total,
            "unblocked": len(records) - blocked_total - ignored_total,
            "ignored": ignored_total,
            "invalid": len(invalid_records),
        },
        "courses": courses,
        "records": records,
        "invalid_records": invalid_records,
    }

    out_path = bank_root / "_errata_index.json"
    out_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path, index


def validate_question(q: Dict[str, Any], bank_key: str) -> Tuple[bool, str]:
    """入库前硬过滤：状态、知识点、难度、答案、题型答案格式。"""
    if q.get('status') is not None and q.get('status') != 1:
        return False, 'status != 1'
    if not q.get('kpointIds'):
        return False, 'kpointIds 为空'
    if q.get('difficulty') is None:
        return False, 'difficulty 缺失'

    answer_raw = q.get('answer', '') or ''
    if isinstance(answer_raw, dict):
        answer_raw = answer_raw.get('stem', '') or ''
    answer_text = convert_answer_html(answer_raw).strip() or clean_html(answer_raw)

    if any(p.match(answer_text) for p in REJECT_ANSWER_PATTERNS) and not has_img(answer_raw):
        return False, f'答案无效: {answer_text[:20]!r}'

    stem_text = clean_html(q.get('stem', '') or '')
    if len(stem_text) < 2 and not has_img(q.get('stem', '') or ''):
        return False, '题干极短且无图'

    if bank_key == 'single_choice' and not re.match(r'^[A-D]\s*$', answer_text):
        return False, f'选择题答案非 A-D: {answer_text[:20]!r}'
    if bank_key == 'judge' and answer_text not in ('正确', '错误', '对', '错', '√', '×'):
        if '正确' not in answer_text and '错误' not in answer_text:
            return False, f'判断题答案非 正确/错误: {answer_text[:20]!r}'

    return True, ''


def classify_question(q: Dict[str, Any], intended_bank_key: str) -> Tuple[str, str]:
    """将 API 错标的简答/综合题机械重分类到选择/判断。"""
    if intended_bank_key not in ('short_answer', 'comprehensive'):
        return intended_bank_key, ''
    stem = clean_html(q.get('stem', '') or '')
    ans = convert_answer_html(q.get('answer', '') or '').strip() or clean_html(q.get('answer', '') or '')
    if JUDGE_STEM_PATTERN.search(stem) and ans in ('正确', '错误'):
        return 'judge', '判断格式：题干末尾含括号 + 答案正确/错误'
    if MCQ_ANSWER_PATTERN.match(ans):
        return 'single_choice', '答案为 A-D，归入选择题'
    return intended_bank_key, ''


def save_bank_items(bank_dir: Path, bank_key: str, questions: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """追加入库：按 questionId 去重、校验、flat array 写回。"""
    bank_dir.mkdir(parents=True, exist_ok=True)
    path = bank_dir / BANK_FILES[bank_key]
    existing = load_json_list(path)
    seen = {str(q.get('questionId', '')) for q in existing if q.get('questionId')}

    added = rejected = duplicate = 0
    for q in questions:
        qid = str(q.get('questionId', ''))
        if not qid or qid in seen:
            duplicate += 1
            continue
        ok, reason = validate_question(q, bank_key)
        if not ok:
            rejected += 1
            print(f"  [入库拒绝] {qid}: {reason}")
            continue
        existing.append(q)
        seen.add(qid)
        added += 1

    with path.open('w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    return {"added": added, "rejected": rejected, "duplicate": duplicate, "total": len(existing)}


def pull_page(
    *,
    course_id: Optional[int],
    kpoint_ids: Optional[Sequence[Any]],
    type_ids: Sequence[Any],
    page_index: int,
    page_size: int,
    cookie: str,
    app_key: str = DEFAULT_APP_KEY,
    sign: str = DEFAULT_SIGN,
) -> Tuple[List[Dict[str, Any]], int]:
    """调用 get-question-list API 拉一页。"""
    payload = build_payload(
        course_id=course_id,
        kpoint_ids=list(kpoint_ids) if kpoint_ids else None,
        type_ids=list(type_ids),
        page_size=page_size,
        page_index=page_index,
        bank_ids=None,
    )
    print(f"  [API拉题] course={course_id or '不限'}, kpoint={len(kpoint_ids or []) or '不限'}, "
          f"type={list(type_ids)}, page={page_index}, size={page_size}")
    print_request_snapshot(payload, prefix="  [API拉题] ")
    result = api_query(payload, app_key=app_key, sign=sign, cookie=cookie)
    print_response_diagnostics(result, prefix="  [API返回] ")
    if result is None or not result.get('valid'):
        error = result.get('error', '无响应') if isinstance(result, dict) else '无响应'
        raise RuntimeError(f"API 调用失败: {error}")
    rows = result.get('result', {}).get('list', []) or []
    total = int(result.get('result', {}).get('totalCount') or 0)
    print(f"  [API返回] {len(rows)} 题（totalCount={total}）")
    return rows, total


def random_page_pull(
    *,
    course_id: Optional[int],
    kpoint_ids: Optional[Sequence[Any]],
    type_ids: Sequence[Any],
    target: int,
    page_size: int,
    existing_ids: Set[str],
    cookie: str,
) -> List[Dict[str, Any]]:
    """选择/判断/填空/简答：随机翻页 + 多级回退。"""
    tried: Set[int] = set()
    collected: List[Dict[str, Any]] = []
    ranges = [(1, 20, 'Level 0: 1~20'), (1, 11, 'Level 1: 1~11'), (1, 6, 'Level 2: 1~6')]
    empty_streak = 0

    for lo, hi, label in ranges:
        candidates = [p for p in range(lo, hi + 1) if p not in tried]
        pages = random.sample(candidates, min(3, len(candidates)))
        tried.update(pages)
        full_pages = 0
        for page in pages:
            rows, _ = pull_page(course_id=course_id, kpoint_ids=kpoint_ids, type_ids=type_ids,
                                page_index=page, page_size=page_size, cookie=cookie)
            if len(rows) == page_size:
                full_pages += 1
                empty_streak = 0
            elif not rows:
                empty_streak += 1
            new_rows = [q for q in rows if str(q.get('questionId', '')) not in existing_ids]
            for q in new_rows:
                existing_ids.add(str(q.get('questionId', '')))
            collected.extend(new_rows)
            print(f"  [{label}] 第{page}页 → {len(new_rows)} 新题（累计 {len(collected)}）")
            if len(collected) >= target:
                return collected
        if full_pages >= 2:
            return collected
        if empty_streak >= 6:
            print("  [随机翻页] 连续 6 页为空，进入顺序兜底")
            break

    for page in [p for p in range(1, 21) if p not in tried]:
        rows, _ = pull_page(course_id=course_id, kpoint_ids=kpoint_ids, type_ids=type_ids,
                            page_index=page, page_size=page_size, cookie=cookie)
        new_rows = [q for q in rows if str(q.get('questionId', '')) not in existing_ids]
        for q in new_rows:
            existing_ids.add(str(q.get('questionId', '')))
        collected.extend(new_rows)
        print(f"  [Level 3] 第{page}页 → {len(new_rows)} 新题（累计 {len(collected)}）")
        if len(collected) >= target:
            break
    return collected


def pull_all_pages(
    *,
    course_id: Optional[int],
    kpoint_ids: Optional[Sequence[Any]],
    type_ids: Sequence[Any],
    target: int,
    page_size: int,
    existing_ids: Set[str],
    cookie: str,
    max_pages: int = 20,
) -> List[Dict[str, Any]]:
    """综合/计算题：从第 1 页开始扫尽页面。"""
    collected: List[Dict[str, Any]] = []
    empty_streak = 0
    for page in range(1, max_pages + 1):
        rows, _ = pull_page(course_id=course_id, kpoint_ids=kpoint_ids, type_ids=type_ids,
                            page_index=page, page_size=page_size, cookie=cookie)
        if not rows:
            empty_streak += 1
            if empty_streak >= 2:
                print(f"  [扫尽] 连续 {empty_streak} 页为空，停止")
                break
            continue
        empty_streak = 0
        new_rows = [q for q in rows if str(q.get('questionId', '')) not in existing_ids]
        if not new_rows:
            print(f"  [扫尽] 第 {page} 页全部重复，停止")
            break
        for q in new_rows:
            existing_ids.add(str(q.get('questionId', '')))
        collected.extend(new_rows)
        print(f"  [扫尽] 第{page}页 → {len(new_rows)} 新题（累计 {len(collected)}）")
        if len(rows) < page_size or len(collected) >= target:
            break
    return collected


def pull_for_section(
    *,
    bank_dir: Path,
    course_id: Optional[int],
    kpoint_ids: Optional[Sequence[Any]],
    type_ids: Sequence[Any],
    section_type: str,
    needed: int,
    cookie: str,
) -> Dict[str, Any]:
    """按 v2 规则为一个题型拉题并入库。"""
    if section_type not in SECTION_TYPE_MAP:
        raise ValueError(f"未知 section_type: {section_type}; 可选 {', '.join(SECTION_TYPE_MAP)}")
    bank_key = SECTION_TYPE_MAP[section_type]['bank_key']
    bank = load_bank(bank_dir)
    existing_ids = {str(q.get('questionId', '')) for rows in bank.values() for q in rows if q.get('questionId')}
    errata_ids = load_errata_ids(bank_dir)
    if errata_ids:
        existing_ids.update(errata_ids)
        print(f"[错题排除] blocked={len(errata_ids)}（仅参与本次拉题去重/排除，不写入 _used.json）")

    multiplier = 5 if section_type in ('short_answer', 'calc') else 3
    target = max(needed * multiplier, needed)
    page_size = 100 if section_type == 'calc' else min(max(target, 60), 100)

    if section_type == 'calc':
        print(f"[综合/计算题] 需 {needed} 题，按 {multiplier}x 扫尽页面")
        pulled = pull_all_pages(course_id=course_id, kpoint_ids=kpoint_ids, type_ids=type_ids,
                                target=target, page_size=page_size, existing_ids=existing_ids, cookie=cookie)
    else:
        print(f"[普通题型] 需 {needed} 题，按 {multiplier}x 随机翻页")
        pulled = random_page_pull(course_id=course_id, kpoint_ids=kpoint_ids, type_ids=type_ids,
                                  target=target, page_size=page_size, existing_ids=existing_ids, cookie=cookie)

    classified = {key: [] for key in BANK_FILES}
    rerouted: List[str] = []
    for q in pulled:
        target_key, note = classify_question(q, bank_key)
        classified[target_key].append(q)
        if note:
            rerouted.append(f"{q.get('questionId')}: {bank_key} → {target_key}（{note}）")

    save_stats = {}
    for key, rows in classified.items():
        if rows:
            save_stats[key] = save_bank_items(bank_dir, key, rows)

    if rerouted:
        print("[题型重分类]")
        for line in rerouted[:10]:
            print(f"  {line}")
        if len(rerouted) > 10:
            print(f"  ... 共 {len(rerouted)} 条")

    return {
        "section_type": section_type,
        "intended_bank_key": bank_key,
        "pulled": len(pulled),
        "saved": save_stats,
        "rerouted": rerouted,
    }


# ---------------------------------------------------------------------------
# kpoint 合并导致的串知识点过滤
# ---------------------------------------------------------------------------

# 默认关键词冲突映射表：考点名称关键词 → 该考点卷不应出现的题干关键词
# 按课程扩展，当前为通用占位。实际使用时由调用方传入课程专属映射。
DEFAULT_CONTENT_CONFLICT: Dict[str, List[str]] = {
    # 示例：电子信息类
    # '电路': ['磁场', '磁路', '电磁感应'],
    # '模拟': ['数字', '逻辑', '二进制', '卡诺图'],
    # '数字': ['放大', '三极管', '运放', '反馈'],
}


def apply_content_filter(
    pool: List[Dict[str, Any]],
    exam_point_name: str,
    conflict_map: Optional[Dict[str, List[str]]] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """kpoint 合并导致的串知识点过滤。

    当窄考点合并后，不同考点可能共享合并后的 kpointId 集合。
    API 返回的题目可能来自集合中"相邻但不属于本题考点"的知识点——
    例如考点为"冷却系统"，但拉到了"润滑系统"的题目。

    通过考点名称与题干关键词做互斥过滤来清理。

    Args:
        pool: 待过滤题目列表
        exam_point_name: 当前考点名称（C 列），如"冷却系统水路循环"
        conflict_map: 课程专属关键词冲突映射表，{考点关键词: [互斥题干关键词]}
                      不传则使用 DEFAULT_CONTENT_CONFLICT

    Returns:
        (filtered_pool, removed_count)
    """
    if not pool or not exam_point_name:
        return pool, 0

    cmap: Dict[str, List[str]] = conflict_map if conflict_map else DEFAULT_CONTENT_CONFLICT
    if not cmap:
        return pool, 0

    # 找出与当前考点名称匹配的冲突规则
    forbidden_keywords: List[str] = []
    for point_kw, conflict_kws in cmap.items():
        if point_kw in exam_point_name:
            forbidden_keywords.extend(conflict_kws)

    if not forbidden_keywords:
        return pool, 0

    filtered: List[Dict[str, Any]] = []
    removed = 0
    for q in pool:
        stem = q.get('stem', '') or ''
        # 检查题干中是否包含互斥关键词
        if any(kw in stem for kw in forbidden_keywords):
            removed += 1
            continue
        filtered.append(q)

    if removed:
        print(f"  [内容过滤] 考点「{exam_point_name}」，移除 {removed} 道串知识点题目"
              f"（互斥关键词：{forbidden_keywords}）")

    return filtered, removed


def main() -> None:
    parser = argparse.ArgumentParser(description='独立版学科网 API 拉题工具（不生成试卷）')
    parser.add_argument('--bank-dir', help='本地题库目录，写入 choice/fill/judge/short/comp.json')
    parser.add_argument('--bank-root', help='题库根目录；配合 --sync-errata-index 使用，通常为 03_题库 或输出题库根目录')
    parser.add_argument('--sync-errata-index', action='store_true', help='扫描各课程 _errata.json，生成题库根目录 _errata_index.json 后退出')
    parser.add_argument('--course-id', type=int, help='课程 ID')
    parser.add_argument('--kpoint-ids', help='知识点 ID，逗号分隔；不传则不限知识点')
    parser.add_argument('--type-ids', help='API 题型 ID，逗号分隔；必须来自 categories 映射或配置')
    parser.add_argument('--section-type', choices=sorted(SECTION_TYPE_MAP), help='流程题型：choice/fill/judge/short_answer/calc')
    parser.add_argument('--needed', type=int, default=10, help='本轮预计需要的题数；工具会按倍率多拉候选')
    parser.add_argument('--cookie', default=DEFAULT_COOKIE, help='Cookie；也可设置环境变量 XKW_COOKIE')
    args = parser.parse_args()

    if args.sync_errata_index:
        bank_root = Path(args.bank_root) if args.bank_root else (Path(args.bank_dir).parent if args.bank_dir else None)
        if bank_root is None:
            raise SystemExit('--sync-errata-index 需要 --bank-root，或通过 --bank-dir 推导题库根目录。')
        out_path, index = sync_errata_index(bank_root)
        summary = index.get('summary', {})
        print(f"[错题索引] 扫描 {Path(bank_root).resolve()}")
        print(
            f"  课程 {summary.get('courses', 0)} 个, records={summary.get('records', 0)}, "
            f"blocked={summary.get('blocked', 0)}, ignored={summary.get('ignored', 0)}, "
            f"unblocked={summary.get('unblocked', 0)}, invalid={summary.get('invalid', 0)}"
        )
        print(f"[错题索引] 写入 {out_path}")
        return

    missing = [name for name, value in (
        ('--bank-dir', args.bank_dir),
        ('--course-id', args.course_id),
        ('--type-ids', args.type_ids),
        ('--section-type', args.section_type),
    ) if value in (None, '')]
    if missing:
        raise SystemExit('非 --sync-errata-index 模式必须提供 ' + ', '.join(missing))

    if not args.cookie:
        raise SystemExit('缺少 Cookie：请设置环境变量 XKW_COOKIE 或使用 --cookie 传入。')

    summary = pull_for_section(
        bank_dir=Path(args.bank_dir),
        course_id=args.course_id,
        kpoint_ids=parse_ids(args.kpoint_ids),
        type_ids=parse_ids(args.type_ids) or [],
        section_type=args.section_type,
        needed=args.needed,
        cookie=args.cookie,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
