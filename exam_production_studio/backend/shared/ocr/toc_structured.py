"""结构化教材目录（阶段 A4）。

把教材目录解析为层级节点列表并落盘 ``toc_structured.json``，供阶段 C/D 的规划生成消费。
两条抽取路径（文字版文本层 / 图片版视觉 OCR）都归一到本模块的 TocNode 结构。

节点层级约定（对齐一课一练 8 列规划表的行层级）：
- level 1：一级标题（单元/章），如「第1章 电路的基本概念与基本定律」；
- level 2：二级标题（章/节），如「一、电路基础知识」；
- level 3+：更细条目（可选）。
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

STRUCTURED_FILENAME = "toc_structured.json"

# 一级标题：第X章 / 第X单元 / 单元X / 第X篇 / 绪论 / 预备知识
_L1_PATTERNS = [
    re.compile(r"^\s*第\s*[一二三四五六七八九十百零\d]+\s*[章单元篇部]"),
    re.compile(r"^\s*单元\s*[一二三四五六七八九十\d]+"),
    re.compile(r"^\s*(绪论|预备知识|导论|概论)\b"),
]
# 二级标题：第X节 / 一、 / （一） / 1.1 / 1．
_L2_PATTERNS = [
    re.compile(r"^\s*第\s*[一二三四五六七八九十\d]+\s*节"),
    re.compile(r"^\s*[一二三四五六七八九十]+\s*[、.．]"),
    re.compile(r"^\s*[（(]\s*[一二三四五六七八九十\d]+\s*[)）]"),
    re.compile(r"^\s*\d+\.\d+"),
    re.compile(r"^\s*\d+\s*[．.、]"),
]
# 行尾页码（目录点线 + 数字），抽取时清除
_TRAILING_PAGE = re.compile(r"[\s\.·。\u2026]*\d+\s*$")


@dataclass
class TocNode:
    level: int
    title: str
    page: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level, "title": self.title, "page": self.page}


@dataclass
class StructuredToc:
    textbook: str = ""
    source_pdf: str = ""
    pdf_kind: str = ""          # text | image
    nodes: list[TocNode] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "textbook": self.textbook,
            "source_pdf": self.source_pdf,
            "pdf_kind": self.pdf_kind,
            "nodes": [n.to_dict() for n in self.nodes],
        }


def _clean_title(line: str) -> str:
    s = line.strip()
    s = _TRAILING_PAGE.sub("", s).strip()
    return s


def _line_level(line: str) -> int | None:
    """判断一行属于哪个层级；非标题行返回 None。"""
    s = line.strip()
    if not s:
        return None
    for pat in _L1_PATTERNS:
        if pat.match(s):
            return 1
    for pat in _L2_PATTERNS:
        if pat.match(s):
            return 2
    return None


def build_from_bookmarks(toc: list[list[Any]]) -> list[TocNode]:
    """由 PyMuPDF ``doc.get_toc()`` 结果（[level, title, page]）构造节点。"""
    nodes: list[TocNode] = []
    for item in toc or []:
        try:
            level, title, page = int(item[0]), str(item[1]).strip(), item[2]
        except (ValueError, IndexError, TypeError):
            continue
        if not title:
            continue
        nodes.append(TocNode(level=max(1, level), title=title, page=page if isinstance(page, int) else None))
    return nodes


def build_from_text(text: str) -> list[TocNode]:
    """由目录页纯文本（文本层抽取 / OCR 结果）按行正则识别层级。

    只保留能识别出层级的行；其余行作为上一标题的更细条目（level+1）附着，避免噪声。
    """
    nodes: list[TocNode] = []
    last_level = 0
    for raw in text.splitlines():
        lvl = _line_level(raw)
        title = _clean_title(raw)
        if not title:
            continue
        if lvl is None:
            # 未识别层级：若已有上级标题，作为其下一层条目；否则跳过噪声
            if last_level == 0:
                continue
            lvl = min(last_level + 1, 3)
        else:
            last_level = lvl
        nodes.append(TocNode(level=lvl, title=title))
    return nodes


def save_structured(out_path: str | Path, structured: StructuredToc) -> Path:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(structured.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def load_structured(path: str | Path) -> StructuredToc | None:
    """读取 toc_structured.json，反序列化为 StructuredToc；文件缺失/损坏返回 None。"""
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    nodes = [
        TocNode(level=int(n.get("level", 1)), title=str(n.get("title", "")), page=n.get("page"))
        for n in data.get("nodes", [])
        if str(n.get("title", "")).strip()
    ]
    return StructuredToc(
        textbook=data.get("textbook", ""),
        source_pdf=data.get("source_pdf", ""),
        pdf_kind=data.get("pdf_kind", ""),
        nodes=nodes,
    )


def structured_from_dict(data: dict[str, Any]) -> StructuredToc:
    """由（前端编辑保存的）dict 反序列化，用于写回接口。"""
    nodes = [
        TocNode(level=int(n.get("level", 1)), title=str(n.get("title", "")).strip(), page=n.get("page"))
        for n in data.get("nodes", [])
        if str(n.get("title", "")).strip()
    ]
    return StructuredToc(
        textbook=data.get("textbook", ""),
        source_pdf=data.get("source_pdf", ""),
        pdf_kind=data.get("pdf_kind", ""),
        nodes=nodes,
    )
