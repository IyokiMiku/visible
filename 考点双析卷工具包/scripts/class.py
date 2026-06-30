"""
文档分类工具

功能：
  在脚本所在目录下创建"解析版"和"原卷版"两个文件夹，
  将文件名含"（解析版）"的 .docx 移入"解析版"文件夹，
  将文件名含"（原卷版）"的 .docx 移入"原卷版"文件夹。

用法：
  python class.py
"""

import os
import sys
import shutil


def main():
    base_dir = os.environ.get("EXAM_TOOL_WORKDIR")
    if not base_dir or not os.path.isdir(base_dir):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__)) or "."

    dir_jiexi = os.path.join(base_dir, "解析版")
    dir_yuanjuan = os.path.join(base_dir, "原卷版")

    os.makedirs(dir_jiexi, exist_ok=True)
    os.makedirs(dir_yuanjuan, exist_ok=True)

    moved_jiexi = 0
    moved_yuanjuan = 0

    for f in os.listdir(base_dir):
        if not f.endswith(".docx") or f.startswith("~"):
            continue

        src = os.path.join(base_dir, f)
        if not os.path.isfile(src):
            continue

        is_jiexi = "解析版" in f
        is_yuanjuan = "原卷版" in f

        if is_jiexi:
            dst = os.path.join(dir_jiexi, f)
            shutil.move(src, dst)
            print(f"  解析版 <- {f}")
            moved_jiexi += 1
        elif is_yuanjuan:
            dst = os.path.join(dir_yuanjuan, f)
            shutil.move(src, dst)
            print(f"  原卷版 <- {f}")
            moved_yuanjuan += 1

    print(f"\n完成：移动 {moved_jiexi} 个解析版，{moved_yuanjuan} 个原卷版。")

    if moved_jiexi == 0 and moved_yuanjuan == 0:
        print('未找到文件名含"解析版"或"原卷版"的 .docx 文件。')

    input("按 Enter 退出...")


if __name__ == "__main__":
    main()
