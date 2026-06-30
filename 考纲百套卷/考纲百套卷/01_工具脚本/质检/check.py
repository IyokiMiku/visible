"""旧版质检兼容层（已废弃）。

所有质检功能已迁移到 rules.py / report.py。
本文件保留作为兼容入口，内部全部委托给新版模块。
"""

from .rules import (
    _is_duplicate_stem_pair,
    make_issue,
    normalize_question_type,
    run_quality_checks,
)
from .report import build_quality_report, write_markdown_report

# 兼容旧调用
local_check = run_quality_checks  # type: ignore[assignment]
_text_similarity = lambda a, b: _is_duplicate_stem_pair(a, b)[1]  # type: ignore[assignment]

__all__ = [
    "_is_duplicate_stem_pair",
    "_text_similarity",
    "build_quality_report",
    "local_check",
    "make_issue",
    "normalize_question_type",
    "run_quality_checks",
    "write_markdown_report",
]
