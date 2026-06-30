"""生成试卷前的真题风格库预检与自动生成。"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from .paths import BASE_DIR, REF_DIR

STYLE_DIR = REF_DIR / "真题风格"
EXAM_BANK_DIR = BASE_DIR / "03_项目数据" / "真题题库"
STYLE_TOOL_DIR = BASE_DIR / "01_工具脚本" / "真题风格"

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
STYLE_SAMPLE_FILES = {"_自动汇总样本.txt"}
SUPPORTED_SOURCE_SUFFIXES = {".txt", ".docx", ".pdf"}

_PROVINCE_ALIASES = {
    "内蒙古自治区": ["内蒙古自治区", "内蒙古"],
    "内蒙古": ["内蒙古", "内蒙古自治区"],
    "新疆维吾尔自治区": ["新疆维吾尔自治区", "新疆"],
    "新疆": ["新疆", "新疆维吾尔自治区"],
    "西藏自治区": ["西藏自治区", "西藏"],
    "西藏": ["西藏", "西藏自治区"],
    "广西壮族自治区": ["广西壮族自治区", "广西"],
    "广西": ["广西", "广西壮族自治区"],
    "宁夏回族自治区": ["宁夏回族自治区", "宁夏"],
    "宁夏": ["宁夏", "宁夏回族自治区"],
}


def _safe_path_part(text):
    """保持与真题风格提取脚本一致的路径清理规则。"""
    import re

    text = (text or "").strip()
    return re.sub(r'[\\/:*?"<>|\s]+', "_", text).strip("_") or "未命名"


def _province_candidates(province):
    """返回省份/自治区目录候选，兼容简称和全称。"""
    province = (province or "").strip()
    candidates = _PROVINCE_ALIASES.get(province, [province])
    result = []
    for name in candidates:
        if name and name not in result:
            result.append(name)
    return result


def _style_dir_for(meta):
    """当前省份/考类对应的规范结构化风格库目录；输出统一使用省份全称。"""
    return STYLE_DIR / _safe_path_part(meta.get("province", "")) / _safe_path_part(meta.get("category", ""))


def _style_dir_candidates(meta):
    """返回可读取的风格库目录候选，兼容省份全称和简称。"""
    category = _safe_path_part(meta.get("category", ""))
    candidates = []
    if not category:
        return candidates
    for province in _province_candidates(meta.get("province", "")):
        candidate = STYLE_DIR / _safe_path_part(province) / category
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _find_existing_style_dir(meta):
    """查找已有可用风格库目录；读取兼容简称/全称，生成仍写入规范全称目录。"""
    for candidate in _style_dir_candidates(meta):
        if _style_library_ready(candidate):
            return candidate
    return None


def _exam_bank_dir_for(meta, province=None):
    """当前省份/考类对应的题库目录；province 为空时使用 meta 中的规范省份。"""
    province = province or meta.get("province", "")
    return EXAM_BANK_DIR / _safe_path_part(province) / _safe_path_part(meta.get("category", ""))


def exam_style_config_path(meta):
    """返回当前省份/考类的真题风格开关配置文件路径。"""
    return _exam_bank_dir_for(meta) / "真题风格配置.json"


def _find_exam_style_config_path(meta):
    """按省份候选查找已存在的真题风格配置文件。"""
    category = _safe_path_part(meta.get("category", ""))
    if not category:
        return None
    for province in _province_candidates(meta.get("province", "")):
        path = EXAM_BANK_DIR / _safe_path_part(province) / category / "真题风格配置.json"
        if path.exists():
            return path
    return None


def is_exam_style_disabled(meta):
    """当真题风格配置文件中 config 为 false 时，禁用真题和真题风格读取。"""
    path = _find_exam_style_config_path(meta)
    if not path:
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return data.get("config") is False


def write_exam_style_disabled_config(meta):
    """写入 config=false，表示当前省份/考类不读取真题和真题风格。"""
    target_dir = _exam_bank_dir_for(meta)
    target_dir.mkdir(parents=True, exist_ok=True)
    config_path = target_dir / "真题风格配置.json"
    note_path = target_dir / "真题风格配置说明.txt"
    data = {
        "config": False,
        "reason": "用户确认当前考类暂不补充真题；生成试卷时禁用真题和真题风格参考。",
        "province": meta.get("province", ""),
        "category": meta.get("category", ""),
        "how_to_enable": "如需重新启用，请将 config 改为 true，或删除本文件后重新运行 create.py。",
    }
    config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    note_path.write_text(
        "当前省份/考类已配置 config=false。\n"
        "在改回 true 或删除 真题风格配置.json 之前，生成器不会读取该类真题，也不会读取该类或通用真题风格库。\n"
        "如需恢复：打开 真题风格配置.json，将 \"config\" 改为 true，或删除该配置文件。\n",
        encoding="utf-8",
    )
    return config_path


def _prompt_missing_exam_bank(meta, style_dir, source_dir=None):
    """无对应题库或题库无可处理文件时，询问是否持久禁用真题/风格。"""
    print("\n当前省份/考类尚无可用真题题库，无法生成真题风格库：")
    print(f"  省份/考类: {meta.get('province', '')} {meta.get('category', '')}")
    print(f"  期望风格库: {style_dir}")
    if source_dir:
        print(f"  题库目录: {source_dir}")
    else:
        print(f"  题库根目录: {EXAM_BANK_DIR}")
    print("请选择后续处理方式：")
    print("  1. 我会补充真题，本次先跳过风格生成")
    print("  2. 暂不补充，生成 config=false，今后不读取真题和真题风格")
    print("  3. 本次跳过，但不写配置")
    choice = input("请选择 [1/2/3，默认1]: ").strip()
    if choice == "2":
        return "disable"
    if choice == "3":
        return "skip"
    return "wait"


def _handle_missing_exam_bank(meta, style_dir, source_dir, mode):
    """处理无题库/无可处理真题文件的情况。"""
    if mode == "ask" and sys.stdin is not None and sys.stdin.isatty():
        action = _prompt_missing_exam_bank(meta, style_dir, source_dir)
        if action == "disable":
            config_path = write_exam_style_disabled_config(meta)
            print(f"已写入真题风格禁用配置：{config_path}")
            print("后续生成将不读取真题，也不读取真题风格；改回 config=true 或删除该文件后恢复。")
        elif action == "wait":
            print("已记录为本次跳过。请补充真题后重新运行 create.py。")
        else:
            print("本次跳过真题风格生成，未写入配置。")
    else:
        print("\n未找到当前省份/考类的可用真题题库，已跳过真题风格生成。")
        print("如暂不补充真题，可在交互模式选择生成 config=false；非交互模式不会自动禁用。")
    return False


def _has_nonempty_text(path):
    """判断文本文件是否有实际内容。"""
    try:
        return path.exists() and path.is_file() and bool(path.read_text(encoding="utf-8", errors="ignore").strip())
    except OSError:
        return False


def _style_library_ready(style_dir):
    """判断风格库是否已有结构化风格文件；自动汇总样本不算可用风格。"""
    if not style_dir.exists() or not style_dir.is_dir():
        return False

    return any(_has_nonempty_text(style_dir / name) for name in PREFERRED_STYLE_FILES)


def _style_dir_has_sample_only(style_dir):
    """判断目录是否只有自动汇总样本，尚未生成真正的风格文件。"""
    if not style_dir.exists() or not style_dir.is_dir():
        return False
    txt_files = [path for path in style_dir.glob("*.txt") if _has_nonempty_text(path)]
    return bool(txt_files) and all(path.name in STYLE_SAMPLE_FILES for path in txt_files)


def _find_exam_bank_dir(meta):
    """查找当前省份/考类对应的原始真题题库目录。"""
    category = _safe_path_part(meta.get("category", ""))
    if not category:
        return None

    for province in _province_candidates(meta.get("province", "")):
        candidate = EXAM_BANK_DIR / _safe_path_part(province) / category
        if candidate.exists() and candidate.is_dir():
            return candidate

    return None


def _has_supported_sources(source_dir):
    """题库目录是否包含可尝试提取的真题文件。"""
    if not source_dir or not source_dir.exists():
        return False
    return any(
        path.is_file()
        and not path.name.startswith("~")
        and path.suffix.lower() in SUPPORTED_SOURCE_SUFFIXES
        for path in source_dir.rglob("*")
    )


def _load_style_tool():
    """按需加载真题风格提取脚本，避免生成器启动时做额外导入。"""
    if str(STYLE_TOOL_DIR) not in sys.path:
        sys.path.insert(0, str(STYLE_TOOL_DIR))
    import extract_exam_style

    return extract_exam_style


def _prompt_style_action(source_dir, style_dir):
    """交互询问风格库缺失时的处理方式。"""
    print("\n检测到当前省份/考类的真题风格库缺失或为空：")
    print(f"  风格库目录: {style_dir}")
    print(f"  题库目录: {source_dir}")
    print("可在生成试卷前先从题库生成真题风格库。")
    print("  1. 自动蒸馏风格库（调用 API）")
    print("  2. 只生成可人工填写的模板（不调用 API）")
    print("  3. 跳过，继续生成试卷")
    choice = input("请选择 [1/2/3，默认3]: ").strip()
    if choice == "1":
        return "api"
    if choice == "2":
        return "template"
    return "skip"


def _build_style_args(meta, source_dir, no_api):
    """构造 extract_exam_style.process_source_dir 所需参数对象。"""
    return SimpleNamespace(
        source_dir=str(source_dir),
        province=meta.get("province", ""),
        exam_category=meta.get("category", ""),
        category="",
        output=None,
        no_api=no_api,
        max_examples=8,
        split_files=True,
        sample_only=False,
        ocr_pdf=True,
        ocr_pages="",
        ocr_dpi=2.5,
        ocr_lang="chi_sim",
        tessdata=None,
        ocr_preprocess=False,
    )


def ensure_exam_style_ready(meta, client, config, mode="ask"):
    """确保当前规划表对应的真题风格库可用。

    mode:
      - "ask": 缺失时交互询问；非交互环境只提示并跳过
      - "auto": 缺失时调用 API 自动蒸馏
      - "template": 缺失时只生成模板，不调用 API
      - "skip": 不生成，只提示
    """
    province = meta.get("province", "")
    category = meta.get("category", "")
    if not province or not category:
        print("\n未识别到省份或考类，跳过真题风格库预检。")
        return False

    if is_exam_style_disabled(meta):
        config_path = _find_exam_style_config_path(meta)
        print("\n当前省份/考类已配置 config=false，跳过真题题库与真题风格库。")
        print(f"  配置文件: {config_path}")
        return False

    style_dir = _style_dir_for(meta)
    existing_style_dir = _find_existing_style_dir(meta)
    if existing_style_dir:
        print(f"\n真题风格库已存在：{existing_style_dir}")
        return True

    sample_only_dirs = [candidate for candidate in _style_dir_candidates(meta) if _style_dir_has_sample_only(candidate)]
    if sample_only_dirs:
        print("\n检测到当前省份/考类目录下只有 _自动汇总样本.txt，尚未生成各题型真题风格文件。")
        for sample_dir in sample_only_dirs:
            print(f"  样本目录: {sample_dir}")
        print("应重新生成真题风格库，或至少生成/填写 风格总则.txt、各题型风格.txt、代表样题.txt 等文件。")

    source_dir = _find_exam_bank_dir(meta)
    if not source_dir:
        return _handle_missing_exam_bank(meta, style_dir, None, mode)

    if not _has_supported_sources(source_dir):
        return _handle_missing_exam_bank(meta, style_dir, source_dir, mode)

    action = mode
    if mode == "ask":
        if sys.stdin is not None and sys.stdin.isatty():
            action = _prompt_style_action(source_dir, style_dir)
        else:
            print("\n检测到真题风格库缺失，但当前不是交互环境，已跳过自动生成。")
            print("如需自动蒸馏，请加 --auto-style；如只需模板，请加 --style-template。")
            return False

    if action == "skip":
        print("\n已跳过真题风格库生成，将继续按现有参考资料生成试卷。")
        return False

    no_api = action == "template"
    if no_api:
        print("\n正在生成真题风格库模板（不调用 API）...")
    else:
        print("\n正在从真题题库自动蒸馏真题风格库（将调用 API）...")

    style_tool = _load_style_tool()
    if no_api:
        display = f"{province}{category}"
        style_tool.write_split_templates(style_dir, display)
        ok = True
    else:
        args = _build_style_args(meta, source_dir, no_api=False)
        ok = style_tool.process_source_dir(args, client=client, config=config)

    if ok and _style_library_ready(style_dir):
        print(f"真题风格库已准备完成：{style_dir}")
        return True

    print("真题风格库未能生成可用内容。")
    print("可能原因：PDF 为扫描版/图片型，无法直接提取文字。可先用 01_工具脚本/OCR/ocr_pdf.py 或人工摘录代表题后再蒸馏。")
    return False
