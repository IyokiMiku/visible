"""全局设置（阶段七，设计文档 §5.5）：LLM/学科网/视觉/阈值。

存入 settings 表（key/value，点号命名），config.py 据此覆盖 .env。
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

import db
from shared import config_errors
from ._common import ok

router = APIRouter(prefix="/api/settings", tags=["settings"])

_KEYS = [
    "llm.api_key", "llm.base_url", "llm.model", "llm.temperature", "llm.max_tokens",
    "xueke.cookie", "xueke.app_key", "xueke.sign",
    "vision.api_key", "vision.base_url", "vision.model", "vision.enabled",
    "thresholds.match", "thresholds.max_fix_rounds",
    "output.dir",
    "ai.trace_enabled", "ai.trace_keep_runs",
]


class SettingsIn(BaseModel):
    llm: dict[str, Any] | None = None
    xueke: dict[str, Any] | None = None
    vision: dict[str, Any] | None = None
    thresholds: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    ai: dict[str, Any] | None = None


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
    return {"llm": llm, "xueke": xueke, "vision": g("vision"),
            "thresholds": g("thresholds"), "output": g("output"), "ai": g("ai")}


@router.get("")
def get_settings():
    return ok(_grouped(masked=True))


@router.put("")
def put_settings(body: SettingsIn):
    groups = {"llm": body.llm, "xueke": body.xueke, "vision": body.vision,
              "thresholds": body.thresholds, "output": body.output, "ai": body.ai}
    for prefix, data in groups.items():
        if not data:
            continue
        for k, v in data.items():
            key = f"{prefix}.{k}"
            if v == "***已配置***":  # 未修改的掩码值跳过
                continue
            db.execute("INSERT INTO settings (key, value) VALUES (?,?) "
                       "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(v)))
    config_errors.clear()  # 用户已重新保存 → 清除运行时配置错误标记
    return ok(_grouped(masked=True))


# 必填项取值：settings 表 > .env，不套用内置默认（口径与首次运行表单一致）
_REQUIRED = [
    ("llm", "api_key", "LLM_API_KEY", "未填写大模型 API 密钥"),
    ("llm", "base_url", "LLM_BASE_URL", "未填写大模型接口地址"),
    ("llm", "model", "LLM_MODEL", "未填写大模型名称"),
    ("xueke", "cookie", "XKW_COOKIE", "未填写学科网 Cookie"),
]


def _effective(flat: dict[str, str], setting_key: str, env_key: str) -> str:
    v = (flat.get(setting_key) or "").strip()
    if v:
        return v
    return (os.getenv(env_key) or "").strip()


@router.get("/check")
def check_settings():
    """自检：返回 {ok, issues}。issues 含静态缺失项与最近一次运行时配置错误。"""
    flat = _get_all()
    issues: list[dict[str, Any]] = []
    for group, field, env_key, msg in _REQUIRED:
        if not _effective(flat, f"{group}.{field}", env_key):
            issues.append({"group": group, "field": field, "message": msg})

    temp = _effective(flat, "llm.temperature", "LLM_TEMPERATURE")
    if not temp:
        issues.append({"group": "llm", "field": "temperature", "message": "未填写温度（建议 0.01 ~ 0.3）"})
    else:
        try:
            t = float(temp)
            if t < 0.01 or t > 0.3:
                issues.append({"group": "llm", "field": "temperature", "message": "温度需在 0.01 ~ 0.3 之间"})
        except ValueError:
            issues.append({"group": "llm", "field": "temperature", "message": "温度必须是数字"})

    runtime = config_errors.get_last()
    if runtime:
        issues.append({"group": runtime.get("group", ""), "field": runtime.get("field"),
                       "message": runtime.get("message", "最近一次运行因设置失败"), "runtime": True})

    return ok({"ok": len(issues) == 0, "issues": issues})


# ---------------- 学科网 Cookie 自动获取 ----------------
@router.post("/xueke/cookie/auto-read")
def xueke_cookie_auto_read():
    """方式二：从本机已登录浏览器读取学科网 Cookie。"""
    from shared.xueke_cookie import read_from_browser
    return ok(read_from_browser())


@router.post("/xueke/cookie/login/start")
def xueke_cookie_login_start():
    """方式一：打开学科网登录窗口，用户登录后点击 confirm 抓取。"""
    from shared.xueke_cookie import login_session
    return ok(login_session.start())


@router.post("/xueke/cookie/login/confirm")
def xueke_cookie_login_confirm():
    from shared.xueke_cookie import login_session
    return ok(login_session.confirm())


@router.post("/xueke/cookie/login/cancel")
def xueke_cookie_login_cancel():
    from shared.xueke_cookie import login_session
    return ok(login_session.cancel())


@router.get("/xueke/cookie/login/status")
def xueke_cookie_login_status():
    from shared.xueke_cookie import login_session
    return ok(login_session.status())
