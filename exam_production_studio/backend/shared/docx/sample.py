"""样张生成：用示例参数生成"编写说明 + 三行标题"的无题 docx，供专属配置页预览。

不写入任何真实项目数据，仅用于直观展示该类型的首部编写说明与标题样式。
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

import config
from engine import registry
from engine.context import ProjectContext
from . import naming
from .docx_utils1 import add_editorial_note_text, add_paragraph_with_style, set_margins

# 各类型预览用示例参数（仅用于排版展示）。
_SAMPLE_FIELDS: dict[str, dict] = {
    "yikeyilian": {
        "province": "重庆市",
        "exam_type_name": "高职分类考试",
        "course": "电工基础",
        "textbook": "电工基础",
        "edition": "高教版·第三版",
        "exam_category": "电子与信息大类",
    },
    "kaogang_100": {
        "province": "重庆市",
        "exam_type_name": "高职分类考试",
        "course": "机械基础",
        "exam_category": "机械加工类",
    },
    "shuangxi": {
        "province": "重庆市",
        "exam_type_name": "高职分类考试",
        "course": "机械基础",
        "exam_category": "机械加工类",
    },
}

_SAMPLE_TOPIC = "示例主题（钢的热处理工艺）"
_SAMPLE_SUBTYPE = "考点训练卷"


def _preview_dir() -> Path:
    d = config.BASE_DIR / "data" / "_preview"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sample_pdf_path(paper_type: str) -> Path:
    """样张 PDF 的固定输出路径（与 build_sample_docx 输出同名同目录）。"""
    return _preview_dir() / f"{paper_type}_sample.pdf"


def _sample_ctx(paper_type: str) -> ProjectContext:
    fields = _SAMPLE_FIELDS.get(paper_type, _SAMPLE_FIELDS["yikeyilian"])
    return ProjectContext(project_id="_preview", paper_type=paper_type, **fields)


def build_sample_docx(paper_type: str, note_template: str | None = None) -> Path:
    """生成样张 docx，返回路径。

    note_template 非 None 时用其渲染编写说明（预览未保存的草稿）；否则使用
    当前已保存的模板（configs/{type}/编写说明.tpl.txt 或默认）。
    """
    ctx = _sample_ctx(paper_type)
    suffix = "教师讲解卷" if paper_type == "shuangxi" else ""

    # 与 generator._new_document 一致：有类型模板就用它（保留页眉页脚），否则空白文档。
    tpl = None
    try:
        tpl = registry.get(paper_type).template_docx
    except Exception:
        tpl = None
    if tpl and Path(tpl).exists():
        doc = Document(str(tpl))
    else:
        doc = Document()
        set_margins(doc)

    note_text = naming.build_editorial_note(
        ctx, 1, paper_name=_SAMPLE_TOPIC, paper_subtype=_SAMPLE_SUBTYPE,
        topic=_SAMPLE_TOPIC, template=note_template,
    )
    if note_text:
        add_editorial_note_text(doc, note_text)

    for line in naming.build_title_lines(
        ctx, 1, paper_name=_SAMPLE_TOPIC, paper_subtype=_SAMPLE_SUBTYPE,
        suffix=suffix, topic=_SAMPLE_TOPIC,
    ):
        if not line:
            continue
        add_paragraph_with_style(
            doc, line, font_name="宋体", font_size=14, bold=True,
            alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=2,
        )

    out_path = _preview_dir() / f"{paper_type}_sample.docx"
    doc.save(str(out_path))
    return out_path
