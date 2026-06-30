"""
待人工审核 DOCX 处理工具

功能：
  1. 在工作目录中查找文件名包含“待人工审核”的 DOCX 文档；
  2. 按“第X练”序号从小到大逐一用系统默认程序（通常为 WPS/Word）打开；
  3. 从同目录的“质检报告.md”读取该试卷的问题并显示在控制台；
  4. 人工审核通过后，在控制台按 Enter：
     - 去掉文件名中的“（待人工审核）”；
     - 生成对应“原卷版”；
     - 将解析版+原卷版打包为 zip；
     - 将解析版移动到“解析版”文件夹，原卷版移动到“原卷版”文件夹。

用法：
  双击运行，或在目标目录下执行：python fix.py

说明：
  若双击本脚本，默认处理脚本所在目录。
  也可设置环境变量 EXAM_TOOL_WORKDIR 指定要处理的目录。
"""

import os
import re
import shutil
import sys
import zipfile
from pathlib import Path


def _find_generator_dir():
    """向上查找项目根目录中的生成器目录，兼容脚本被复制到生成结果目录后运行。"""
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "01_工具脚本" / "生成器"
        if (candidate / "postprocess.py").exists():
            return candidate
    return None


GENERATOR_DIR = _find_generator_dir()
if GENERATOR_DIR and str(GENERATOR_DIR) not in sys.path:
    sys.path.insert(0, str(GENERATOR_DIR))

try:
    from postprocess import _convert_to_blank
except Exception as exc:
    _convert_to_blank = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


MANUAL_REVIEW_MARKS = ("（待人工审核）", "(待人工审核)", "待人工审核")


def _get_work_dir():
    """获取工作目录：优先环境变量，其次脚本所在目录。"""
    env_dir = os.environ.get("EXAM_TOOL_WORKDIR")
    if env_dir and os.path.isdir(env_dir):
        return Path(env_dir).resolve()
    return Path(__file__).resolve().parent


def _question_seq(path):
    """从文件名提取“第X练”序号，用于排序。"""
    match = re.search(r"第\s*(\d+)\s*练", path.name)
    return int(match.group(1)) if match else 10**9


