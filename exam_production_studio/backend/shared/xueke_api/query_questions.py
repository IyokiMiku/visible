"""学科网题库查询 HTTP 层（阶段四/接入：源 学科网API拉题移植版/query_questions.py 去硬编码）。

去硬编码改造：
- 移除从工具包 config.json 读取明文 cookie 的逻辑；cookie/app_key/sign 由调用方从 config 注入。
- DEFAULT_APP_KEY / DEFAULT_SIGN 为学科网 API 网关固定应用标识（非用户密钥），可被 settings/.env 覆盖。
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any

API_URL = "https://yanyi.zxxk.com/11181/18001/api-question/v1/question/get-question-list"
# 网关固定应用标识（非用户私密凭据）；如需覆盖请在「全局设置」填 XKW_APP_KEY/XKW_SIGN。
DEFAULT_APP_KEY = "4f2a82224eb140e5964d0891a1affcc6"
DEFAULT_SIGN = "dfe533d82b4e5ee8aa390b1f775537ae"


class XuekeAuthError(RuntimeError):
    """学科网鉴权失败：Cookie 失效/未登录/无权限。用于精准点亮「全局设置」红点。"""

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


def build_payload(
    course_id: int | None = None,
    kpoint_ids: list | None = None,
    primary_kpoint_ids: list | None = None,
    type_ids: list | None = None,
    top_type_ids: list | None = None,
    catalog_ids: list | None = None,
    bank_ids: list | None = None,
    difficulty_low: float | None = None,
    difficulty_up: float | None = None,
    page_index: int = 1,
    page_size: int = 10,
    fields: list | None = None,
    operation_tags: list | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
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
    payload["structFormat"] = "HTML"
    payload["formatEnum"] = "LATEX"
    return payload


def query(
    payload: dict[str, Any],
    *,
    url: str = API_URL,
    app_key: str | None = None,
    sign: str | None = None,
    cookie: str | None = None,
    timeout: int = 30,
) -> dict[str, Any] | None:
    app_key = app_key or DEFAULT_APP_KEY
    sign = sign or DEFAULT_SIGN
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "*/*")
    req.add_header("User-Agent", "exam-production-studio/1.0")
    if cookie:
        req.add_header("Cookie", cookie)
    if app_key:
        req.add_header("appKey", app_key)
    if sign:
        req.add_header("sign", sign)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[xueke] HTTP {e.code}: {body[:300]}", file=sys.stderr)
        if e.code in (401, 403):
            raise XuekeAuthError(f"学科网登录状态失效或无权限（HTTP {e.code}）") from e
        return None
    except urllib.error.URLError as e:
        print(f"[xueke] Network error: {e.reason}", file=sys.stderr)
        return None
