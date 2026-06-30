"""产物归档与下载（阶段七，设计文档 §5.4）。"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from engine import archive
from ._common import fail, load_ctx, ok

router = APIRouter(prefix="/api/projects", tags=["artifacts"])

_ILLEGAL = re.compile(r'[\\/:*?"<>|]')


def _safe_filename(name: str, fallback: str) -> str:
    cleaned = _ILLEGAL.sub("", name or "").strip()
    return cleaned or fallback


def _rel(ctx, p: Path) -> str:
    try:
        return str(p.relative_to(ctx.root))
    except ValueError:
        return str(p)


@router.get("/{project_id}/artifacts")
def list_artifacts(project_id: str):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    groups: dict[str, list] = {"成品": [], "质检报告": [], "其他": []}
    out = ctx.dir("生成结果")
    if out.exists():
        for f in sorted(out.rglob("*")):
            if f.is_file():
                item = {"name": f.name, "path": _rel(ctx, f), "size": f.stat().st_size}
                if f.suffix == ".docx":
                    groups["成品"].append(item)
                else:
                    groups["其他"].append(item)
    rep = ctx.dir("质检报告")
    if rep.exists():
        for f in sorted(rep.glob("*.md")):
            groups["质检报告"].append({"name": f.name, "path": _rel(ctx, f), "size": f.stat().st_size})
    return ok(groups)


@router.get("/{project_id}/artifacts/zip")
def zip_artifacts(project_id: str):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    out = ctx.dir("生成结果")
    out.mkdir(parents=True, exist_ok=True)
    zip_path = out / f"{_safe_filename(ctx.name, project_id)}_打包.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in out.rglob("*"):
            if f.is_file() and f != zip_path:
                zf.write(f, f.relative_to(out))
    return FileResponse(str(zip_path), filename=zip_path.name)


@router.post("/{project_id}/artifacts/open")
def open_output_folder(project_id: str):
    """在本机资源管理器/访达中打开该项目的归档输出目录（不存在则创建）。

    仅适用于后端与用户同机的本地运行场景。
    """
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    dest = archive.dest_dir(ctx)
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return fail(f"无法创建输出目录：{e}")
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(dest))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(dest)])
        else:
            subprocess.Popen(["xdg-open", str(dest)])
    except Exception as e:  # noqa: BLE001
        return fail(f"打开文件夹失败：{e}")
    return ok({"path": str(dest)})


@router.get("/{project_id}/artifacts/download")
def download_artifact(project_id: str, path: str):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    target = (ctx.root / path).resolve()
    # 路径安全：必须位于项目树内
    if not str(target).startswith(str(ctx.root.resolve())) or not target.exists():
        return fail("文件不存在或路径非法", status=404)
    return FileResponse(str(target), filename=target.name)
