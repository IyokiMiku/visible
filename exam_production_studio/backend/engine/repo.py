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
def replace_papers(project_id: str, rows: list[dict[str, Any]]) -> None:
    db.execute("DELETE FROM papers WHERE project_id=?", (project_id,))
    for r in rows:
        db.execute(
            "INSERT INTO papers (id, project_id, paper_no, paper_type, module, topic, point_name, kpoint_id, status, docx_paths, qc_report_path)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (new_id("pp_"), project_id, r.get("paper_no"), r.get("paper_subtype", ""),
             r.get("module", ""), r.get("topic", ""), r.get("point_name", ""),
             r.get("kpoint_id", ""), r.get("status", "planned"),
             _dump(r.get("docx_paths", [])), r.get("qc_report_path", "")),
        )


def get_papers(project_id: str) -> list[dict[str, Any]]:
    return db.query("SELECT * FROM papers WHERE project_id=? ORDER BY paper_no", (project_id,))


def get_paper(project_id: str, paper_no: int) -> dict[str, Any] | None:
    return db.query_one("SELECT * FROM papers WHERE project_id=? AND paper_no=?", (project_id, paper_no))


def update_paper(project_id: str, paper_no: int, **fields: Any) -> None:
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
