"""根据规划表题型方案生成/维护题型定义 JSON。"""
import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
QUESTION_TYPES_DIR = BASE_DIR / "02_配置资源" / "题型定义"
STYLE_TOOL_DIR = BASE_DIR / "01_工具脚本" / "真题风格"

TYPE_META = {
    "单选": ("single_choice", "单项选择题", "{stem}（   ）\nA. {option_a}\t\t\tB. {option_b}\nC. {option_c}\t\t\tD. {option_d}\n【答案】{answer}\n【解析】{explanation}"),
    "单项选择": ("single_choice", "单项选择题", "{stem}（   ）\nA. {option_a}\t\t\tB. {option_b}\nC. {option_c}\t\t\tD. {option_d}\n【答案】{answer}\n【解析】{explanation}"),
    "选择": ("single_choice", "单项选择题", "{stem}（   ）\nA. {option_a}\t\t\tB. {option_b}\nC. {option_c}\t\t\tD. {option_d}\n【答案】{answer}\n【解析】{explanation}"),
    "多选": ("multiple_choice", "多项选择题", "{stem}（   ）\nA. {option_a}\t\t\tB. {option_b}\nC. {option_c}\t\t\tD. {option_d}\n【答案】{answer}\n【解析】{explanation}"),
    "判断": ("true_false", "判断题", "{stem}（   ）\n【答案】{answer}\n【解析】{explanation}"),
    "填空": ("fill_blank", "填空题", "{stem}______。\n【答案】{answer}\n【解析】{explanation}"),
    "简答": ("short_answer", "简答题", "{stem}\n【答案】{answer}\n【解析】{explanation}"),
    "计算": ("calculation", "计算题", "{stem}\n【答案】{answer}\n【解析】{explanation}"),
    "综合": ("comprehensive", "综合题", "{stem}\n【答案】{answer}\n【解析】{explanation}"),
}

DEFAULT_STYLES = {
    "single_choice": {
        "stem": "题干直接、专业，围绕概念识别、结构功能、操作规范、故障原因或参数判断设问。",
        "options": "四个选项为同类短语或同类完整句，长度接近，干扰项来自相邻概念、常见误操作或同系统易混部件。",
        "answer": "答案为唯一字母，解析用1-3句说明知识依据和排除理由。",
    },
    "multiple_choice": {
        "stem": "设问应明确多选任务，避免答案数量暗示。",
        "options": "选项同层级、同结构，正确项与干扰项均应专业可信。",
        "answer": "答案为两个或多个字母，解析说明每个正确项依据及典型错误项原因。",
    },
    "true_false": {
        "stem": "题干为完整判断句，判断点单一明确，避免模棱两可的绝对化或口语化表达。",
        "answer": "答案为√或×，解析说明正误依据。",
    },
    "fill_blank": {
        "stem": "空格考查核心术语、参数、步骤名称或关键结论，统一用6个下划线表示；一道填空题可以设置一个或多个空白处。",
        "answer": "答案简洁准确；多个空的答案按题干空白顺序书写，解析对应说明每个空。",
    },
    "short_answer": {
        "stem": "围绕作用、步骤、注意事项、故障原因或操作规范设问，范围不宜过宽。",
        "answer": "按（1）（2）（3）分条，每点为完整句或完整短句。",
        "explanation": "解析说明答题思路、知识依据或易错点，不得只写见答案。",
    },
    "calculation": {
        "stem": "题干给出完整已知条件、求解目标和单位要求，可结合电路、测量或设备参数场景。",
        "answer": "答案带单位，解析按公式—代入—计算—结论书写，使用普通文本数学表达。",
        "explanation": "适中及困难题应体现计算结果服务于判断、比较或分析。",
    },
    "comprehensive": {
        "stem": "以电路、测量、设备运行、故障现象、操作场景或计算应用为情境，设置2-3个相互关联小问。",
        "subQuestions": "小问形成计算→判断→分析/措施，或现象→原因→处理的逻辑链条，避免互不相关的小问堆砌。",
        "answer": "答案按（1）（2）（3）分行书写；含计算时必须给出结果和单位。",
        "explanation": "解析说明公式来源、判断依据、故障原因或操作规范，不得只重复答案。",
    },
}


def _safe_path_part(text):
    text = (text or "").strip()
    return re.sub(r'[\\/:*?"<>|\s]+', "_", text).strip("_") or "未命名"


def parse_question_type_counts(qtypes):
    counts = {}
    for raw_name, count in re.findall(r"([一-龥]+?)(\d+)", qtypes or ""):
        name = raw_name.strip()
        meta_key = None
        for key in sorted(TYPE_META, key=len, reverse=True):
            if key in name:
                meta_key = key
                break
        if not meta_key:
            meta_key = name
        counts[meta_key] = counts.get(meta_key, 0) + int(count)
    return counts


def _type_entry(type_name, count):
    type_id, display_name, template = TYPE_META.get(type_name, (type_name, type_name, "{stem}\n【答案】{answer}\n【解析】{explanation}"))
    entry = {
        "id": type_id,
        "name": display_name,
        "defaultCount": count,
        "format": {"template": template},
        "style": DEFAULT_STYLES.get(type_id, {}),
    }
    if type_id == "comprehensive":
        entry["qualityRules"] = [
            "综合题必须有真实专业情境，不应只是概念问答。",
            "多个小问之间必须有关联，优先形成计算→判断→分析/措施链条。",
            "答案和解析按（1）（2）（3）分行书写。",
        ]
    return entry


