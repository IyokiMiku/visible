"""配置与密钥加载（阶段一：配置与密钥外置）。

凭据来源优先级：settings 表（用户在全局设置页填写）> .env > 内置默认。
源码中不保存任何明文密钥。
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv 未安装时不致命
    load_dotenv = None

# 项目根目录：backend/ 的上一级
BASE_DIR = Path(__file__).resolve().parent.parent

if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env")


def _env(key: str, default: str = "") -> str:
    value = os.getenv(key)
    return value if value is not None else default


def get_db_path() -> Path:
    """SQLite 路径，默认 data/studio.db，相对路径相对项目根解析。"""
    raw = _env("STUDIO_DB", "data/studio.db")
    path = Path(raw)
    return path if path.is_absolute() else BASE_DIR / path


def _load_settings() -> dict[str, str]:
    """读取 settings 表（key/value）。表/库不存在时返回空字典（阶段二前的兼容）。"""
    db_path = get_db_path()
    if not db_path.exists():
        return {}
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return {}
    return {str(k): ("" if v is None else str(v)) for k, v in rows}


def _merge(settings: dict[str, str], setting_key: str, env_key: str, default: str = "") -> str:
    """settings 表优先，其次 .env，最后默认；空字符串视为未设置。"""
    db_value = settings.get(setting_key, "").strip()
    if db_value:
        return db_value
    env_value = _env(env_key, "").strip()
    if env_value:
        return env_value
    return default


def get_llm_config() -> dict[str, Any]:
    s = _load_settings()
    return {
        "api_key": _merge(s, "llm.api_key", "LLM_API_KEY"),
        "base_url": _merge(s, "llm.base_url", "LLM_BASE_URL", "https://api.openai.com/v1"),
        "model": _merge(s, "llm.model", "LLM_MODEL", "gpt-4o"),
    }


def get_xueke_config() -> dict[str, Any]:
    s = _load_settings()
    return {
        "cookie": _merge(s, "xueke.cookie", "XKW_COOKIE"),
        "app_key": _merge(s, "xueke.app_key", "XKW_APP_KEY"),
        "sign": _merge(s, "xueke.sign", "XKW_SIGN"),
    }


def _default_desktop() -> Path:
    """探测桌面目录（兼容 OneDrive 重定向与中文“桌面”）。"""
    home = Path.home()
    candidates: list[Path] = []
    for env_key in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        v = os.getenv(env_key)
        if v:
            candidates.append(Path(v) / "Desktop")
    candidates += [home / "Desktop", home / "桌面"]
    for c in candidates:
        try:
            if c.exists():
                return c
        except OSError:
            continue
    return home / "Desktop"


def get_output_root() -> Path:
    """成品归档根目录：settings(output.dir) > .env(OUTPUT_DIR) > 默认 桌面/生成结果。

    相对路径相对项目根解析。
    """
    s = _load_settings()
    raw = _merge(s, "output.dir", "OUTPUT_DIR", "").strip()
    if raw:
        p = Path(raw)
        return p if p.is_absolute() else BASE_DIR / p
    return _default_desktop() / "生成结果"


def get_export_root() -> Path:
    """规划表等「生产规划」产物的导出根目录。

    settings(output.export_dir) > .env(EXPORT_DIR) > 默认 桌面/输出结果。
    规划表/映射表/细目表导出到 <此根>/生产规划/{产品名}/{省份}_{考类}/。
    """
    s = _load_settings()
    raw = _merge(s, "output.export_dir", "EXPORT_DIR", "").strip()
    if raw:
        p = Path(raw)
        return p if p.is_absolute() else BASE_DIR / p
    return _default_desktop() / "输出结果"


def get_ai_trace_config() -> dict[str, Any]:
    """AI 调用追踪（把每次 LLM 的 prompt/响应落盘，供排查）。

    enabled：settings(ai.trace_enabled) > .env(AI_TRACE_ENABLED) > 默认 true。
    keep_runs：只保留最近 N 次运行的记录目录，默认 10。
    """
    s = _load_settings()
    enabled_raw = _merge(s, "ai.trace_enabled", "AI_TRACE_ENABLED", "true").strip().lower()
    keep_raw = _merge(s, "ai.trace_keep_runs", "AI_TRACE_KEEP_RUNS", "10").strip()
    try:
        keep_runs = int(keep_raw)
    except ValueError:
        keep_runs = 10
    return {
        "enabled": enabled_raw not in ("0", "false", "no", "off", ""),
        "keep_runs": max(1, keep_runs),
    }


def get_vision_config() -> dict[str, Any]:
    """视觉模型配置（预留）。未配置 api_key 时 enabled=False。"""
    s = _load_settings()
    cfg = {
        "api_key": _merge(s, "vision.api_key", "VISION_API_KEY"),
        "base_url": _merge(s, "vision.base_url", "VISION_BASE_URL"),
        "model": _merge(s, "vision.model", "VISION_MODEL"),
    }
    cfg["enabled"] = bool(cfg["api_key"])
    return cfg


if __name__ == "__main__":
    print("STUDIO_DB:", get_db_path())
    print("LLM     :", get_llm_config())
    print("XUEKE   :", get_xueke_config())
    print("VISION  :", get_vision_config())
