"""学科网 课程/题型/知识点 解析（接入：源 学科网API拉题移植版/kpoint_resolver.py 去硬编码）。

数据源：configs/xueke_mapping/（大类 md：课程→courseId、题型→typeId；
knowledge_points/*.md：知识点树 名称→kpointId）。

考点名 → kpointId：先在本地知识点树做字符串/关键词匹配；未命中且已配置 LLM 时用 AI 兜底。
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import config

MAPPING_DIR = config.BASE_DIR / "configs" / "xueke_mapping"
KP_DIR = MAPPING_DIR / "knowledge_points"
# 专业大类 → 专业 → 课程（含 courseId）目录，供创建向导级联下拉与 courseId 精确解析。
PROFESSION_TREE_PATH = MAPPING_DIR / "专业课程树.json"
# 课程(courseId) → 顶级题型(typeId, name) 目录，供按 courseId 精确解析拉题 typeId。
COURSE_TYPES_PATH = MAPPING_DIR / "课程题型.json"


@lru_cache(maxsize=1)
def load_profession_tree() -> dict[str, Any]:
    """读取 专业课程树.json（大类→专业→课程）。文件缺失/损坏时返回空目录。"""
    if not PROFESSION_TREE_PATH.exists():
        return {"categories": []}
    try:
        data = json.loads(PROFESSION_TREE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"categories": []}
    return data if isinstance(data, dict) else {"categories": []}


def course_name_by_id(course_id: int) -> str:
    """按 courseId 反查课程名（取目录中首个匹配）。未命中返回空串。"""
    for cat in load_profession_tree().get("categories") or []:
        for prof in cat.get("professions") or []:
            for c in prof.get("courses") or []:
                if c.get("courseId") == course_id:
                    return str(c.get("courseName") or "")
    return ""


@lru_cache(maxsize=1)
def load_course_types() -> dict[int, dict[str, int]]:
    """读取 课程题型.json，构建 {courseId: {题型名: typeId}}。文件缺失/损坏返回空表。"""
    if not COURSE_TYPES_PATH.exists():
        return {}
    try:
        data = json.loads(COURSE_TYPES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[int, dict[str, int]] = {}
    for c in (data.get("courses") if isinstance(data, dict) else None) or []:
        cid = c.get("courseId")
        if cid is None:
            continue
        types: dict[str, int] = {}
        for t in c.get("types") or []:
            name = (t.get("name") or "").strip()
            tid = t.get("typeId")
            if name and tid is not None:
                types[name] = int(tid)
        out[int(cid)] = types
    return out


def resolve_type_ids_by_course_id(course_id: int | None, our_type_name: str) -> list[int]:
    """按 courseId 将我方题型名 → 学科网 typeId 列表（读 课程题型.json，同义词匹配）。

    比 resolve_type_ids（按课程名匹配）更精确：courseId 是稳定主键，不受各省课程名差异影响。
    命中优先级：先精确匹配同义词，再包含匹配；未命中返回 []。
    """
    if course_id is None or not our_type_name:
        return []
    try:
        cid = int(course_id)
    except (TypeError, ValueError):
        return []
    types = load_course_types().get(cid)
    if not types:
        return []
    synonyms = TYPE_NAME_SYNONYMS.get(our_type_name, [our_type_name])
    for syn in synonyms:
        exact = [tid for tname, tid in types.items() if tname == syn]
        if exact:
            return exact
    for syn in synonyms:
        partial = [tid for tname, tid in types.items() if syn in tname or tname in syn]
        if partial:
            return partial
    return []

# 我方标准名（最终生成统一命名）→ 学科网题型表中可能出现的名称（按名称匹配，最稳）。
# 注意：学科网各题型为独立类型（如 分析计算题 / 综合应用题 互不相同），同义词列表不得交叉，
# 否则归一化与 typeId 解析会互相误匹配。每个列表第一项应为学科网真实名称（用于精确匹配）。
TYPE_NAME_SYNONYMS = {
    "单项选择题": ["单选题", "单项选择题", "单选", "选择题"],
    "多项选择题": ["多项选择题", "多选题", "多选"],
    "判断题": ["判断题", "判断", "是非题"],
    "填空题": ["填空题", "填空"],
    "简答题": ["简答题", "简答", "问答题"],
    "综合应用题": ["综合应用题", "综合题", "综合"],
    "计算题": ["分析计算题", "计算题", "计算"],
    "作图题": ["作图题", "作图"],
    "识图题": ["识图题", "识图"],
    "简答作图题": ["简答作图题", "作图简答题"],
}

# 同义词 → 标准名 的反查表（首次出现者优先，避免歧义同义词被后写覆盖）。
_SYNONYM_TO_CANONICAL: dict[str, str] = {}
for _canon, _syns in TYPE_NAME_SYNONYMS.items():
    for _syn in _syns:
        _SYNONYM_TO_CANONICAL.setdefault(_syn, _canon)


def normalize_type_name(name: str) -> str:
    """把任意题型别名归一化为标准名（如 单选题/单选/选择题 → 单项选择题）。

    用于最终生成等环节统一命名；无法识别时原样返回。
    """
    if not name:
        return name
    n = name.strip()
    if n in TYPE_NAME_SYNONYMS:  # 已是标准名，优先返回自身
        return n
    return _SYNONYM_TO_CANONICAL.get(n, n)


def _list_categories() -> list[Path]:
    return sorted(MAPPING_DIR.glob("*.md")) if MAPPING_DIR.exists() else []


@lru_cache(maxsize=None)
def _parse_category(md_path_str: str) -> tuple[dict[str, int], dict[str, dict[str, str]]]:
    """解析单个大类 md：返回 (courses{name:courseId}, types_by_course{course:{typeName:typeId}})。"""
    courses: dict[str, int] = {}
    types_by_course: dict[str, dict[str, str]] = {}
    md_path = Path(md_path_str)
    if not md_path.exists():
        return courses, types_by_course
    text = md_path.read_text(encoding="utf-8")

    # 课程表：仅在「## 课程ID映射」段内解析，避免误抓题型行
    course_section = text
    m_start = text.find("## 课程ID映射")
    if m_start != -1:
        m_end = text.find("## 题型", m_start)
        course_section = text[m_start: m_end if m_end != -1 else None]
    for mt in re.finditer(r"\|\s*(\d+)\s*\|\s*([^\|]+?)\s*\|", course_section):
        courses[mt.group(2).strip()] = int(mt.group(1))

    # 题型表：### 课程 (courseId=NN) 后的表格
    for cname, cid in courses.items():
        sec = re.search(rf"###\s*[^\n]*\(courseId={cid}\)[^\n]*\n(.*?)(?=\n###|\Z)", text, re.S)
        types: dict[str, str] = {}
        if sec:
            for tm in re.finditer(r"\|\s*(\d+)\s*\|\s*([^\|]+?)\s*\|\s*(yes|no)\s*\|", sec.group(1)):
                types[tm.group(2).strip()] = tm.group(1)
        types_by_course[cname] = types
    return courses, types_by_course


def resolve_course(course_name: str, category: str | None = None) -> int | None:
    if not course_name:
        return None
    paths = [MAPPING_DIR / f"{category}.md"] if category else _list_categories()
    for p in paths:
        courses, _ = _parse_category(str(p))
        if course_name in courses:
            return courses[course_name]
        for name, cid in courses.items():
            if course_name in name or name in course_name:
                return cid
    return None


def resolve_all_types(course_name: str) -> dict[str, str]:
    for p in _list_categories():
        _, types_by_course = _parse_category(str(p))
        if course_name in types_by_course and types_by_course[course_name]:
            return types_by_course[course_name]
    return {}


def resolve_type_ids(course_name: str, our_type_name: str) -> list[int]:
    """我方题型名 → 学科网 typeId 列表（按名称同义匹配）。"""
    types = resolve_all_types(course_name)
    if not types:
        return []
    synonyms = TYPE_NAME_SYNONYMS.get(our_type_name, [our_type_name])
    # 按同义词优先级匹配：先精确，再包含；命中某一同义词即返回，避免"选择题"等宽词误匹配多个题型
    for syn in synonyms:
        exact = [int(tid) for tname, tid in types.items() if tname == syn]
        if exact:
            return exact
    for syn in synonyms:
        partial = [int(tid) for tname, tid in types.items() if syn in tname or tname in syn]
        if partial:
            return partial
    return []


@lru_cache(maxsize=None)
def load_kpoint_tree(course_name: str) -> tuple[dict[str, Any], ...]:
    """跨全部 knowledge_points/*.md 搜索 ### 课程 段的知识点树。

    返回节点元组（每个 {id, name, parent_id, level}）。
    """
    if not KP_DIR.exists():
        return ()
    nodes: list[dict[str, Any]] = []
    seen: set[int] = set()
    for md_path in sorted(KP_DIR.glob("*.md")):
        try:
            content = md_path.read_text(encoding="utf-8")
        except OSError:
            continue
        start = content.find(f"### {course_name}")
        if start == -1:
            for m in re.finditer(r"^### (.+)$", content, re.M):
                hdr = m.group(1).strip()
                if hdr == course_name or hdr in course_name or course_name in hdr:
                    start = m.start()
                    break
        if start == -1:
            continue
        nxt = content.find("\n### ", start + 1)
        section = content[start: nxt if nxt != -1 else None]
        block = re.search(r"```\n(.*?)```", section, re.S)
        if not block:
            continue
        parent_stack: list[tuple[int, int]] = []
        for line in block.group(1).split("\n"):
            m = re.search(r"(.+?)\s*\((\d+)\)", line)
            if not m:
                continue
            name = re.sub(r"^[├└│─\s]+", "", m.group(1)).strip()
            kid = int(m.group(2))
            if kid in seen:
                continue
            seen.add(kid)
            indent = 0
            for ch in line:
                if ch in " │├└─":
                    indent += 1
                elif ch.strip():
                    break
                else:
                    indent += 1
            indent //= 4
            parent_id: int | None = None
            level = 1
            while parent_stack and parent_stack[-1][0] >= indent:
                parent_stack.pop()
            if parent_stack:
                parent_id = parent_stack[-1][1]
                level = len(parent_stack) + 1
            parent_stack.append((indent, kid))
            nodes.append({"id": kid, "name": name, "parent_id": parent_id, "level": level})
    return tuple(nodes)


def search_kpoints(query: str, course_name: str) -> list[dict[str, Any]]:
    nodes = list(load_kpoint_tree(course_name))
    if not nodes or not query:
        return []
    results = [n for n in nodes if query in n["name"] or n["name"] in query]
    if results:
        return sorted(results, key=lambda n: (0 if query == n["name"] else 1, n["level"]))
    keywords = [k for k in re.split(r"[、，,\s/]+", query) if len(k) >= 2]
    if keywords:
        results = [n for n in nodes if all(k in n["name"] for k in keywords)]
        if not results:
            results = [n for n in nodes if any(k in n["name"] for k in keywords)]
    return sorted(results, key=lambda n: n["level"])


def _ai_match(course_name: str, point_name: str) -> list[int]:
    """LLM 兜底：在知识树里为单个考点找 kpointId。未配置或失败返回 []。"""
    from shared.ai import llm
    if not llm.is_configured():
        return []
    nodes = list(load_kpoint_tree(course_name))
    if not nodes:
        return []
    tree_text = "\n".join(f"{n['id']}\t{'　' * (n['level'] - 1)}{n['name']}" for n in nodes)
    prompt = (
        "根据知识树为考点找出最匹配的知识点 ID（可多个）。只输出 JSON 数组，如 [123,456]。\n\n"
        f"知识树(id\\t名称)：\n{tree_text}\n\n考点：{point_name}\n"
    )
    try:
        resp = llm.complete(prompt, temperature=0.1, max_tokens=200).strip()
        resp = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp)
        ids = json.loads(resp)
        return [int(x) for x in ids if isinstance(x, int)]
    except Exception:
        return []


def resolve(ctx, point_name: str) -> tuple[str, float]:
    """考点名 → (kpointId, confidence)。

    本地树命中：完全相等≈0.95，包含≈0.85，关键词≈0.7；AI 兜底≈0.6；未命中 ('',0.0)。
    """
    course = getattr(ctx, "course", "") or ""
    if not point_name or not course:
        return "", 0.0
    hits = search_kpoints(point_name, course)
    if hits:
        top = hits[0]
        if point_name == top["name"]:
            conf = 0.95
        elif point_name in top["name"] or top["name"] in point_name:
            conf = 0.85
        else:
            conf = 0.7
        return str(top["id"]), conf
    ids = _ai_match(course, point_name)
    if ids:
        return str(ids[0]), 0.6
    return "", 0.0


def resolve_course_id(ctx) -> int | None:
    return resolve_course(getattr(ctx, "course", "") or "", None)


def resolve_layered(point_text: str, course_name: str,
                    nodes: list[dict[str, Any]] | None = None) -> tuple[list[int], str]:
    """分层匹配考点文本 → kpointId 列表（映射表 D4）。

    优先级：L3 叶子 → L2 父节点；**禁止 L1 根节点**（范围过大会串知识点）。
    命中返回 (ids, 'AI匹配')；未命中返回 ([], 'AI生成')。
    - 去层级前缀（了解/理解/掌握 + 序号）后取关键词；
    - nodes 可注入（测试用），默认取 load_kpoint_tree(course_name)。
    """
    if nodes is None:
        nodes = list(load_kpoint_tree(course_name))
    if not nodes or not point_text:
        return [], "AI生成"

    query = re.sub(r"^\s*\d+[.．、]\s*", "", str(point_text)).strip()
    query = re.sub(r"^(了解|理解|掌握|熟悉|熟练掌握|能|会|认识)", "", query).strip()

    def _match(nodes_subset: list[dict[str, Any]]) -> list[int]:
        exact = [n["id"] for n in nodes_subset if n["name"] == query]
        if exact:
            return exact
        contains = [n["id"] for n in nodes_subset if n["name"] in query or query in n["name"]]
        if contains:
            return contains
        kws = [k for k in re.split(r"[、，,\s/和与及]+", query) if len(k) >= 2]
        if kws:
            return [n["id"] for n in nodes_subset if any(k in n["name"] for k in kws)]
        return []

    leaves = [n for n in nodes if n["level"] >= 3]
    ids = _match(leaves)
    if ids:
        return ids, "AI匹配"
    l2 = [n for n in nodes if n["level"] == 2]
    ids = _match(l2)
    if ids:
        return ids, "AI匹配"
    # L1 禁止匹配：宁缺毋滥
    return [], "AI生成"
