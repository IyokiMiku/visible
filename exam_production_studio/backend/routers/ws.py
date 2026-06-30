"""WebSocket 实时推送（阶段七，设计文档 §5.6）。"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from engine import events

router = APIRouter(tags=["ws"])


@router.websocket("/ws/projects/{project_id}")
async def ws_project(websocket: WebSocket, project_id: str):
    await websocket.accept()
    queue = events.subscribe(project_id)
    await websocket.send_json({"event": "connected", "project_id": project_id})

    async def _recv() -> None:
        try:
            while True:
                msg = await websocket.receive_text()
                if msg == "ping":
                    await websocket.send_json({"event": "pong"})
        except WebSocketDisconnect:
            raise
        except Exception:
            raise

    recv_task = asyncio.create_task(_recv())
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=20)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                await websocket.send_json({"event": "heartbeat"})
            if recv_task.done():
                break
    except WebSocketDisconnect:
        pass
    finally:
        recv_task.cancel()
        events.unsubscribe(project_id, queue)
