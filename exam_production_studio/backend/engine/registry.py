"""试卷类型注册表（阶段三，设计文档 §6.2）。

读取 configs/{type}/config.json → ModeConfig；解析模板/规范绝对路径。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import config

CONFIGS_DIR = config.BASE_DIR / "configs"


@dataclass
class ModeConfig:
    type: str
    display_name: str
    plan_base: str
    need_mapping: bool
    need_mesh: bool
    need_split: bool
    pull_multiplier: int
    name_template: str
    default_volume_config: dict[str, Any]
    template_docx: Path | None
    spec_md: Path | None
    question_types_dir: Path | None
    config_dir: Path
    raw: dict[str, Any]


def _resolve(base: Path, rel: str | None) -> Path | None:
    if not rel:
        return None
    p = base / rel
    return p if p.exists() else None


@lru_cache(maxsize=None)
def get(paper_type: str) -> ModeConfig:
    cfg_dir = CONFIGS_DIR / paper_type
    cfg_path = cfg_dir / "config.json"
    if not cfg_path.exists():
        raise KeyError(f"未知试卷类型或缺少配置: {paper_type} ({cfg_path})")
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    return ModeConfig(
        type=data.get("type", paper_type),
        display_name=data.get("display_name", paper_type),
        plan_base=data.get("plan_base", "syllabus"),
        need_mapping=bool(data.get("need_mapping", True)),
        need_mesh=bool(data.get("need_mesh", False)),
        need_split=bool(data.get("need_split", False)),
        pull_multiplier=int(data.get("pull_multiplier", 1)),
        name_template=data.get("name_template", ""),
        default_volume_config=data.get("default_volume_config", {}),
        template_docx=_resolve(cfg_dir, data.get("template_docx")),
        spec_md=_resolve(cfg_dir, data.get("spec_md")),
        question_types_dir=_resolve(cfg_dir, data.get("question_types_dir")),
        config_dir=cfg_dir,
        raw=data,
    )


def all_types() -> list[str]:
    if not CONFIGS_DIR.exists():
        return []
    return sorted(p.name for p in CONFIGS_DIR.iterdir() if (p / "config.json").exists())
