#!/usr/bin/env python3
"""规划表源头校验命令行入口。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from planning import load_planning_workbook, parse_paper_numbers  # noqa: E402
from paths import PLAN_DIR  # noqa: E402
from planning_validation import (  # noqa: E402
    ApiAssessOptions,
    assess_api_coverage,
    build_report_dict,
    print_console_summary,
    validate_planning_structure,
    write_json_report,
    write_markdown_report,
)


def parse_papers(raw: str | None) -> set[int] | None:
    if not raw:
        return None
    numbers = parse_paper_numbers(raw)
    if numbers:
        return set(numbers)
    result: set[int] = set()
    for part in raw.replace("，", ",").replace("、", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            if start.strip().isdigit() and end.strip().isdigit():
                a, b = int(start), int(end)
                if a > b:
                    a, b = b, a
                result.update(range(a, b + 1))
        elif part.isdigit():
            result.add(int(part))
    return result or None


def parse_scope(raw: str) -> set[str]:
    value = (raw or "point").strip().lower()
    if value == "all":
        return {"all"}
    aliases = {
        "point": "point",
        "考点": "point",
        "topic": "topic",
        "专题": "topic",
        "course": "course",
        "综合": "course",
    }
    scope = {aliases.get(part.strip(), part.strip()) for part in value.replace("，", ",").split(",") if part.strip()}
    return scope or {"point"}


def find_default_plan() -> Path:
    candidates = sorted(path for path in PLAN_DIR.rglob("*考点规划总表.xlsx") if not path.name.startswith("~$"))
    if not candidates:
        raise SystemExit(f"未在 {PLAN_DIR} 下找到 *考点规划总表.xlsx，请用 --plan 指定。")
    if len(candidates) > 1:
        print("找到多个规划表，请用 --plan 指定其中一个：", file=sys.stderr)
        for path in candidates:
            print(f"- {path}", file=sys.stderr)
        raise SystemExit(2)
    return candidates[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验考纲百套卷规划表源头质量，并可选评估 API 覆盖风险。")
    parser.add_argument("--plan", help="考点规划总表 xlsx 路径；不传则尝试在生产规划目录中自动查找。")
    parser.add_argument("--api-assess", action="store_true", help="开启 API 覆盖评估。默认只做本地结构校验。")
    parser.add_argument("--api-dry-run", action="store_true", help="只解析课程/题型/知识点映射，不真正请求 API。")
    parser.add_argument("--papers", help="API 评估限定卷号，如 1-20,34。结构校验始终全量执行。")
    parser.add_argument("--scope", default="point", help="API 评估范围：point、point,topic、all。默认 point。")
    parser.add_argument("--page-size", type=int, default=50, help="API 每次取样数量下限，默认 50。")
    parser.add_argument("--cookie", help="显式传入 API Cookie；不传则使用 XKW_COOKIE 或配置文件。")
    parser.add_argument("--timeout", type=int, default=30, help="API 请求超时秒数，默认 30。")
    parser.add_argument("--json-out", help="输出 JSON 报告路径。")
    parser.add_argument("--md-out", help="输出 Markdown 报告路径。")
    parser.add_argument("--fail-on", choices=["error", "critical-api"], default="error", help="控制退出码。默认结构 error 非 0。")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    plan_path = Path(args.plan) if args.plan else find_default_plan()
    if not plan_path.exists():
        print(f"规划表不存在：{plan_path}", file=sys.stderr)
        return 2

    try:
        meta, rows, paper_index = load_planning_workbook(plan_path)
    except Exception as exc:
        print(f"读取规划表失败：{exc}", file=sys.stderr)
        return 2

    issues = validate_planning_structure(meta, rows, paper_index)
    api_options = ApiAssessOptions(
        enabled=args.api_assess,
        dry_run=args.api_dry_run,
        papers=parse_papers(args.papers),
        scope=parse_scope(args.scope),
        page_size=args.page_size,
        cookie=args.cookie,
        timeout=args.timeout,
    )
    api_coverage, api_issues = assess_api_coverage(meta, paper_index, api_options)
    issues.extend(api_issues)

    report = build_report_dict(meta, paper_index, issues, api_coverage)
    print_console_summary(report)

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        write_json_report(out, report)
        print(f"JSON报告：{out}")
    if args.md_out:
        out = Path(args.md_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        write_markdown_report(out, report)
        print(f"Markdown报告：{out}")

    issue_counts = report["summary"]["issue_counts"]
    risk_counts = report["summary"]["api_risk_counts"]
    if args.fail_on == "error" and issue_counts.get("error", 0) > 0:
        return 1
    if args.fail_on == "critical-api" and (issue_counts.get("error", 0) > 0 or risk_counts.get("critical", 0) > 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
