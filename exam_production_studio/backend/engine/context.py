"""ProjectContext：业务变量 + 路径解析（阶段三，设计文档 §6.1）。

所有步骤只接收 ProjectContext，不再读写硬编码路径/省份。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import config


def parse_range(text: str, total: int | None = None) -> list[int]:
    """移植一课一练 runner._parse_generation_range。

    支持 all / 单序号 / 连续范围(1-5) / 逗号合并(3,7,12)。
    - "all"：给定 total 时返回 [1..total]；未给定 total 返回 []（由调用方按"全部"处理）。
    """
    s = str(text or "").strip()
    if not s:
        raise ValueError("卷号范围不能为空")
    if s.lower() == "all":
        return list(range(1, total + 1)) if total else []

    selected: list[int] = []
    for part in s.replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            bounds = [x.strip() for x in part.split("-", 1)]
            if len(bounds) != 2 or not bounds[0] or not bounds[1]:
                raise ValueError(f"无效范围: {part}")
            start, end = int(bounds[0]), int(bounds[1])
            if start > end:
                start, end = end, start
            selected.extend(range(start, end + 1))
        else:
            selected.append(int(part))
    if not selected:
        raise ValueError("卷号范围不能为空")
    return sorted(set(selected))


def project_root(project_id: str) -> Path:
    return config.BASE_DIR / "data" / "projects" / project_id


@dataclass
class ProjectContext:
    project_id: str
    paper_type: str
    province: str = ""
    exam_category: str = ""
    course: str = ""
    textbook: str = ""
    edition: str = ""
    exam_type_name: str = ""
    name_template: str = ""
    volume_config: dict[str, Any] = field(default_factory=dict)
    paper_range: str = "all"
    plan_source: str = "ocr"
    output_versions: list[str] = field(default_factory=lambda: ["原卷版", "解析版"])
    ai_options: dict[str, Any] = field(default_factory=dict)
    name: str = ""
    root: Path = field(default=Path("."))

    def __post_init__(self) -> None:
        if self.root == Path("."):
            self.root = project_root(self.project_id)

    # ---- 路径解析 ----
    def input_dir(self, name: str = "") -> Path:
        base = self.root / "03_输入"
        return base / name if name else base

    def dir(self, name: str) -> Path:
        """标准输出子目录（位于 04_生成输出 下）。"""
        return self.root / "04_生成输出" / name

    def ensure_dirs(self) -> None:
        for sub in (
            "知识点数量", "教材目录扫描", "生产规划", "_临时/API原始结果",
            "组卷待质检", "质检报告", "生成结果", "运行记录",
        ):
            self.dir(sub).mkdir(parents=True, exist_ok=True)
        self.input_dir().mkdir(parents=True, exist_ok=True)

    # ---- 业务派生 ----
    def pull_multiplier(self) -> int:
        return 2 if self.paper_type == "shuangxi" else 1

    def selected_papers(self, total: int | None = None) -> list[int]:
        return parse_range(self.paper_range, total)

    def confidence_threshold(self) -> float:
        return float(self.ai_options.get("match_threshold", 0.85))

    def max_fix_rounds(self) -> int:
        return int(self.ai_options.get("max_fix_rounds", 2))

    # ---- 构造 ----
    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ProjectContext":
        def _json(val: Any, default: Any) -> Any:
            if val is None or val == "":
                return default
            if isinstance(val, (dict, list)):
                return val
            try:
                return json.loads(val)
            except (TypeError, ValueError):
                return default

        return cls(
            project_id=row["id"],
            paper_type=row.get("paper_type", ""),
            province=row.get("province", "") or "",
            exam_category=row.get("exam_category", "") or "",
            course=row.get("course", "") or "",
            textbook=row.get("textbook", "") or "",
            edition=row.get("edition", "") or "",
            exam_type_name=row.get("exam_type_name", "") or "",
            name_template=row.get("name_template", "") or "",
            volume_config=_json(row.get("volume_config"), {}),
            paper_range=row.get("paper_range", "all") or "all",
            plan_source=row.get("plan_source", "ocr") or "ocr",
            output_versions=_json(row.get("output_versions"), ["原卷版", "解析版"]),
            ai_options=_json(row.get("ai_options"), {}),
            name=row.get("name", "") or "",
        )
