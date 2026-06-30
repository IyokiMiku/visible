"""OpenAI-compatible API helpers for planning-table generation."""

import json
import re
import sys
import time

from openai import OpenAI

from plan_modules.config import CONFIG_PATH
from plan_modules.topic_generator import collect_point_records


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_json_object(text):
    """从模型输出中提取 JSON 对象文本，兼容被 ```json 包裹的情况。"""
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        return fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def generate_ai_theme_map(courses, model=None):
    """调用 config.json 中的 OpenAI 兼容 API，根据每个考纲知识点生成简短试卷主题。"""
    records = collect_point_records(courses)
    if not records:
        return {}

    config = load_config()
    model = model or config.get("model")
    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    prompt = {
        "task": "为每个考纲知识点生成适合作为一课一练试卷标题的简短中文主题。",
        "requirements": [
            "必须逐条处理输入中的每一个考点，不能遗漏、合并或新增。",
            "主题应体现考纲知识点本身，而不是直接使用节名。",
            "主题要短，一般 4 到 10 个汉字；必要时可稍长。",
            "去掉掌握、熟悉、了解、理解、能、会等认知层次词。",
            "不要使用（一）（二）（1）（2）等卷次或序号后缀。",
            "不要输出‘试卷’‘练习’‘专题’等泛化词。",
            "如果考点包含多个并列要求，提炼最核心、最适合命题的主题。",
        ],
        "examples": [
            {"point": "认识机器的组成及各组成部分的作用", "theme": "认识机器组成"},
            {"point": "掌握平面图形尺寸标注的方法", "theme": "平面图形尺寸标注"},
            {"point": "了解常用金属材料的性能", "theme": "金属材料性能"},
        ],
        "output_format": {
            "themes": [
                {"id": "输入 items 中的 id", "theme": "生成的主题"}
            ]
        },
        "items": records,
    }

    system_prompt = (
        "你是职业教育考试命题规划助手，擅长把考纲知识点提炼成简短、准确、适合试卷主题栏使用的中文标题。"
        "请只返回一个合法 JSON 对象，不要添加 Markdown、解释或多余文字。"
    )
    user_prompt = json.dumps(prompt, ensure_ascii=False)

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=config.get("max_tokens", 8000),
                temperature=0.2,
            )
            content = response.choices[0].message.content
            data = json.loads(_extract_json_object(content))
            break
        except json.JSONDecodeError:
            print("错误：AI 返回内容不是有效 JSON")
            sys.exit(1)
        except Exception as e:
            print(f"错误：AI 主题生成调用失败 (第{attempt + 1}次): {e}")
            if attempt == 2:
                sys.exit(1)
            time.sleep((attempt + 1) * 8)

    valid_ids = {r["id"] for r in records}
    theme_map = {}
    for item in data.get("themes", []):
        item_id = item.get("id")
        theme = str(item.get("theme", "")).strip()
        if item_id in valid_ids and theme:
            theme_map[item_id] = theme

    missing = valid_ids - set(theme_map)
    if missing:
        print(f"警告：AI 未返回 {len(missing)} 个考点主题，将使用规则兜底生成。")

    return theme_map


def ai_match_toc_to_outline(toc_items, outline_points, model=None):
    """调用 config.json 中的 API，把教材目录项匹配到考纲知识点。"""
    if not toc_items or not outline_points:
        return {}
    config = load_config()
    model = model or config.get("model")
    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
    prompt = {
        "task": "把教材目录条目匹配到最相关的考纲知识点。只允许选择给定的 point id，不得新增知识点。",
        "rules": [
            "每个目录条目可匹配0到3个考纲知识点。",
            "只有语义明确相关时才匹配；不确定时返回空数组。",
            "confidence 范围0-1，低于0.55视为待人工确认。",
        ],
        "toc_items": [{"id": i["id"], "chapter": i["chapter"], "section": i["section"], "theme": i["theme"]} for i in toc_items],
        "outline_points": [{"id": p["id"], "course": p["course"], "section": p["section"], "point": p["text"], "level": p["level"]} for p in outline_points],
        "output_format": {"matches": [{"toc_id": "toc-1", "matched_point_ids": ["1-1-1"], "confidence": 0.8, "reason": "简述理由"}]},
    }
    system_prompt = "你是职业教育教材目录与考试大纲对齐助手。请只返回合法 JSON 对象，不要输出 Markdown。"
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                max_tokens=config.get("max_tokens", 8000),
                temperature=0.1,
            )
            data = json.loads(_extract_json_object(response.choices[0].message.content))
            break
        except Exception as e:
            print(f"  AI 匹配失败 (第{attempt + 1}次): {e}")
            if attempt == 2:
                return {}
            time.sleep((attempt + 1) * 8)

    point_by_id = {p["id"]: p for p in outline_points}
    result = {}
    for item in data.get("matches", []):
        if float(item.get("confidence", 0) or 0) < 0.55:
            continue
        matched = [point_by_id[pid] for pid in item.get("matched_point_ids", []) if pid in point_by_id]
        if matched:
            result[item.get("toc_id")] = matched[:3]
    return result
