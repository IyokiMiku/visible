"""shared/qc：质检规则与报告。"""
from .rules import run_quality_checks
from .report import write_report, append_error_report

__all__ = ["run_quality_checks", "write_report", "append_error_report"]
