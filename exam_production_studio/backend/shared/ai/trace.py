"""AI 调用追踪：把每次 LLM 的 prompt / 响应 / 用量落盘，供排查生成问题。

设计要点：
- 用 contextvars 传当前「项目根 / run_id / 节点 / 卷号」，避免改动深层的每个 AI 调用点。
- 整条流程（runner → driver → shared/ai.call_api）在同一 worker 线程内同步执行，
  故在 runner 里 set 的 contextvar 能被深层 call_api 读到。
- 落盘位置：<项目根>/04_生成输出/运行记录/AI调用/<run_id>/<序号>_<节点>[_第N卷].json
- 只保留最近 keep_runs 次运行的记录目录（begin 时清理），避免磁盘无限增长。
- 任何异常都不得影响主流程：所有 IO 都吞掉异常。
"""
from __future__ import annotations

import contextvars
import json
import re
import shutil
import time
from pathlib import Path
from typing import Any

import config

_ILLEGAL = re.compile(r'[\\/:*?"<>|\r\n\t]+')

# 当前线程/上下文的追踪状态；None 表示未开启或未处于流程中
_state: contextvars.ContextVar[dict | None] = contextvars.ContextVar("ai_trace", default=None)


def _safe(name: str) -> str:
    return _ILLEGAL.sub("_", str(name or "")).strip("_ ") or "unknown"


def _prune(base: Path, keep_runs: int) -> None:
    """只保留最近 keep_runs 个运行目录（按修改时间倒序）。"""
    try:
        runs = [d for d in base.iterdir() if d.is_dir()]
    except OSError:
        return
    runs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    for old in runs[keep_runs:]:
        try:
            shutil.rmtree(old, ignore_errors=True)
        except OSError:
            pass


def begin(root: Path, run_id: str) -> None:
    """流程开始时调用：按配置初始化本次运行的记录目录。未开启则置空。"""
    try:
        cfg = config.get_ai_trace_config()
    except Exception:  # noqa: BLE001
        cfg = {"enabled": True, "keep_runs": 10}
    if not cfg.get("enabled", True):
        _state.set(None)
        return
    base = Path(root) / "04_生成输出" / "运行记录" / "AI调用"
    run_dir = base / _safe(run_id)
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        _prune(base, int(cfg.get("keep_runs", 10)))
    except OSError:
        _state.set(None)
        return
    _state.set({"dir": run_dir, "run_id": run_id, "node": "", "paper_no": None, "seq": 0})


def stage(node: str = "", paper_no: int | None = None) -> None:
    """进入某个流程阶段时更新当前节点/卷号（供落盘文件命名与归类）。"""
    st = _state.get()
    if st is None:
        return
    if node:
        st["node"] = node
    st["paper_no"] = paper_no


def end() -> None:
    _state.set(None)


def active() -> bool:
    return _state.get() is not None


def log_call(
    *,
    messages: list[dict[str, str]],
    response: str | None = None,
    error: str | None = None,
    model: str = "",
    temperature: Any = None,
    max_tokens: Any = None,
    usage: Any = None,
    elapsed_ms: int | None = None,
) -> None:
    """记录一次 LLM 调用（成功或失败）。无追踪上下文时直接跳过。"""
    st = _state.get()
    if st is None:
        return
    st["seq"] += 1
    seq = st["seq"]
    node = st.get("node") or "unknown"
    paper = st.get("paper_no")
    fname = f"{seq:03d}_{_safe(node)}"
    if paper is not None:
        fname += f"_第{paper}卷"
    rec = {
        "seq": seq,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "run_id": st.get("run_id"),
        "node": node,
        "paper_no": paper,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "elapsed_ms": elapsed_ms,
        "usage": usage,
        "messages": messages,
        "response": response,
        "error": error,
    }
    try:
        (st["dir"] / f"{fname}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass
