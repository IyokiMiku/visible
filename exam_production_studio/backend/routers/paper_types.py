"""产品类型专属配置（编写说明模板 + 编写规范.md + 模板样张预览）。

所有写操作限定在 configs/{type}/ 下；预览用 LibreOffice 把样张 docx 转 PDF。
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

import db
from engine import registry
from shared.docx import naming
from shared.docx.convert import LibreOfficeNotFound, docx_to_pdf
from shared.docx.sample import build_sample_docx
from shared.xueke_api import kpoint_resolver
from ._common import fail, ok

router = APIRouter(prefix="/api/paper-types", tags=["paper-types"])

_ALLOWED = {"yikeyilian", "kaogang_100", "shuangxi"}
_SPEC_FILENAME = "编写规范.md"

# 自定义题型（个性化、仅本机生效）存 settings 表的这一条键里。
# 结构：{ paper_type: { entry_id | "__global__": [题型名, ...] } }
_CUSTOM_KEY = "custom.question_types"
# 未匹配到具体考类/课程时，自定义题型归入的通用分组。
_GLOBAL_ENTRY = "__global__"

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


def _match_course_entry(index: dict, *keys: str) -> dict | None:
    """按 课程/考类 名称或别名在 题型定义/index.json 中匹配出对应条目（含 id/file）。"""
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
                        return c
    return None


def _entry_id(entry: dict) -> str:
    return str(entry.get("id") or entry.get("name") or "").strip() or _GLOBAL_ENTRY


def normalize_custom_name(name: str) -> str:
    """自定义题型统一以“题”结尾（如 名词解释 → 名词解释题），空值返回空串。

    以“题”结尾可保证 AI 补题结果按题型标题正确归类（parse_paper_text 依赖含“题”字）。
    """
    n = (name or "").strip()
    if not n:
        return ""
    return n if n.endswith("题") else n + "题"


def _load_custom() -> dict:
    row = db.query_one("SELECT value FROM settings WHERE key=?", (_CUSTOM_KEY,))
    if not row or not row.get("value"):
        return {}
    try:
        data = json.loads(row["value"])
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _save_custom(data: dict) -> None:
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (_CUSTOM_KEY, json.dumps(data, ensure_ascii=False)),
    )


def _custom_for(paper_type: str, entry_id: str) -> list[str]:
    return list(((_load_custom().get(paper_type) or {}).get(entry_id)) or [])


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
    """返回 {question_types, source, matched, matched_id, custom_types}。

    优先按 课程/考类 命中 题型定义/<file>.json 的 questionTypes（归一化为标准名）；
    未命中则回退到全局标准名列表。再把该考类绑定的自定义题型去重追加到末尾。
    """
    mode = registry.get(paper_type)
    qt_dir = mode.question_types_dir
    base_types: list[str] = []
    source = "global"
    matched: str | None = None
    entry_id = _GLOBAL_ENTRY
    if qt_dir is not None:
        qt_dir = Path(qt_dir)
        if qt_dir.exists():
            index = _read_json(qt_dir / "index.json")
            entry = _match_course_entry(index, course or "", category or "")
            if entry:
                types = _types_from_file(qt_dir, entry.get("file", ""))
                if types:
                    base_types = types
                    source = "course"
                    matched = entry.get("file")
                    entry_id = _entry_id(entry)
    if not base_types:
        base_types = list(kpoint_resolver.TYPE_NAME_SYNONYMS.keys())

    custom = _custom_for(paper_type, entry_id)
    merged = list(base_types)
    for t in custom:
        if t and t not in merged:
            merged.append(t)
    return {
        "question_types": merged,
        "source": source,
        "matched": matched,
        "matched_id": entry_id,
        "custom_types": custom,
    }


@router.get("/{paper_type}/question-types")
def get_question_types(paper_type: str, course: str = "", category: str = ""):
    if paper_type not in _ALLOWED:
        return fail("未知试卷类型", status=404)
    return ok(_resolve_question_types(paper_type, course, category))


@router.get("/{paper_type}/library")
def get_type_library(paper_type: str):
    """题型库总览：按考类/课程分组，含内置题型（只读）与自定义题型（可增删）。"""
    if paper_type not in _ALLOWED:
        return fail("未知试卷类型", status=404)
    custom_all = _load_custom().get(paper_type) or {}
    groups: list[dict] = []
    mode = registry.get(paper_type)
    qt_dir = mode.question_types_dir
    if qt_dir is not None:
        qt_dir = Path(qt_dir)
        if qt_dir.exists():
            index = _read_json(qt_dir / "index.json")
            for c in index.get("courses") or []:
                eid = _entry_id(c)
                groups.append({
                    "id": eid,
                    "name": c.get("name", eid),
                    "builtin_types": _types_from_file(qt_dir, c.get("file", "")),
                    "custom_types": list(custom_all.get(eid) or []),
                })
    groups.append({
        "id": _GLOBAL_ENTRY,
        "name": "通用（未匹配到考类/课程时生效）",
        "builtin_types": list(kpoint_resolver.TYPE_NAME_SYNONYMS.keys()),
        "custom_types": list(custom_all.get(_GLOBAL_ENTRY) or []),
    })
    return ok({"paper_type": paper_type, "groups": groups})


class CustomTypesIn(BaseModel):
    entry_id: str = _GLOBAL_ENTRY
    types: list[str] = []


@router.put("/{paper_type}/custom-types")
def put_custom_types(paper_type: str, body: CustomTypesIn):
    """覆盖式保存某考类/课程的自定义题型列表（统一强制“题”后缀、去重）。"""
    if paper_type not in _ALLOWED:
        return fail("未知试卷类型", status=404)
    entry_id = (body.entry_id or "").strip() or _GLOBAL_ENTRY
    cleaned: list[str] = []
    for t in body.types:
        n = normalize_custom_name(str(t))
        if n and n not in cleaned:
            cleaned.append(n)
    data = _load_custom()
    pt = data.get(paper_type) or {}
    if cleaned:
        pt[entry_id] = cleaned
    else:
        pt.pop(entry_id, None)
    if pt:
        data[paper_type] = pt
    else:
        data.pop(paper_type, None)
    _save_custom(data)
    return ok({"entry_id": entry_id, "types": cleaned})


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
