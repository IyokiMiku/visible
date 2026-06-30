"""轻量事件总线（阶段五/七：runner → WebSocket 推送）。

runner 在工作线程同步 publish；WS 端在事件循环 subscribe 得到 asyncio.Queue。
publish 通过 call_soon_threadsafe 投递，跨线程安全。
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

_lock = threading.Lock()
_subs: dict[str, list[tuple[asyncio.AbstractEventLoop, "asyncio.Queue[dict]"]]] = {}


def subscribe(project_id: str) -> "asyncio.Queue[dict]":
    loop = asyncio.get_event_loop()
    q: asyncio.Queue[dict] = asyncio.Queue()
    with _lock:
        _subs.setdefault(project_id, []).append((loop, q))
    return q


def unsubscribe(project_id: str, q: "asyncio.Queue[dict]") -> None:
    with _lock:
        lst = _subs.get(project_id, [])
        _subs[project_id] = [(l, qq) for (l, qq) in lst if qq is not q]


def publish(project_id: str, event: dict[str, Any]) -> None:
    with _lock:
        targets = list(_subs.get(project_id, []))
    for loop, q in targets:
        try:
            loop.call_soon_threadsafe(q.put_nowait, event)
        except RuntimeError:
            pass
