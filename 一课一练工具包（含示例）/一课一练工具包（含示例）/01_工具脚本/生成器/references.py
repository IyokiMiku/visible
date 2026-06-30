"""参考资料和真题风格库加载。"""
import re

from .exam_style import is_exam_style_disabled
from .paths import REF_DIR
from .planning import _province_name_variants

MAX_EXAM_REF_CHARS = 5000
MAX_TEXTBOOK_REF_CHARS = 6000
MAX_STYLE_REF_CHARS = 5000
MAX_REF_CHARS = 12000

def _read_limited_text(path, limit):
    """读取文本并按字符数截断。"""
    text = path.read_text(encoding="utf-8")
    if len(text) > limit:
        text = text[:limit] + "\n\n...（内容已截断，以上内容足够参考）"
    return text

def _style_dir_candidates(style_dir, meta):
    """按优先级返回真题风格库目录候选，读取时兼容省份全称和简称。"""
    province = meta.get("province", "")
    category = meta.get("category", "")
    exam_type = "高职分类考试" if "高职" in meta.get("config_line", "") else "高职分类考试"

    candidates = []
    for province_name in _province_name_variants(province):
        if province_name and category:
            candidates.append(style_dir / province_name / category)
        if province_name:
            candidates.append(style_dir / province_name / "通用")
    candidates.append(style_dir / "通用" / exam_type)
    candidates.append(style_dir / "通用")

    # 去重并保序
    seen = set()
    result = []
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result

