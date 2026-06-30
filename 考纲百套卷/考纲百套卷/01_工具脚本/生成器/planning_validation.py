"""规划表源头校验与 API 覆盖风险评估。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from collections import Counter, defaultdict
import json
import re
import sys

try:  # 支持作为脚本直接运行时导入同目录模块。
    from .planning import (
        COURSE_PAPER_TYPE,
        POINT_PAPER_TYPE,
        TOPIC_PAPER_TYPE,
        PaperPlan,
        PlanRow,
        PlanningMeta,
        format_paper_label,
        parse_paper_numbers,
    )
except ImportError:  # pragma: no cover
    from planning import (  # type: ignore
        COURSE_PAPER_TYPE,
        POINT_PAPER_TYPE,
        TOPIC_PAPER_TYPE,
        PaperPlan,
        PlanRow,
        PlanningMeta,
        format_paper_label,
        parse_paper_numbers,
    )

BASE_DIR = Path(__file__).resolve().parents[2]
API_DIR = BASE_DIR / "01_工具脚本" / "学科网API拉题移植版"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

try:  # API 评估是可选能力，本地结构校验不依赖这些模块。
    import query_questions  # type: ignore
    from api_pull_core import classify_question, validate_question  # type: ignore
    from kpoint_resolver import (  # type: ignore
        get_mapping_ai_generate_papers,
        load_mapping_table,
        resolve_course,
        resolve_type,
    )
except Exception:  # pragma: no cover
    query_questions = None  # type: ignore
    classify_question = None  # type: ignore
    validate_question = None  # type: ignore
    get_mapping_ai_generate_papers = None  # type: ignore
    load_mapping_table = None  # type: ignore
    resolve_course = None  # type: ignore
    resolve_type = None  # type: ignore

LEVELS = ("error", "warning", "info")
RISK_LEVELS = ("critical", "high", "medium", "low", "none", "unknown", "ai_only")
PAPER_TYPES = (POINT_PAPER_TYPE, TOPIC_PAPER_TYPE, COURSE_PAPER_TYPE)

QUESTION_BANK_KEYS = {
    "单选": "single_choice",
    "单选题": "single_choice",
    "单项选择题": "single_choice",
    "选择题": "single_choice",
    "判断": "judge",
    "判断题": "judge",
    "填空": "fill_blank",
    "填空题": "fill_blank",
    "简答": "short_answer",
    "简答题": "short_answer",
    "问答题": "short_answer",
    "综合": "comprehensive",
    "综合题": "comprehensive",
    "综合应用题": "comprehensive",
    "计算题": "comprehensive",
    "分析计算题": "comprehensive",
}


@dataclass
class ValidationIssue:
    code: str
    level: str
    message: str
    suggestion: str = ""
    row_no: int | None = None
    paper_no: int | None = None
    paper_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RequiredBucket:
    question_type: str
    required: int
    difficulty: str = ""


@dataclass
class ApiCoverageResult:
    paper_no: int
    paper_label: str
    paper_type: str
    module: str
    topic: str = ""
    point_name: str = ""
    course_id: int | None = None
    kpoint_ids: list[int] = field(default_factory=list)
    question_type: str = ""
    type_ids: list[str] = field(default_factory=list)
    required: int = 0
    api_total: int | None = None
    api_returned: int | None = None
    effective: int | None = None
    coverage_ratio: float | None = None
    risk_level: str = "unknown"
    api_status: str = "unknown"
    message: str = ""
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ApiAssessOptions:
    enabled: bool = False
    dry_run: bool = False
    papers: set[int] | None = None
    scope: set[str] = field(default_factory=lambda: {"point"})
    page_size: int = 50
    cookie: str | None = None
    timeout: int = 30


def _issue(
    code: str,
    level: str,
    message: str,
    suggestion: str = "",
    row_no: int | None = None,
    paper_no: int | None = None,
    paper_type: str = "",
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        level=level,
        message=message,
        suggestion=suggestion,
        row_no=row_no,
        paper_no=paper_no,
        paper_type=paper_type,
    )


def _paper_type_scope_key(paper_type: str) -> str:
    if paper_type == POINT_PAPER_TYPE:
        return "point"
    if paper_type == TOPIC_PAPER_TYPE:
        return "topic"
    if paper_type == COURSE_PAPER_TYPE:
        return "course"
    return "unknown"


def _count_by_level(issues: list[ValidationIssue]) -> dict[str, int]:
    counts = Counter(issue.level for issue in issues)
    return {level: counts.get(level, 0) for level in LEVELS}


def _parse_ref(row: PlanRow, paper_type: str) -> tuple[int, str, int, str]:
    if paper_type == POINT_PAPER_TYPE:
        return row.point_count, row.point_paper_ref, 6, "考点训练卷"
    if paper_type == TOPIC_PAPER_TYPE:
        return row.topic_count, row.topic_paper_ref, 8, "专题训练卷"
    return row.course_count, row.course_paper_ref, 10, "课程综合卷"


def scan_paper_references(rows: list[PlanRow]) -> dict[int, list[dict[str, Any]]]:
    refs: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for paper_type in PAPER_TYPES:
            count, ref, column, _ = _parse_ref(row, paper_type)
            numbers = parse_paper_numbers(ref)
            for number in numbers:
                refs[number].append(
                    {
                        "paper_type": paper_type,
                        "row_no": row.row_no,
                        "column": column,
                        "ref": ref,
                        "count": count,
                        "module": row.module,
                        "topic": row.topic,
                    }
                )
    return refs


def validate_paper_number_rules(rows: list[PlanRow], paper_index: dict[int, PaperPlan]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not paper_index:
        return [_issue("paper_index_empty", "error", "未解析到任何卷号。", "检查 F/H/J 三列卷号填写。")]

    numbers = sorted(paper_index)
    if numbers[0] != 1:
        issues.append(
            _issue(
                "paper_no_not_start_from_1",
                "warning",
                f"卷号从 {format_paper_label(numbers[0])} 开始，不是第1卷。",
                "如无特殊原因，建议从第1卷开始连续编号。",
                paper_no=numbers[0],
            )
        )

    missing = [number for number in range(numbers[0], numbers[-1] + 1) if number not in paper_index]
    if missing:
        issues.append(
            _issue(
                "paper_no_gap",
                "error",
                "缺少卷号：" + "、".join(format_paper_label(number) for number in missing),
                "补齐缺失卷号，或调整前后卷号使其连续。",
            )
        )

    total = len(numbers)
    if total < 80 or total > 120:
        issues.append(
            _issue(
                "paper_count_out_of_range",
                "warning",
                f"总卷数为 {total}，不在建议范围 80-120 内。",
                "确认是否为小规模试点；正式百套卷建议控制在 80-120 卷。",
            )
        )

    refs = scan_paper_references(rows)
    for paper_no, ref_items in sorted(refs.items()):
        types = {item["paper_type"] for item in ref_items}
        if len(types) > 1:
            locations = "；".join(
                f"第{item['row_no']}行{item['paper_type']}({item['ref']})" for item in ref_items
            )
            issues.append(
                _issue(
                    "paper_type_conflict",
                    "error",
                    f"{format_paper_label(paper_no)} 同时出现在多个卷型中：{locations}",
                    "同一卷号只能属于考点训练卷、专题训练卷、课程综合卷中的一种。",
                    paper_no=paper_no,
                )
            )
        point_refs = [item for item in ref_items if item["paper_type"] == POINT_PAPER_TYPE]
        if len(point_refs) > 1:
            locations = "；".join(f"第{item['row_no']}行({item['ref']})" for item in point_refs)
            issues.append(
                _issue(
                    "point_paper_duplicated",
                    "warning",
                    f"{format_paper_label(paper_no)} 作为考点训练卷被多行引用：{locations}",
                    "考点训练卷通常应只对应一个考点；如需覆盖多个考点，建议改为专题训练卷。",
                    paper_no=paper_no,
                    paper_type=POINT_PAPER_TYPE,
                )
            )
    return issues


def validate_count_consistency(rows: list[PlanRow]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for row in rows:
        count, ref, _, label = _parse_ref(row, POINT_PAPER_TYPE)
        numbers = parse_paper_numbers(ref)
        if count and not ref:
            issues.append(_issue("count_without_ref", "error", f"第{row.row_no}行 {label} 有数量但无卷号。", "补充 F 列卷号或清空 E 列数量。", row.row_no, paper_type=POINT_PAPER_TYPE))
        if ref and not count:
            issues.append(_issue("ref_without_count", "error", f"第{row.row_no}行 {label} 有卷号但数量为空或为0。", "补充 E 列数量，且应等于 F 列解析出的卷号数。", row.row_no, paper_type=POINT_PAPER_TYPE))
        if ref and not numbers:
            issues.append(_issue("unparseable_ref", "error", f"第{row.row_no}行 {label} 卷号无法解析：{ref}", "使用“第1卷”“第1-3卷”“第1、2、3卷”等格式。", row.row_no, paper_type=POINT_PAPER_TYPE))
        if count and numbers and count != len(numbers):
            issues.append(_issue("count_ref_mismatch", "error", f"第{row.row_no}行 {label} 数量为 {count}，但卷号解析为 {len(numbers)} 个：{ref}", "修正数量或卷号范围，使二者一致。", row.row_no, paper_type=POINT_PAPER_TYPE))

    topic_groups: dict[tuple[str, str, str], PlanRow] = {}
    course_groups: dict[tuple[str, str], PlanRow] = {}
    for row in rows:
        if row.topic_count or row.topic_paper_ref:
            topic_groups.setdefault((row.module, row.topic, row.topic_paper_ref), row)
        if row.course_count or row.course_paper_ref:
            course_groups.setdefault((row.module, row.course_paper_ref), row)

    for (_, _, ref), row in topic_groups.items():
        _validate_group_count(row, TOPIC_PAPER_TYPE, issues)
    for (_, ref), row in course_groups.items():
        _validate_group_count(row, COURSE_PAPER_TYPE, issues)
    return issues


def _validate_group_count(row: PlanRow, paper_type: str, issues: list[ValidationIssue]) -> None:
    count, ref, _, label = _parse_ref(row, paper_type)
    numbers = parse_paper_numbers(ref)
    if count and not ref:
        issues.append(_issue("count_without_ref", "error", f"第{row.row_no}行 {label} 有数量但无卷号。", "补充卷号或清空数量。", row.row_no, paper_type=paper_type))
    if ref and not count:
        issues.append(_issue("ref_without_count", "error", f"第{row.row_no}行 {label} 有卷号但数量为空或为0。", "补充数量，且应等于卷号数。", row.row_no, paper_type=paper_type))
    if ref and not numbers:
        issues.append(_issue("unparseable_ref", "error", f"第{row.row_no}行 {label} 卷号无法解析：{ref}", "使用标准卷号格式。", row.row_no, paper_type=paper_type))
    if count and numbers and count != len(numbers):
        issues.append(_issue("count_ref_mismatch", "error", f"第{row.row_no}行 {label} 数量为 {count}，但卷号解析为 {len(numbers)} 个：{ref}", "修正数量或卷号范围。", row.row_no, paper_type=paper_type))


def validate_required_columns(rows: list[PlanRow]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for row in rows:
        if row.point_name and not row.point_content:
            has_point_paper = bool(parse_paper_numbers(row.point_paper_ref))
            issues.append(
                _issue(
                    "missing_point_content",
                    "error" if has_point_paper else "warning",
                    f"第{row.row_no}行 C列有考点“{row.point_name}”，但 D列考纲原文为空。",
                    "补齐 D 列掌握/理解/了解考点内容；该列是后续出题和校验依据。",
                    row_no=row.row_no,
                    paper_type=POINT_PAPER_TYPE if has_point_paper else "",
                )
            )
    return issues


def validate_topic_course_coverage(rows: list[PlanRow]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    topic_groups: dict[tuple[str, str], list[PlanRow]] = defaultdict(list)
    module_groups: dict[str, list[PlanRow]] = defaultdict(list)
    for row in rows:
        if row.module:
            module_groups[row.module].append(row)
        if row.module and row.topic:
            topic_groups[(row.module, row.topic)].append(row)

    for (module, topic), group in sorted(topic_groups.items()):
        has_point_papers = any(parse_paper_numbers(row.point_paper_ref) for row in group)
        topic_refs = {row.topic_paper_ref for row in group if row.topic_paper_ref}
        if has_point_papers and not topic_refs:
            issues.append(
                _issue(
                    "missing_topic_paper",
                    "warning",
                    f"专题“{module} / {topic}”有考点训练卷，但未配置专题训练卷。",
                    "确认是否需要专题训练卷；如该专题考点较多，建议配置专题卷承接综合训练。",
                    paper_type=TOPIC_PAPER_TYPE,
                )
            )
        if len(topic_refs) > 1:
            issues.append(
                _issue(
                    "multiple_topic_refs",
                    "warning",
                    f"专题“{module} / {topic}”出现多个专题卷号引用：{sorted(topic_refs)}。",
                    "确认是否有意拆分；否则建议统一 H 列卷号范围。",
                    paper_type=TOPIC_PAPER_TYPE,
                )
            )

    for module, group in sorted(module_groups.items()):
        has_point_papers = any(parse_paper_numbers(row.point_paper_ref) for row in group)
        course_refs = {row.course_paper_ref for row in group if row.course_paper_ref}
        if has_point_papers and not course_refs:
            issues.append(
                _issue(
                    "missing_course_paper",
                    "warning",
                    f"课程“{module}”有考点训练卷，但未配置课程综合卷。",
                    "确认是否需要课程综合卷；正式百套卷通常建议每门课程有综合卷。",
                    paper_type=COURSE_PAPER_TYPE,
                )
            )
        if len(course_refs) > 1:
            issues.append(
                _issue(
                    "multiple_course_refs",
                    "warning",
                    f"课程“{module}”出现多个课程综合卷号引用：{sorted(course_refs)}。",
                    "确认是否有意拆分；否则建议统一 J 列卷号范围。",
                    paper_type=COURSE_PAPER_TYPE,
                )
            )
    return issues


def validate_planning_structure(
    meta: PlanningMeta,
    rows: list[PlanRow],
    paper_index: dict[int, PaperPlan],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(validate_paper_number_rules(rows, paper_index))
    issues.extend(validate_count_consistency(rows))
    issues.extend(validate_required_columns(rows))
    issues.extend(validate_topic_course_coverage(rows))
    return issues


def build_required_buckets(meta: PlanningMeta, paper: PaperPlan) -> tuple[list[RequiredBucket], ValidationIssue | None]:
    if paper.blueprint_rows:
        counts: Counter[tuple[str, str]] = Counter()
        for row in paper.blueprint_rows:
            qtype = (row.question_type or "").strip()
            if qtype:
                counts[(qtype, row.difficulty or "")] += 1
        if counts:
            return [RequiredBucket(question_type=qtype, difficulty=diff, required=count) for (qtype, diff), count in counts.items()], None

    summaries = meta.question_type_summaries.get(paper.module, [])
    buckets: list[RequiredBucket] = []
    for item in summaries:
        qtype = str(item.get("type", "")).strip()
        count = _to_int(item.get("count"))
        if qtype and count > 0:
            buckets.append(RequiredBucket(question_type=qtype, required=count))
    if buckets:
        return buckets, None

    return [], _issue(
        "required_unknown",
        "warning",
        f"{paper.paper_label} {paper.module} 无法从细目表或题型结构汇总推导题量需求。",
        "补充规划表底部各课程题型结构，或为专题/综合卷提供细目表。",
        paper_no=paper.paper_no,
        paper_type=paper.paper_type,
    )


def _to_int(value: Any) -> int:
    text = "" if value is None else str(value).strip()
    if not text:
        return 0
    try:
        return int(float(text))
    except Exception:
        match = re.search(r"\d+", text)
        return int(match.group(0)) if match else 0


def _mapping_key(paper_no: int) -> str:
    return format_paper_label(paper_no)


def assess_api_coverage(
    meta: PlanningMeta,
    paper_index: dict[int, PaperPlan],
    options: ApiAssessOptions,
) -> tuple[list[ApiCoverageResult], list[ValidationIssue]]:
    if not options.enabled:
        return [], []

    issues: list[ValidationIssue] = []
    results: list[ApiCoverageResult] = []
    if query_questions is None or resolve_course is None or resolve_type is None:
        issues.append(_issue("api_modules_unavailable", "warning", "API 评估模块不可用，已跳过 API 覆盖评估。", "检查学科网API拉题移植版目录是否完整。"))
        return results, issues

    mapping = load_mapping_table(meta.province, meta.exam_category) if load_mapping_table else {}
    ai_only = get_mapping_ai_generate_papers(meta.province, meta.exam_category) if get_mapping_ai_generate_papers else set()

    for paper in paper_index.values():
        if options.papers and paper.paper_no not in options.papers:
            continue
        if _paper_type_scope_key(paper.paper_type) not in options.scope and "all" not in options.scope:
            continue
        buckets, bucket_issue = build_required_buckets(meta, paper)
        if bucket_issue:
            issues.append(bucket_issue)
        if not buckets:
            continue
        results.extend(_assess_paper_api(meta, paper, buckets, mapping, ai_only, options))
    return results, issues


def _assess_paper_api(
    meta: PlanningMeta,
    paper: PaperPlan,
    buckets: list[RequiredBucket],
    mapping: dict[str, list[int]],
    ai_only: set[str],
    options: ApiAssessOptions,
) -> list[ApiCoverageResult]:
    key = _mapping_key(paper.paper_no)
    base_kwargs = dict(
        paper_no=paper.paper_no,
        paper_label=paper.paper_label,
        paper_type=paper.paper_type,
        module=paper.module,
        topic=paper.topic,
        point_name=paper.point_name,
    )

    if key in ai_only:
        return [
            ApiCoverageResult(
                **base_kwargs,
                question_type=bucket.question_type,
                required=bucket.required,
                risk_level="ai_only",
                api_status="ai_generate_planned",
                message="映射表标记为 AI 生成，跳过 API 覆盖判断。",
                suggestions=["确认该卷按 AI 补题流程生产，不纳入 API 拉题承诺。"],
            )
            for bucket in buckets
        ]

    kpoint_ids = mapping.get(key, [])
    if not mapping:
        return [_unknown_result(base_kwargs, bucket, "missing_mapping_table", "未找到知识点映射表，无法评估 API 覆盖。", "先生成或补齐映射表后重跑规划表校验。") for bucket in buckets]
    if not kpoint_ids:
        return [_unknown_result(base_kwargs, bucket, "missing_kpoint_ids", "该卷未解析到知识点 ID，无法评估 API 覆盖。", "检查映射表中该卷知识点 ID 或 AI生成标记。") for bucket in buckets]

    course_id = resolve_course(paper.module, meta.exam_category)
    if course_id is None:
        course_id = resolve_course(paper.module, None)
    if course_id is None:
        return [_unknown_result(base_kwargs, bucket, "unresolved_course", f"课程“{paper.module}”无法解析 courseId。", "检查课程名称是否与学科网映射表一致。", kpoint_ids=kpoint_ids) for bucket in buckets]

    results: list[ApiCoverageResult] = []
    for bucket in buckets:
        type_id = resolve_type(paper.module, bucket.question_type, meta.exam_category)
        if type_id is None:
            type_id = resolve_type(paper.module, bucket.question_type, None)
        if type_id is None:
            results.append(_unknown_result(base_kwargs, bucket, "unresolved_type", f"题型“{bucket.question_type}”无法解析 typeId。", "检查题型名称是否与学科网映射表一致。", course_id=course_id, kpoint_ids=kpoint_ids))
            continue
        if options.dry_run:
            results.append(
                ApiCoverageResult(
                    **base_kwargs,
                    course_id=course_id,
                    kpoint_ids=kpoint_ids,
                    question_type=bucket.question_type,
                    type_ids=[str(type_id)],
                    required=bucket.required,
                    risk_level="unknown",
                    api_status="dry_run",
                    message="API dry-run：已解析课程、题型、知识点，但未请求 API。",
                    suggestions=["去掉 --api-dry-run 后可获取 api_total/api_returned/effective。"],
                )
            )
            continue
        results.append(_query_api_bucket(base_kwargs, course_id, kpoint_ids, str(type_id), bucket, options))
    return results


def _unknown_result(
    base_kwargs: dict[str, Any],
    bucket: RequiredBucket,
    status: str,
    message: str,
    suggestion: str,
    course_id: int | None = None,
    kpoint_ids: list[int] | None = None,
) -> ApiCoverageResult:
    return ApiCoverageResult(
        **base_kwargs,
        course_id=course_id,
        kpoint_ids=kpoint_ids or [],
        question_type=bucket.question_type,
        required=bucket.required,
        risk_level="unknown",
        api_status=status,
        message=message,
        suggestions=[suggestion],
    )


def _query_api_bucket(
    base_kwargs: dict[str, Any],
    course_id: int,
    kpoint_ids: list[int],
    type_id: str,
    bucket: RequiredBucket,
    options: ApiAssessOptions,
) -> ApiCoverageResult:
    page_size = max(options.page_size, min(max(bucket.required * 3, 30), 100))
    payload = query_questions.build_payload(
        course_id=course_id,
        kpoint_ids=kpoint_ids,
        type_ids=[type_id],
        page_index=1,
        page_size=page_size,
        bank_ids=None,
    )
    try:
        result = query_questions.query(payload, cookie=options.cookie, timeout=options.timeout)
    except Exception as exc:  # pragma: no cover - depends on network
        return _unknown_result(base_kwargs, bucket, "failed", f"API 请求异常：{exc}", "先修复 Cookie/网络/API 后重跑；不能据此判断缺题。", course_id, kpoint_ids)

    if not result or not result.get("valid", False):
        msg = "API 无响应或返回 invalid。"
        if isinstance(result, dict):
            msg = f"API 返回异常：{result.get('error', msg)}"
        return _unknown_result(base_kwargs, bucket, "failed", msg, "先修复 Cookie/网络/API 后重跑；不能据此判断缺题。", course_id, kpoint_ids)

    body = result.get("result", {}) or {}
    questions = body.get("list", []) or []
    api_total = _to_int(body.get("totalCount"))
    api_returned = len(questions)
    bank_key = _bank_key_for_question_type(bucket.question_type)
    effective = _effective_count(questions, bank_key)
    risk = classify_api_risk(bucket.required, api_total, api_returned, effective, "ok")
    coverage_ratio = round(effective / bucket.required, 3) if bucket.required else None
    coverage = ApiCoverageResult(
        **base_kwargs,
        course_id=course_id,
        kpoint_ids=kpoint_ids,
        question_type=bucket.question_type,
        type_ids=[type_id],
        required=bucket.required,
        api_total=api_total,
        api_returned=api_returned,
        effective=effective,
        coverage_ratio=coverage_ratio,
        risk_level=risk,
        api_status="ok",
    )
    coverage.suggestions = build_api_suggestions(coverage)
    return coverage


def _bank_key_for_question_type(question_type: str) -> str:
    normalized = re.sub(r"\s+", "", question_type or "")
    return QUESTION_BANK_KEYS.get(normalized, "")


def _effective_count(questions: list[dict[str, Any]], bank_key: str) -> int:
    if not bank_key or validate_question is None:
        return len({str(q.get("questionId")) for q in questions if q.get("questionId")})
    seen: set[str] = set()
    count = 0
    for q in questions:
        qid = str(q.get("questionId") or "")
        if not qid or qid in seen:
            continue
        seen.add(qid)
        target_key = bank_key
        if classify_question is not None:
            target_key, _ = classify_question(q, bank_key)
        if target_key != bank_key:
            continue
        ok, _ = validate_question(q, bank_key)
        if ok:
            count += 1
    return count


def classify_api_risk(required: int, api_total: int | None, api_returned: int | None, effective: int | None, status: str) -> str:
    if status != "ok" or required <= 0 or api_total is None or effective is None:
        return "unknown"
    if api_total < required or effective < required * 0.5:
        return "critical"
    if effective < required:
        return "high"
    if effective >= required * 3 and api_total >= required * 5:
        return "none"
    if effective >= required * 2 and api_total >= required * 3:
        return "low"
    return "medium"


def build_api_suggestions(result: ApiCoverageResult) -> list[str]:
    if result.risk_level == "critical":
        return [
            "API 候选量低于本卷题量需求，建议合并相邻/上级考点。",
            "如该考点必须保留，建议降低该题型题量或预置 AI 补题。",
            "若同专题多个考点都偏窄，建议改为专题训练卷承接。",
        ]
    if result.risk_level == "high":
        return [
            "有效题量低于需求，建议检查题型映射和题目过滤规则。",
            "正式生产前应扩大知识点范围、降低题量或预置 AI 补题。",
        ]
    if result.risk_level == "medium":
        return ["题源勉强够用但冗余不足，建议扩大考点或保留 AI 补题预案。"]
    if result.risk_level == "unknown":
        return ["当前不是缺题结论；请先修复 API/映射/Cookie 问题后重跑。"]
    return []


def build_report_dict(
    meta: PlanningMeta,
    paper_index: dict[int, PaperPlan],
    issues: list[ValidationIssue],
    api_coverage: list[ApiCoverageResult],
) -> dict[str, Any]:
    numbers = sorted(paper_index)
    type_counts = Counter(paper.paper_type for paper in paper_index.values())
    risk_counts = Counter(item.risk_level for item in api_coverage)
    return {
        "plan_path": str(meta.path),
        "province": meta.province,
        "exam_category": meta.exam_category,
        "summary": {
            "paper_count": len(numbers),
            "paper_min": numbers[0] if numbers else None,
            "paper_max": numbers[-1] if numbers else None,
            "paper_type_counts": {paper_type: type_counts.get(paper_type, 0) for paper_type in PAPER_TYPES},
            "issue_counts": _count_by_level(issues),
            "api_risk_counts": {risk: risk_counts.get(risk, 0) for risk in RISK_LEVELS},
        },
        "issues": [issue.to_dict() for issue in issues],
        "api_coverage": [item.to_dict() for item in api_coverage],
    }


def write_json_report(path: str | Path, report: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown_report(path: str | Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    lines = [
        f"# 规划表源头校验报告",
        "",
        f"- 规划表：`{report['plan_path']}`",
        f"- 省份/考类：{report.get('province', '')} {report.get('exam_category', '')}",
        f"- 卷数：{summary['paper_count']}（{summary['paper_min']} - {summary['paper_max']}）",
        f"- 结构问题：error {summary['issue_counts']['error']} / warning {summary['issue_counts']['warning']} / info {summary['issue_counts']['info']}",
        "",
        "## 卷型统计",
        "",
    ]
    for paper_type, count in summary["paper_type_counts"].items():
        lines.append(f"- {paper_type}：{count}")

    issues = report.get("issues", [])
    lines.extend(["", "## 结构问题", ""])
    if issues:
        lines.append("| 等级 | 代码 | 行号 | 卷号 | 卷型 | 问题 | 建议 |")
        lines.append("|---|---|---:|---:|---|---|---|")
        for issue in issues:
            lines.append(
                "| {level} | {code} | {row} | {paper} | {ptype} | {msg} | {suggestion} |".format(
                    level=issue.get("level", ""),
                    code=issue.get("code", ""),
                    row=issue.get("row_no") or "",
                    paper=issue.get("paper_no") or "",
                    ptype=issue.get("paper_type", ""),
                    msg=_md_cell(issue.get("message", "")),
                    suggestion=_md_cell(issue.get("suggestion", "")),
                )
            )
    else:
        lines.append("未发现结构问题。")

    coverage = report.get("api_coverage", [])
    lines.extend(["", "## API 覆盖风险", ""])
    if coverage:
        lines.append("| 风险 | 卷号 | 卷型 | 课程 | 考点 | 题型 | required | total | returned | effective | 状态 | 建议 |")
        lines.append("|---|---:|---|---|---|---|---:|---:|---:|---:|---|---|")
        for item in sorted(coverage, key=lambda x: _risk_sort_key(x.get("risk_level", "unknown")))[:80]:
            lines.append(
                "| {risk} | {paper} | {ptype} | {module} | {point} | {qtype} | {required} | {total} | {returned} | {effective} | {status} | {suggestion} |".format(
                    risk=item.get("risk_level", ""),
                    paper=item.get("paper_no", ""),
                    ptype=item.get("paper_type", ""),
                    module=_md_cell(item.get("module", "")),
                    point=_md_cell(item.get("point_name", "") or item.get("topic", "")),
                    qtype=_md_cell(item.get("question_type", "")),
                    required=item.get("required", ""),
                    total=item.get("api_total") if item.get("api_total") is not None else "",
                    returned=item.get("api_returned") if item.get("api_returned") is not None else "",
                    effective=item.get("effective") if item.get("effective") is not None else "",
                    status=item.get("api_status", ""),
                    suggestion=_md_cell("；".join(item.get("suggestions", []))),
                )
            )
    else:
        lines.append("未启用 API 覆盖评估，或没有可评估项。")

    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _md_cell(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def _risk_sort_key(risk: str) -> int:
    order = {"critical": 0, "high": 1, "medium": 2, "unknown": 3, "ai_only": 4, "low": 5, "none": 6}
    return order.get(risk, 9)


def print_console_summary(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print(f"规划表源头校验：{report.get('province', '')} {report.get('exam_category', '')}".strip())
    print(f"- 卷号：共 {summary['paper_count']} 卷，范围 {summary['paper_min']} - {summary['paper_max']}")
    print("- 卷型：" + "，".join(f"{k} {v}" for k, v in summary["paper_type_counts"].items()))
    print("- 结构问题：" + "，".join(f"{k} {v}" for k, v in summary["issue_counts"].items()))
    if report.get("api_coverage"):
        print("- API风险：" + "，".join(f"{k} {v}" for k, v in summary["api_risk_counts"].items() if v))
        risky = [item for item in report["api_coverage"] if item["risk_level"] in {"critical", "high"}]
        if risky:
            print("最高风险：")
            for item in sorted(risky, key=lambda x: _risk_sort_key(x["risk_level"]))[:5]:
                print(
                    f"- {item['risk_level']} {format_paper_label(item['paper_no'])} "
                    f"{item['module']} / {item.get('point_name') or item.get('topic')} / {item['question_type']}："
                    f"required={item['required']}, total={item.get('api_total')}, "
                    f"returned={item.get('api_returned')}, effective={item.get('effective')}"
                )
