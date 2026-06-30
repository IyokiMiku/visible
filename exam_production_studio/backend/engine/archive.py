"""成品归档到本地输出目录。

目录结构：<输出根>/<卷类>/<省份简称 考类>/<教材或课程>/
  - 根目录默认 桌面/生成结果（可在全局设置改）。
  - 成品 docx 直接放在课程层；质检报告放在课程层的 质检报告/ 子目录。
  - 省份用简称（仅文件夹名；文档命名仍用全称，见 shared/docx/naming.py）。
  - 复制（保留 data/ 原件）；默认覆盖；目标被占用无法覆盖时，该文件改存 _v2/_v3…。
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import config
from engine import registry

_ILLEGAL = re.compile(r'[\\/:*?"<>|]')

# 去后缀得到省份简称（长后缀优先，避免“自治区”被“区”之类误伤）
_PROVINCE_SUFFIXES = (
    "维吾尔自治区", "壮族自治区", "回族自治区", "自治区",
    "特别行政区", "省", "市",
)


def short_province(province: str) -> str:
    """省份简称（如 内蒙古自治区→内蒙古、重庆市→重庆）。仅用于文件夹名。"""
    p = (province or "").strip()
    for suf in _PROVINCE_SUFFIXES:
        if p.endswith(suf) and len(p) > len(suf):
            return p[: -len(suf)]
    return p


def _safe(name: str, fallback: str = "未命名") -> str:
    s = _ILLEGAL.sub("", (name or "").strip())
    return s or fallback


def _leaf_name(ctx) -> str:
    """叶子层：一课一练用教材名，其余用课程名；缺失时回退另一个。"""
    if ctx.paper_type == "yikeyilian":
        return _safe(ctx.textbook or ctx.course, "未命名课程")
    return _safe(ctx.course or ctx.textbook, "未命名课程")


def dest_dir(ctx) -> Path:
    """该项目对应的归档目录：<根>/<卷类>/<省份简称 考类>/<教材或课程>/。"""
    try:
        display = registry.get(ctx.paper_type).display_name
    except Exception:
        display = ctx.paper_type
    region = f"{short_province(ctx.province)} {(ctx.exam_category or '').strip()}".strip()
    return (
        config.get_output_root()
        / _safe(display, ctx.paper_type or "未分类卷类")
        / _safe(region, "未分类")
        / _leaf_name(ctx)
    )


def _copy_overwrite_or_v2(src: Path, dst_dir: Path) -> Path:
    """复制到目标目录：默认覆盖同名；目标被占用无法覆盖时改存 _v2/_v3…。"""
    dst_dir.mkdir(parents=True, exist_ok=True)
    target = dst_dir / src.name
    try:
        return Path(shutil.copy2(src, target))
    except PermissionError:
        stem, suffix = target.stem, target.suffix
        n = 2
        while n <= 99:
            alt = dst_dir / f"{stem}_v{n}{suffix}"
            try:
                return Path(shutil.copy2(src, alt))
            except PermissionError:
                n += 1
        raise


def archive_project(ctx) -> Path:
    """把项目成品(docx)与质检报告复制到输出目录，返回目标目录。"""
    dest = dest_dir(ctx)
    src_out = ctx.dir("生成结果")
    if src_out.exists():
        for f in sorted(src_out.rglob("*")):
            if f.is_file() and f.suffix.lower() == ".docx":
                _copy_overwrite_or_v2(f, dest)
    src_qc = ctx.dir("质检报告")
    if src_qc.exists():
        qc_dest = dest / "质检报告"
        for f in sorted(src_qc.rglob("*.md")):
            _copy_overwrite_or_v2(f, qc_dest)
    return dest
