"""考纲百套卷命令行入口。

运行后提供两个模式：
  1. 质检修复模式：对 组卷待质检 中的 DOCX 进行质检 + AI 修复 + 生成试卷
  2. 仅生成模式：重新调用学科网 API 拉取题目 + AI 补题，覆盖组卷待质检，再质检修复
"""
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR / "01_工具脚本"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from 生成器.runner import main as run_main


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  考纲百套卷 — 试卷生成系统")
    print("=" * 60)
    print()
    print("请选择运行模式：")
    print("  1. 质检修复模式 — 对「组卷待质检」中的 DOCX 进行质检 + AI 修复 + 生成试卷")
    print("  2. 仅生成模式 — 重新拉取题目 + 质检修复（覆盖已有文件）")
    print()

    while True:
        choice = input("请输入 1 或 2：").strip()
        if choice in ("1", "2"):
            break
        print("无效输入，请重新输入。")

    print(f"\n已选择模式 {choice}：{'质检修复模式' if choice == '1' else '仅生成模式'}")
    print()
    run_main(mode=int(choice))
