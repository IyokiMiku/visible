"""FastAPI 入口（阶段七）。出卷集成工作台后端。"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config
import db
from routers import (artifacts, flow, projects, resources, review, settings, qc, ws)

app = FastAPI(title="出卷集成工作台 / Exam Production Studio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


@app.get("/api/health")
def health():
    return {"code": 0, "message": "ok", "data": {"service": "exam_production_studio"}}


for _r in (projects, resources, flow, review, qc, artifacts, settings):
    app.include_router(_r.router)
app.include_router(ws.router)

# 可选：托管前端构建产物（阶段九：npm run build → frontend/dist）
_dist = config.BASE_DIR / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")
