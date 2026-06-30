"""docx -> pdf 转换（依赖 LibreOffice soffice，headless 模式）。

保真预览用：保留页眉页脚、蓝框编写说明、标题样式。需本机安装 LibreOffice，
或通过环境变量 SOFFICE_PATH 指定 soffice 可执行文件路径。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path


class LibreOfficeNotFound(RuntimeError):
    """未找到 soffice 可执行文件。"""


_COMMON_PATHS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice",
    "/usr/local/bin/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def find_soffice() -> str | None:
    """按优先级查找 soffice：SOFFICE_PATH 环境变量 > PATH > 常见安装路径。"""
    env = os.getenv("SOFFICE_PATH")
    if env and Path(env).exists():
        return env
    for name in ("soffice", "soffice.exe", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    for p in _COMMON_PATHS:
        if Path(p).exists():
            return p
    return None


def docx_to_pdf(docx_path, out_dir=None, timeout: int = 120) -> Path:
    """把 docx 转为 pdf，返回 pdf 路径。soffice 缺失时抛 LibreOfficeNotFound。"""
    docx_path = Path(docx_path)
    out_dir = Path(out_dir) if out_dir else docx_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    soffice = find_soffice()
    if not soffice:
        raise LibreOfficeNotFound(
            "未找到 LibreOffice（soffice），无法把样张转为 PDF 预览。"
            "请安装 LibreOffice，或设置环境变量 SOFFICE_PATH 指向 soffice 可执行文件。"
        )

    pdf_path = out_dir / (docx_path.stem + ".pdf")
    # 覆盖前先删旧文件，便于轮询判断本次是否真正产出。
    try:
        if pdf_path.exists():
            pdf_path.unlink()
    except OSError:
        pass

    # 注意：不要传 -env:UserInstallation 指向新建 profile —— 实测会触发
    # LibreOffice 自带 Python 初始化失败而无法产出 PDF；用默认 profile 即可。
    cmd = [
        soffice,
        "--headless",
        "--norestore",
        "--convert-to",
        "pdf",
        "--outdir",
        str(out_dir),
        str(docx_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("LibreOffice 转换超时（可能有实例占用，请关闭已打开的 LibreOffice 后重试）。") from exc

    # soffice.exe 在 Windows 上可能在 PDF 写盘前就返回，轮询等待产出。
    for _ in range(40):
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            return pdf_path
        time.sleep(0.5)

    msg = (proc.stderr or proc.stdout or b"").decode("utf-8", "ignore")[:500]
    raise RuntimeError(f"LibreOffice 转换失败：{msg or '未生成 PDF 文件'}")
