"""出题/补题 prompt（阶段四 shared/ai，源 prompts.build_generation_prompt 去硬编码）。

省份/考类/课程等全部参数化，依据各类型 编写规范.md 作为权威标准。
"""
from __future__ import annotations

from typing import Any

from engine import registry


def _load_spec(paper_type: str) -> str:
    try:
        mode = registry.get(paper_type)
        if mode.spec_md and mode.spec_md.exists():
            return mode.spec_md.read_text(encoding="utf-8")
    except Exception:
        pass
    return ""


def build_generation_prompt(ctx, plan: dict[str, Any], shortfall: dict[str, int]) -> str:
    """构造补题 prompt：按题型缺口数量生成。

    plan: {topic, kpoints, difficulty:{easy,medium,hard}, ...}
    shortfall: {题型: 缺口数量}
    """
    spec = _load_spec(ctx.paper_type)
    topic = plan.get("topic") or plan.get("paper_name") or ctx.course
    kpoints = plan.get("kpoints") or plan.get("point_name") or ""
    diff = plan.get("difficulty") or {"easy": 80, "medium": 10, "hard": 10}
    type_lines = "\n".join(f"- {t}：{n} 道" for t, n in shortfall.items() if n > 0)

    head = (
        "请严格按照下方《编写规范》为指定主题补充生成试题。\n"
        "只输出试题正文（从题型标题开始），每题后紧跟【答案】与【解析】，"
        "不要输出任何标题、说明、markdown 标记或自检清单。\n\n"
        f"- 省份：{ctx.province}\n"
        f"- 考试类型：{ctx.exam_type_name}\n"
        f"- 考类：{ctx.exam_category}\n"
        f"- 课程：{ctx.course}\n"
        f"- 主题/考点：{topic}\n"
        f"- 知识点范围：{kpoints}\n"
        f"- 难度分布：简单{diff.get('easy',80)}% 适中{diff.get('medium',10)}% 困难{diff.get('hard',10)}%\n"
        f"- 需补充题型与数量：\n{type_lines}\n"
    )
    if spec:
        head += "\n===== 编写规范 =====\n" + spec
    return head
