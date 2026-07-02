"""引擎数据访问层：集中 projects/papers/runs/flow_logs/review_items/quality_summary 读写。"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import db


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _dump(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False)


# ---- projects ----
def get_project(project_id: str) -> dict[str, Any] | None:
    return db.query_one("SELECT * FROM projects WHERE id=?", (project_id,))


def set_project_status(project_id: str, status: str) -> None:
    db.execute("UPDATE projects SET status=?, updated_at=? WHERE id=?", (status, now(), project_id))


def update_project_field(project_id: str, field: str, value: Any) -> None:
    db.execute(f"UPDATE projects SET {field}=?, updated_at=? WHERE id=?", (value, now(), project_id))


# ---- papers ----
# 存入 papers.meta(JSON) 的层级/级别/标号字段（阶段 B）。非固定列的这些键统一归入 meta，
# 读取时回填到行 dict 顶层，兼容“老代码读 topic、新代码读 level/unit_name”两种方式。
_META_KEYS = (
    "course", "unit_name", "unit_no", "chapter_name", "chapter_no", "section_no", "section_name",
    "level", "syllabus_no", "original_paper_no", "difficulty", "paper_subtype",
    "theme", "kpoint_ids", "map_method", "map_remark",
)


def _pack_meta(r: dict[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = dict(r.get("meta") or {})
    for k in _META_KEYS:
        if k in r and r[k] is not None and k not in meta:
            meta[k] = r[k]
    return meta


def _unpack_meta(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("meta")
    meta: dict[str, Any] = {}
    if raw:
        try:
            meta = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except (TypeError, ValueError):
            meta = {}
    row["meta"] = meta
    for k, v in meta.items():
        row.setdefault(k, v)
    return row


def replace_papers(project_id: str, rows: list[dict[str, Any]]) -> None:
    db.execute("DELETE FROM papers WHERE project_id=?", (project_id,))
    for r in rows:
        meta = _pack_meta(r)
        db.execute(
            "INSERT INTO papers (id, project_id, paper_no, paper_type, module, topic, point_name, kpoint_id, status, docx_paths, qc_report_path, meta)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (new_id("pp_"), project_id, r.get("paper_no"), r.get("paper_subtype", ""),
             r.get("module", ""), r.get("topic", ""), r.get("point_name", ""),
             r.get("kpoint_id", ""), r.get("status", "planned"),
             _dump(r.get("docx_paths", [])), r.get("qc_report_path", ""),
             _dump(meta) if meta else None),
        )


def get_papers(project_id: str) -> list[dict[str, Any]]:
    return [_unpack_meta(r) for r in
            db.query("SELECT * FROM papers WHERE project_id=? ORDER BY paper_no", (project_id,))]


def get_paper(project_id: str, paper_no: int) -> dict[str, Any] | None:
    r = db.query_one("SELECT * FROM papers WHERE project_id=? AND paper_no=?", (project_id, paper_no))
    return _unpack_meta(r) if r else None


def update_paper(project_id: str, paper_no: int, **fields: Any) -> None:
    if not fields:
        return
    # 允许更新 meta 内字段：把 _META_KEYS 命中的键合并进现有 meta 后整体写回
    meta_updates = {k: fields.pop(k) for k in list(fields) if k in _META_KEYS}
    if "meta" in fields and isinstance(fields["meta"], dict):
        meta_updates = {**fields.pop("meta"), **meta_updates}
    if meta_updates:
        cur = get_paper(project_id, paper_no) or {}
        merged = {**(cur.get("meta") or {}), **meta_updates}
        fields["meta"] = _dump(merged)
    if not fields:
        return
    sets, vals = [], []
    for k, v in fields.items():
        sets.append(f"{k}=?")
        vals.append(_dump(v) if k == "docx_paths" else v)
    vals += [project_id, paper_no]
    db.execute(f"UPDATE papers SET {','.join(sets)} WHERE project_id=? AND paper_no=?", vals)


# ---- runs ----
def create_run(project_id: str) -> str:
    rid = new_id("run_")
    db.execute(
        "INSERT INTO runs (id, project_id, status, current_node, progress, started_at) VALUES (?,?,?,?,?,?)",
        (rid, project_id, "running", "", 0.0, now()),
    )
    return rid


def get_run(run_id: str) -> dict[str, Any] | None:
    return db.query_one("SELECT * FROM runs WHERE id=?", (run_id,))


def latest_run(project_id: str) -> dict[str, Any] | None:
    return db.query_one("SELECT * FROM runs WHERE project_id=? ORDER BY started_at DESC LIMIT 1", (project_id,))


def update_run(run_id: str, **fields: Any) -> None:
    if not fields:
        return
    sets = ",".join(f"{k}=?" for k in fields)
    db.execute(f"UPDATE runs SET {sets} WHERE id=?", list(fields.values()) + [run_id])


# ---- flow_logs ----
def add_log(project_id: str, run_id: str, node: str, message: str, level: str = "info") -> dict[str, Any]:
    db.execute(
        "INSERT INTO flow_logs (project_id, run_id, node, level, message, created_at) VALUES (?,?,?,?,?,?)",
        (project_id, run_id, node, level, message, now()),
    )
    return {"project_id": project_id, "run_id": run_id, "node": node, "level": level,
            "message": message, "created_at": now()}


def get_logs(project_id: str, limit: int = 500) -> list[dict[str, Any]]:
    return db.query("SELECT * FROM flow_logs WHERE project_id=? ORDER BY id DESC LIMIT ?", (project_id, limit))[::-1]


# ---- review_items ----
def enqueue_review(project_id: str, run_id: str, node: str, rtype: str, paper_no: int | None,
                   confidence: float, payload: dict[str, Any]) -> str:
    rid = new_id("rv_")
    db.execute(
        "INSERT INTO review_items (id, project_id, run_id, node, type, paper_no, confidence, payload, status, created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (rid, project_id, run_id, node, rtype, paper_no, confidence, _dump(payload), "pending", now()),
    )
    return rid


def pending_reviews(project_id: str) -> list[dict[str, Any]]:
    rows = db.query("SELECT * FROM review_items WHERE project_id=? AND status='pending' ORDER BY created_at", (project_id,))
    for r in rows:
        try:
            r["payload"] = json.loads(r["payload"]) if r["payload"] else {}
        except (TypeError, ValueError):
            pass
    return rows


def all_reviews(project_id: str) -> list[dict[str, Any]]:
    rows = db.query("SELECT * FROM review_items WHERE project_id=? ORDER BY created_at", (project_id,))
    for r in rows:
        try:
            r["payload"] = json.loads(r["payload"]) if r["payload"] else {}
        except (TypeError, ValueError):
            pass
    return rows


def get_review(review_id: str) -> dict[str, Any] | None:
    r = db.query_one("SELECT * FROM review_items WHERE id=?", (review_id,))
    if r:
        try:
            r["payload"] = json.loads(r["payload"]) if r["payload"] else {}
        except (TypeError, ValueError):
            pass
    return r


def set_review_status(review_id: str, status: str) -> None:
    db.execute("UPDATE review_items SET status=? WHERE id=?", (status, review_id))


# ---- quality_summary ----
def save_quality(project_id: str, paper_no: int, q: dict[str, Any]) -> None:
    db.execute("DELETE FROM quality_summary WHERE project_id=? AND paper_no=?", (project_id, paper_no))
    db.execute(
        "INSERT INTO quality_summary (id, project_id, paper_no, score, adopted, ai_filled, manual_confirmed,"
        " format_ok, completeness, coverage, ai_risk, suggestion) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (new_id("qs_"), project_id, paper_no, q.get("score", 0), q.get("adopted", 0), q.get("ai_filled", 0),
         q.get("manual_confirmed", 0), 1 if q.get("format_ok") else 0, q.get("completeness", 0),
         q.get("coverage", 0), q.get("ai_risk", ""), q.get("suggestion", "")),
    )


def get_quality(project_id: str) -> list[dict[str, Any]]:
    return db.query("SELECT * FROM quality_summary WHERE project_id=? ORDER BY paper_no", (project_id,))
