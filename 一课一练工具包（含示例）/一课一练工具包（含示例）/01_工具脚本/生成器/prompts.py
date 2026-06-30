"""试卷生成 Prompt 构建。"""
import re

from .question_types import load_question_type_prompt_section
from .references import _load_reference_materials


def build_generation_prompt(meta, topic, set_idx, spec_text, existing_summaries=None):
    """构建发送给 Claude 的出题提示词

    Args:
        existing_summaries: 已生成的题目摘要列表（用于分批生成时避免重复）
    """

    # 解析题型数量
    qt_str = topic["question_types"]
    single_match = re.search(r"单选(?:题)?(\d+)", qt_str)
    judge_match = re.search(r"判断(?:题)?(\d+)", qt_str)
    comp_match = re.search(r"综合(?:题)?(\d+)", qt_str)
    fill_match = re.search(r"填空(?:题)?(\d+)", qt_str)
    multi_match = re.search(r"多选(?:题)?(\d+)", qt_str)
    short_match = re.search(r"简答(?:题)?(\d+)", qt_str)
    calc_match = re.search(r"计算(?:题)?(\d+)", qt_str)
    # "选择X"视为单选（与"多选X"区分）
    if not single_match:
        single_match = re.search(r"选择(\d+)", qt_str)

    single_count = int(single_match.group(1)) if single_match else 0
    judge_count = int(judge_match.group(1)) if judge_match else 0
    comp_count = int(comp_match.group(1)) if comp_match else 0
    fill_count = int(fill_match.group(1)) if fill_match else 0
    multi_count = int(multi_match.group(1)) if multi_match else 0
    short_count = int(short_match.group(1)) if short_match else 0
    calc_count = int(calc_match.group(1)) if calc_match else 0

    single_answer_cap = max(1, int(single_count * 0.4)) if single_count > 0 else 0

    # 难度比例
    diff_str = topic["difficulty"]
    diff_parts = diff_str.split(":")
    if len(diff_parts) == 3:
        easy_pct, mid_pct, hard_pct = int(diff_parts[0]), int(diff_parts[1]), int(diff_parts[2])
    else:
        easy_pct, mid_pct, hard_pct = 80, 10, 10

    # 计算各难度的题目数
    total_choice = single_count + multi_count
    if total_choice > 0:
        hard_count = max(1, round(total_choice * hard_pct / 100))
        mid_count = max(1, round(total_choice * mid_pct / 100))
        easy_count = max(0, total_choice - hard_count - mid_count)
    else:
        hard_count = mid_count = easy_count = 0

    # 从教材列表获取当前课程对应的教材
    textbook_info = meta["textbooks"]

    # 主题后缀
    set_suffix = f"(第{set_idx}套)" if topic["sets"] > 1 else ""

    # 构建输出格式示例（大题编号动态计算）
    _CN_NUMS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    sec_idx = 0
    format_parts = []

    # 单项选择题
    format_parts.append(f"""{_CN_NUMS[sec_idx]}、单项选择题
1. 题干文本（   ）
A. 选项A\t\t\tB. 选项B
C. 选项C\t\t\tD. 选项D
【答案】X
【解析】解析文本（完整陈述句，禁止使用→=↑↓等符号）

2. ...（以此类推）""")
    sec_idx += 1
    q_start = single_count + 1

    # 多项选择题（如有）
    if multi_count > 0:
        format_parts.append(f"""{_CN_NUMS[sec_idx]}、多项选择题
{q_start}. 题干文本（   ）
A. 选项A\t\t\tB. 选项B
C. 选项C\t\t\tD. 选项D
【答案】XY（2—3个字母，禁止ABCD全选）
【解析】解析文本""")
        sec_idx += 1
        q_start += multi_count

    # 判断题
    if judge_count > 0:
        format_parts.append(f"""{_CN_NUMS[sec_idx]}、判断题
{q_start}. 判断题题干。（   ）
【答案】√ 或 ×
【解析】解析文本""")
        sec_idx += 1
        q_start += judge_count

    # 填空题（如有）
    if fill_count > 0:
        format_parts.append(f"""{_CN_NUMS[sec_idx]}、填空题
{q_start}. 填空题题干______，相关结论为______。
【答案】答案1；答案2
【解析】解析文本（按题干空白顺序说明每个答案）""")
        sec_idx += 1
        q_start += fill_count

    # 简答题（如有）
    if short_count > 0:
        format_parts.append(f"""{_CN_NUMS[sec_idx]}、简答题
{q_start}. 简述……。
【答案】（1）完整要点句。
（2）完整要点句。
（3）完整要点句。
【解析】说明答题思路、知识依据或易错点，不得只重复答案。""")
        sec_idx += 1
        q_start += short_count

    # 计算题（如有）
    if calc_count > 0:
        format_parts.append(f"""{_CN_NUMS[sec_idx]}、计算题
{q_start}. 已知……，求……。
【答案】最终结果（带单位）
【解析】根据公式……。代入数据得……。计算结果为……，因此……。""")
        sec_idx += 1
        q_start += calc_count

    # 综合题（如有）
    if comp_count > 0:
        format_parts.append(f"""{_CN_NUMS[sec_idx]}、综合题
{q_start}. 综合题题干
【答案】完整答案
【解析】解析文本""")

    format_example = "\n\n".join(format_parts)

    # 综合题难度要求：规划表中本章节/主题综合题达到3道及以上时，至少1道必须为困难题
    comp_difficulty_requirement = ""
    if comp_count >= 3:
        comp_difficulty_requirement = "\n- 综合题：至少1道必须为困难难度（多步计算/故障推理链/跨知识点综合），并在题干或解析中体现多步骤分析过程"
    calc_requirement = ""
    if calc_count > 0:
        calc_requirement = "\n- 计算题：题干必须给出完整已知条件、求解目标和单位要求；答案必须带单位；解析按公式—代入—计算—结论书写"
    short_requirement = ""
    if short_count > 0:
        short_requirement = "\n- 简答题：答案必须按“（1）”“（2）”“（3）”分条书写，每点为完整句或完整短句；解析说明答题思路或知识依据"

    # 窄考点/极重要主题防重复：生成阶段先分配不同考查角度，减少生成后靠质检返修。
    angle_templates = [
        "概念识别：考查基本定义、适用条件或规范名称，题干避免直接复述正确选项",
        "结构功能：考查部件/电路/机构的组成、作用或相互关系",
        "工作过程：考查动作顺序、信号/电流/力的传递路径或状态变化",
        "故障判断：给出异常现象，判断可能原因、检测部位或处理方向",
        "参数变化：考查条件改变后性能、读数、状态或结果如何变化",
        "应用场景：给出生产、维修、测量或操作情境，判断正确做法",
        "对比辨析：比较相近概念、结构、工况或方法的区别",
        "计算/判断：结合简单数据、图示描述或逻辑条件进行计算、判断或推理",
    ]
    angle_count = single_count + multi_count + judge_count + fill_count + short_count + calc_count + comp_count
    angle_lines = []
    if angle_count >= 6 or "极重要" in topic.get("level", ""):
        for idx in range(1, angle_count + 1):
            angle_lines.append(f"- 第{idx}题：{angle_templates[(idx - 1) % len(angle_templates)]}")
    angle_section = ""
    if angle_lines:
        angle_section = f"""
【考查角度分配——窄考点防重复，必须执行】
本主题如果考点较窄，不要反复用“下列关于……正确的是”这类同一问法。请按题号尽量采用以下不同角度命题；同一核心词可以出现，但题干情境、设问任务和考查动作必须不同：
{chr(10).join(angle_lines)}
"""

    # 加载参考资料（真题+教材）
    ref_text = _load_reference_materials(topic, meta)
    ref_section = ""
    if ref_text:
        ref_section = f"\n【参考资料——请模仿真题的出题风格和难度，基于教材内容确保知识准确】\n\n{ref_text}\n"

    question_type_section = load_question_type_prompt_section(meta, topic)
    if question_type_section:
        question_type_section = "\n" + question_type_section

    system_prompt = f"""你是一位经验丰富的中职教育命题专家，严格按照高职高考/高职分类考试真题标准出题。

以下是你必须严格遵守的出题规范（任何违反都是不合格的）：

{spec_text}
{ref_section}{question_type_section}
【特别强调——最容易犯的错误】：
1. 选项长度比：最长选项字数÷最短选项字数必须≤2.0，绝对禁止一个选项20字其他选项2-3字
2. 干扰项禁止使用"正常""无影响""不动""更省油""无要求""任意"等废词
3. 单选题答案分布必须均衡：A/B/C/D任一选项作为正确答案的次数，不准大于单选题总数的40%；生成前先规划答案字母，禁止集中在A、B或任何单一选项
4. 每卷必须有≥1道适中难度题+≥1道困难/计算题
5. 四个选项必须句式结构一致（都是短语、或都是完整句）
6. 解析禁止写单个短语（如"耐磨处理。""精密配合。"），必须写1-3句完整因果句，直击题目要点
7. 括号（ ）位置不必强制放在句末，应放在语义最自然的位置，使填入选项后读起来通顺
8. 生成题目中不要有注解，例如“中央处理器（CPU）”；应直接使用教材中的规范名称，不额外加英文缩写或括号解释
9. 不要出现仅有一个选项含有“或”“和”“且”“以及”“并且”等连接词；四个选项的语言结构必须保持同类、对称
10. 简答题必须按要点分条书写，每点用“（1）”“（2）”“（3）”编号，答案为完整句或完整短句；【解析】说明答题思路、知识依据或易错点，不得只写“见答案”。
11. 综合题或计算题包含多个小问时，答案必须按小问分行书写，如（1）……换行（2）……，不要把不同小题答案挤在同一段。
    如果某个小问答案需要写两句或两行，第二句仍写在同一个小问后面，禁止另起“（3）”“（4）”等新编号；小问编号数量必须与题干小问数量一致。
12. 算式和物理公式优先使用 Word 原生公式标记：需要分式、根号、上下标、近似号、希腊字母、单位组合等公式排版时，写成 {{{{math:...}}}}，标记内部使用简洁 LaTeX/线性公式语法，如 {{{{math:I=U/R}}}}、{{{{math:Phi=BS}}}}、{{{{math:R=rho L/S}}}}；三极管/电子技术参数下标必须写成公式标记，如 {{{{math:I_CEO}}}}、{{{{math:I_CBO}}}}、{{{{math:h_FE}}}}、{{{{math:P_CM}}}}，禁止写成 ICEO、ICBO、hFE、PCM 纯文本；普通中文解释写在标记外。禁止使用 \\(...\\)、$...$ 包裹公式。简单符号仍可直接写“×、ρ、Ω、≈”。
13. 计算题解析必须句子通顺且结果完整：不能只写“甲为2×3.14×50×0.10，乙为2×3.14×50×0.20”这类半截算式；必须写出物理量名称、公式、代入、计算结果和单位。"""

    user_prompt = f"""请为以下主题生成一份完整的一课一练试卷{set_suffix}：

【基本信息】
- 省份：{meta["province"]}
- 类别：{meta["category"]}
- 课程：{topic["course"]}
- 章节：{topic["section"]}
- 主题：{topic["theme"]}
- 考纲知识点：{topic["knowledge"]}
- 考纲编号：{topic["exam_ref"]}
- 参考教材：{textbook_info}
- 重要程度：{topic["level"]}

【题型和数量要求】
- 单选题：{single_count}道（必须先规划答案分布；A/B/C/D任一选项作为正确答案不得超过{single_answer_cap}道，即不准大于单选题总数的40%；尤其避免A、B集中；同时保证每题答案唯一、选项合理）
{f"- 判断题：{judge_count}道（对错比约4:6至5:5）" if judge_count > 0 else ""}\
{f"- 多选题：{multi_count}道（每题答案必须为2—3个字母，禁止ABCD全选；正确项和错误项都必须合理，不能靠明显错误或废选项凑答案；多选答案A/B/C/D出现应尽量均衡）" if multi_count > 0 else ""}\
{f"- 填空题：{fill_count}道（空格处用6个下划线______表示，禁止用括号；每道题可以设置一个或多个空白处，多个空的答案按题干空白顺序在【答案】中书写）" if fill_count > 0 else ""}\
{f"- 简答题：{short_count}道{short_requirement}" if short_count > 0 else ""}\
{f"- 计算题：{calc_count}道{calc_requirement}" if calc_count > 0 else ""}\
{f"- 综合题：{comp_count}道{comp_difficulty_requirement}" if comp_count > 0 else ""}

【难度分布（选择题）】
- 容易（识记）：{easy_count}道
- 适中（理解+简单计算/应用）：{mid_count}道
- 困难（多步计算/故障推理链/跨知识点综合）：{hard_count}道
{angle_section}
【输出格式要求——极其重要，必须严格遵守】

1. 直接输出试卷正文，禁止在开头添加任何标题、标记、说明文字（如 # ## 标题、文件名、"以下是试卷"等）
2. 大类题型标题直接写"一、单项选择题""二、判断题"等（有多选则写"X、多项选择题"），禁止添加任何 markdown 标记（如 ### #）
3. 选择题选项用制表符\t分隔同行的两个选项，格式如下：
   A. 选项A\t\t\tB. 选项B
   C. 选项C\t\t\tD. 选项D
   禁止使用表格、列表或其他格式排列选项
4. 简答题答案必须按“（1）”“（2）”“（3）”分条书写，每点为完整句或完整短句；解析说明答题思路、知识依据或易错点。
5. 综合题或计算题包含多个小问时，答案与解析必须按小问分行书写：每个小题单独一行，以“（1）”“（2）”开头；不要把不同小题答案挤在同一段。若某个小问有两句或两行解释，继续写在该小问编号后，不能因自然换行新增“（3）”“（4）”等无对应题干的小问编号。
6. 算式和物理公式优先使用 Word 原生公式标记：需要分式、根号、上下标、近似号、希腊字母、单位组合等公式排版时，写成 {{{{math:...}}}}，标记内部使用简洁 LaTeX/线性公式语法，如 {{{{math:I=U/R}}}}、{{{{math:Phi=BS}}}}、{{{{math:R=rho L/S}}}}；三极管/电子技术参数下标必须写成公式标记，如 {{{{math:I_CEO}}}}、{{{{math:I_CBO}}}}、{{{{math:h_FE}}}}、{{{{math:P_CM}}}}，禁止写成 ICEO、ICBO、hFE、PCM 纯文本；普通中文解释写在标记外。禁止使用 \\(...\\)、$...$ 包裹公式。简单符号仍可直接写“×、ρ、Ω、≈”。
7. 计算题解析必须写完整计算链：物理量名称 + 公式 + 代入 + 计算结果 + 单位，禁止只罗列代入式。
8. 禁止在末尾输出自检清单、备注或任何额外内容——在输出前请在内部完成自检，不要写入输出中

严格按以下格式输出（从"一、单项选择题"直接开始，前面不要有任何内容）：

{format_example}

【内部自检（不要输出到结果中）】：
输出前请逐题确认以下各项，但不要将此清单写入输出文本：
- 选项长度比≤2.0（最长÷最短）
- 单选题答案分布：A/B/C/D任一选项不得超过{single_answer_cap}道，不准大于单选题总数的40%，不得集中在A、B
- 多选题答案为2—3个字母，禁止ABCD全选；多选答案A/B/C/D出现应尽量均衡
- 无废选项（无"正常""无影响"等）
- 句式结构一致
- 有≥1道适中题+≥1道困难题
- 简答题按要点分条，计算题有公式、代入、结果和单位
- 解析无禁用符号
- 与已有题目不重复（若提供了已有摘要）
- 【最重要】答案自暴露检测：逐题检查正确答案选项中≥4字的关键词是否出现在题干中。如果出现，必须立即重新构思该题（修改题干措辞或更换考查角度），直到题干不再包含正确答案的特征词汇。绝不允许带着自暴露问题输出。"""

    # 注入已有题目摘要（分批防重复）
    if existing_summaries:
        avoid_section = "\n".join(f"  - {s}" for s in existing_summaries)
        user_prompt += f"""

【本卷已有题目（严禁重复）】
以下是本卷已生成的题目摘要，你生成的题目不得与下列任何一道考查相同知识点或使用相同情境：
{avoid_section}

请确保新生成的每道题都有独立的考查角度，不得只换数字或措辞。"""

    return system_prompt, user_prompt
