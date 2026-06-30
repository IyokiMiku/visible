"""质检报告输出工具。"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any


def write_report(report: dict[str, Any], path: str | Path) -> None:
    """写出 JSON 质检报告。"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def summarize_report(
    question_reports: list[dict[str, Any]], paper_issues: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """汇总单题和全卷质检结果。"""
    total = len(question_reports)
    status_counts = Counter(item.get("status") or "unknown" for item in question_reports)
    issue_counts: Counter[str] = Counter()

    for item in question_reports:
        for issue in item.get("issues") or []:
            issue_counts[str(issue.get("name") or issue.get("code") or "未命名问题")] += 1
    for issue in paper_issues or []:
        issue_counts[str(issue.get("name") or issue.get("code") or "未命名问题")] += 1

    return {
        "total": total,
        "passed": status_counts.get("passed", 0),
        "failed": status_counts.get("failed", 0),
        "warning": status_counts.get("warning", 0),
        "paper_issues": len(paper_issues or []),
        "issue_counts": dict(issue_counts),
    }


def _paper_meta(paper: Any) -> dict[str, Any]:
    meta = getattr(paper, "meta", None)
    return {
        "paper_no": getattr(paper, "paper_no", None),
        "paper_label": getattr(paper, "paper_label", ""),
        "paper_type": getattr(paper, "paper_type", ""),
        "module": getattr(paper, "module", ""),
        "topic": getattr(paper, "topic", ""),
        "point_name": getattr(paper, "point_name", ""),
        "province": getattr(meta, "province", "") if meta else "",
        "exam_category": getattr(meta, "exam_category", "") if meta else "",
    }


def build_quality_report(
    paper: Any,
    loaded_paper: Any,
    question_reports: list[dict[str, Any]],
    paper_issues: list[dict[str, Any]],
    loaded_questions_path: str | Path | None = None,
) -> dict[str, Any]:
    """构建单卷结构化质检报告。"""
    return {
        "paper": _paper_meta(paper),
        "source": {
            "manual_paper_path": str(getattr(loaded_paper, "path", "")),
            "loaded_questions_path": str(loaded_questions_path or ""),
            "blueprint_path": str(getattr(paper, "blueprint_path", "") or ""),
        },
        "loaded_paper": {
            "paper_label": getattr(loaded_paper, "paper_label", ""),
            "title": getattr(loaded_paper, "title", ""),
            "warnings": list(getattr(loaded_paper, "warnings", []) or []),
        },
        "summary": summarize_report(question_reports, paper_issues),
        "paper_issues": paper_issues,
        "questions": question_reports,
    }


def _escape_md(value: Any) -> str:
    text = str(value or "")
    text = text.replace("|", "\\|").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return text.strip()


def _issue_names(issues: list[dict[str, Any]]) -> str:
    if not issues:
        return ""
    return "；".join(_escape_md(issue.get("name") or issue.get("code")) for issue in issues)


def _issue_messages(issues: list[dict[str, Any]]) -> str:
    if not issues:
        return ""
    return "；".join(_escape_md(issue.get("message") or issue.get("name")) for issue in issues)


def render_markdown_report(report: dict[str, Any]) -> str:
    """渲染 Markdown 质检报告。"""
    paper = report.get("paper") or {}
    source = report.get("source") or {}
    loaded = report.get("loaded_paper") or {}
    summary = report.get("summary") or {}
    paper_label = paper.get("paper_label") or "未命名试卷"

    lines: list[str] = [f"# {paper_label} 质检报告", ""]
    lines.extend(
        [
            "## 总览",
            "",
            f"- 卷型：{_escape_md(paper.get('paper_type'))}",
            f"- 地区/考类：{_escape_md(' '.join(part for part in [paper.get('province'), paper.get('exam_category')] if part))}",
            f"- 知识模块：{_escape_md(paper.get('module'))}",
            f"- 专题/考点：{_escape_md(paper.get('topic') or paper.get('point_name'))}",
            f"- 人工组卷文件：`{_escape_md(source.get('manual_paper_path'))}`",
            f"- 拆题结果：`{_escape_md(source.get('loaded_questions_path'))}`",
            f"- 细目表：`{_escape_md(source.get('blueprint_path') or '无')}`",
            f"- 拆题数量：{summary.get('total', 0)}",
            f"- 质检结果：通过 {summary.get('passed', 0)}，失败 {summary.get('failed', 0)}，警告 {summary.get('warning', 0)}，全卷问题 {summary.get('paper_issues', 0)}",
            "",
        ]
    )

    warnings = loaded.get("warnings") or []
    if warnings:
        lines.extend(["## 拆题提示", ""])
        for warning in warnings:
            lines.append(f"- {_escape_md(warning)}")
        lines.append("")

    issue_counts = summary.get("issue_counts") or {}
    if issue_counts:
        lines.extend(["## 问题类型统计", "", "| 问题 | 数量 |", "|---|---:|"])
        for name, count in issue_counts.items():
            lines.append(f"| {_escape_md(name)} | {count} |")
        lines.append("")

    lines.extend(["## 全卷问题", ""])
    paper_issues = report.get("paper_issues") or []
    if paper_issues:
        lines.extend(["| 严重级别 | 问题 | 说明 |", "|---|---|---|"])
        for issue in paper_issues:
            lines.append(
                f"| {_escape_md(issue.get('severity'))} | {_escape_md(issue.get('name'))} | {_escape_md(issue.get('message'))} |"
            )
    else:
        lines.append("无。")
    lines.append("")

    lines.extend(["## 逐题结果", "", "| 题号 | 题型 | 期望题型 | 状态 | 问题 |", "|---:|---|---|---|---|"])
    for item in report.get("questions") or []:
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_md(item.get("question_no")),
                    _escape_md(item.get("question_type")),
                    _escape_md(item.get("expected_type")),
                    _escape_md(item.get("status")),
                    _issue_names(item.get("issues") or []),
                ]
            )
            + " |"
        )
    lines.append("")

    problem_questions = [item for item in report.get("questions") or [] if item.get("issues")]
    lines.extend(["## 失败/警告题目", ""])
    if problem_questions:
        for item in problem_questions:
            lines.append(f"### 第{_escape_md(item.get('question_no'))}题（{_escape_md(item.get('status'))}）")
            lines.append("")
            if item.get("stem_preview"):
                lines.append(f"> {_escape_md(item.get('stem_preview'))}")
                lines.append("")
            lines.append(_issue_messages(item.get("issues") or []))
            lines.append("")
    else:
        lines.append("无失败或警告题目。")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_markdown_report(report: dict[str, Any], path: str | Path) -> None:
    """写出 Markdown 质检报告。"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_markdown_report(report), encoding="utf-8")
