"""驱动公共实现（阶段六）：把通用流程委托给 engine.steps。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.drivers.base import PaperQuestions, QCResult
from engine.steps import assemble as step_assemble
from engine.steps import kpoint_count as step_kpoint
from engine.steps import mapping as step_mapping
from engine.steps import naming as step_naming
from engine.steps import planning as step_planning
from engine.steps import pull as step_pull
from engine.steps import qc as step_qc


class CommonDriver:
    type: str = ""
    flow_nodes: list[str] = []

    def kpoint_count(self, ctx) -> Path:
        return step_kpoint.kpoint_count(ctx)

    def gen_planning(self, ctx, source: str, force: bool = False) -> tuple[Path, list[dict[str, Any]]]:
        return step_planning.gen_planning(ctx, source, force)

    def gen_mapping(self, ctx) -> tuple[Path, list[dict[str, Any]]]:
        return step_mapping.gen_mapping(ctx)

    def gen_mesh(self, ctx) -> list[Path] | None:
        return None

    def confirm_naming(self, ctx, exam_info: dict) -> None:
        step_naming.confirm_naming(ctx, exam_info)

    def produce_questions(self, ctx, paper_no: int) -> tuple[PaperQuestions, list[dict[str, Any]]]:
        return step_pull.produce_questions(ctx, paper_no)

    def assemble(self, ctx, paper_no: int, qs: PaperQuestions) -> list[Path]:
        return step_assemble.assemble(ctx, paper_no, qs)

    def qc(self, ctx, paper_no: int, qs: PaperQuestions) -> tuple[QCResult, list[dict[str, Any]]]:
        return step_qc.qc(ctx, paper_no, qs)
