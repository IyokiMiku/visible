"""本地质检集成与定向修复。"""
import importlib.util
import re
import sys

from .config_io import _record_token_usage, call_api
from .paths import BASE_DIR
from .text_processing import _clean_paper_text

MAX_REGEN_ATTEMPTS = 3

def _quick_check(paper_text):
    """对试卷文本进行快速本地质检，返回 (严重问题列表, 警告列表, 评分, 信息列表)"""
    check_dir = (BASE_DIR / "01_工具脚本" / "质检").resolve()
    check_file = check_dir / "check.py"
    if str(check_dir) not in sys.path:
        sys.path.insert(0, str(check_dir))

    try:
        from check import local_check
    except ModuleNotFoundError as exc:
        if exc.name != "check" or not check_file.exists():
            raise
        import importlib.util

        spec = importlib.util.spec_from_file_location("local_quality_check", check_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载质检模块: {check_file}") from exc
        check_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(check_module)
        local_check = check_module.local_check

    issues, questions = local_check(paper_text)
    severe = [i for i in issues if i["severity"] == "严重"]
    warnings = [i for i in issues if i["severity"] == "警告"]
    infos = [i for i in issues if i["severity"] == "信息"]

    score = 100 - len(severe) * 15 - len(warnings) * 5
    score = max(0, score)

    return severe, warnings, score, questions, infos

def _print_qc_summary(severe, warnings, score, infos=None):
    """打印质检摘要"""
    if severe:
        print(f"  质检: {score}/100 | 严重问题 {len(severe)} 个:")
        for issue in severe:
            print(f"    ✗ [第{issue['question']}题] {issue['type']}: {issue['detail']}")
    if warnings:
        print(f"  质检: 警告 {len(warnings)} 个:")
        for issue in warnings[:3]:
            print(f"    ⚠ [第{issue['question']}题] {issue['type']}: {issue['detail']}")
        if len(warnings) > 3:
            print(f"    ...及其他 {len(warnings)-3} 个警告")
    if not severe and not warnings:
        print(f"  质检: {score}/100 ✓ 通过")
    # 显示信息类提示（如答案分布）
    if infos:
        for info in infos:
            print(f"    ℹ {info['type']}: {info['detail']}")


def _issue_key(issue):
    """用于比较修复前后问题是否新增或遗留。"""
    return (str(issue.get("question", "")), issue.get("type", ""), issue.get("detail", ""))


def _print_issue_list(title, issues, marker):
    """打印一组质检问题，避免回滚日志只给分数不列原因。"""
    if not issues:
        print(f"    {title}: 无")
        return
    print(f"    {title}:")
    for issue in issues:
        print(f"      {marker} [第{issue.get('question', '')}题] {issue.get('type', '')}: {issue.get('detail', '')}")


def _print_repair_comparison(before_severe, before_warnings, new_severe, new_warnings):
    """打印修复前后问题明细，说明为什么采用或回滚。"""
    before_keys = {_issue_key(i) for i in before_severe + before_warnings}
    new_keys = {_issue_key(i) for i in new_severe + new_warnings}
    added = [i for i in new_severe + new_warnings if _issue_key(i) not in before_keys]
    resolved = [i for i in before_severe + before_warnings if _issue_key(i) not in new_keys]

    _print_issue_list("修复后严重问题", new_severe, "✗")
    _print_issue_list("修复后警告问题", new_warnings, "⚠")
    if added:
        _print_issue_list("本轮新增问题", added, "+")
    if resolved:
        _print_issue_list("本轮已消除问题", resolved, "-")

def _ask_user_keep(score, warnings):
    """当仅有轻微问题时，询问用户是否保留"""
    print(f"\n  试卷评分 {score}/100，仅有轻微问题（{len(warnings)}个警告）。")
    while True:
        choice = input("  是否保留此试卷？(y=保留 / n=重新生成): ").strip().lower()
        if choice in ("y", "yes", "是", ""):
            return True
        elif choice in ("n", "no", "否"):
            return False
        print("  请输入 y 或 n")


def _swap_option_texts_in_lines(lines, opt_lines_idx, old_answer, new_answer):
    """交换同一道选择题中两个选项的文本，保留原来的选项字母和行内排版。"""
    option_refs = {}
    parsed_lines = {}

    for idx in opt_lines_idx:
        line = lines[idx]
        matches = list(re.finditer(r"([A-D])([\.．]\s*)", line))
        if not matches:
            continue
        parts = []
        for pos, match in enumerate(matches):
            start = match.end()
            end = matches[pos + 1].start() if pos + 1 < len(matches) else len(line)
            segment = line[start:end]
            seg_match = re.match(r"^(\s*)(.*?)(\s*)$", segment, flags=re.DOTALL)
            leading, option_text, trailing = seg_match.groups() if seg_match else ("", segment, "")
            letter = match.group(1)
            part = {
                "letter": letter,
                "content_start": start,
                "content_end": end,
                "leading": leading,
                "text": option_text,
                "trailing": trailing,
            }
            parts.append(part)
            option_refs[letter] = part
        parsed_lines[idx] = (line, parts)

    if old_answer not in option_refs or new_answer not in option_refs:
        return False

    old_text = option_refs[old_answer]["text"].strip()
    new_text = option_refs[new_answer]["text"].strip()
    replacements = {old_answer: new_text, new_answer: old_text}

    for idx, (line, parts) in parsed_lines.items():
        rebuilt = []
        cursor = 0
        for part in parts:
            rebuilt.append(line[cursor:part["content_start"]])
            replacement = replacements.get(part["letter"], part["text"].strip())
            rebuilt.append(f"{part['leading']}{replacement}{part['trailing']}")
            cursor = part["content_end"]
        rebuilt.append(line[cursor:])
        lines[idx] = "".join(rebuilt)

    return True


def _fix_answer_distribution(paper_text):
    """通过交换选项顺序来调整答案分布，使ABCD尽可能分散

    策略：找出出现次数最多的答案字母，将部分题的选项顺序互换，
    使正确答案从高频字母变为低频字母。
    """
    lines = paper_text.split("\n")

    # 提取所有单选题的位置和答案
    choice_items = []  # [(line_idx_of_answer, current_answer, option_lines_range)]
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 找到题目开头
        q_match = re.match(r"^(\d+)[\.．、]\s*", line)
        if q_match:
            q_start = i
            # 找该题的选项行和答案行
            j = i + 1
            option_start = None
            answer_idx = None
            while j < len(lines):
                jline = lines[j].strip()
                if re.search(r"[A-D][\.．]\s*\S", jline) and option_start is None:
                    option_start = j
                if jline.startswith("【答案】"):
                    ans_match = re.match(r"【答案】\s*([A-D])$", jline)
                    if ans_match:
                        answer_idx = j
                        choice_items.append({
                            "q_start": q_start,
                            "option_start": option_start,
                            "answer_idx": answer_idx,
                            "answer": ans_match.group(1),
                        })
                    break
                if re.match(r"^\d+[\.．、]\s*", jline) or re.match(r"^[一二三四五六七八九十][、.．]", jline):
                    break
                j += 1
            i = j if j > i else i + 1
        else:
            i += 1

    if len(choice_items) < 4:
        return paper_text

    # 统计分布
    dist = {"A": 0, "B": 0, "C": 0, "D": 0}
    for item in choice_items:
        dist[item["answer"]] += 1

    max_count = max(dist.values())
    total = len(choice_items)

    # 任一选项不得大于单选题总数的40%；少量题时按向下取整控制上限。
    max_allowed = max(1, int(total * 0.4))
    if max_count <= max_allowed:
        return paper_text

    # 找出最多和最少的字母。
    sorted_letters = sorted(dist.items(), key=lambda x: x[1], reverse=True)
    most_letter = sorted_letters[0][0]

    # 只把超出40%上限的题从高频答案换到仍未达到上限的低频答案。
    targets = [item for item in choice_items if item["answer"] == most_letter]
    targets_to_fix = []
    replacements = {}
    for item in targets:
        if dist[most_letter] <= max_allowed:
            break
        candidate_letters = [
            letter for letter, count in sorted(dist.items(), key=lambda x: x[1])
            if letter != most_letter and count < max_allowed
        ]
        if not candidate_letters:
            break
        new_letter = candidate_letters[0]
        targets_to_fix.append(item)
        replacements[id(item)] = new_letter
        dist[most_letter] -= 1
        dist[new_letter] += 1

    for item in targets_to_fix:
        if item["option_start"] is None:
            continue

        # 找到该题的选项文本（可能在1-2行内）
        opt_lines_idx = []
        j = item["option_start"]
        while j < item["answer_idx"]:
            if re.search(r"[A-D][\.．]\s*\S", lines[j]):
                opt_lines_idx.append(j)
            j += 1

        # 在选项行中交换 most_letter 和 least_letter 的文本
        old_answer = most_letter
        new_answer = replacements.get(id(item))
        if not new_answer:
            continue

        swapped = _swap_option_texts_in_lines(lines, opt_lines_idx, old_answer, new_answer)
        if not swapped:
            continue

        # 选项文本已交换，答案字母同步改为新位置。
        lines[item["answer_idx"]] = f"【答案】{new_answer}"

    result = "\n".join(lines)
    new_dist = {"A": 0, "B": 0, "C": 0, "D": 0}
    for item in choice_items:
        if item in targets_to_fix:
            new_dist[replacements.get(id(item), item["answer"])] += 1
        else:
            new_dist[item["answer"]] += 1
    print(f"  → 已调整答案分布: {' '.join(f'{k}={v}' for k,v in new_dist.items())}")

    return result

def _extract_question_blocks(paper_text):
    """提取每道题的完整题块、所属大题题型和摘要，用于定向修复"""
    lines = paper_text.split("\n")
    blocks = {}
    current_type = ""
    current_num = None
    current_lines = []

    def save_current():
        if current_num is None or not current_lines:
            return
        block = "\n".join(current_lines).strip()
        first_line = current_lines[0].strip()
        stem = re.sub(r"^\d+[\.．、]\s*", "", first_line)
        stem = re.sub(r"（\s*）\s*$", "", stem).strip()
        blocks[current_num] = {
            "block": block,
            "type": current_type,
            "stem": stem,
            "summary": stem[:80] if stem else block.replace("\n", " ")[:80],
        }

    for line in lines:
        stripped = line.strip()
        if re.match(r"^[一二三四五六七八九十][、.．]", stripped):
            save_current()
            current_type = re.sub(r"^[一二三四五六七八九十][、.．]\s*", "", stripped).strip()
            current_num = None
            current_lines = []
            continue

        m = re.match(r"^(\d+)[\.．、]\s*", stripped)
        if m:
            save_current()
            current_num = int(m.group(1))
            current_lines = [line]
        elif current_num is not None:
            current_lines.append(line)

    save_current()
    return blocks

def _question_format_requirement(question_type, original_block):
    """根据原题所属大题生成修复时的格式要求，防止主观题被重出成选择题。"""
    # 优先按“大题标题”判断题型，不能因为综合题题干里出现“判断/分析”等动词就误判成判断题。
    section_type = question_type or ""
    if any(keyword in section_type for keyword in ("综合", "简答", "计算", "分析", "应用", "作图", "绘图", "画图")):
        return "必须保持为原来的主观题/综合题题型：不要生成判断题句式，不要只输出“正确/错误”或“√/×”；不要生成A-D选项；必须保留综合题设问、完整【答案】和【解析】。"
    if "多项" in section_type or "多选" in section_type:
        return "必须保持为多项选择题：保留A-D四个选项，【答案】必须为2—3个字母，禁止ABCD全选，并给出【解析】；如需修复全选问题，可以重出整题，或将其中一个原正确选项改写为合理错误项，但必须同步修改答案和解析，且选项长度比≤2.0、四个选项句式一致。"
    if "单项" in section_type or "单选" in section_type:
        return "必须保持为单项选择题：保留A-D四个选项，【答案】只能是一个字母，并给出【解析】；四个选项必须为同类短语，选项长度比≤2.0。"
    if "判断" in section_type:
        return "必须保持为判断题：不要生成A-D选项，【答案】只能为“√”或“×”，并给出【解析】。"
    if "填空" in section_type:
        return "必须保持为填空题：不要生成A-D选项，保留填空设问形式，并给出【答案】和【解析】。"

    # 兜底：只有大题标题无法识别时，才参考原题内容。
    text = original_block or ""
    if "多项" in text or "多选" in text:
        return "必须保持为多项选择题：保留A-D四个选项，【答案】必须为2—3个字母，禁止ABCD全选，并给出【解析】；如需修复全选问题，可以重出整题，或将其中一个原正确选项改写为合理错误项，但必须同步修改答案和解析，且选项长度比≤2.0、四个选项句式一致。"
    if "单项" in text or "单选" in text or re.search(r"[A-D][\.．]\s*\S", text):
        return "必须保持为单项选择题：保留A-D四个选项，【答案】只能是一个字母，并给出【解析】；四个选项必须为同类短语，选项长度比≤2.0。"
    if "填空" in text:
        return "必须保持为填空题：不要生成A-D选项，保留填空设问形式，并给出【答案】和【解析】。"
    if any(keyword in text for keyword in ("综合", "简答", "计算", "分析", "应用", "作图", "绘图", "画图")):
        return "必须保持为原来的主观题题型：不要生成A-D选项，按原题型输出题干、必要小问、【答案】和【解析】。"
    if "判断" in text:
        return "必须保持为判断题：不要生成A-D选项，【答案】只能为“√”或“×”，并给出【解析】。"
    return "必须保持原题所属题型和原有格式；如果原题没有A-D选项，重出题也不得添加A-D选项。"


def _is_option_length_issue(issue):
    """判断是否为选择题选项长度失衡问题。"""
    text = f"{issue.get('type', '')} {issue.get('detail', '')}"
    return "选项长度失衡" in text or "长度比" in text


def _option_text_len(text):
    """选项长度统计：忽略空白和常见标点，贴近质检脚本的长度判断。"""
    return len(re.sub(r"[\s，。；、,.．;:：()（）【】\[\]]+", "", text or ""))


def _extract_options_from_block(block):
    """从题块中提取 A-D 选项文本，兼容一行多个选项或每行一个选项。"""
    text = block or ""
    option_area = text.split("【答案】", 1)[0]
    matches = list(re.finditer(r"([A-D])[\.．]\s*", option_area))
    options = {}
    for idx, match in enumerate(matches):
        letter = match.group(1)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(option_area)
        value = option_area[start:end].strip()
        value = re.sub(r"\n+", " ", value).strip()
        if letter in "ABCD" and value:
            options[letter] = value
    return options


def _option_length_report(block):
    """返回题块选项长度报告，用于修复提示和替换后诊断。"""
    options = _extract_options_from_block(block)
    if len(options) < 4:
        return "未能完整识别 A-D 四个选项"
    lengths = {letter: _option_text_len(options.get(letter, "")) for letter in "ABCD"}
    min_len = max(min(lengths.values()), 1)
    max_len = max(lengths.values())
    ratio = max_len / min_len
    detail = " / ".join(f"{letter}({lengths[letter]}字)" for letter in "ABCD")
    return f"当前选项长度：{detail}，长度比={ratio:.1f}"


def _short_option_repair_guidance(issues):
    """针对选项长度失衡生成更硬的修复约束。"""
    if not any(_is_option_length_issue(issue) for issue in issues):
        return ""
    return """

【选项长度失衡专项硬规则】
本次存在“选项长度失衡/长度比超限”问题，必须按以下规则重出选择题：
1. A-D 四个选项一律写成同类短语或同类短句，不要两个短语、两个解释性长句混用。
2. 每个选项建议控制在 6—16 个汉字；最长选项不得超过最短选项的 1.8 倍，绝不能超过 2.0。
3. 禁止在选项中写“因为……所以……”“与……有关而与……无关”等长解释；原因必须放到【解析】中。
4. 四个选项应使用相同句式，例如都写“表示……的物理量”、都写“与……有关”、或都写一个术语短语。
5. 如果原选项一长一短，必须整体重构四个选项，而不是只压缩最长项或只替换答案字母。
6. 输出前自行检查 A-D 字数，若任一选项明显超过其他选项，请继续压缩后再输出。"""

def _issue_question_nums(issue):
    """从质检问题中提取涉及的题号。支持单题和“1&2”这类重复题格式。"""
    q_value = issue.get("question")
    if not q_value or q_value == "全卷":
        return []
    nums = []
    for part in str(q_value).split("&"):
        try:
            nums.append(int(part.strip()))
        except (ValueError, TypeError):
            pass
    return nums

def _choose_duplicate_target_nums(duplicate_issues, question_blocks, preferred_nums=None):
    """为题干重复问题选择尽可能少的重出题号。

    将每条“题干重复”视为一条边，选择覆盖所有重复边的最小改动集合的近似解：
      - 若某题已经因答案自暴露/其他问题需要重出，则优先用它覆盖重复边；
      - 否则每轮选择覆盖剩余重复边最多的题；
      - 覆盖数相同则优先改较靠后的题，尽量保留前面的基础题。
    """
    preferred_nums = set(preferred_nums or [])
    pairs = []
    issue_by_pair = []

    for issue in duplicate_issues:
        nums = [n for n in _issue_question_nums(issue) if n in question_blocks]
        if len(nums) >= 2:
            pair = tuple(dict.fromkeys(nums[:2]))
            if len(pair) == 2:
                pairs.append(pair)
                issue_by_pair.append((pair, issue))

    if not pairs:
        return set(), []

    remaining = set(range(len(pairs)))
    target_nums = set()

    while remaining:
        candidates = set()
        for idx in remaining:
            candidates.update(pairs[idx])

        def coverage(num):
            return sum(1 for idx in remaining if num in pairs[idx])

        preferred_candidates = [n for n in candidates if n in preferred_nums]
        if preferred_candidates:
            chosen = max(preferred_candidates, key=lambda n: (coverage(n), n))
        else:
            chosen = max(candidates, key=lambda n: (coverage(n), n))

        target_nums.add(chosen)
        remaining = {idx for idx in remaining if chosen not in pairs[idx]}

    duplicate_details = []
    for pair, issue in issue_by_pair:
        chosen_in_pair = [n for n in pair if n in target_nums]
        chosen_text = "、".join(str(n) for n in chosen_in_pair) if chosen_in_pair else "未选择"
        duplicate_details.append(
            f"第{issue.get('question', '')}题重复：{issue.get('detail', '')}；本次重出第{chosen_text}题"
        )

    return target_nums, duplicate_details

def _fix_duplicate_questions(client, config, meta, topic, set_idx, spec_text,
                             paper_text, duplicate_issues, session_usage=None, daily_usage=None,
                             preferred_nums=None):
    """重复题定向修复：选择能覆盖全部重复关系的最少题目重出。"""
    question_blocks = _extract_question_blocks(paper_text)
    if not question_blocks:
        return paper_text

    target_nums, duplicate_details = _choose_duplicate_target_nums(
        duplicate_issues, question_blocks, preferred_nums=preferred_nums
    )

    if not target_nums:
        pairs = ",".join(str(i.get("question", "")) for i in duplicate_issues)
        print(f"  → 警告：重复项 {pairs} 无法定位可修复题号，请检查查重/修复逻辑。")
        return paper_text

    repair_sections = []
    for num in sorted(target_nums):
        original_block = question_blocks[num]["block"]
        question_type = question_blocks[num].get("type", "") or "未识别题型"
        format_requirement = _question_format_requirement(question_type, original_block)
        avoid_summaries = []
        for other_num, info in sorted(question_blocks.items()):
            if other_num == num:
                continue
            avoid_summaries.append(f"第{other_num}题：{info['summary']}")
        repair_sections.append(f"""【需要重出的题目：第{num}题】
原题所属题型：{question_type}
原题：
{original_block}

本题格式要求：{format_requirement}

必须避开的其他题目摘要：
{chr(10).join(avoid_summaries)}""")

    fix_prompt = f"""以下试卷中存在题干重复问题。请只重出指定题号的题目，其他题保持不变。

【重复问题】
{chr(10).join(duplicate_details)}

【当前主题信息】
- 课程：{topic.get('course', '')}
- 章节：{topic.get('section', '')}
- 主题：{topic.get('theme', '')}
- 考纲知识点：{topic.get('knowledge', '')}
- 考纲编号：{topic.get('exam_ref', '')}

【重出任务】
{chr(10).join(repair_sections)}

【硬性要求】
1. 只输出需要替换的题目，不要输出完整试卷，不要输出说明文字。
2. 必须保持原题号不变，只重出上述指定题号。
3. 必须严格保持“原题所属题型”和“本题格式要求”：单选仍为单选，多选仍为多选，判断仍为判断，综合/简答/计算等主观题不得改成选择题。
4. 新题仍需围绕当前主题、考纲知识点和原题所属题型。
5. 新题不得与“必须避开的其他题目摘要”中的任何题在题干、情境、设问角度、核心关键词组合上相似。
6. 禁止只替换数字、设备名称、选项顺序；必须换一个考查角度或应用场景。
7. 如原题是选择题，题干中不得包含正确答案的≥4字关键词，选项长度比≤2.0，四个选项句式一致；如原题是多选题，【答案】必须为2—3个字母，禁止ABCD全选。
8. 输出格式必须与原题型一致：选择题包含选项，非选择题不得添加A-D选项，均需包含【答案】、【解析】。
9. 算式和物理公式优先使用 Word 原生公式标记：需要分式、根号、上下标、近似号、希腊字母、单位组合等公式排版时，写成 {{{{math:...}}}}，标记内部使用简洁 LaTeX/线性公式语法，如 {{{{math:I=U/R}}}}、{{{{math:Phi=BS}}}}、{{{{math:R=rho L/S}}}}；三极管/电子技术参数下标必须写成公式标记，如 {{{{math:I_CEO}}}}、{{{{math:I_CBO}}}}、{{{{math:h_FE}}}}、{{{{math:P_CM}}}}，禁止写成 ICEO、ICBO、hFE、PCM 纯文本；普通中文解释写在标记外。禁止使用 \\(...\\)、$...$ 包裹公式。简单符号仍可直接写“×、ρ、Ω、≈”。"""

    sys_prompt = """你是一位试卷去重修复专家。你需要在不改动其他题的前提下，只重出指定题号。
重出的题目必须避开已给出的全卷其他题摘要，避免题干、情境和设问角度重复。"""

    result, usage = call_api(
        client, config["model"], sys_prompt, fix_prompt,
        max_tokens=config.get("max_tokens", 8000),
        temperature=config.get("temperature", 0.7),
    )

    if usage:
        _record_token_usage(session_usage, daily_usage, usage, config)

    if not result:
        return paper_text

    fixed_text = _replace_questions_in_paper(paper_text, result, target_nums)
    print(f"  → 重复题仅修复第{','.join(str(n) for n in sorted(target_nums))}题（最少覆盖重复关系）")
    return fixed_text

def _fix_problem_questions(client, config, meta, topic, set_idx, spec_text,
                           paper_text, issues, session_usage=None, daily_usage=None):
    """只重新生成有问题的题目，保留其他题目不变

    策略：将有问题的题号和具体问题描述发给AI，让其只输出替换后的题目。
    然后在原文中替换对应题目块。
    """
    # 收集有问题的题号
    problem_nums = set()
    problem_details = []
    for issue in issues:
        nums = _issue_question_nums(issue)
        if nums:
            problem_nums.update(nums)
            nums_text = "&".join(str(n) for n in nums)
            problem_details.append(f"第{nums_text}题: {issue['type']} - {issue['detail']}")

    if not problem_nums:
        return paper_text

    question_blocks = _extract_question_blocks(paper_text)
    option_length_guidance = _short_option_repair_guidance(issues)
    repair_sections = []
    for num in sorted(problem_nums):
        info = question_blocks.get(num, {})
        original_block = info.get("block", "")
        question_type = info.get("type", "") or "未识别题型"
        format_requirement = _question_format_requirement(question_type, original_block)
        option_report = ""
        if any(_is_option_length_issue(issue) and num in _issue_question_nums(issue) for issue in issues):
            option_report = f"\n本题选项长度诊断：{_option_length_report(original_block)}\n"
        avoid_summaries = []
        for other_num, other_info in sorted(question_blocks.items()):
            if other_num == num:
                continue
            avoid_summaries.append(f"第{other_num}题：{other_info.get('summary', '')}")
        repair_sections.append(f"""【需要修复的题目：第{num}题】
原题所属题型：{question_type}
原题：
{original_block}

本题格式要求：{format_requirement}
{option_report}
必须避开的其他题目摘要：
{chr(10).join(avoid_summaries)}""")

    # 构建修复 prompt
    fix_prompt = f"""以下试卷中有几道题存在质量问题，请只重新出这几道题，其他题保持不变。

【有问题的题目及原因】
{chr(10).join(problem_details)}
{option_length_guidance}
【需要修复的原题】
{chr(10).join(repair_sections)}

【要求】
请只输出需要替换的题目，不要输出完整试卷，不要输出其他说明文字。
必须保持原题号不变，并严格保持“原题所属题型”和“本题格式要求”：单选仍为单选，多选仍为多选，判断仍为判断，综合/简答/计算等主观题不得改成选择题。

【修复强度要求——不要小修小补】
1. 必须先针对“有问题的题目及原因”逐项彻底消除问题，不允许只换一两个字、只调整选项顺序、只改答案字母。
2. 如果原题的问题涉及题干、选项、答案、解析中的任一部分，必须重构整道题：重新设计题干表达、四个选项/答案和解析，而不是局部打补丁。
3. 新题必须明显区别于原题和其他题目摘要：更换考查角度或应用场景，不得只替换数字、设备名称或同义词。
4. 如原题是选择题：题干中不得包含正确答案的较长连续片段；选项长度比≤2.0；四个选项句式一致；正确答案唯一；干扰项必须有实质性。
   - 如原题是多选题：【答案】必须为2—3个字母，禁止ABCD全选；若问题是“多选题全选”，可以重出整题，或将其中一个原正确选项改成合理错误项，但必须同步修改答案和解析，且不能使用废选项、不能让该选项明显短/长。
5. 解析必须是1-3句完整因果句，直接说明为什么答案正确、其他关键干扰为什么不成立；禁止只写短语。
6. 不得新增任何质量问题：不得出现废选项、禁用符号、题干重复、答案自暴露、解析过短或题型改变。
7. 如原题不是选择题，不得添加A-D选项，按原题型输出题干、必要小问、【答案】和【解析】。
8. 算式和物理公式优先使用 Word 原生公式标记：需要分式、根号、上下标、近似号、希腊字母、单位组合等公式排版时，写成 {{{{math:...}}}}，标记内部使用简洁 LaTeX/线性公式语法，如 {{{{math:I=U/R}}}}、{{{{math:Phi=BS}}}}、{{{{math:R=rho L/S}}}}；三极管/电子技术参数下标必须写成公式标记，如 {{{{math:I_CEO}}}}、{{{{math:I_CBO}}}}、{{{{math:h_FE}}}}、{{{{math:P_CM}}}}，禁止写成 ICEO、ICBO、hFE、PCM 纯文本；普通中文解释写在标记外。禁止使用 \\(...\\)、$...$ 包裹公式。简单符号仍可直接写“×、ρ、Ω、≈”。"""

    sys_prompt = f"""你是一位试卷修复专家。你需要修复指定题目的质量问题，只输出修复后的题目。
保持题号不变，保持原有的考查方向但换一个角度或情境重新命题。"""

    result, usage = call_api(
        client, config["model"], sys_prompt, fix_prompt,
        max_tokens=config.get("max_tokens", 8000),
        temperature=config.get("temperature", 0.7),
    )

    if usage:
        _record_token_usage(session_usage, daily_usage, usage, config)

    if not result:
        return paper_text

    # 将修复后的题目替换到原文中
    fixed_text = _replace_questions_in_paper(paper_text, result, problem_nums)
    if fixed_text == paper_text:
        returned_nums = sorted(_extract_question_blocks(result).keys())
        expected_nums = ",".join(str(n) for n in sorted(problem_nums))
        returned_text = ",".join(str(n) for n in returned_nums) or "未识别到题号"
        print(f"  → 修复结果未能替换：期望题号 {expected_nums}，模型返回题号 {returned_text}。")
        return paper_text

    if any(_is_option_length_issue(issue) for issue in issues):
        fixed_blocks = _extract_question_blocks(fixed_text)
        for num in sorted(problem_nums):
            block = fixed_blocks.get(num, {}).get("block", "")
            if block:
                print(f"  → 第{num}题修复后{_option_length_report(block)}")

    print(f"  → 已替换第{','.join(str(n) for n in sorted(problem_nums))}题，等待复检确认")
    return fixed_text

def _repair_qc_issues_targeted(client, config, meta, topic, set_idx, spec_text,
                               paper_text, severe, warnings, score, infos,
                               session_usage=None, daily_usage=None,
                               max_rounds=3):
    """按优先级定向修复质检问题，尽可能少改题。

    修复顺序：
      1. 答案自暴露（即使只是警告也优先修）；
      2. 其他单题质量问题；
      3. 题干重复（用最小题号集合覆盖全部重复关系）。
    每轮只处理当前最高优先级的一组问题，修复后立即重新质检，避免继续改动已合格题目。
    """
    repaired_rounds = 0
    # 跟踪已修复题号，避免同一题反复修复无效（如 AI 持续返回空解析）
    prior_fixed_nums = set()  # 本轮已修复过的题号（防止同一修复轮次内重复修同一题）

    for repair_round in range(1, max_rounds + 1):
        blocking_issues = severe + warnings
        if score > 90 and not blocking_issues:
            break
        if not blocking_issues:
            break

        before_text = paper_text
        before_severe = severe
        before_warnings = warnings
        before_score = score
        before_infos = infos
        before_blocking_count = len(before_severe) + len(before_warnings)

        # 1. 答案自暴露优先：它在本地质检中通常是"警告"，但会直接影响命题质量。
        exposure_issues = [i for i in blocking_issues if i.get("type") == "答案自暴露"]
        # 过滤掉已修复过的
        exposure_issues = [i for i in exposure_issues
                          if not set(_issue_question_nums(i)).issubset(prior_fixed_nums)]
        if exposure_issues:
            nums = sorted({n for issue in exposure_issues for n in _issue_question_nums(issue)})
            prior_fixed_nums.update(nums)
            print(f"  → 优先修复答案自暴露：第{','.join(str(n) for n in nums)}题...")
            paper_text = _fix_problem_questions(
                client, config, meta, topic, set_idx, spec_text,
                paper_text, exposure_issues,
                session_usage, daily_usage,
            )
        else:
            # 2. 其他明确落到单题的问题：只重出这些题。
            duplicate_issues = [i for i in severe if i.get("type") == "题干重复"]
            single_question_issues = [
                i for i in blocking_issues
                if i.get("type") != "题干重复" and _issue_question_nums(i)
            ]

            if single_question_issues:
                # 过滤掉已经在本轮修复过的问题（避免AI持续返回无效修复的死循环）
                fresh_issues = []
                for issue in single_question_issues:
                    issue_nums = set(_issue_question_nums(issue))
                    if not issue_nums.issubset(prior_fixed_nums):
                        fresh_issues.append(issue)
                if fresh_issues:
                    nums = sorted({n for issue in fresh_issues for n in _issue_question_nums(issue)})
                    prior_fixed_nums.update(nums)
                    print(f"  → 定向修复单题质量问题：第{','.join(str(n) for n in nums)}题...")
                    paper_text = _fix_problem_questions(
                        client, config, meta, topic, set_idx, spec_text,
                        paper_text, fresh_issues,
                        session_usage, daily_usage,
                    )
            elif duplicate_issues:
                # 过滤掉已修复过的题号
                fresh_dup = []
                for issue in duplicate_issues:
                    issue_nums = set(_issue_question_nums(issue))
                    if not issue_nums.issubset(prior_fixed_nums):
                        fresh_dup.append(issue)
                if not fresh_dup:
                    # 所有重复题号都已修复过，停止本轮修复
                    break
                duplicate_issues = fresh_dup
                # 3. 查重最后处理；选择最少题目覆盖全部重复关系。
                # 窄考点下若重复项过多，逐题重出容易陷入“反复修同一题但不收敛”的循环，直接交给人工审核兜底。
                if len(duplicate_issues) >= 8:
                    print(f"  → 题干重复项过多（{len(duplicate_issues)}个），停止自动逐题修复，避免窄考点反复重出死循环。")
                    break
                question_blocks = _extract_question_blocks(paper_text)
                target_nums, _ = _choose_duplicate_target_nums(duplicate_issues, question_blocks)
                if not target_nums:
                    pairs = ",".join(str(i.get("question", "")) for i in duplicate_issues)
                    print(f"  → 警告：重复项 {pairs} 无法定位可修复题号，请检查查重/修复逻辑。")
                    break
                print(f"  → 修复题干重复：第{','.join(str(i['question']) for i in duplicate_issues)}题存在重复，仅重出第{','.join(str(n) for n in sorted(target_nums))}题...")
                paper_text = _fix_duplicate_questions(
                    client, config, meta, topic, set_idx, spec_text,
                    paper_text, duplicate_issues,
                    session_usage, daily_usage,
                )
            else:
                # 例如全卷级问题若无法通过选项交换解决，就交给整卷重生兜底。
                break

        if paper_text == before_text:
            print("  → 定向修复未替换到题目，停止本轮定向修复。")
            break

        cleaned = _clean_paper_text(paper_text)
        new_severe, new_warnings, new_score, _, new_infos = _quick_check(cleaned)
        new_blocking_count = len(new_severe) + len(new_warnings)

        # 安全阀：修复后如果分数降低、严重问题变多，或问题总数变多，就回滚到修复前版本。
        if (new_score < before_score
                or len(new_severe) > len(before_severe)
                or new_blocking_count > before_blocking_count):
            print(
                f"  → 本轮修复未采用：评分 {before_score}/100 → {new_score}/100，"
                f"严重问题 {len(before_severe)} → {len(new_severe)}，"
                f"严重+警告 {before_blocking_count} → {new_blocking_count}。已回滚到修复前版本。"
            )
            _print_repair_comparison(before_severe, before_warnings, new_severe, new_warnings)
            paper_text = before_text
            severe = before_severe
            warnings = before_warnings
            score = before_score
            infos = before_infos
            break

        repaired_rounds += 1
        severe, warnings, score, infos = new_severe, new_warnings, new_score, new_infos
        _print_qc_summary(severe, warnings, score, infos)

        if score > 90 and not severe and not warnings:
            break

    return paper_text, severe, warnings, score, infos, repaired_rounds

def _replace_questions_in_paper(original_text, fixed_text, target_nums):
    """将修复后的题目块替换到原始试卷文本中"""
    # 解析修复文本中的题目块
    fixed_blocks = {}
    lines = fixed_text.split("\n")
    current_num = None
    current_lines = []

    for line in lines:
        m = re.match(r"^(\d+)[\.．、]\s*", line.strip())
        if m:
            if current_num is not None and current_num in target_nums:
                fixed_blocks[current_num] = "\n".join(current_lines)
            current_num = int(m.group(1))
            current_lines = [line]
        elif current_num is not None:
            current_lines.append(line)

    if current_num is not None and current_num in target_nums:
        fixed_blocks[current_num] = "\n".join(current_lines)

    if not fixed_blocks:
        return original_text

    # 在原文中定位并替换对应题目块
    orig_lines = original_text.split("\n")
    result_lines = []
    i = 0
    while i < len(orig_lines):
        line = orig_lines[i]
        m = re.match(r"^(\d+)[\.．、]\s*", line.strip())
        if m:
            q_num = int(m.group(1))
            if q_num in fixed_blocks:
                # 跳过原题块（直到下一题或下一大类标题）
                j = i + 1
                while j < len(orig_lines):
                    next_line = orig_lines[j].strip()
                    if re.match(r"^\d+[\.．、]\s*", next_line):
                        break
                    if re.match(r"^[一二三四五六七八九十][、.．]", next_line):
                        break
                    j += 1
                # 插入修复后的题目
                result_lines.append(fixed_blocks[q_num])
                result_lines.append("")
                i = j
                continue
        result_lines.append(line)
        i += 1

    return "\n".join(result_lines)
