#!/usr/bin/env python3
"""
学科网题库查询脚本
调用 get-question-list API，按课程/知识点/题型/难度拉取试题，输出 JSON。

用法:
  python query_questions.py \
    --app-key 4f2a82224eb140e5964d0891a1affcc6 \
    --sign dfe533d82b4e5ee8aa390b1f775537ae \
    --course-id {course_id} \
    --type-ids {type_id} \
    --difficulty-low 0.4 \
    --difficulty-up 0.6 \
    --page-size 2 \
    --output result.json
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# ---- API 配置 ----
API_URL = "https://yanyi.zxxk.com/11181/18001/api-question/v1/question/get-question-list"
DEFAULT_APP_KEY = "4f2a82224eb140e5964d0891a1affcc6"
DEFAULT_SIGN = "dfe533d82b4e5ee8aa390b1f775537ae"


def _load_cookie() -> str:
    cookie = os.environ.get("XKW_COOKIE", "")
    if cookie:
        return cookie
    config_path = Path(__file__).resolve().parent.parent.parent / "02_配置资源" / "config.json"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            return cfg.get("xkw_cookie", "")
        except Exception:
            pass
    return ""


DEFAULT_COOKIE = _load_cookie()
DEFAULT_BANK_IDS = None

# 全量 fields 列表，根据需要增减
ALL_FIELDS = [
    "question_id", "course_id", "type_id", "top_type_id", "type_feature_ids",
    "paper_id", "source", "year", "difficulty",
    "stem", "answer", "explanation", "more_explanations",
    "catalog_ids", "source_catalog_ids", "kpointIds", "primary_k_point_ids",
    "tag_ids", "status", "application_id", "source_id", "paper_type_id",
    "paper_tag_ids", "media", "sub_course", "option_k_points",
    "kpoint_abilities", "trick_ids", "version_ids", "text_book_ids",
    "merge_to", "fresh_score", "sub_question_props",
    "en_words", "multi_explanation",
    "create_date", "update_date", "publish_date", "qml_update_date",
    "sync_date", "variant_questions", "stem_text", "bank_ids",
    "operation_tags",
]

REQUEST_FIELD_GROUPS = [
    ("courseId",),
    ("kpointIds",),
    ("primaryKPointIds", "primary_k_point_ids"),
    ("typeIds",),
    ("topTypeIds",),
    ("catalogIds",),
    ("difficultyLowLimit",),
    ("difficultyUpLimit",),
    ("pageIndex",),
    ("pageSize",),
]

RESPONSE_FIELD_GROUPS = [
    ("questionId", "question_id"),
    ("courseId", "course_id"),
    ("typeId", "type_id"),
    ("topTypeId", "top_type_id"),
    ("kpointIds",),
    ("primaryKPointIds", "primary_k_point_ids"),
    ("catalogIds", "catalog_ids"),
    ("difficulty",),
    ("stem",),
    ("answer",),
    ("explanation", "more_explanations"),
    ("status",),
]


def _compact_json(value, max_chars=140):
    text = json.dumps(value, ensure_ascii=False, sort_keys=True) if not isinstance(value, str) else value
    text = " ".join(str(text).split())
    if len(text) > max_chars:
        return text[:max_chars] + "……"
    return text


def describe_payload(payload):
    parts = []
    for group in REQUEST_FIELD_GROUPS:
        for key in group:
            if key in payload:
                parts.append(f"{key}={_compact_json(payload.get(key))}")
                break
        else:
            parts.append(f"{group[0]}=<unset>")
    return ", ".join(parts)


def _question_list(result):
    if not isinstance(result, dict):
        return []
    body = result.get("result") or {}
    rows = body.get("list") or []
    return rows if isinstance(rows, list) else []


def summarize_question_field_gaps(result):
    rows = _question_list(result)
    summary = []
    if not rows:
        return summary

    for aliases in RESPONSE_FIELD_GROUPS:
        missing = 0
        samples = []
        for idx, row in enumerate(rows, 1):
            if not isinstance(row, dict):
                missing += 1
                if len(samples) < 3:
                    samples.append(f"第{idx}题: 非对象")
                continue
            if any(row.get(alias) not in (None, "", [], {}) for alias in aliases if alias in row):
                continue
            missing += 1
            if len(samples) < 3:
                qid = row.get("questionId") or row.get("question_id") or idx
                samples.append(f"第{idx}题({qid})")
        if missing:
            summary.append({
                "field": "/".join(aliases),
                "missing": missing,
                "sample": samples,
            })
    return summary


def print_request_snapshot(payload, *, prefix=""):
    print(f"{prefix}请求参数：{describe_payload(payload)}", file=sys.stderr)


def print_response_diagnostics(result, *, prefix=""):
    if not isinstance(result, dict):
        print(f"{prefix}返回结构异常：{type(result).__name__}", file=sys.stderr)
        return
    body = result.get("result") or {}
    total_count = body.get("totalCount", "?") if isinstance(body, dict) else "?"
    returned_count = len(_question_list(result))
    print(
        f"{prefix}返回摘要：valid={result.get('valid', False)}, totalCount={total_count}, returned={returned_count}",
        file=sys.stderr,
    )
    gaps = summarize_question_field_gaps(result)
    if not gaps:
        print(f"{prefix}字段诊断：未发现缺失字段", file=sys.stderr)
        return
    print(f"{prefix}字段诊断：发现 {len(gaps)} 类字段缺失", file=sys.stderr)
    for gap in gaps:
        sample = ", ".join(gap["sample"]) if gap["sample"] else "无样例"
        print(f"{prefix}  - {gap['field']}: 缺失 {gap['missing']} 题（{sample}）", file=sys.stderr)


def build_payload(
    course_id=None,
    kpoint_ids=None,
    primary_kpoint_ids=None,
    type_ids=None,
    top_type_ids=None,
    catalog_ids=None,
    bank_ids=DEFAULT_BANK_IDS,
    difficulty_low=None,
    difficulty_up=None,
    page_index=1,
    page_size=10,
    fields=None,
    operation_tags=None,
):
    """构造 API 请求 body."""
    payload = {
        "pageIndex": page_index,
        "pageSize": page_size,
        "fields": fields or ALL_FIELDS,
    }
    if bank_ids:
        payload["bankIds"] = bank_ids
    if course_id is not None:
        payload["courseId"] = course_id
    if kpoint_ids:
        payload["kpointIds"] = kpoint_ids
    if primary_kpoint_ids:
        payload["primaryKPointIds"] = primary_kpoint_ids
    if type_ids:
        payload["typeIds"] = type_ids
    if top_type_ids:
        payload["topTypeIds"] = top_type_ids
    if catalog_ids:
        payload["catalogIds"] = catalog_ids
    if difficulty_low is not None:
        payload["difficultyLowLimit"] = difficulty_low
    if difficulty_up is not None:
        payload["difficultyUpLimit"] = difficulty_up
    if operation_tags:
        payload["operationTags"] = operation_tags

    # 默认使用 HTML 结构 + LATEX 公式
    payload["structFormat"] = "HTML"
    payload["formatEnum"] = "LATEX"

    return payload


def query(payload, url=API_URL, app_key=None, sign=None, cookie=None, timeout=30):
    """发送 POST 请求并返回解析后的 JSON."""
    if cookie is None:
        cookie = DEFAULT_COOKIE
    if app_key is None:
        app_key = DEFAULT_APP_KEY
    if sign is None:
        sign = DEFAULT_SIGN
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "*/*")
    req.add_header("User-Agent", "kaogang-question-bank/1.0")
    if cookie:
        req.add_header("Cookie", cookie)
    if app_key:
        req.add_header("appKey", app_key)
    if sign:
        req.add_header("sign", sign)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {err_body}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        return None


def summarize_result(result):
    """从 API 返回中提取简要统计信息."""
    rows = _question_list(result)
    if not result:
        return {"error": "No response from API"}
    if not result.get("valid", False):
        return {"error": f"API error: {result.get('error', 'unknown')}"}
    r = result.get("result") or {}
    return {
        "totalCount": r.get("totalCount"),
        "totalPages": r.get("totalPages"),
        "returnedCount": len(rows),
        "sampleQuestionIds": [
            (q.get("questionId") or q.get("question_id"))
            for q in rows[:5]
            if isinstance(q, dict)
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="学科网题库查询")
    parser.add_argument("--course-id", type=int, help="课程ID")
    parser.add_argument("--kpoint-ids", help="知识点ID列表，逗号分隔")
    parser.add_argument("--primary-kpoint-ids", help="主知识点ID列表，逗号分隔")
    parser.add_argument("--type-ids", help="题型ID列表，逗号分隔")
    parser.add_argument("--top-type-ids", help="一级题型ID列表，逗号分隔")
    parser.add_argument("--catalog-ids", help="章节ID列表，逗号分隔")
    parser.add_argument("--difficulty-low", type=float, help="难度下限 (0=难, 1=易)")
    parser.add_argument("--difficulty-up", type=float, help="难度上限 (0=难, 1=易)")
    parser.add_argument("--page-index", type=int, default=1, help="页码")
    parser.add_argument("--page-size", type=int, default=10, help="每页数量")
    parser.add_argument("--operation-tags", help="运营标签ID列表，逗号分隔")
    parser.add_argument("--output", "-o", help="输出 JSON 文件路径")
    parser.add_argument("--summary", action="store_true", help="仅输出统计摘要")
    parser.add_argument("--app-key", default=DEFAULT_APP_KEY, help="API 鉴权 appKey")
    parser.add_argument("--cookie", default=DEFAULT_COOKIE, help="API Cookie 鉴权；也可设置环境变量 XKW_COOKIE")
    parser.add_argument("--sign", default=DEFAULT_SIGN, help="API 鉴权 sign")
    parser.add_argument("--no-bank-ids", action="store_true", help="不限制题库ID，搜全库")
    parser.add_argument("--merge-to", help="合并模式：追加到已有题库文件（去重）")
    args = parser.parse_args()

    # 解析逗号分隔列表
    def parse_ids(raw):
        if not raw:
            return None
        return [int(x.strip()) if x.strip().isdigit() else x.strip() for x in raw.split(",")]

    payload = build_payload(
        course_id=args.course_id,
        kpoint_ids=parse_ids(args.kpoint_ids),
        primary_kpoint_ids=parse_ids(args.primary_kpoint_ids),
        type_ids=parse_ids(args.type_ids),
        top_type_ids=parse_ids(args.top_type_ids),
        catalog_ids=parse_ids(args.catalog_ids),
        difficulty_low=args.difficulty_low,
        difficulty_up=args.difficulty_up,
        page_index=args.page_index,
        page_size=args.page_size,
        operation_tags=parse_ids(args.operation_tags),
        bank_ids=None if args.no_bank_ids else DEFAULT_BANK_IDS,
    )

    print_request_snapshot(payload)
    result = query(payload, app_key=args.app_key, sign=args.sign, cookie=args.cookie)

    if result is None:
        sys.exit(1)

    print_response_diagnostics(result)

    # ---- 合并模式：追加到已有题库文件 ----
    if args.merge_to:
        new_list = _question_list(result)
        if new_list:
            # 读取已有数据
            existing = []
            if os.path.exists(args.merge_to):
                try:
                    with open(args.merge_to, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        existing = data
                    elif isinstance(data, dict):
                        existing = data.get("result", {}).get("list", [])
                        if not isinstance(existing, list):
                            existing = []
                except Exception:
                    existing = []

            # 按 questionId 去重合并
            seen_ids = {str(q.get("questionId", "") or q.get("question_id", "")) for q in existing}
            added = 0
            for q in new_list:
                if not isinstance(q, dict):
                    continue
                qid = str(q.get("questionId", "") or q.get("question_id", ""))
                if qid and qid not in seen_ids:
                    existing.append(q)
                    seen_ids.add(qid)
                    added += 1

            # 写入 flat array 格式（持久化题库标准格式）
            os.makedirs(os.path.dirname(args.merge_to) or ".", exist_ok=True)
            with open(args.merge_to, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

            skipped = len(new_list) - added
            total = result.get("result", {}).get("totalCount", 0)
            print(
                f"合并到 {args.merge_to}: 拉取 {len(new_list)} 题, 新增 {added} 题, "
                f"跳过重复 {skipped} 题, 库内现有 {len(existing)} 题 (总计 {total})"
            )
        else:
            print(f"合并到 {args.merge_to}: API 返回 0 题，未写入")
        sys.exit(0)

    if args.summary:
        summary = summarize_result(result)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Written to {args.output} ({result.get('result', {}).get('totalCount', 0)} total)")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
