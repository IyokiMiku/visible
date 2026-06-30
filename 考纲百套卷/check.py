"""考纲百套卷双击质检与定向修复入口（新版结构化质检）。

双击运行后，从 04_生成输出/组卷待质检 中选择考类和试卷，
使用 paper_loader.py + rules.py 执行结构化质检；
未通过时可调用 regenerator.py 定向修复问题题目。
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR / "01_工具脚本"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

PENDING_DIR = BASE_DIR / "04_生成输出" / "组卷待质检"
REPORT_DIR = BASE_DIR / "04_生成输出" / "质检报告"


def _display_path(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _is_allowed_pending_file(path: Path) -> bool:
    name = path.name
    stem = path.stem.lower()
    if name.startswith("~$"):
        return False
    if path.suffix.lower() == ".docx" and stem.endswith("_repaired"):
        return False
    artifact_markers = (
        "questions_repaired",
        "（待人工审核）",
        "(待人工审核)",
        "考纲百套卷（解析版）",
        "考纲百套卷（原卷版）",
        "考纲百套卷(解析版)",
        "考纲百套卷(原卷版)",
    )
    return not any(marker in name for marker in artifact_markers)


def _select_exam_category() -> list[Path]:
    if not PENDING_DIR.exists():
        print("未找到组卷待质检目录。")
        print(f"请先将待质检试卷放入: {PENDING_DIR}")
        return []

    categories = sorted([p for p in PENDING_DIR.iterdir() if p.is_dir()])
    root_files = sorted(p for p in PENDING_DIR.glob("*.txt") if _is_allowed_pending_file(p)) + sorted(
        p for p in PENDING_DIR.glob("*.docx") if _is_allowed_pending_file(p)
    )

    if not categories and not root_files:
        print("组卷待质检目录中没有找到 .txt 或 .docx 文件。")
        return []

    if not categories:
        return [PENDING_DIR]

    print("\n请选择考类：")
    for i, category in enumerate(categories, 1):
        print(f"  {i}. {category.name}")
    if root_files:
        print(f"  {len(categories) + 1}. 根目录文件")

    choice = input("\n请选择编号: ").strip()
    try:
        idx = int(choice) - 1
        if root_files and idx == len(categories):
            return [PENDING_DIR]
        return [categories[idx]]
    except (ValueError, IndexError):
        return []


def _select_files(search_roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in search_roots:
        if root == PENDING_DIR:
            files.extend(p for p in sorted(root.glob("*.txt")) if _is_allowed_pending_file(p))
            files.extend(p for p in sorted(root.glob("*.docx")) if _is_allowed_pending_file(p))
        else:
            files.extend(p for p in sorted(root.rglob("*.txt")) if _is_allowed_pending_file(p))
            files.extend(p for p in sorted(root.rglob("*.docx")) if _is_allowed_pending_file(p))

    files = sorted(dict.fromkeys(files))
    if not files:
        print("选中的目录中没有 .txt 或 .docx 文件。")
        return []

    print("\n可质检试卷：")
    for i, fp in enumerate(files, 1):
        print(f"  {i}. {_display_path(fp, PENDING_DIR)}")

    choice = input("\n请选择（编号 或 all）: ").strip().lower()
    if choice in ("all", "全部"):
        return files
    try:
        return [files[int(choice) - 1]]
    except (ValueError, IndexError):
        return []


def _pause() -> None:
    try:
        input("\n按回车退出...")
    except EOFError:
        pass


def main() -> None:
    print("=" * 60)
    print("考纲百套卷试卷质检工具（新版结构化质检）")
    print("=" * 60)

    roots = _select_exam_category()
    if not roots:
        _pause()
        return

    files = _select_files(roots)
    if not files:
        _pause()
        return

    from 生成器.paper_loader import load_manual_paper
    from 生成器.paper_loader import LoadedPaper
    from 质检.rules import run_quality_checks
    from 质检.report import build_quality_report, render_markdown_report, write_markdown_report
    from 生成器.planning import PaperPlan, POINT_PAPER_TYPE

    for file_path in files:
        print(f"\n▶ 检查: {_display_path(file_path, PENDING_DIR)}")

        try:
            # 构造一个占位 PaperPlan（仅用于报告）
            paper = PaperPlan(
                paper_no=0,
                paper_label=file_path.stem,
                paper_type=POINT_PAPER_TYPE,
                module="",
                topic="",
                point_name="",
                rows=[],
                point_content="",
            )

            loaded = load_manual_paper(file_path, paper)
            if not loaded or not loaded.questions:
                print("  未解析到任何题目，请检查文件格式。")
                continue

            print(f"  解析题数: {len(loaded.questions)}")

            # 结构化质检
            question_reports, paper_issues = run_quality_checks(paper, loaded.questions)

            # 构建和输出报告
            report = build_quality_report(paper, loaded, question_reports, paper_issues, file_path)
            summary = report.get("summary") or {}
            print(
                f"  质检完成: 通过 {summary.get('passed', 0)}, "
                f"失败 {summary.get('failed', 0)}, "
                f"警告 {summary.get('warning', 0)}"
            )

            # 保存 MD 报告到质检报告目录
            category_name = file_path.parent.name
            report_subdir = REPORT_DIR / category_name
            report_subdir.mkdir(parents=True, exist_ok=True)
            md_path = report_subdir / f"{file_path.stem}_质检报告.md"
            write_markdown_report(report, md_path)
            print(f"  报告: {md_path}")

        except Exception as exc:
            print(f"  处理失败: {exc}")

    _pause()


if __name__ == "__main__":
    main()
