"""SQLite 连接与建表（阶段二：数据层）。

表：projects / resources / papers / runs / flow_logs / review_items /
    quality_summary / settings（见设计文档 §4.1）。
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable

import config

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    paper_type      TEXT,
    province        TEXT,
    exam_category   TEXT,
    course          TEXT,
    textbook        TEXT,
    edition         TEXT,
    exam_type_name  TEXT,
    name_template   TEXT,
    volume_config   TEXT,
    paper_range     TEXT,
    plan_source     TEXT,
    output_versions TEXT,
    ai_options      TEXT,
    status          TEXT DEFAULT 'draft',
    wizard_step     INTEGER DEFAULT 0,
    created_at      TEXT,
    updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS resources (
    id          TEXT PRIMARY KEY,
    project_id  TEXT,
    kind        TEXT,
    filename    TEXT,
    path        TEXT,
    status      TEXT DEFAULT 'imported'
);

CREATE TABLE IF NOT EXISTS papers (
    id          TEXT PRIMARY KEY,
    project_id  TEXT,
    paper_no    INTEGER,
    paper_type  TEXT,
    module      TEXT,
    topic       TEXT,
    point_name  TEXT,
    kpoint_id   TEXT,
    status      TEXT DEFAULT 'pending',
    docx_paths  TEXT,
    qc_report_path TEXT,
    meta        TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id           TEXT PRIMARY KEY,
    project_id   TEXT,
    status       TEXT,
    current_node TEXT,
    progress     REAL DEFAULT 0,
    started_at   TEXT,
    finished_at  TEXT
);

CREATE TABLE IF NOT EXISTS flow_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT,
    run_id     TEXT,
    node       TEXT,
    level      TEXT,
    message    TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS review_items (
    id         TEXT PRIMARY KEY,
    project_id TEXT,
    run_id     TEXT,
    node       TEXT,
    type       TEXT,
    paper_no   INTEGER,
    confidence REAL,
    payload    TEXT,
    status     TEXT DEFAULT 'pending',
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS quality_summary (
    id               TEXT PRIMARY KEY,
    project_id       TEXT,
    paper_no         INTEGER,
    score            REAL,
    adopted          INTEGER,
    ai_filled        INTEGER,
    manual_confirmed INTEGER,
    format_ok        INTEGER,
    completeness     REAL,
    coverage         REAL,
    ai_risk          TEXT,
    suggestion       TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def get_conn() -> sqlite3.Connection:
    """线程内复用连接。"""
    conn = getattr(_local, "conn", None)
    if conn is None:
        db_path = config.get_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _local.conn = conn
    return conn


_MIGRATIONS = [
    ("papers", "kpoint_id", "ALTER TABLE papers ADD COLUMN kpoint_id TEXT"),
    # 阶段 B：承载层级（单元/章/节）、级别、考纲标号、原始卷号等，统一存 JSON，避免宽表迁移
    ("papers", "meta", "ALTER TABLE papers ADD COLUMN meta TEXT"),
    # 创建向导草稿：记住上次停在第几步（0/1/2），「继续创建」时回到该步
    ("projects", "wizard_step", "ALTER TABLE projects ADD COLUMN wizard_step INTEGER DEFAULT 0"),
]


def init_db() -> None:
    """首次启动自动建表；对已有库做轻量列迁移。"""
    conn = get_conn()
    conn.executescript(SCHEMA)
    for table, column, ddl in _MIGRATIONS:
        cols = {r["name"] for r in query(f"PRAGMA table_info({table})")}
        if column not in cols:
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                pass
    conn.commit()


def query(sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    cur = get_conn().execute(sql, tuple(params))
    return [dict(row) for row in cur.fetchall()]


def query_one(sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    conn = get_conn()
    cur = conn.execute(sql, tuple(params))
    conn.commit()
    return cur.rowcount


def executemany(sql: str, seq_params: Iterable[Iterable[Any]]) -> None:
    conn = get_conn()
    conn.executemany(sql, [tuple(p) for p in seq_params])
    conn.commit()


def table_names() -> list[str]:
    return [r["name"] for r in query("SELECT name FROM sqlite_master WHERE type='table'")]


if __name__ == "__main__":
    init_db()
    print("tables:", sorted(table_names()))
