"""组卷底层（阶段四 shared/docx，源 docx_utils1/docx_generation 去硬编码）。

按 ctx + 类型模板生成 docx：三行标题、题干（公式/图片）、选项表、答案/解析红字。
variant='解析版' 含答案解析；'原卷版' 不含。

富内容渲染统一走移植自考纲百套卷的 docx_utils1：
- 公式：$...$ / \\(...\\) / {{math:...}} → Word 原生 OMML（含数字字母斜体），失败降级清洗文本；
- 图片：题干图/选项图按 local_path 插入（URL 由 images.ensure_local_images 预下载）；
- 答案/解析：统一红字；解析标签去重，避免出现【解析】【详解】重复标签。
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from engine import registry
from engine.drivers.base import PaperQuestions
from shared.xueke_api.kpoint_resolver import normalize_type_name
from . import naming
from .docx_utils1 import (
    add_editorial_note_text,
    add_labeled_text,
    add_paragraph_with_style,
    add_structured_choice_question,
    copy_template,
    save_docx,
    set_margins,
)
from .images import ensure_local_images

RED = (255, 0, 0)
_CN_NUM = "一二三四五六七八九十"

# 主观题：原卷版需在题后留出空白作答区
SUBJECTIVE_TYPES = {"简答题", "计算题", "综合应用题", "分析题", "作图题", "识图题", "简答作图题"}
_ANSWER_SPACE_LINES = 4

# 需要卷首「时间/总分 + 班级密封线」两行的产品（一课一练不标分值，不加）
_EXAM_INFO_TYPES = {"shuangxi", "kaogang_100"}

# 解析标签去重：反复剥离开头的【解析|详解|分析…】，最终统一加单个【解析】
_DUP_LABEL_RE = re.compile(
    r"^(?:【\s*(?:解析|详解|分析|答案解析|试题解析|题目解析|解题思路|点睛)\s*】|(?:解析|详解|分析)\s*[:：])\s*"
)
_STUB_ANALYSIS_RE = re.compile(r"^(?:(?:略|无)\s*[。.]?|—|－－|--|[.。])?\s*$")


def _strip_dup_analysis_labels(text: str) -> str:
    """移除重复/前缀解析标签，生成时再统一补一个【解析】。"""
    value = str(text or "").strip()
    while True:
        cleaned = _DUP_LABEL_RE.sub("", value).strip()
        if cleaned == value:
            return cleaned
        value = cleaned


def _should_emit_analysis(text: str) -> bool:
    t = str(text or "").strip()
    return bool(t) and not _STUB_ANALYSIS_RE.match(t)


def _new_document(ctx) -> Document:
    """优先用类型模板（保留页眉页脚），无模板时用空白文档 + 标准页边距。"""
    try:
        mode = registry.get(ctx.paper_type)
        tpl = mode.template_docx
    except Exception:
        tpl = None
    if tpl and Path(tpl).exists():
        # copy_template 会先落盘一份再打开；这里用临时名，最终仍由 save_docx 覆盖写。
        doc = Document(str(tpl))
    else:
        doc = Document()
        set_margins(doc)
    return doc


def _add_title(doc: Document, lines: list[str]) -> None:
    for ln in lines:
        if not ln:
            continue
        add_paragraph_with_style(
            doc, ln, font_name="宋体", font_size=14, bold=True,
            alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=2,
        )


def _paper_total_score(ctx) -> int | float:
    """按 volume_config.by_type 合计 count×score_per，作为卷首总分显示。"""
    by_type = (getattr(ctx, "volume_config", {}) or {}).get("by_type") or {}
    total = 0.0
    for v in by_type.values():
        try:
            total += float(v.get("count", 0)) * float(v.get("score_per", 0))
        except (TypeError, ValueError):
            continue
    return int(total) if float(total).is_integer() else total


def _section_score_map(ctx) -> dict[str, float]:
    """题型（归一化名）→ 每小题分值，取自 volume_config.by_type。"""
    by_type = (getattr(ctx, "volume_config", {}) or {}).get("by_type") or {}
    out: dict[str, float] = {}
    for raw, v in by_type.items():
        try:
            score = float((v or {}).get("score_per", 0) or 0)
        except (TypeError, ValueError):
            continue
        if score <= 0:
            continue
        out[normalize_type_name(str(raw))] = score
    return out


def _fmt_num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def _section_note(count: int, score_per: float | None) -> str:
    """题型标题后的括注：（本大题共X小题，每题Y分，共Z分）；无分值时仅标题量。"""
    if count <= 0:
        return ""
    if not score_per or score_per <= 0:
        return f"（本大题共{count}小题）"
    total = float(score_per) * count
    return f"（本大题共{count}小题，每题{_fmt_num(score_per)}分，共{_fmt_num(total)}分）"


def _add_exam_info(doc: Document, ctx) -> None:
    """卷首「时间：X分钟  总分：Y分」+「班级/姓名/学号/成绩」两行（仅指定产品）。"""
    if getattr(ctx, "paper_type", "") not in _EXAM_INFO_TYPES:
        return
    vc = getattr(ctx, "volume_config", {}) or {}
    try:
        minutes = int(vc.get("exam_minutes") or 60)
    except (TypeError, ValueError):
        minutes = 60
    total = _paper_total_score(ctx)
    add_paragraph_with_style(
        doc, f"时间：{minutes}分钟    总分：{total}分",
        font_name="宋体", font_size=10.5,
        alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=2,
    )
    add_paragraph_with_style(
        doc, "班级＿＿＿＿　姓名＿＿＿＿　学号＿＿＿＿　成绩＿＿＿＿",
        font_name="宋体", font_size=10.5,
        alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=2,
    )


def _option_dicts(q) -> list[dict]:
    """把 options 文本 + 对齐的 option_images 组装成 docx_utils1 可消费的结构。"""
    dicts: list[dict] = []
    for i, text in enumerate(q.options or []):
        images = q.option_images[i] if i < len(q.option_images or []) else []
        dicts.append({
            "label": chr(ord("A") + i),
            "text": str(text or "").strip(),
            "images": list(images or []),
        })
    return dicts


def _render_question(doc: Document, q, img_dir: Path) -> None:
    # 预下载图片到本地，补齐 local_path
    q.stem_images = ensure_local_images(q.stem_images, img_dir)
    if q.option_images:
        q.option_images = [ensure_local_images(imgs, img_dir) for imgs in q.option_images]

    stem = f"{q.number}. {str(q.stem or '').strip()}".rstrip()
    has_stem_img = bool(q.stem_images)
    has_opt_img = any(q.option_images or [])

    if q.options or has_opt_img:
        add_structured_choice_question(doc, stem, _option_dicts(q), stem_images=q.stem_images)
    elif has_stem_img:
        add_structured_choice_question(doc, stem, [], stem_images=q.stem_images)
    else:
        add_paragraph_with_style(doc, stem, font_name="宋体", font_size=10.5, space_after=2)


def _render_answer_analysis(doc: Document, q) -> None:
    answer = str(q.answer or "").strip()
    if answer:
        add_labeled_text(doc, "【答案】", answer, color=RED)
    analysis = _strip_dup_analysis_labels(q.analysis)
    if _should_emit_analysis(analysis):
        add_labeled_text(doc, "【解析】", analysis, color=RED)


def generate_docx(
    ctx,
    qs: PaperQuestions,
    *,
    variant: str = "解析版",
    paper_name: str = "",
    paper_subtype: str = "考点训练卷",
    suffix: str = "",
    topic: str = "",
    out_dir: Path | None = None,
) -> Path:
    """生成单份 docx，返回路径。"""
    out_dir = out_dir or ctx.dir("生成结果")
    out_dir.mkdir(parents=True, exist_ok=True)
    img_dir = ctx.dir("_临时") / "images"
    fname = naming.build_filename(
        ctx, qs.paper_no, paper_name=paper_name, variant=variant,
        paper_subtype=paper_subtype, suffix=suffix, topic=topic,
    )
    out_path = out_dir / f"{fname}.docx"

    doc = _new_document(ctx)
    note_text = naming.build_editorial_note(
        ctx, qs.paper_no, paper_name=paper_name, paper_subtype=paper_subtype, topic=topic,
    )
    if note_text:
        add_editorial_note_text(doc, note_text)
    _add_title(doc, naming.build_title_lines(
        ctx, qs.paper_no, paper_name=paper_name, paper_subtype=paper_subtype,
        suffix=suffix, topic=topic,
    ))
    _add_exam_info(doc, ctx)
    doc.add_paragraph()

    # 按题型分组保持顺序
    grouped: dict[str, list] = {}
    order: list[str] = []
    for q in qs.questions:
        if q.qtype not in grouped:
            grouped[q.qtype] = []
            order.append(q.qtype)
        grouped[q.qtype].append(q)

    show_answer = variant == "解析版"
    score_map = _section_score_map(ctx)
    for ti, qtype in enumerate(order):
        cn = _CN_NUM[ti] if ti < len(_CN_NUM) else str(ti + 1)
        note = _section_note(len(grouped[qtype]), score_map.get(qtype))
        add_paragraph_with_style(doc, f"{cn}、{qtype}{note}", font_name="黑体", font_size=12, bold=True, space_after=6)
        is_subjective = qtype in SUBJECTIVE_TYPES
        for q in grouped[qtype]:
            _render_question(doc, q, img_dir)
            if show_answer:
                _render_answer_analysis(doc, q)
            elif is_subjective:
                # 原卷版：主观题后留出空白作答区，供学生作答
                for _ in range(_ANSWER_SPACE_LINES):
                    add_paragraph_with_style(doc, "", font_name="宋体", font_size=10.5, space_after=2)

    save_docx(doc, str(out_path))
    return out_path
