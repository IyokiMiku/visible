"""图片下载助手（shared/docx）。

学科网拉题返回的图片是 URL（{"url":..,"width":..,"height":..}）。
docx_utils1._add_image_run 只插入本地文件（URL 下载“由数据层负责”），
因此组卷前需把图片下载到项目临时目录，并把 local_path 写回图片条目。

设计为尽力而为：任何一张图下载失败都只跳过该图，绝不中断整卷生成。
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable

try:
    import requests
except ImportError:  # 允许无 requests 时安静降级（图片跳过）
    requests = None

_EXT_RE = re.compile(r"\.(png|jpe?g|gif|bmp|webp)(?:\?|$)", re.IGNORECASE)


def _guess_ext(url: str) -> str:
    m = _EXT_RE.search(url or "")
    return f".{m.group(1).lower()}" if m else ".png"


def _download_one(url: str, dest_dir: Path) -> Path | None:
    if requests is None or not url:
        return None
    name = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16] + _guess_ext(url)
    target = dest_dir / name
    if target.exists() and target.stat().st_size > 0:
        return target
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        target.write_bytes(resp.content)
        return target if target.stat().st_size > 0 else None
    except Exception as exc:  # noqa: BLE001
        print(f"  → 警告：下载图片失败 {url[:80]}：{exc}")
        return None


def ensure_local_images(items: Iterable[dict[str, Any]] | None, dest_dir: Path) -> list[dict[str, Any]]:
    """为图片条目补齐 local_path（就地下载 URL）。返回补齐后的列表。"""
    result: list[dict[str, Any]] = []
    if not items:
        return result
    dest_dir.mkdir(parents=True, exist_ok=True)
    for item in items:
        if not isinstance(item, dict):
            continue
        enriched = dict(item)
        local = enriched.get("local_path") or enriched.get("path")
        if not (local and Path(local).exists()):
            path = _download_one(str(enriched.get("url") or ""), dest_dir)
            if path is not None:
                enriched["local_path"] = str(path)
        result.append(enriched)
    return result
