"""规划表阶段准备真题风格库与题型定义配置。"""
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

BASE_DIR = Path(__file__).resolve().parents[2]
EXAM_BANK_DIR = BASE_DIR / "03_项目数据" / "真题题库"
STYLE_DIR = BASE_DIR / "03_项目数据" / "参考资料" / "真题风格"
STYLE_TOOL_DIR = BASE_DIR / "01_工具脚本" / "真题风格"

_AUTONOMOUS_REGION_MAP = {
    "内蒙古": "内蒙古自治区",
    "新疆": "新疆维吾尔自治区",
    "西藏": "西藏自治区",
    "广西": "广西壮族自治区",
    "宁夏": "宁夏回族自治区",
}

SUPPORTED_SOURCE_SUFFIXES = {".txt", ".docx", ".pdf"}
PREFERRED_STYLE_FILES = [
    "风格总则.txt",
    "单选题风格.txt",
    "多选题风格.txt",
    "判断题风格.txt",
    "填空题风格.txt",
    "简答题风格.txt",
    "计算题风格.txt",
    "综合题风格.txt",
    "代表样题.txt",
]


def safe_path_part(text):
    """清理路径非法字符。"""
    text = (text or "").strip()
    return re.sub(r'[\\/:*?"<>|\s]+', "_", text).strip("_") or "未分类"


def normalize_province_name(province):
    """自治区输出统一为规范全称。"""
    name = str(province or "").strip()
    return _AUTONOMOUS_REGION_MAP.get(name, name)


def province_name_variants(province):
    """读取资料时兼容省份全称和简称。"""
    name = str(province or "").strip()
    normalized = normalize_province_name(name)
    variants = []
    for item in (normalized, name):
        if item and item not in variants:
            variants.append(item)
    for short_name, full_name in _AUTONOMOUS_REGION_MAP.items():
        if normalized == full_name and short_name not in variants:
            variants.append(short_name)
    return sorted(variants, key=len, reverse=True)


def split_province_category(title_prefix):
    """从标题前缀中解析省份和考类，兼容自治区全称/简称。"""
    text = (title_prefix or "").strip()
    province_pattern = r"(内蒙古自治区|新疆维吾尔自治区|西藏自治区|广西壮族自治区|宁夏回族自治区|[一-龥]+(?:省|市|自治区)|内蒙古|新疆|西藏|广西|宁夏)"
    match = re.search(province_pattern, text)
    if not match:
        return "", ""
    province = normalize_province_name(match.group(1))
    rest = text
    for name in province_name_variants(province):
        if name in rest:
            rest = rest.replace(name, "", 1)
            break
    cat_match = re.search(r"([一-龥]+类)", rest)
    return province, cat_match.group(1) if cat_match else ""


def parse_question_type_counts(qtypes):
    """解析“单选5+填空3+综合2”形式的题型数量。"""
    counts = {}
    for name, count in re.findall(r"([一-龥]+?)(\d+)", qtypes or ""):
        counts[name] = counts.get(name, 0) + int(count)
    return counts


def question_type_total(qtypes):
    return sum(parse_question_type_counts(qtypes).values())


def validate_question_plan(qtypes, total_questions=10, label="题型配置"):
    """校验规划表题型数量合计。"""
    actual = question_type_total(qtypes)
    if actual != int(total_questions):
        raise ValueError(f"{label}合计为 {actual} 道，不等于要求的 {total_questions} 道：{qtypes}")
    return actual


def style_library_ready(style_dir):
    """判断风格库是否已有可用 txt 内容。"""
    style_dir = Path(style_dir)
    if not style_dir.exists() or not style_dir.is_dir():
        return False
    for name in PREFERRED_STYLE_FILES:
        path = style_dir / name
        if path.exists() and path.is_file() and path.read_text(encoding="utf-8", errors="ignore").strip():
            return True
    for path in style_dir.glob("*.txt"):
        if path.read_text(encoding="utf-8", errors="ignore").strip():
            return True
    return False


