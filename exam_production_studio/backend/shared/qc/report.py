"""质检报告写入（阶段四 shared/qc，源 report 去硬编码：写入项目树）。"""
from __future__ import annotations

from pathlib import Path

from engine.drivers.base import QCResult


def _esc(text: str) -> str:
    """转义 Markdown 表格单元格中的竖线与换行。"""
    return str(text or "").replace("\n", " ").replace("|", "\\|")


def write_report(ctx, qc: QCResult) -> Path:
    out_dir = ctx.dir("质检报告")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"第{qc.paper_no}卷_质检报告.md"
    status = "通过" if qc.passed else "待人工审核"
    lines = [
        f"# 第{qc.paper_no}卷 质检报告",
        "",
        f"- 评分：{qc.score:.0f}/100",
        f"- 结论：{status}",
        f"- 题量完整度：{qc.completeness:.0%}",
        f"- 知识点覆盖：{qc.coverage:.0%}",
        f"- 格式校验：{'通过' if qc.format_ok else '不通过'}",
        f"- AI 风险：{qc.ai_risk}",
        "",
    ]

    if qc.structured:
        per_q = sorted((i for i in qc.structured if i.scope == "单题"),
                       key=lambda i: (i.question_no or 0))
        whole = [i for i in qc.structured if i.scope != "单题"]

        lines.append("## 单题问题")
        if per_q:
            lines.append("| 题号 | 严重度 | 类型 | 详情 |")
            lines.append("|---|---|---|---|")
            for i in per_q:
                lines.append(f"| {i.question_no} | {i.severity} | {_esc(i.type)} | {_esc(i.detail)} |")
        else:
            lines.append("- 无")

        lines += ["", "## 全卷 / 跨卷问题"]
        if whole:
            lines.append("| 范围 | 严重度 | 类型 | 详情 |")
            lines.append("|---|---|---|---|")
            for i in whole:
                loc = ("第" + "&".join(str(n) for n in i.related_nos) + "题") if i.related_nos else i.scope
                lines.append(f"| {_esc(loc)} | {i.severity} | {_esc(i.type)} | {_esc(i.detail)} |")
        else:
            lines.append("- 无")
    else:
        # 兜底：无结构化数据时沿用字符串列表
        lines.append("## 问题列表")
        lines += [f"- {i}" for i in qc.issues] if qc.issues else ["- 无"]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def append_error_report(ctx, paper_no: int, issues: list[str]) -> Path:
    """汇总错误到 生成结果/错误报告.md。"""
    out = ctx.dir("生成结果")
    out.mkdir(parents=True, exist_ok=True)
    path = out / "错误报告.md"
    block = [f"\n## 第{paper_no}卷"] + [f"- {i}" for i in issues] if issues else [f"\n## 第{paper_no}卷", "- 无"]
    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(block) + "\n")
    return path
