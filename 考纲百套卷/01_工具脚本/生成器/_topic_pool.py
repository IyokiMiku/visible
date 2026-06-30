"""
专题级中间小题库模块。

每个专题维护一个 JSON 小题库文件，API 拉到的题目入池去重，
同专题后续卷优先从池中取题，避免重复拉取和重复使用。
专题全部试卷生成完毕后，池文件自动删除。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .paths import CLEAN_OUTPUT_DIR, manual_paper_dir_for_meta


def _pool_dir(meta: Any) -> Path:
    """返回小题库目录。"""
    province = getattr(meta, "province", "") or ""
    category = getattr(meta, "exam_category", "") or ""
    if province and category:
        return CLEAN_OUTPUT_DIR / f"{province} {category}" / "小题库"
    return CLEAN_OUTPUT_DIR / "小题库"


def _sanitize_filename(name: str) -> str:
    """将专题/课程名转为安全的文件名片段。"""
    import re
    return re.sub(r"[\\/:*?\"<>|]", "_", name).strip()


def _question_id(q: dict) -> str:
    """为一道题目生成唯一 ID。优先使用 question_id，否则用题干 MD5。"""
    qid = str(q.get("question_id", "")).strip()
    if qid:
        return qid
    stem = str(q.get("stem", "") or "")
    return hashlib.md5(stem.encode("utf-8")).hexdigest()[:16]


def _pool_key(kpoint_ids: list[int]) -> str:
    """以 kpoint ID 集合为键（排序后拼接），相同知识点集共享小题库。"""
    return ",".join(str(kid) for kid in sorted(set(kpoint_ids))) if kpoint_ids else "_empty"


def _pool_path(meta: Any, kpoint_ids: list[int]) -> Path:
    """返回指定知识点集的小题库文件路径。"""
    key = _pool_key(kpoint_ids)
    return _pool_dir(meta) / f"{key}_pool.json"




def _topic_pool_path(meta: Any, module: str, topic: str) -> Path:
    """返回同专题共享小题库文件路径。"""
    module_part = _sanitize_filename(module or "未命名课程")
    topic_part = _sanitize_filename(topic or "未命名专题")
    return _pool_dir(meta) / f"{module_part}__{topic_part}_pool.json"


def load_topic_pool(meta: Any, module: str, topic: str) -> dict:
    """加载同课程同专题共享小题库。"""
    path = _topic_pool_path(meta, module, topic)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "questions" in data:
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "pool_key": f"{module}::{topic}",
        "module": module,
        "topic": topic,
        "course_id": 0,
        "kpoint_ids": [],
        "questions": {},
    }


def save_topic_pool(meta: Any, module: str, topic: str, pool: dict) -> None:
    """保存同专题共享小题库。"""
    path = _topic_pool_path(meta, module, topic)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pool, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def delete_topic_pool(meta: Any, module: str, topic: str) -> None:
    """删除同专题共享小题库文件。"""
    path = _topic_pool_path(meta, module, topic)
    if path.exists():
        path.unlink()

def load_pool(meta: Any, kpoint_ids: list[int]) -> dict:
    """
    加载指定知识点集的小题库。

    返回格式:
    {
        "kpoint_key": "87644,87650",
        "course_id": 10002,
        "kpoint_ids": [87644, 87650, ...],
        "questions": {
            "qid_xxx": {"data": {...}, "used_by": null | "第1卷"},
            ...
        }
    }
    """
    path = _pool_path(meta, kpoint_ids)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return _empty_pool(kpoint_ids)
    return _empty_pool(kpoint_ids)


def _empty_pool(kpoint_ids: list[int]) -> dict:
    return {"kpoint_key": _pool_key(kpoint_ids), "course_id": 0, "kpoint_ids": kpoint_ids, "questions": {}}


def save_pool(meta: Any, kpoint_ids: list[int], pool: dict) -> None:
    """保存小题库到文件。"""
    path = _pool_path(meta, kpoint_ids)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(pool, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def delete_pool(meta: Any, kpoint_ids: list[int]) -> None:
    """删除指定知识点集的小题库文件。"""
    path = _pool_path(meta, kpoint_ids)
    if path.exists():
        path.unlink()


def add_questions_to_pool(
    pool: dict,
    questions: list[dict],
    kpoint_ids: list[int],
    course_id: int,
) -> int:
    """将题目加入小题库。返回新增数量（去重后）。"""
    pool["kpoint_ids"] = sorted(set(pool.get("kpoint_ids", []) + kpoint_ids))
    pool["course_id"] = course_id
    added = 0
    for q in questions:
        qid = _question_id(q)
        if qid not in pool["questions"]:
            # 深拷贝题目数据
            copy = {}
            for key in ("question_id", "course_id", "type_id", "difficulty",
                         "stem", "answer", "explanation", "options",
                         "source", "year", "question_type"):
                if key in q:
                    copy[key] = q[key]
            pool["questions"][qid] = {"data": copy, "used_by": None}
            added += 1
    return added


def get_unused_questions(
    pool: dict,
    qtype: str,
    difficulty: str,
    count: int,
) -> list[dict]:
    """从小题库中取未使用的题目，取指定数量后标记为已用。"""
    candidates = []
    for qid, entry in pool["questions"].items():
        if entry["used_by"]:
            continue
        data = entry["data"]
        # 题型匹配：优先精确匹配，其次模糊
        pool_qtype = data.get("question_type", "") or data.get("_question_type", "")
        if pool_qtype == qtype:
            candidates.append((qid, entry))
        elif qtype in pool_qtype or pool_qtype in qtype:
            candidates.append((qid, entry))

    if not candidates:
        return []

    # 按需要数量取
    import random
    random.shuffle(candidates)

    result = []
    for qid, entry in candidates[:count]:
        data = entry["data"].copy()
        data["_target_difficulty"] = difficulty
        data["_question_type"] = qtype
        data["_from_pool"] = True
        result.append(data)
        entry["used_by"] = "使用中"  # 临时标记，调用方应在完成后传 paper_label 持久化

    return result


def mark_used(
    pool: dict,
    question_ids: list[str],
    paper_label: str,
) -> None:
    """将指定题目标记为已被某卷使用。"""
    for qid in question_ids:
        if qid in pool["questions"]:
            pool["questions"][qid]["used_by"] = paper_label


def scan_generated_papers(meta: Any) -> set[str]:
    """扫描组卷待质检目录，返回已有待质检组卷的卷号集合（如 {'第1卷', '第2卷'}）。"""
    manual_dir = manual_paper_dir_for_meta(meta)
    if not manual_dir.exists():
        return set()

    generated: set[str] = set()
    import re
    for f in manual_dir.iterdir():
        if not f.is_file():
            continue
        if f.suffix.lower() not in (".docx", ".json"):
            continue
        # 提取卷号
        match = re.search(r"第(\d+)卷", f.stem)
        if match:
            generated.add(f"第{match.group(1)}卷")
    return generated


def get_topic_pool_question_count(pool: dict, unused_only: bool = False) -> tuple[int, int]:
    """返回题库中 (总题数, 未使用题数)。"""
    total = len(pool["questions"])
    unused = sum(1 for v in pool["questions"].values() if not v.get("used_by"))
    return total, unused


def compact_pool(pool: dict) -> None:
    """清理非必要的元数据，减少文件体积。"""
    # 移除 used_by 标记为使用中的临时状态（转为 null）
    for entry in pool["questions"].values():
        if entry.get("used_by") == "使用中":
            entry["used_by"] = None