def style_dir_for(province, category):
    """风格库输出目录：省份统一规范全称。"""
    return STYLE_DIR / safe_path_part(normalize_province_name(province)) / safe_path_part(category)


def find_existing_style_dir(province, category):
    """读取时兼容省份全称/简称。"""
    for name in province_name_variants(province):
        candidate = STYLE_DIR / safe_path_part(name) / safe_path_part(category)
        if style_library_ready(candidate):
            return candidate
    return None


def find_exam_bank_dir(province, category):
    """查找真题题库目录，兼容省份全称/简称。"""
    if not category:
        return None
    for name in province_name_variants(province):
        candidate = EXAM_BANK_DIR / safe_path_part(name) / safe_path_part(category)
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def has_supported_sources(source_dir):
    source_dir = Path(source_dir) if source_dir else None
    if not source_dir or not source_dir.exists():
        return False
    return any(
        path.is_file()
        and not path.name.startswith("~")
        and path.suffix.lower() in SUPPORTED_SOURCE_SUFFIXES
        for path in source_dir.rglob("*")
    )


def load_style_tool():
    if str(STYLE_TOOL_DIR) not in sys.path:
        sys.path.insert(0, str(STYLE_TOOL_DIR))
    import extract_exam_style
    return extract_exam_style


def prepare_exam_style(province, category, mode="auto", client=None, config=None):
    """在规划表阶段准备专属真题风格库。

    mode: auto 调 API 蒸馏；template 只写模板；skip 跳过。
    """
    if mode == "skip":
        print("  已跳过真题风格库准备。")
        return False
    province = normalize_province_name(province)
    style_dir = style_dir_for(province, category)
    existing = find_existing_style_dir(province, category)
    if existing:
        print(f"  真题风格库已存在：{existing}")
        return True

    source_dir = find_exam_bank_dir(province, category)
    if not source_dir:
        print(f"  未找到真题题库目录，跳过风格库生成：{EXAM_BANK_DIR}")
        return False
    if not has_supported_sources(source_dir):
        print(f"  真题题库目录无 txt/docx/pdf 可处理文件，跳过：{source_dir}")
        return False

    style_tool = load_style_tool()
    if mode == "template":
        print(f"  正在生成真题风格库模板：{style_dir}")
        style_tool.write_split_templates(style_dir, f"{province}{category}")
        return True

    print(f"  正在从真题题库生成真题风格库：{source_dir}")
    args = SimpleNamespace(
        source_dir=str(source_dir),
        province=province,
        exam_category=category,
        category="",
        output=None,
        no_api=False,
        max_examples=8,
        split_files=True,
    )
    ok = style_tool.process_source_dir(args, client=client, config=config)
    return bool(ok)


def prepare_planning_assets(title_prefix, qtypes, total_questions=10, style_mode="auto", type_config_mode="template", client=None, config=None, textbooks=None, refresh_type_config=False):
    """生成规划表后准备题型定义和真题风格库。"""
    province, category = split_province_category(title_prefix)
    if not province or not category:
        print("\n未能从标题解析省份/考类，跳过题型配置和真题风格准备。")
        return

    print("\n正在准备规划表配套资源：")
    print(f"  省份/考类：{province} {category}")
    validate_question_plan(qtypes, total_questions)

    try:
        from question_type_config import ensure_question_type_config
        ensure_question_type_config(
            province=province,
            category=category,
            qtypes=qtypes,
            mode=type_config_mode,
            client=client,
            config=config,
            textbooks=textbooks or [],
            refresh=refresh_type_config,
        )
    except Exception as exc:
        print(f"  警告：题型定义配置准备失败：{exc}")

    try:
        prepare_exam_style(province, category, mode=style_mode, client=client, config=config)
    except Exception as exc:
        print(f"  警告：真题风格库准备失败：{exc}")
