"""题型定义 JSON 加载与 prompt 注入辅助。"""
import json
import re
from pathlib import Path

from .paths import QUESTION_TYPES_DIR

_TYPE_ALIASES = {
    "单选": "single_choice",
    "单项选择": "single_choice",
    "选择": "single_choice",
    "多选": "multiple_choice",
    "多项选择": "multiple_choice",
    "判断": "true_false",
    "填空": "fill_blank",
    "简答": "short_answer",
    "计算": "calculation",
    "综合": "comprehensive",
}

_ID_ALIASES = {
    "single-choice": "single_choice",
    "single_choice": "single_choice",
    "multiple-choice": "multiple_choice",
    "multiple_choice": "multiple_choice",
    "true-false": "true_false",
    "true_false": "true_false",
    "fill-blank": "fill_blank",
    "fill_blank": "fill_blank",
    "short-answer": "short_answer",
    "short_answer": "short_answer",
    "calculation": "calculation",
    "comprehensive": "comprehensive",
}


def _safe_load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _normalize_key(text):
    return re.sub(r"[\s_\-]+", "", str(text or "").strip().lower())


def _type_id(raw):
    text = str(raw or "").strip()
    if not text:
        return ""
    for name in sorted(_TYPE_ALIASES, key=len, reverse=True):
        if name in text:
            return _TYPE_ALIASES[name]
    normalized = text.replace("-", "_")
    return _ID_ALIASES.get(normalized, normalized)


def parse_planned_type_ids(qtypes):
    """从规划表“题型”列解析当前卷涉及的题型 id。"""
    ids = []
    for raw_name, count in re.findall(r"([一-龥]+?)(\d+)", qtypes or ""):
        try:
            if int(count) <= 0:
                continue
        except ValueError:
            continue
        type_id = _type_id(raw_name)
        if type_id and type_id not in ids:
            ids.append(type_id)
    return ids


def _load_index():
    index_path = QUESTION_TYPES_DIR / "index.json"
    data = _safe_load_json(index_path)
    if not isinstance(data, dict):
        return []
    return data.get("courses") or []


def _find_config_file(meta):
    if not QUESTION_TYPES_DIR.exists():
        return None

    province = meta.get("province", "")
    category = meta.get("category", "")
    candidates = [category, f"{province}{category}"]
    candidate_keys = {_normalize_key(item) for item in candidates if item}

    for entry in _load_index():
        names = [entry.get("name", ""), *(entry.get("aliases") or [])]
        keys = {_normalize_key(item) for item in names if item}
        if candidate_keys & keys:
            file_name = entry.get("file")
            if file_name:
                path = QUESTION_TYPES_DIR / file_name
                if path.exists():
                    return path

    direct = QUESTION_TYPES_DIR / f"{category}.json"
    if category and direct.exists():
        return direct
    return None


def load_question_type_config(meta):
    path = _find_config_file(meta)
    if not path:
        return None, None
    data = _safe_load_json(path)
    if not isinstance(data, dict):
        return None, None
    return data, path


def _short_json(value, max_chars=700):
    if value in (None, "", [], {}):
        return ""
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "……"
    return text


def _question_type_map(config):
    result = {}
    for item in config.get("questionTypes") or []:
        type_id = _type_id(item.get("id") or item.get("name"))
        if type_id:
            result[type_id] = item
    return result


def load_question_type_prompt_section(meta, topic):
    """生成题型画像 prompt 片段；题量仍以规划表为准。"""
    config, path = load_question_type_config(meta)
    if not config:
        return ""

    planned_ids = parse_planned_type_ids(topic.get("question_types", ""))
    type_map = _question_type_map(config)
    selected = [(type_id, type_map[type_id]) for type_id in planned_ids if type_id in type_map]

    lines = [
        "【当前考类题型画像——不覆盖规划表题量】",
        "以下内容来自题型定义 JSON，只用于约束当前考类的场景、设问方式、干扰项来源、综合题组织和难度表现；不得改变规划表中的题型和数量。",
        f"来源：{path.name}",
    ]

    profile = config.get("categoryProfile") or {}
    if profile:
        overall = _short_json(profile.get("overall"))
        contexts = _short_json(profile.get("commonContexts"))
        difficulty = _short_json(profile.get("difficultyMapping"))
        if overall:
            lines.append(f"- 整体画像：{overall}")
        if contexts:
            lines.append(f"- 常见情境：{contexts}")
        if difficulty:
            lines.append(f"- 难度映射：{difficulty}")

    if selected:
        lines.append("- 当前规划表涉及题型画像：")
        for type_id, item in selected:
            lines.append(f"  - {item.get('name') or type_id}：")
            for label, key in [
                ("风格", "style"),
                ("适用情境", "preferredContexts"),
                ("推荐模式", "preferredPatterns"),
                ("避免模式", "avoidPatterns"),
                ("干扰项来源", "distractorSources"),
                ("质量规则", "qualityRules"),
            ]:
                text = _short_json(item.get(key))
                if text:
                    lines.append(f"    - {label}：{text}")
    else:
        lines.append("- 当前规划表涉及题型未在 JSON 中找到精确匹配；继续按编写规范和真题风格库生成。")

    return "\n".join(lines) + "\n"
