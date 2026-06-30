"""
待人工审核试卷处理工具

功能：
  1. 在工作目录中查找文件名包含"待人工审核"的 DOCX 文档；
  2. 按试卷序号从小到大逐一打开；
  3. 从同目录的"错误收集.md"读取该试卷的问题并显示在控制台；
  4. 人工审核通过后，去掉文件名中的"（待人工审核）"。

用法：
  双击运行，或在目标目录下执行：python fix.py
"""

import os
import re
from pathlib import Path


WORK_DIR = Path(__file__).resolve().parent
MANUAL_MARK = "（待人工审核）"


def _paper_seq(path: Path) -> int:
    """从文件名提取"第X卷"序号，用于排序。"""
    match = re.search(r"第\s*(\d+)\s*卷", path.name)
    return int(match.group(1)) if match else 10 ** 9


def _read_errors(work_dir: Path, paper_label: str) -> str:
    """从错误收集.md 中读取指定试卷的问题行。"""
    err_path = work_dir / "错误收集.md"
    if not err_path.exists():
        return "未找到错误收集.md。"

    lines = err_path.read_text(encoding="utf-8", errors="ignore").split("\n")
    matched = [line.strip() for line in lines if f"| {paper_label} |" in line]
    if matched:
        return "\n".join(matched)
    return f"错误收集.md 中未匹配到 {paper_label} 的问题记录。"


def _open_docx(path: Path) -> None:
    """用 Windows 默认关联程序打开 DOCX。"""
    try:
        os.startfile(str(path))
    except Exception:
        print(f"无法自动打开，请手动打开：{path}")


def _collect_pending(work_dir: Path) -> list[Path]:
    """收集工作目录中待人工审核的 DOCX，按卷号排序。"""
    files = []
    for p in work_dir.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() != ".docx" or p.name.startswith("~"):
            continue
        if MANUAL_MARK in p.name:
            files.append(p)
    return sorted(files, key=_paper_seq)


def main() -> None:
    print("=" * 60)
    print("  待人工审核试卷处理工具")
    print("=" * 60)
    print(f"工作目录：{WORK_DIR}")

    files = _collect_pending(WORK_DIR)
    if not files:
        print("\n未找到文件名包含「待人工审核」的 DOCX 文档。")
        input("按 Enter 退出...")
        return

    print(f"\n共 {len(files)} 个待审核文档，按试卷序号从小到大处理。")

    for idx, docx_path in enumerate(files, 1):
        seq = _paper_seq(docx_path)
        paper_label = f"第{seq}卷"

        print("\n" + "=" * 60)
        print(f"[{idx}/{len(files)}] {docx_path.name}")
        print("=" * 60)
        print("\n【该试卷质量问题】")
        print(_read_errors(WORK_DIR, paper_label))
        print("\n正在打开文档，请人工审核。")
        _open_docx(docx_path)

        answer = input(
            "\n审核通过并已关闭文档后，按 Enter 去掉「待人工审核」标记；"
            "输入 s 跳过；输入 q 退出："
        ).strip().lower()
        if answer == "q":
            print("已退出。")
            break
        if answer == "s":
            print("已跳过。")
            continue

        new_name = docx_path.name.replace(MANUAL_MARK, "")
        new_path = docx_path.parent / new_name
        while True:
            try:
                docx_path.rename(new_path)
                print(f"  ✓ 已重命名：{new_name}")
                break
            except PermissionError:
                input("  文件可能仍被占用，请关闭文档后按 Enter 重试...")

    print("\n处理完成。")
    input("按 Enter 退出...")


if __name__ == "__main__":
    main()
