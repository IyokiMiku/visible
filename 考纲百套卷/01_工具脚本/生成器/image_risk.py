"""配图风险前置检测模块。

在规划表阶段扫描高配图风险考点，提前暴露缺图风险，
避免到审核阶段才发现"这类题必须有图但现在没图"的高返工成本。

五个环节：
  1. 规划表阶段扫描高配图风险考点 → classify_paper_risk()
  2. 单卷 PaperPlan 标记 image_risk_level → attach_image_risk()
  3. preflight 阶段展示风险警告 → format_risk_warnings()
  4. auto_review 输出图题风险清单 → check_image_requirement()
  5. 人工 QC 优先检查高风险卷 → build_image_risk_report()
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


# ============================================================
# 配图风险关键词库
# ============================================================

# 高风险课程/模块名 — 整卷几乎每道题都需要配图
HIGH_RISK_COURSES = [
    "机械制图", "工程制图", "建筑制图", "土木工程制图",
    "机械基础", "机械设计基础", "机械制造基础",
    "汽车构造", "汽车底盘", "汽车发动机", "汽车电气",
    "液压与气压传动", "液压传动", "气压传动",
]

# 高风险专题名 — 该专题下大部分题需要配图
HIGH_RISK_TOPICS = [
    # 制图识图类
    "装配图", "零件图", "三视图", "剖视图", "断面图",
    "轴测图", "标准件", "常用件", "螺纹", "齿轮",
    "尺寸标注", "公差", "配合", "表面粗糙度",
    # 电路图类
    "电路图", "原理图", "接线图", "电气原理图",
    "波形图", "时序图", "逻辑图", "状态转换图",
    "真值表", "卡诺图", "功能表",
    # 液压/气动类
    "液压回路", "气动回路", "液压系统", "气压系统",
    "液压元件", "气动元件", "方向控制回路",
    # 机械结构类
    "机构运动简图", "机构简图", "传动系统",
    "轮系", "定轴轮系", "周转轮系",
]

# 高风险考点内容关键词 — 命中任一个即判定为该考点需要配图
HIGH_RISK_POINT_KEYWORDS = [
    # 读图/识图类
    "读图", "识图", "看图", "识读", "读懂",
    "如图所示", "如图", "下图", "上图", "图中", "图示",
    "根据图", "从图中", "看图回答",
    # 绘图/作图类
    "绘制", "画出", "补画", "补全", "画图", "作图",
    "绘制流程图", "绘制电路",
    # 标注类
    "标注", "尺寸标注", "公差标注", "技术要求",
    # 看图填空/选择
    "看图填空", "看图选择", "看图判断",
    # 读电路图
    "读电路图", "分析电路", "电路分析",
    "波形分析", "时序分析",
    # 读装配图
    "读装配图", "拆画零件图", "由装配图",
    # 读零件图
    "读零件图", "零件图表达",
]

# 中风险关键词 — 部分题型需要配图
MEDIUM_RISK_POINT_KEYWORDS = [
    "结构", "组成", "工作原理", "工作过程",
    "传动路线", "油路", "气路", "电路连接",
    "接线", "布线", "装配", "拆装",
    "外形", "形状", "轮廓", "剖面",
    "测量", "检测", "调试", "故障诊断",
    "万用表", "示波器", "信号发生器",
    "引脚", "端口", "接口", "插头",
    "传感器", "执行器", "控制器",
]

# 明确需要配图的题型 — 这些题型没有图就不成立
IMAGE_REQUIRED_QUESTION_TYPES = [
    "作图题", "识图题", "绘图题", "改错题(图)",
    "补图题", "读图题", "连线题",
]

# 描述"如图所示"但没有图的关键词 — 如果题目含这些但无图片，即为缺图
MISSING_IMAGE_MARKERS = [
    r"如图\s*所示", r"如图\s*\d", r"如下图", r"上图所示",
    r"图中", r"图示", r"见图", r"参照图", r"看图",
    r"根据.*?图", r"从.*?图中", r"阅读.*?图",
]


# ============================================================
# 风险等级定义
# ============================================================

@dataclass
class ImageRiskResult:
    """单卷配图风险检测结果。"""
    paper_no: int = 0
    paper_label: str = ""
    paper_type: str = ""
    module: str = ""
    topic: str = ""
    point_name: str = ""
    risk_level: str = "none"         # none / low / medium / high
    risk_score: int = 0              # 0-100
    risk_reasons: list[str] = field(default_factory=list)
    affected_points: list[str] = field(default_factory=list)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def _match_any(text: str, keywords: list[str]) -> list[str]:
    """返回 text 中命中的关键词列表。"""
    hits = []
    for keyword in keywords:
        if keyword in text:
            hits.append(keyword)
    return hits


# ============================================================
# 环节 1: 规划表阶段扫描
# ============================================================

def classify_paper_risk(
    paper_no: int,
    paper_label: str,
    paper_type: str,
    module: str = "",
    topic: str = "",
    point_name: str = "",
    point_content: str = "",
    rows: list[Any] | None = None,
) -> ImageRiskResult:
    """根据规划表信息判定单卷配图风险等级。

    判定规则（优先级递减）：
      1. 模块名命中 HIGH_RISK_COURSES → high (90)
      2. 专题名命中 HIGH_RISK_TOPICS → high (80)
      3. 考点内容命中 HIGH_RISK_POINT_KEYWORDS → high (70)
      4. 考点内容命中 MEDIUM_RISK_POINT_KEYWORDS → medium (50)
      5. 其他 → low/none

    多考点卷（专题训练卷/课程综合卷）取所有行中最高风险。
    """
    reasons: list[str] = []
    risk_score = 0
    all_point_texts: list[str] = []

    # 收集所有考点文本
    if point_content:
        all_point_texts.append(point_content)
    if rows:
        for row in rows:
            pc = getattr(row, "point_content", "")
            if pc:
                all_point_texts.append(_clean_text(pc))
            pn = getattr(row, "point_name", "")
            if pn:
                all_point_texts.append(_clean_text(pn))

    combined_text = "\n".join(all_point_texts)

    # 规则 1: 模块名检查
    course_hits = _match_any(module, HIGH_RISK_COURSES)
    if course_hits:
        reasons.append(f"高风险课程：{module}")
        risk_score = max(risk_score, 90)

    # 规则 2: 专题名检查
    topic_hits = _match_any(topic, HIGH_RISK_TOPICS)
    if topic_hits:
        reasons.append(f"高风险专题：{', '.join(topic_hits)}")
        risk_score = max(risk_score, 80)

    # 规则 3: 考点内容高风险关键词
    high_hits = _match_any(combined_text, HIGH_RISK_POINT_KEYWORDS)
    if high_hits:
        reasons.append(f"高风险考点关键词：{', '.join(high_hits[:5])}" +
                       (f"等{len(high_hits)}个" if len(high_hits) > 5 else ""))
        risk_score = max(risk_score, 70)

    # 规则 4: 考点内容中风险关键词
    medium_hits = _match_any(combined_text, MEDIUM_RISK_POINT_KEYWORDS)
    if medium_hits and risk_score < 50:
        reasons.append(f"中风险考点关键词：{', '.join(medium_hits[:5])}" +
                       (f"等{len(medium_hits)}个" if len(medium_hits) > 5 else ""))
        risk_score = max(risk_score, 50)

    # 确定等级
    if risk_score >= 70:
        risk_level = "high"
    elif risk_score >= 40:
        risk_level = "medium"
    elif risk_score > 0:
        risk_level = "low"
    else:
        risk_level = "none"

    return ImageRiskResult(
        paper_no=paper_no,
        paper_label=paper_label,
        paper_type=paper_type,
        module=module,
        topic=topic,
        point_name=point_name,
        risk_level=risk_level,
        risk_score=risk_score,
        risk_reasons=reasons,
        affected_points=[p for p in all_point_texts if p],
    )


# ============================================================
# 环节 2: 单卷标记
# ============================================================

def attach_image_risk(paper: Any) -> ImageRiskResult:
    """将配图风险检测结果附加到 PaperPlan 对象。

    调用后会设置 paper.image_risk_level, paper.image_risk_score,
    paper.image_risk_reasons 三个属性。
    """
    result = classify_paper_risk(
        paper_no=getattr(paper, "paper_no", 0),
        paper_label=getattr(paper, "paper_label", ""),
        paper_type=getattr(paper, "paper_type", ""),
        module=getattr(paper, "module", ""),
        topic=getattr(paper, "topic", ""),
        point_name=getattr(paper, "point_name", ""),
        point_content=getattr(paper, "point_content", ""),
        rows=getattr(paper, "rows", None),
    )

    # 附加到 PaperPlan
    paper.image_risk_level = result.risk_level        # type: ignore[attr-defined]
    paper.image_risk_score = result.risk_score        # type: ignore[attr-defined]
    paper.image_risk_reasons = result.risk_reasons    # type: ignore[attr-defined]

    return result


def attach_image_risks_batch(papers: list[Any]) -> dict[str, list[ImageRiskResult]]:
    """批量检测配图风险，按风险等级分组返回。"""
    by_level: dict[str, list[ImageRiskResult]] = defaultdict(list)
    for paper in papers:
        result = attach_image_risk(paper)
        by_level[result.risk_level].append(result)
    return dict(by_level)


# ============================================================
# 环节 3: 出题规避 (preflight 阶段警告)
# ============================================================

def format_risk_warnings(by_level: dict[str, list[ImageRiskResult]]) -> list[str]:
    """格式化配图风险警告，供 preflight 对话框展示。"""
    warnings: list[str] = []

    high_risks = by_level.get("high", [])
    medium_risks = by_level.get("medium", [])

    if high_risks:
        labels = ", ".join(r.paper_label for r in high_risks[:10])
        more = f" 等共{len(high_risks)}卷" if len(high_risks) > 10 else ""
        warnings.append(
            f"⚠️ 高风险配图卷 {len(high_risks)} 卷：{labels}{more} — "
            f"这些卷的考点大概率需要配图，请确保题目来源包含图片或提前准备配图资源。"
        )

    if medium_risks:
        labels = ", ".join(r.paper_label for r in medium_risks[:10])
        more = f" 等共{len(medium_risks)}卷" if len(medium_risks) > 10 else ""
        warnings.append(
            f"⚡ 中风险配图卷 {len(medium_risks)} 卷：{labels}{more} — "
            f"部分考点可能需要配图，建议抽查确认。"
        )

    # 按论文标注具体原因
    for result in high_risks[:5]:
        warnings.append(f"  [{result.paper_label}] {result.topic or result.point_name}：{'；'.join(result.risk_reasons)}")

    return warnings


# ============================================================
# 环节 4: auto_review 图题检测
# ============================================================

def check_image_requirement(
    question: dict[str, Any],
    paper_context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """检测单题是否存在缺图风险。

    检查项：
      1. 题干含"如图/下图/图中"等标记但无图片 → 严重缺图
      2. 题型为作图题/识图题但无图片 → 严重缺图
      3. 考点为高风险配图类，题干缺图 → 警告

    Returns:
        list of issues (空列表表示通过)
    """
    from 质检.rules import make_issue, FAILED, WARNING

    issues: list[dict[str, str]] = []
    stem = _clean_text(question.get("stem", ""))
    raw_text = _clean_text(question.get("raw_text", ""))
    combined_text = f"{stem}\n{raw_text}"

    # 检查是否有图片数据
    has_image = bool(
        question.get("protected_original_docx_block")
        or question.get("stem_images")
        or question.get("images")
        or question.get("option_images")
        or question.get("image_url")
        or question.get("img_url")
        or any((question.get("image_flags") or {}).values())
        or any((question.get("image_refs") or {}).get(part) for part in ("stem", "answer", "analysis"))
    )
    # 也检查选项中是否有图片
    options = question.get("options") or []
    for opt in options:
        if isinstance(opt, dict) and (opt.get("image") or opt.get("images")):
            has_image = True
            break

    question_no = question.get("question_no", "?")

    # 检查 1: 题干含"如图"等标记但无图
    for marker in MISSING_IMAGE_MARKERS:
        if re.search(marker, combined_text) and not has_image:
            issues.append(make_issue(
                "missing_required_image",
                "题干引用图但无图片",
                FAILED,
                f"第{question_no}题题干含\"如图/图中\"等图引用标记，但题目未包含图片数据。",
            ))
            break  # 一种缺图只报一次

    # 检查 2: 题型为作图/识图题但无图
    qtype = _clean_text(question.get("question_type", ""))
    if any(t in qtype for t in IMAGE_REQUIRED_QUESTION_TYPES):
        if not has_image:
            issues.append(make_issue(
                "image_required_type_no_image",
                f"{qtype}缺图",
                FAILED,
                f"第{question_no}题为{qtype}，必须包含图片但未检测到图片数据。",
            ))

    # 检查 3: 高风险考点 + 缺图 (仅警告)
    if paper_context:
        risk_level = paper_context.get("image_risk_level", "")
        if risk_level == "high" and not has_image:
            # 检查是否是纯理论不需要图的题
            pure_theory_markers = ["定义", "概念", "性质", "特点", "分类", "作用", "属于"]
            if not any(m in stem for m in pure_theory_markers):
                issues.append(make_issue(
                    "high_risk_no_image",
                    "高配图风险卷缺图",
                    WARNING,
                    f"第{question_no}题所属卷为高配图风险，建议确认是否需要配图。",
                ))

    return issues


def check_all_questions_image_risk(
    questions: list[dict[str, Any]],
    paper_context: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], int, int]:
    """对整卷题目执行配图风险检测。

    Returns:
        (per_question_reports, missing_image_count, warning_count)
    """
    reports: list[dict[str, Any]] = []
    missing_count = 0
    warning_count = 0

    for idx, question in enumerate(questions):
        issues = check_image_requirement(question, paper_context)
        has_failed = any(i.get("severity") == "failed" for i in issues)

        reports.append({
            "index": idx,
            "question_no": question.get("question_no", idx + 1),
            "stem_preview": _clean_text(question.get("stem", ""))[:60],
            "has_image_marker": any(
                re.search(m, _clean_text(question.get("stem", "")))
                for m in MISSING_IMAGE_MARKERS
            ),
            "has_image_data": bool(
                question.get("protected_original_docx_block")
                or question.get("stem_images")
                or question.get("images")
                or question.get("image_url")
                or any((question.get("image_flags") or {}).values())
                or any((question.get("image_refs") or {}).get(part) for part in ("stem", "answer", "analysis"))
            ),
            "issues": issues,
            "status": "failed" if has_failed else ("warning" if issues else "passed"),
        })

        if has_failed:
            missing_count += 1
        elif issues:
            warning_count += 1

    return reports, missing_count, warning_count


# ============================================================
# 环节 5: 配图风险报告
# ============================================================

def build_image_risk_report(
    papers: list[Any],
    by_level: dict[str, list[ImageRiskResult]] | None = None,
) -> dict[str, Any]:
    """生成全局配图风险清单，供人工 QC 优先检查。

    Returns:
        {
            "summary": {"high": N, "medium": N, "low": N, "none": N},
            "high_risk_papers": [...],   # 优先检查
            "medium_risk_papers": [...],
            "low_risk_papers": [...],
            "checklist": [
                {"paper_label": ..., "risk_level": ..., "risk_reasons": ..., "suggestion": ...}
            ]
        }
    """
    if by_level is None:
        by_level = attach_image_risks_batch(papers)

    high = by_level.get("high", [])
    medium = by_level.get("medium", [])
    low = by_level.get("low", [])

    def paper_dict(result: ImageRiskResult) -> dict[str, Any]:
        suggestion = ""
        if result.risk_level == "high":
            suggestion = "优先审核：逐题检查是否缺图，确保所有'如图'引用均有配图"
        elif result.risk_level == "medium":
            suggestion = "抽查审核：重点检查含'读图/识图/结构/原理'描述的题目"
        else:
            suggestion = "常规审核"

        return {
            "paper_label": result.paper_label,
            "paper_type": result.paper_type,
            "module": result.module,
            "topic": result.topic or result.point_name,
            "risk_level": result.risk_level,
            "risk_score": result.risk_score,
            "risk_reasons": result.risk_reasons,
            "suggestion": suggestion,
        }

    checklist = []
    # 高风险在前
    checklist.extend(paper_dict(r) for r in high)
    checklist.extend(paper_dict(r) for r in medium)
    checklist.extend(paper_dict(r) for r in low)

    return {
        "summary": {
            "high": len(high),
            "medium": len(medium),
            "low": len(low),
            "none": len(by_level.get("none", [])),
            "total": sum(len(v) for v in by_level.values()),
        },
        "high_risk_papers": [paper_dict(r) for r in high],
        "medium_risk_papers": [paper_dict(r) for r in medium],
        "low_risk_papers": [paper_dict(r) for r in low],
        "checklist": checklist,
    }


def render_image_risk_markdown(report: dict[str, Any]) -> str:
    """将配图风险报告渲染为 Markdown。"""
    summary = report.get("summary", {})
    checklist = report.get("checklist", [])

    lines = [
        "# 配图风险前置检测报告",
        "",
        "## 总览",
        "",
        f"- 总卷数：{summary.get('total', 0)}",
        f"- 🔴 高风险：{summary.get('high', 0)} 卷（优先处理）",
        f"- 🟡 中风险：{summary.get('medium', 0)} 卷",
        f"- 🟢 低风险：{summary.get('low', 0)} 卷",
        f"- ⚪ 无风险：{summary.get('none', 0)} 卷",
        "",
        "---",
        "",
        "## 人工 QC 优先检查清单",
        "",
        "| 优先级 | 卷号 | 卷型 | 知识模块 | 专题/考点 | 风险分 | 原因 | 建议 |",
        "|---|---:|---|---|---:|---|---|",
    ]

    for item in checklist:
        level_icon = {"high": "🔴", "medium": "🟡", "low": "🟢", "none": "⚪"}.get(
            item.get("risk_level", ""), "⚪"
        )
        reasons = "；".join(item.get("risk_reasons", []))
        lines.append(
            f"| {level_icon} | {item.get('paper_label', '')} "
            f"| {item.get('paper_type', '')} "
            f"| {item.get('module', '')} "
            f"| {item.get('topic', '')} "
            f"| {item.get('risk_score', 0)} "
            f"| {reasons} "
            f"| {item.get('suggestion', '')} |"
        )

    lines.extend(["", ""])
    return "\n".join(lines) + "\n"