def build_template_config(province, category, qtypes, textbooks=None):
    counts = parse_question_type_counts(qtypes)
    return {
        "id": _safe_path_part(category),
        "name": category,
        "province": province,
        "description": f"{province}{category}一课一练题型定义；题量由规划表题型列控制，本文档只定义题型风格、格式和质量要求。",
        "questionCountPolicy": {
            "source": "planning_table",
            "defaultTotal": sum(counts.values()),
            "note": "出卷时以规划表“题型”列为准；defaultCount 仅作为生成规划表或人工校对参考。",
        },
        "textbooks": textbooks or [],
        "questionTypes": [_type_entry(name, count) for name, count in counts.items()],
    }


def _load_config():
    config_path = BASE_DIR / "02_配置资源" / "config.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


def _load_style_tool():
    if str(STYLE_TOOL_DIR) not in sys.path:
        sys.path.insert(0, str(STYLE_TOOL_DIR))
    import extract_exam_style
    return extract_exam_style


def _extract_json_object(text):
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        return fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def _generate_config_with_api(province, category, qtypes, textbooks, client, config):
    style_tool = _load_style_tool()
    sample_text = ""
    try:
        from planning_assets import find_exam_bank_dir
        source_dir = find_exam_bank_dir(province, category)
        if source_dir:
            sample_text = style_tool.collect_source_texts(source_dir)[:40000]
    except Exception:
        sample_text = ""

    template = build_template_config(province, category, qtypes, textbooks)
    system_prompt = "你是职业教育高职分类考试题型配置专家。请根据真题样本总结题型定义 JSON，不要照搬真题内容。只返回合法 JSON。"
    user_prompt = f"""请为{province}{category}生成题型定义 JSON。

硬性要求：
1. 题量由规划表控制，JSON 中 defaultCount 只作为参考，不能覆盖用户题量。
2. 保留以下题型及数量：{qtypes}
3. 每个题型写出 format.template、style、qualityRules 或注意事项。
4. 综合题必须强调专业情境、2-3个关联小问、计算/判断/分析链条、答案解析按（1）（2）分行。
5. 不得照搬真题题干、选项、情境或数值。

基础模板：
{json.dumps(template, ensure_ascii=False, indent=2)}

真题样本（可能为空）：
{sample_text}
"""
    response = client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        max_tokens=config.get("max_tokens", 8000),
        temperature=0.2,
    )
    return json.loads(_extract_json_object(response.choices[0].message.content))


def _update_index(category, province):
    QUESTION_TYPES_DIR.mkdir(parents=True, exist_ok=True)
    index_path = QUESTION_TYPES_DIR / "index.json"
    if index_path.exists():
        data = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        data = {"courses": [], "qualityRules": {}}
    courses = data.setdefault("courses", [])
    file_name = f"{category}.json"
    aliases = [category, category.replace("类", ""), f"{province}{category}"]
    if category.endswith("类"):
        aliases.append(category[:-1])
    if province.endswith("自治区"):
        aliases.append(f"{province.replace('自治区', '')}{category}")
    if province == "内蒙古自治区":
        aliases.extend(["内蒙古", f"内蒙古{category}", category.replace("类", "")])
    if province == "新疆维吾尔自治区":
        aliases.append(f"新疆{category}")
    if province == "广西壮族自治区":
        aliases.append(f"广西{category}")
    if province == "宁夏回族自治区":
        aliases.append(f"宁夏{category}")

    entry = {
        "id": _safe_path_part(category),
        "name": category,
        "aliases": list(dict.fromkeys([a for a in aliases if a])),
        "file": file_name,
    }
    for idx, existing in enumerate(courses):
        if existing.get("name") == category or existing.get("file") == file_name:
            merged_aliases = list(dict.fromkeys((existing.get("aliases") or []) + entry["aliases"]))
            existing.update(entry)
            existing["aliases"] = merged_aliases
            courses[idx] = existing
            break
    else:
        courses.append(entry)
    index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  已更新题型定义索引：{index_path}")


def _build_config_data(province, category, qtypes, mode, client=None, config=None, textbooks=None):
    if mode == "auto":
        if client is None:
            from openai import OpenAI
            config = config or _load_config()
            client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
        return _generate_config_with_api(province, category, qtypes, textbooks or [], client, config or _load_config())
    return build_template_config(province, category, qtypes, textbooks or [])


def ensure_question_type_config(province, category, qtypes, mode="template", client=None, config=None, textbooks=None, refresh=False, suggest_if_exists=True):
    """生成/更新题型定义 JSON。

    mode=auto 时尝试调用 API 总结真题；mode=skip 时只维护 index。
    已存在的正式 JSON 默认不覆盖，避免冲掉人工调整；可用 refresh=True 覆盖。
    """
    QUESTION_TYPES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = QUESTION_TYPES_DIR / f"{category}.json"

    if mode == "skip":
        print("  已跳过题型定义生成，仅维护索引。")
        _update_index(category, province)
        return output_path if output_path.exists() else None

    data = _build_config_data(province, category, qtypes, mode, client=client, config=config, textbooks=textbooks or [])

    if output_path.exists() and not refresh:
        print(f"  题型定义已存在，默认不覆盖：{output_path}")
        if suggest_if_exists:
            suggest_path = QUESTION_TYPES_DIR / f"{category}_建议版.json"
            suggest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"  已生成题型定义建议版：{suggest_path}")
        _update_index(category, province)
        return output_path

    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  已生成题型定义：{output_path}")
    _update_index(category, province)
    return output_path
