"""配置类错误的分类与记录（精准红点用）。

区分「配置错误」与普通异常：只有配置错误才点亮前端「全局设置」红点。
运行时最近一次配置错误持久化到 settings 表键 `_runtime.config_error`（JSON），
供 GET /api/settings/check 读取；保存设置或流程正常完成时清除。
"""
from __future__ import annotations

import json
from typing import Any

import db

_KEY = "_runtime.config_error"


class ConfigError(Exception):
    """因用户配置（密钥/地址/模型/Cookie 等）导致的失败。

    group: 'llm' | 'xueke'；field: 具体字段（可为 None）；message: 面向用户的说明。
    """

    def __init__(self, group: str, field: str | None, message: str):
        super().__init__(message)
        self.group = group
        self.field = field
        self.message = message


def record(group: str, field: str | None, message: str) -> None:
    """记录最近一次运行时配置错误（覆盖式）。失败不抛出，避免影响主流程。"""
    try:
        payload = json.dumps(
            {"group": group, "field": field, "message": message, "time": db.query("SELECT datetime('now','localtime') AS t")[0]["t"]},
            ensure_ascii=False,
        )
        db.execute(
            "INSERT INTO settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (_KEY, payload),
        )
    except Exception:  # noqa: BLE001
        pass


def record_error(err: ConfigError) -> None:
    record(err.group, err.field, err.message)


def get_last() -> dict[str, Any] | None:
    """读取最近一次运行时配置错误；无则返回 None。"""
    try:
        row = db.query_one("SELECT value FROM settings WHERE key=?", (_KEY,))
    except Exception:  # noqa: BLE001
        return None
    if not row or not row.get("value"):
        return None
    try:
        return json.loads(row["value"])
    except (ValueError, TypeError):
        return None


def clear() -> None:
    """清除运行时配置错误标记（保存设置成功、或流程正常完成时调用）。"""
    try:
        db.execute("DELETE FROM settings WHERE key=?", (_KEY,))
    except Exception:  # noqa: BLE001
        pass