def _clean_manual_review_name(filename):
    """去掉待人工审核标记，并清理多余空格。"""
    cleaned = filename
    for mark in MANUAL_REVIEW_MARKS:
        cleaned = cleaned.replace(mark, "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _safe_rename(src, dst):
    """重命名文件；若文档仍被 WPS/Word 占用，提示关闭后重试。"""
    while True:
        try:
            src.rename(dst)
            return dst
        except PermissionError:
            input("\n文件可能仍被 WPS/Word 占用。请保存并关闭该文档后，按 Enter 重试...")
        except FileExistsError:
            raise FileExistsError(f"目标文件已存在，无法重命名：{dst}")


def _read_report_section(work_dir, seq):
    """从质检报告.md 中读取指定第X练的问题段落。"""
    report_path = work_dir / "质检报告.md"
    if not report_path.exists():
        return "未找到质检报告.md，无法显示该试卷的问题。"

    text = report_path.read_text(encoding="utf-8", errors="ignore")
    pattern = re.compile(
        rf"(^##\s*第\s*{seq}\s*练[^\n]*\n.*?)(?=^##\s*第\s*\d+\s*练|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    matches = pattern.findall(text)
    if matches:
        return "\n".join(section.strip() for section in matches).strip()
    return f"质检报告.md 中未匹配到第{seq}练的问题记录。"


def _open_docx(path):
    """用 Windows 默认关联程序打开 DOCX。默认程序设为 WPS 时会用 WPS 打开。"""
    try:
        os.startfile(str(path))
    except AttributeError:
        print(f"当前系统不支持 os.startfile，请手动打开：{path}")
    except Exception as exc:
        print(f"打开文档失败，请手动打开：{path}\n原因：{exc}")


def _make_unique_path(path):
    """目标存在时自动追加编号，避免覆盖旧文件。"""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    idx = 2
    while True:
        candidate = parent / f"{stem}_{idx}{suffix}"
        if not candidate.exists():
            return candidate
        idx += 1


def _create_original_docx(jiexi_path):
    """由解析版生成原卷版。"""
    if _convert_to_blank is None:
        raise RuntimeError(f"无法导入原卷版生成函数：{_IMPORT_ERROR}")
    if "解析版" not in jiexi_path.name:
        raise ValueError(f"文件名不含“解析版”，无法生成原卷版：{jiexi_path.name}")

    yuanjuan_name = jiexi_path.name.replace("解析版", "原卷版")
    yuanjuan_path = _make_unique_path(jiexi_path.parent / yuanjuan_name)
    _convert_to_blank(str(jiexi_path), str(yuanjuan_path))
    return yuanjuan_path


def _base_zip_name(jiexi_path):
    """按后处理脚本的命名规则生成 zip 文件名。"""
    base = re.sub(r"[（(]解析版[）)].*$", "", jiexi_path.stem).strip()
    if not base:
        base = jiexi_path.stem.replace("解析版", "").strip()
    return f"{base}.zip"


def _create_zip(work_dir, jiexi_path, yuanjuan_path):
    """将解析版和原卷版打包为 zip，zip 留在工作目录根部。"""
    zip_path = _make_unique_path(work_dir / _base_zip_name(jiexi_path))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(jiexi_path, jiexi_path.name)
        zf.write(yuanjuan_path, yuanjuan_path.name)
    return zip_path


def _classify_files(work_dir, jiexi_path, yuanjuan_path, zip_path=None):
    """将解析版、原卷版、压缩包分别移动到子文件夹。"""
    jiexi_dir = work_dir / "解析版"
    yuanjuan_dir = work_dir / "原卷版"
    archive_dir = work_dir / "压缩包"
    jiexi_dir.mkdir(exist_ok=True)
    yuanjuan_dir.mkdir(exist_ok=True)
    archive_dir.mkdir(exist_ok=True)

    final_jiexi = _make_unique_path(jiexi_dir / jiexi_path.name)
    final_yuanjuan = _make_unique_path(yuanjuan_dir / yuanjuan_path.name)
    shutil.move(str(jiexi_path), str(final_jiexi))
    shutil.move(str(yuanjuan_path), str(final_yuanjuan))

    final_zip = None
    if zip_path is not None and zip_path.exists():
        final_zip = _make_unique_path(archive_dir / zip_path.name)
        shutil.move(str(zip_path), str(final_zip))

    return final_jiexi, final_yuanjuan, final_zip


def _collect_manual_review_docx(work_dir):
    """只收集工作目录根部的待人工审核 DOCX，不进入解析版/原卷版/_原始文本子目录。"""
    files = []
    for path in work_dir.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() != ".docx" or path.name.startswith("~"):
            continue
        if "待人工审核" in path.name:
            files.append(path)
    return sorted(files, key=lambda p: (_question_seq(p), p.name))


def main():
    work_dir = _get_work_dir()
    print("=" * 70)
    print("待人工审核 DOCX 处理工具")
    print("=" * 70)
    print(f"工作目录：{work_dir}")

    files = _collect_manual_review_docx(work_dir)
    if not files:
        print("\n未找到文件名包含“待人工审核”的 DOCX 文档。")
        input("按 Enter 退出...")
        return

    print(f"\n共找到 {len(files)} 个待人工审核文档，将按试卷序号从小到大处理。")

    for idx, docx_path in enumerate(files, 1):
        seq = _question_seq(docx_path)
        print("\n" + "=" * 70)
        print(f"[{idx}/{len(files)}] {docx_path.name}")
        print("=" * 70)
        print("\n【该试卷质检问题】")
        print(_read_report_section(work_dir, seq))
        print("\n正在打开文档，请在 WPS 中人工审核并保存修改。")
        _open_docx(docx_path)

        answer = input(
            "\n人工审核通过并已保存/关闭文档后，按 Enter 继续；"
            "输入 s 跳过该文档；输入 q 退出："
        ).strip().lower()
        if answer == "q":
            print("已退出。")
            break
        if answer == "s":
            print("已跳过该文档。")
            continue

        cleaned_name = _clean_manual_review_name(docx_path.name)
        cleaned_path = docx_path.parent / cleaned_name
        if cleaned_path.exists() and cleaned_path != docx_path:
            cleaned_path = _make_unique_path(cleaned_path)

        print("\n[1/4] 清除文件名中的“待人工审核”标记...")
        jiexi_path = _safe_rename(docx_path, cleaned_path)
        print(f"  ✓ {jiexi_path.name}")

        print("[2/4] 生成原卷版...")
        yuanjuan_path = _create_original_docx(jiexi_path)
        print(f"  ✓ {yuanjuan_path.name}")

        print("[3/4] 打包 zip...")
        zip_path = _create_zip(work_dir, jiexi_path, yuanjuan_path)
        print(f"  ✓ {zip_path.name}")

        print("[4/4] 分类到解析版/原卷版/压缩包文件夹...")
        final_jiexi, final_yuanjuan, final_zip = _classify_files(work_dir, jiexi_path, yuanjuan_path, zip_path)
        print(f"  解析版 <- {final_jiexi.name}")
        print(f"  原卷版 <- {final_yuanjuan.name}")
        if final_zip is not None:
            print(f"  压缩包 <- {final_zip.name}")

        print("\n该文档处理完成。")

    print("\n全部处理流程结束。")
    input("按 Enter 退出...")


if __name__ == "__main__":
    main()
