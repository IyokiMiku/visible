"""
文档分类工具

功能：
  在脚本所在目录下创建"解析版"、"原卷版"和"压缩包"三个文件夹，
  将文件名含"（解析版）"的 .docx 移入"解析版"文件夹，
  将文件名含"（原卷版）"的 .docx 移入"原卷版"文件夹，
  将压缩包文件移入"压缩包"文件夹。

用法：
  python class.py
"""

import os
import sys
import shutil


ARCHIVE_EXTENSIONS = {
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".tgz",
    ".tbz2",
    ".txz",
}


def main():
    base_dir = os.environ.get("EXAM_TOOL_WORKDIR")
    if not base_dir or not os.path.isdir(base_dir):
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__)) or "."

    dir_jiexi = os.path.join(base_dir, "解析版")
    dir_yuanjuan = os.path.join(base_dir, "原卷版")
    dir_archive = os.path.join(base_dir, "压缩包")

    os.makedirs(dir_jiexi, exist_ok=True)
    os.makedirs(dir_yuanjuan, exist_ok=True)
    os.makedirs(dir_archive, exist_ok=True)

    moved_jiexi = 0
    moved_yuanjuan = 0
    moved_archive = 0

    for f in os.listdir(base_dir):
        if f.startswith("~") or "待人工审核" in f:
            continue

        src = os.path.join(base_dir, f)
        if not os.path.isfile(src):
            continue

        lower_name = f.lower()
        is_archive = any(lower_name.endswith(ext) for ext in ARCHIVE_EXTENSIONS)
        if is_archive:
            dst = os.path.join(dir_archive, f)
            shutil.move(src, dst)
            print(f"  压缩包 <- {f}")
            moved_archive += 1
            continue

        if not lower_name.endswith(".docx"):
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

    print(f"\n完成：移动 {moved_jiexi} 个解析版，{moved_yuanjuan} 个原卷版，{moved_archive} 个压缩包。")

    if moved_jiexi == 0 and moved_yuanjuan == 0 and moved_archive == 0:
        print('未找到文件名含"解析版"或"原卷版"的 .docx 文件，也未找到压缩包文件。')

    input("按 Enter 退出...")


if __name__ == "__main__":
    main()
