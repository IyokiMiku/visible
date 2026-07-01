"""ModeDriver 协议与共享数据结构（阶段三，设计文档 §6.3）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass
class Question:
    number: int
    qtype: str                      # 单项选择题/填空题/判断题/简答题/综合应用题...
    stem: str
    options: list[str] = field(default_factory=list)  # 选择题选项文本（不含 A./B.）
    answer: str = ""
    analysis: str = ""
    difficulty: str = "简单"        # 简单/适中/困难
    kpoint: str = ""
    source: str = "xueke"           # xueke | ai
    confidence: float = 1.0
    # 富内容：题干图片 + 与 options 对齐的选项图片（每个元素为该选项的图片列表）。
    # 图片条目形如 {"url":..,"width":..,"height":..,"local_path":..}（local_path 由下载层补齐）。
    stem_images: list[dict] = field(default_factory=list)
    option_images: list[list[dict]] = field(default_factory=list)


@dataclass
class PaperQuestions:
    paper_no: int
    questions: list[Question] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def adopted(self) -> int:
        return sum(1 for q in self.questions if q.source == "xueke")

    @property
    def ai_filled(self) -> int:
        return sum(1 for q in self.questions if q.source == "ai")


@dataclass
class QCIssue:
    """结构化质检问题（供审阅页把问题挂到对应题目/全卷）。

    scope: 单题 | 全卷 | 跨卷
    code: 稳定机器键（如 option_length_imbalance），供审阅页绑定修复动作
    question_no: 单题问题的题号；全卷/跨卷为 None
    related_nos: 涉及多题时（如题干查重）记录相关题号
    severity: 严重 | 警告 | 信息
    """
    scope: str
    type: str
    severity: str
    detail: str
    code: str = ""
    question_no: int | None = None
    related_nos: list[int] = field(default_factory=list)

    def to_text(self) -> str:
        """人类可读单行文本（向后兼容旧的 issues: list[str]）。"""
        if self.question_no is not None:
            loc = f"第{self.question_no}题"
        elif self.related_nos:
            loc = "第" + "&".join(str(n) for n in self.related_nos) + "题"
        else:
            loc = self.scope
        return f"[{loc}] {self.type}：{self.detail}"


@dataclass
class QCResult:
    paper_no: int
    score: float
    passed: bool
    issues: list[str] = field(default_factory=list)
    structured: list[QCIssue] = field(default_factory=list)
    report_path: Path | None = None
    completeness: float = 1.0
    coverage: float = 1.0
    format_ok: bool = True
    ai_risk: str = "低"


@runtime_checkable
class ModeDriver(Protocol):
    """类型驱动协议（设计文档 §6.3）。

    实现说明：产出待确认事项的方法额外返回 reviews 列表，便于 runner 统一入队/暂停。
    """
    type: str
    flow_nodes: list[str]

    def kpoint_count(self, ctx) -> Path: ...
    def gen_planning(self, ctx, source: str) -> tuple[Path, list[dict[str, Any]]]: ...
    def gen_mapping(self, ctx) -> tuple[Path, list[dict[str, Any]]]: ...
    def gen_mesh(self, ctx) -> list[Path] | None: ...
    def confirm_naming(self, ctx, exam_info: dict) -> None: ...
    def produce_questions(self, ctx, paper_no: int) -> tuple[PaperQuestions, list[dict[str, Any]]]: ...
    def assemble(self, ctx, paper_no: int, qs: PaperQuestions) -> list[Path]: ...
    def qc(self, ctx, paper_no: int, qs: PaperQuestions) -> tuple[QCResult, list[dict[str, Any]]]: ...
