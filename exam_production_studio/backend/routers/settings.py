"""全局设置（阶段七，设计文档 §5.5）：LLM/学科网/视觉/阈值。

存入 settings 表（key/value，点号命名），config.py 据此覆盖 .env。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

import db
from ._common import ok

router = APIRouter(prefix="/api/settings", tags=["settings"])

_KEYS = [
    "llm.api_key", "llm.base_url", "llm.model", "llm.temperature", "llm.max_tokens",
    "xueke.cookie", "xueke.app_key", "xueke.sign",
    "vision.api_key", "vision.base_url", "vision.model", "vision.enabled",
    "thresholds.match", "thresholds.max_fix_rounds",
]


class SettingsIn(BaseModel):
    llm: dict[str, Any] | None = None
    xueke: dict[str, Any] | None = None
    vision: dict[str, Any] | None = None
    thresholds: dict[str, Any] | None = None


def _get_all() -> dict[str, str]:
    return {r["key"]: r["value"] for r in db.query("SELECT key, value FROM settings")}


def _grouped(masked: bool = True) -> dict[str, Any]:
    flat = _get_all()

    def g(prefix: str) -> dict[str, str]:
        return {k.split(".", 1)[1]: v for k, v in flat.items() if k.startswith(prefix + ".")}

    llm = g("llm")
    xueke = g("xueke")
    if masked:
        if llm.get("api_key"):
            llm["api_key"] = "***已配置***"
        for f in ("cookie", "app_key", "sign"):
            if xueke.get(f):
                xueke[f] = "***已配置***"
    return {"llm": llm, "xueke": xueke, "vision": g("vision"), "thresholds": g("thresholds")}


@router.get("")
def get_settings():
    return ok(_grouped(masked=True))


@router.put("")
def put_settings(body: SettingsIn):
    groups = {"llm": body.llm, "xueke": body.xueke, "vision": body.vision, "thresholds": body.thresholds}
    for prefix, data in groups.items():
        if not data:
            continue
        for k, v in data.items():
            key = f"{prefix}.{k}"
            if v == "***已配置***":  # 未修改的掩码值跳过
                continue
            db.execute("INSERT INTO settings (key, value) VALUES (?,?) "
                       "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(v)))
    return ok(_grouped(masked=True))
