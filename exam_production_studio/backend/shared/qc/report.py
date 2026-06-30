"""质检报告写入（阶段四 shared/qc，源 report 去硬编码：写入项目树）。"""
from __future__ import annotations

from pathlib import Path

from engine.drivers.base import QCResult


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
        "## 问题列表",
    ]
    if qc.issues:
        lines += [f"- {i}" for i in qc.issues]
    else:
        lines.append("- 无")
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
