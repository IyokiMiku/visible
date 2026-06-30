"""AI 返回文本清洗、摘要与主题编号工具。"""
import re

from .planning import _CN_TO_DIGIT

def parse_paper_text(text):
    """将 API 返回的纯文本试卷解析为结构化数据"""
    sections = []
    current_section = None
    current_lines = []

    for line in text.split("\n"):
        stripped = line.strip()
        # 检测大题标题
        if re.match(r"^[一二三四五六七八九十][、.．]", stripped):
            if current_section:
                sections.append({"title": current_section, "content": "\n".join(current_lines)})
            current_section = stripped
            current_lines = []
        else:
            current_lines.append(line)

    if current_section:
        sections.append({"title": current_section, "content": "\n".join(current_lines)})

    return sections

def _normalize_generated_text(text):
    """修正常见模型转义残留，避免数学符号进入 DOCX 前变成乱码。"""
    if not text:
        return text

    # 保护 {{math:...}} 内部的 LaTeX/线性公式，避免被正文清洗逻辑压平成普通文本。
    math_chunks = []

    def _stash_math(match):
        math_chunks.append(match.group(0))
        return f"@@MATH_MARKER_{len(math_chunks) - 1}@@"

    text = re.sub(r"\{\{math:.*?\}\}", _stash_math, text, flags=re.DOTALL)

    # 去掉常见 LaTeX 行内公式包裹，避免 DOCX 中残留反斜杠括号。
    text = re.sub(r"\\\s*\((.*?)\\\s*\)", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\\\s*\[(.*?)\\\s*\]", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\$(.*?)\$", r"\1", text, flags=re.DOTALL)

    # 将常见 LaTeX 分式转为普通文本，优先处理一层花括号分式。
    frac_pattern = re.compile(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}")
    while True:
        new_text = frac_pattern.sub(r"(\1)/(\2)", text)
        if new_text == text:
            break
        text = new_text

    # 先处理成对定界符，避免后续把 \left 里的 \le 误替换成“≤”。
    text = re.sub(r"\\\s*l\s*e\s*f\s*t\s*([（(\[{])", r"\1", text)
    text = re.sub(r"\\\s*r\s*i\s*g\s*h\s*t\s*([）)\]}])", r"\1", text)
    text = re.sub(r"\\\s*r\s*i\s*g\s*h\s*t", "", text)

    replacements = {
        r"\pm": "±",
        r"\times": "×",
        r"\cdot": "·",
        r"\div": "÷",
        r"\le": "≤",
        r"\ge": "≥",
        r"\neq": "≠",
        r"\approx": "≈",
        r"\pi": "π",
        r"\rho": "ρ",
        r"\Omega": "Ω",
        r"\mu": "μ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # 若已经出现“≤ft/≤f t”，通常是 \left 被误替换后的残留，直接还原为左定界符。
    text = re.sub(r"≤\s*f\s*t\s*([（(\[{])", r"\1", text)
    text = re.sub(r"≤\s*f\s*t", "", text)

    # 兼容模型把 LaTeX 符号拆成“\ p m”或“\p m”等异常形式的情况。
    text = re.sub(r"\\\s*p\s*m", "±", text)
    text = re.sub(r"\\\s*t\s*i\s*m\s*e\s*s", "×", text)
    text = re.sub(r"\\\s*r\s*h\s*o", "ρ", text)
    text = re.sub(r"\\\s*O\s*m\s*e\s*g\s*a", "Ω", text)

    # 清理 LaTeX 空格命令和简单分式外层括号，让“(L)/(S)”变成“L/S”。
    text = re.sub(r"\\[,;:!]?", "", text)
    text = re.sub(r"\(([A-Za-z0-9.]+)\)/\(([A-Za-z0-9.]+)\)", r"\1/\2", text)

    # 电子技术常见参数如果被模型写成 ICEO/ICBO 等纯文本，统一转为带下标的公式标记。
    electronic_subscripts = {
        "ICEO": "I_{CEO}",
        "ICBO": "I_{CBO}",
        "IEBO": "I_{EBO}",
        "ICM": "I_{CM}",
        "IC": "I_C",
        "IB": "I_B",
        "IE": "I_E",
        "UCEO": "U_{CEO}",
        "UCBO": "U_{CBO}",
        "UEBO": "U_{EBO}",
        "UCE": "U_{CE}",
        "UCB": "U_{CB}",
        "UBE": "U_{BE}",
        "PCM": "P_{CM}",
        "hFE": "h_{FE}",
        "hfe": "h_{fe}",
        "rbe": "r_{be}",
    }
    for plain, formula in electronic_subscripts.items():
        text = re.sub(
            rf"(?<![A-Za-z0-9_]){re.escape(plain)}(?![A-Za-z0-9_])",
            f"{{{{math:{formula}}}}}",
            text,
        )

    # 兼容“1 2 0 ± 0.03 mm”这类数字被逐位空格拆开的尺寸公差。
    text = re.sub(
        r"(?<!\d)((?:\d\s+){2,}\d)\s*±\s*(\d+(?:\.\d+)?)\s*(mm|cm|m|μm|um)\b",
        lambda m: re.sub(r"\s+", "", m.group(1)) + f"±{m.group(2)} {m.group(3)}",
        text,
    )

    def _restore_math(match):
        idx = int(match.group(1))
        return math_chunks[idx]

    text = re.sub(r"@@MATH_MARKER_(\d+)@@", _restore_math, text)
    return text

def _merge_extra_subanswer_numbers(lines):
    """合并答案/解析中超过题干小问数量的误编号续行。"""
    subq_re = re.compile(r"^[（(](\d+|[一二三四五六七八九十]+)[）)]\s*(.*)$")
    q_start_re = re.compile(r"^\d+[\.．、]")
    section_re = re.compile(r"^[一二三四五六七八九十][、.．]")

    def marker_num(raw):
        if raw.isdigit():
            return int(raw)
        return _CN_TO_DIGIT.get(raw, 0)

    def max_subq_count(q_lines):
        max_num = 0
        for q_line in q_lines:
            for match in re.finditer(r"[（(](\d+|[一二三四五六七八九十]+)[）)]", q_line):
                max_num = max(max_num, marker_num(match.group(1)))
        return max_num

    fixed = []
    current_q_lines = []
    current_subq_count = 0
    in_labeled_block = False

    for line in lines:
        stripped = line.strip()

        if q_start_re.match(stripped) and "【答案】" not in stripped:
            current_q_lines = [stripped]
            current_subq_count = 0
            in_labeled_block = False
            fixed.append(line)
            continue

        if section_re.match(stripped):
            current_q_lines = []
            current_subq_count = 0
            in_labeled_block = False
            fixed.append(line)
            continue

        if stripped.startswith(("【答案】", "【解析】", "【详解】")):
            current_subq_count = max_subq_count(current_q_lines)
            in_labeled_block = True
            fixed.append(line)
            continue

        if in_labeled_block:
            match = subq_re.match(stripped)
            if match and current_subq_count and marker_num(match.group(1)) > current_subq_count and fixed:
                continuation = match.group(2).strip()
                if continuation:
                    fixed[-1] = fixed[-1].rstrip() + " " + continuation
                continue
            fixed.append(line)
            continue

        if current_q_lines and stripped:
            current_q_lines.append(stripped)
        fixed.append(line)

    return fixed


def _clean_paper_text(text):
    """清理 AI 返回的试卷文本：去除思考块、markdown 标记、自检清单等多余内容"""
    text = _normalize_generated_text(text)

    # 部分推理模型/代理偶尔会把隐藏思考以 <think>...</think> 泄露到正文。
    text = re.sub(r"(?is)<think\b[^>]*>.*?</think>\s*", "", text)
    text = re.sub(r"(?is)^.*?</think>\s*", "", text)

    lines = text.split("\n")
    cleaned = []

    # 标记是否进入自检清单区域
    in_checklist = False
    current_section = ""

    for line in lines:
        stripped = line.strip()

        # 跳过自检清单（从"【自检清单"或"□"开头的连续行）
        if "自检清单" in stripped or (in_checklist and stripped.startswith("□")):
            in_checklist = True
            continue
        if in_checklist and not stripped:
            continue
        in_checklist = False

        # 跳过 markdown 标题行（如 # 重庆市一课一练、## 《xxx》）
        if re.match(r"^#{1,6}\s", stripped):
            # 但保留大类题型标题（去掉 ### 前缀）
            content_after_hash = re.sub(r"^#{1,6}\s*", "", stripped)
            if re.match(r"^[一二三四五六七八九十][、.．]", content_after_hash):
                cleaned.append(content_after_hash)
            # 其他 markdown 标题（如 # 重庆市一课一练）直接丢弃
            continue

        if re.match(r"^[一二三四五六七八九十][、.．]", stripped):
            current_section = stripped

        # 判断题答案统一规范为 √ / ×，避免模型输出“对/错/正确/错误”。
        if stripped.startswith("【答案】") and "判断" in current_section:
            ans_text = stripped[4:].strip()
            if ans_text in ("对", "正确", "√", "是"):
                line = "【答案】√"
            elif ans_text in ("错", "错误", "×", "否"):
                line = "【答案】×"

        cleaned.append(line)

    cleaned = _merge_extra_subanswer_numbers(cleaned)

    # 去除首尾空行
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()

    # 模型偶尔会在题目/选项与【答案】之间插入空行；这里统一删除。
    compacted = []
    for idx, line in enumerate(cleaned):
        if not line.strip():
            next_nonempty = ""
            for later in cleaned[idx + 1:]:
                if later.strip():
                    next_nonempty = later.strip()
                    break
            if next_nonempty.startswith(("【答案】", "【解析】", "【详解】")):
                continue
        compacted.append(line)

    return "\n".join(compacted)

def _extract_question_summaries(paper_text):
    """从试卷文本中提取每道题的摘要（题干前80字），用于传入下一批避免重复"""
    summaries = []
    for line in paper_text.split("\n"):
        line = line.strip()
        if re.match(r"^\d+[\.．、]", line):
            summaries.append(line[:80])
    return summaries

def _split_numbered_theme(theme):
    """拆分“xxx（一）/xxx(二)”这类连续主题，返回 (基础主题, 序号)。普通主题序号为 None。"""
    match = re.match(r"^(.+?)[（(]([一二三四五六七八九十]+)[）)]$", str(theme or "").strip())
    if not match:
        return str(theme or "").strip(), None
    base = match.group(1).strip()
    num = _CN_TO_DIGIT.get(match.group(2))
    return base, num