def _collect_style_files_from_dir(directory):
    """按固定顺序收集某个风格库目录下的 txt 文件。"""
    preferred = [
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
    sample_only_files = {"_自动汇总样本.txt"}
    files = []
    for name in preferred:
        path = directory / name
        if path.exists():
            files.append(path)
    for path in sorted(directory.glob("*.txt")):
        if path.name in sample_only_files:
            continue
        if path not in files:
            files.append(path)
    return files

def _load_structured_style_reference(style_dir, meta):
    """加载 省份/考类 结构化真题风格库。"""
    for directory in _style_dir_candidates(style_dir, meta):
        if not directory.exists():
            continue
        files = _collect_style_files_from_dir(directory)
        if not files:
            continue

        parts = []
        remaining = MAX_STYLE_REF_CHARS
        for path in files:
            if remaining <= 0:
                break
            text = _read_limited_text(path, remaining)
            parts.append(f"【{path.stem}】\n{text}")
            remaining -= len(text)
        if parts:
            return f"【风格库目录：{directory.relative_to(style_dir)}】\n" + "\n\n".join(parts)
    return ""

def get_exam_style_reference_status(meta):
    """返回当前生成是否会参考真题风格，用于运行前提示。"""
    if is_exam_style_disabled(meta):
        return "否（config=false，已禁用真题和真题风格）"

    style_dir = REF_DIR / "真题风格"
    if not style_dir.exists():
        return "否（未找到真题风格库目录）"

    structured_text = _load_structured_style_reference(style_dir, meta)
    if structured_text:
        first_line = structured_text.splitlines()[0].replace("【风格库目录：", "").replace("】", "")
        return f"是（{first_line}）"

    province_names = _province_name_variants(meta.get("province", ""))
    category = meta.get("category", "")
    style_keywords = []
    for province_name in province_names:
        if province_name and category:
            style_keywords.append((f"{province_name}{category}", 5))
            style_keywords.append((f"{province_name} {category}", 5))
    if category:
        style_keywords.append((category, 3))
    for province_name in province_names:
        if province_name:
            style_keywords.append((province_name, 1))

    matched_files = []
    for f in style_dir.glob("*.txt"):
        score = sum(weight for kw, weight in style_keywords if kw and kw in f.stem)
        if score > 0:
            matched_files.append((score, f))
    if matched_files:
        matched_files.sort(key=lambda x: x[0], reverse=True)
        return f"是（{matched_files[0][1].name}）"

    return "否（当前省份/考类未匹配到真题风格库）"


def _load_reference_materials(topic, meta):
    """加载与当前主题相关的参考资料（真题+真题风格+教材）

    匹配策略：
      - 真题：按类别关键词匹配文件名（如"汽车类"）
      - 真题风格：优先按省份+类别匹配，其次按类别/课程/主题关键词匹配
      - 教材：按主题名/节名/课程名模糊匹配文件名
    """
    if not REF_DIR.exists():
        return ""

    materials = []
    total_len = 0
    exam_style_disabled = is_exam_style_disabled(meta)

    # 1. 匹配真题文件（按类别匹配）
    exam_dir = REF_DIR / "真题"
    if not exam_style_disabled and exam_dir.exists():
        category = meta.get("category", "")
        province_names = _province_name_variants(meta.get("province", ""))
        matched_files = []
        for f in exam_dir.glob("*.txt"):
            score = 0
            if category and category in f.name:
                score += 2
            if any(province_name and province_name in f.name for province_name in province_names):
                score += 1
            if score > 0:
                matched_files.append((score, f))

        if matched_files:
            matched_files.sort(key=lambda x: x[0], reverse=True)
            best_file = matched_files[0][1]
            text = _read_limited_text(best_file, MAX_EXAM_REF_CHARS)
            materials.append(f"【历年真题参考——请模仿以下真题的出题风格、难度和措辞习惯，但不得照搬题干、选项或情境】\n{text}")
            total_len += len(text)

    # 2. 匹配真题风格库（优先 省份/考类 目录结构，其次兼容旧版扁平 txt）
    style_dir = REF_DIR / "真题风格"
    if not exam_style_disabled and style_dir.exists() and total_len < MAX_REF_CHARS:
        style_text = _load_structured_style_reference(style_dir, meta)

        if not style_text:
            category = meta.get("category", "")
            province_names = _province_name_variants(meta.get("province", ""))
            theme = topic.get("theme", "")
            section = topic.get("section", "")
            course = topic.get("course", "")

            style_keywords = []
            for province_name in province_names:
                if province_name and category:
                    style_keywords.append((f"{province_name}{category}", 5))
                    style_keywords.append((f"{province_name} {category}", 5))
            if category:
                style_keywords.append((category, 3))
            for province_name in province_names:
                if province_name:
                    style_keywords.append((province_name, 1))
            for kw in (course, section, theme):
                if kw:
                    clean_kw = re.sub(r'^[\s（(一二三四五六七八九十）)\d．.、]+', '', kw).strip()
                    if clean_kw:
                        style_keywords.append((clean_kw[:8], 1))

            matched_files = []
            for f in style_dir.glob("*.txt"):
                fname = f.stem
                score = sum(weight for kw, weight in style_keywords if kw and kw in fname)
                if score > 0:
                    matched_files.append((score, f))

            if matched_files:
                matched_files.sort(key=lambda x: x[0], reverse=True)
                selected_files = [f for _, f in matched_files[:2]]
                style_parts = []
                remaining = MAX_STYLE_REF_CHARS
                for style_file in selected_files:
                    if remaining <= 0:
                        break
                    text = _read_limited_text(style_file, remaining)
                    style_parts.append(f"【{style_file.stem}】\n{text}")
                    remaining -= len(text)
                style_text = "\n\n".join(style_parts)

        if style_text:
            materials.append(
                "【真题风格参考——只模仿口吻、设问方式、选项长度、干扰项风格和解析简洁程度；"
                "不得照搬样题内容，知识准确性仍以当前考纲和教材为准】\n"
                f"{style_text}"
            )
            total_len += len(style_text)

    # 3. 匹配教材文件（按课程/章节/主题名匹配）
    textbook_dir = REF_DIR / "教材"
    if textbook_dir.exists() and total_len < MAX_REF_CHARS:
        theme = topic.get("theme", "")
        section = topic.get("section", "")
        course = topic.get("course", "")

        # 提取关键词用于匹配
        keywords = []
        if theme:
            keywords.append(theme)
        if section:
            sec_clean = re.sub(r'^[\s（(一二三四五六七八九十）)\d．.、]+', '', section)
            if sec_clean:
                keywords.append(sec_clean[:6])
        if course:
            course_clean = re.sub(r'课程[一二三四五六七八九十\d]+[：:]', '', course)
            course_clean = re.sub(r'[（(].+[）)]', '', course_clean).strip()
            if course_clean:
                keywords.append(course_clean)

        matched_files = []
        for f in textbook_dir.glob("*.txt"):
            fname = f.stem
            score = sum(1 for kw in keywords if kw and kw in fname)
            if score > 0:
                matched_files.append((score, f))

        if matched_files:
            matched_files.sort(key=lambda x: x[0], reverse=True)
            best_file = matched_files[0][1]
            text = _read_limited_text(best_file, MAX_TEXTBOOK_REF_CHARS)
            materials.append(f"【教材参考内容——出题知识点必须与以下教材内容一致】\n{text}")
            total_len += len(text)

    if not materials:
        return ""

    combined = "\n\n".join(materials)

    # 超长截断
    if len(combined) > MAX_REF_CHARS:
        combined = combined[:MAX_REF_CHARS] + "\n\n...（参考资料已截断，以上内容足够参考）"

    return combined
