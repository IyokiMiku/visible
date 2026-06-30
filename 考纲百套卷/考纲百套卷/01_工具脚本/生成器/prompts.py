"""考纲百套卷 Prompt 构造模块。

用于题目清洗、单题修复/重生成、整卷统一格式等任务。
"""
from __future__ import annotations

from typing import Any


def build_clean_question_prompt(raw_question: dict[str, Any], spec_text: str = "") -> str:
    """构造题库 API 题目的规范化清洗 prompt。"""
    return f"""请将以下题库 API 返回题目清洗为标准结构化题目。

要求：
1. 删除接口冗余字段、无关说明、HTML 残留和展示噪声。
2. 保留题干、选项、答案、解析、知识点、来源 URL。
3. 如果原题缺答案或解析，请标记为待修复，不要编造。
4. 输出 JSON，字段包括：question_type、stem、options、answer、analysis、knowledge_points、source_url、status、issues。

编写规范：
{spec_text}

原始题目：
{raw_question}
"""


def build_regenerate_question_prompt(question: dict[str, Any], issues: list[str], plan_context: dict[str, Any], spec_text: str = "") -> str:
    """构造不合格题目的修复/重生成 prompt。"""
    issues_text = "\n".join(issues)
    all_issues = [i.strip() for i in issues if i.strip()]
    only_analysis_short = all_issues and all(i in ("解析过短", "解析缺少计算过程") for i in all_issues)

    if only_analysis_short:
        extra_rule = (
            "## 本题仅需补写解析\n"
            "题干、选项、答案和题型必须与原文完全一致，不得做任何修改。只输出 analysis 字段的补充内容。\n"
            "解析必须为 2-3 句完整因果句，说明为什么答案正确、其他选项为什么不成立。"
        )
    else:
        extra_rule = (
            "## 处理原则\n"
            "1. 能局部修复的，优先保留原题知识点和题型。\n"
            "2. 题干乱码、选项缺失、知识点不匹配、重复严重时，按规划表重新生成同题型题目。\n"
            "3. 答案必须唯一且与解析一致。\n"
            "4. 解析要说明关键依据，不能只写一句话。\n"
        )

    return f"""请根据质检问题修复或重生成题目。

规划表要求：
{plan_context}

质检问题：
{issues_text}

{extra_rule}
5. 输出 JSON，字段包括：question_type、stem、options、answer、analysis、knowledge_points、fix_type、status。
6. 只输出一行合法 JSON 对象，不要加 Markdown 代码块（```json）、注释或任何额外说明文字。
7. 输出格式参照（这是示例，不要照抄内容）：
{{"question_type":"单项选择题","stem":"在一个电路中...","options":["A. 选项一","B. 选项二","C. 选项三","D. 选项四"],"answer":"A","analysis":"根据欧姆定律...因此选 A。","knowledge_points":["欧姆定律"],"fix_type":"repaired","status":"fixed"}}

编写规范：
{spec_text}

待处理题目：
{question}
"""

def build_final_paper_prompt(paper_questions: list[dict[str, Any]], paper_context: dict[str, Any], spec_text: str = "") -> str:
    """构造最终卷统一格式 prompt。"""
    return f"""请将以下题目整理为考纲百套卷最终试卷文本。

试卷信息：
{paper_context}

要求：
1. 按题型分组，题号连续。
2. 保留答案和解析，形成解析版文本。
3. 格式统一，适合后续转 Word。
4. 不新增规划表之外的题目。

编写规范：
{spec_text}

题目列表：
{paper_questions}
"""


def build_generate_full_paper_prompt(paper_context: dict[str, Any], spec_text: str = "") -> str:
    """构造按规划直接生成整卷试题的 prompt。"""
    return f"""请根据试卷规划直接生成一份完整的考纲百套卷解析版试卷。

试卷规划：
{paper_context}

编写规范（唯一权威标准，必须严格遵守）：
{spec_text}

生成要求：
1. 严格按照试卷规划中的卷号、卷型、课程/模块、专题、考点和细目表约束出题。
2. 若提供 blueprint_rows，必须逐行对应生成题目，题号、题型、难度、考点、考查内容均不得偏离。
3. 若未提供 blueprint_rows，则围绕 planning_rows、point_name 和 point_content 生成完整试卷，不得超出考查范围。
4. 每题必须有题干、答案和完整解析；选择题必须有 A-D 四个选项且答案唯一。
5. 不得照搬真题或样例；不得输出 LaTeX 命令、Markdown、自检清单、额外说明或“以下是试卷”等前缀。
6. 只输出一个 JSON 对象，不要输出 Markdown 代码块（```json）、注释或任何额外说明文字。如果因任何原因无法生成 JSON，返回 {{"questions": []}}。

JSON 输出格式：
{{
  "title": "试卷标题，可为空字符串",
  "questions": [
    {{
      "question_no": 1,
      "question_type": "单选题",
      "heading": "一、单项选择题",
      "stem": "题干文本",
      "options": ["A. 选项", "B. 选项", "C. 选项", "D. 选项"],
      "answer": "A",
      "analysis": "完整解析",
      "knowledge_points": ["考点"],
      "difficulty": "简单/适中/困难"
    }}
  ]
}}
"""
