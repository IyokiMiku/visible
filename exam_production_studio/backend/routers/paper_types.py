"""产品类型专属配置（编写说明模板 + 编写规范.md + 模板样张预览）。

所有写操作限定在 configs/{type}/ 下；预览用 LibreOffice 把样张 docx 转 PDF。
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

from engine import registry
from shared.docx import naming
from shared.docx.convert import LibreOfficeNotFound, docx_to_pdf
from shared.docx.sample import build_sample_docx
from shared.xueke_api import kpoint_resolver
from ._common import fail, ok

router = APIRouter(prefix="/api/paper-types", tags=["paper-types"])

_ALLOWED = {"yikeyilian", "kaogang_100", "shuangxi"}
_SPEC_FILENAME = "编写规范.md"

# 编写说明模板可用占位符（展示给用户）。
_PLACEHOLDERS = [
    {"key": "{province}", "desc": "省份全称"},
    {"key": "{exam_type_name}", "desc": "考试名称/类型"},
    {"key": "{exam_category}", "desc": "考类/专业类别"},
    {"key": "{course}", "desc": "课程名"},
    {"key": "{textbook}", "desc": "教材名称（一课一练）"},
    {"key": "{edition}", "desc": "出版社·版次（一课一练）"},
    {"key": "{vol}", "desc": "卷号/练号"},
    {"key": "{paper_name}", "desc": "试卷主题/名称"},
    {"key": "{paper_subtype}", "desc": "卷型（如考点训练卷）"},
    {"key": "{series_name}", "desc": "系列名（类型显示名）"},
]


def _spec_path(paper_type: str) -> Path:
    return registry.CONFIGS_DIR / paper_type / _SPEC_FILENAME


def _read_text(path: Path) -> str:
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""
    return ""


class TextIn(BaseModel):
    content: str = ""


class PreviewIn(BaseModel):
    editorial_note: str | None = None


@router.get("/{paper_type}")
def get_paper_type(paper_type: str):
    if paper_type not in _ALLOWED:
        return fail("未知试卷类型", status=404)
    try:
        display_name = registry.get(paper_type).display_name
    except Exception:
        display_name = paper_type
    return ok({
        "type": paper_type,
        "display_name": display_name,
        "editorial_note": naming.load_note_template(paper_type),
        "placeholders": _PLACEHOLDERS,
        "spec": _read_text(_spec_path(paper_type)),
    })


@router.put("/{paper_type}/editorial-note")
def put_editorial_note(paper_type: str, body: TextIn):
    if paper_type not in _ALLOWED:
        return fail("未知试卷类型", status=404)
    path = naming.note_template_path(paper_type)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.content, encoding="utf-8")
    return ok({"saved": True})


@router.put("/{paper_type}/spec")
def put_spec(paper_type: str, body: TextIn):
    if paper_type not in _ALLOWED:
        return fail("未知试卷类型", status=404)
    path = _spec_path(paper_type)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.content, encoding="utf-8")
    return ok({"saved": True})


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _match_course_file(index: dict, *keys: str) -> str | None:
    """按 课程/考类 名称或别名在 题型定义/index.json 中匹配出对应文件名。"""
    courses = index.get("courses") or []
    cleaned = [k.strip() for k in keys if k and k.strip()]
    if not cleaned:
        return None
    # 先精确匹配 name/alias，再退化为包含匹配（避免空泛误匹配）
    for exact in (True, False):
        for key in cleaned:
            for c in courses:
                names = [c.get("name", "")] + list(c.get("aliases") or [])
                for n in names:
                    n = (n or "").strip()
                    if not n:
                        continue
                    if (exact and key == n) or (not exact and (n in key or key in n)):
                        return c.get("file")
    return None


def _types_from_file(qt_dir: Path, filename: str) -> list[str]:
    data = _read_json(qt_dir / filename)
    out: list[str] = []
    seen: set[str] = set()
    for qt in data.get("questionTypes") or []:
        name = kpoint_resolver.normalize_type_name(str(qt.get("name", "")).strip())
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _resolve_question_types(paper_type: str, course: str, category: str) -> dict:
    """返回 {question_types, source, matched}。

    优先按 课程/考类 命中 题型定义/<file>.json 的 questionTypes（归一化为标准名）；
    未命中则回退到全局标准名列表，保证下拉不为空、不过度限制。
    """
    mode = registry.get(paper_type)
    qt_dir = mode.question_types_dir
    if qt_dir is not None:
        qt_dir = Path(qt_dir)
        if qt_dir.exists():
            index = _read_json(qt_dir / "index.json")
            matched = _match_course_file(index, course or "", category or "")
            if matched:
                types = _types_from_file(qt_dir, matched)
                if types:
                    return {"question_types": types, "source": "course", "matched": matched}
    return {
        "question_types": list(kpoint_resolver.TYPE_NAME_SYNONYMS.keys()),
        "source": "global",
        "matched": None,
    }


@router.get("/{paper_type}/question-types")
def get_question_types(paper_type: str, course: str = "", category: str = ""):
    if paper_type not in _ALLOWED:
        return fail("未知试卷类型", status=404)
    return ok(_resolve_question_types(paper_type, course, category))


@router.post("/{paper_type}/preview")
def preview(paper_type: str, body: PreviewIn):
    if paper_type not in _ALLOWED:
        return fail("未知试卷类型", status=404)
    try:
        docx_path = build_sample_docx(paper_type, note_template=body.editorial_note)
        pdf_path = docx_to_pdf(docx_path)
    except LibreOfficeNotFound as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        return fail(f"预览生成失败：{exc}")
    return FileResponse(str(pdf_path), media_type="application/pdf", filename=pdf_path.name)
