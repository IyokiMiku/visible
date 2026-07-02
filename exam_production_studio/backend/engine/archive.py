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
import zipfile
from pathlib import Path

import config
from engine import registry

_ILLEGAL = re.compile(r'[\\/:*?"<>|]')
# 从文件名提取「基名」和「版本」，如「第1卷 xxx（解析版）」→ (第1卷 xxx, 解析版)
_VARIANT_RE = re.compile(r"^(.+?)[（(](解析版|原卷版)[）)]")

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


def plan_export_dir(ctx) -> Path:
    """规划表等生产规划产物的导出目录：<导出根>/生产规划/{产品名}/{省份}_{考类}/。"""
    try:
        display = registry.get(ctx.paper_type).display_name
    except Exception:
        display = ctx.paper_type
    region = f"{(ctx.province or '').strip()}_{(ctx.exam_category or '').strip()}".strip("_")
    return (
        config.get_export_root()
        / "生产规划"
        / _safe(display, ctx.paper_type or "未分类")
        / _safe(region, "未分类")
    )


def export_planning_artifact(ctx, src: Path | None) -> Path | None:
    """把单个生产规划产物（规划表/映射表/细目表）复制到导出目录。失败不影响主流程。"""
    try:
        if not src:
            return None
        src = Path(src)
        if not src.exists():
            return None
        return _copy_overwrite_or_v2(src, plan_export_dir(ctx))
    except Exception:  # noqa: BLE001 - 导出失败不应阻断生成
        return None


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


def _move_overwrite(src: Path, dst_dir: Path) -> None:
    """移动文件到子目录，覆盖同名（先删旧目标，避免 Windows 下 move 报错）。"""
    dst_dir.mkdir(parents=True, exist_ok=True)
    target = dst_dir / src.name
    try:
        if target.exists():
            target.unlink()
        shutil.move(str(src), str(target))
    except (OSError, shutil.Error):
        pass


def _package_and_classify(dest: Path) -> None:
    """G2/G3：对归档目录根部的成品 docx 配对打包 zip，并分类到 解析版/原卷版/压缩包。"""
    docx_files = [
        f for f in dest.iterdir()
        if f.is_file() and f.suffix.lower() == ".docx" and not f.name.startswith("~")
    ]
    groups: dict[str, dict[str, Path]] = {}
    for f in docx_files:
        m = _VARIANT_RE.match(f.stem)
        if not m:
            continue
        base, variant = m.group(1).strip(), m.group(2)
        groups.setdefault(base, {})[variant] = f

    for base, variants in groups.items():
        # 配对（解析版+原卷版）打包 zip（打包用源文件，尚未移动）
        if "解析版" in variants and "原卷版" in variants:
            zip_dir = dest / "压缩包"
            zip_dir.mkdir(parents=True, exist_ok=True)
            zip_path = zip_dir / f"{base}.zip"
            try:
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for v in ("解析版", "原卷版"):
                        zf.write(variants[v], variants[v].name)
            except OSError:
                pass
        # 分类移动
        for variant, path in variants.items():
            _move_overwrite(path, dest / variant)


def archive_project(ctx) -> Path:
    """把项目成品(docx)与质检报告复制到输出目录，配对打包并分类，返回目标目录。"""
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
    # G2/G3：配对打包 zip + 分类到 解析版/原卷版/压缩包
    _package_and_classify(dest)
    return dest
