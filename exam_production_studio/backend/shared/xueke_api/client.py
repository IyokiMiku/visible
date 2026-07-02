"""学科网拉题入口 pull_for_plan（接入真实 API：源 学科网API拉题移植版）。

凭据：cookie/app_key/sign 来自 config.get_xueke_config()（app_key/sign 缺省走网关默认）。
课程/题型/知识点映射：
  - course_id：plan['course_id'] 或 ctx.ai_options['xueke_course_id']
  - kpoint_ids：plan['kpoint_ids']（聚合卷多值）优先，回退 plan['kpoint_id']（单值）
  - type_ids：ctx.ai_options['xueke_type_ids'] = {题型名: [type_id,...]}
无 cookie/课程ID/题型映射时返回明确说明，由上层走 AI 补题/待确认。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import config
from engine.drivers.base import Question
from shared import config_errors
from .api_pull_core import pull_questions
from .query_questions import XuekeAuthError
from . import kpoint_resolver
from .html_content_converter import (
    convert_answer_html, convert_explanation_html, convert_stem_html, is_image_only_question,
)

SECTION_BY_NAME = {
    "单项选择题": "choice", "多项选择题": "choice", "选择题": "choice",
    "填空题": "fill", "判断题": "judge", "简答题": "short_answer",
    "综合应用题": "calc", "综合题": "calc", "计算题": "calc",
    "作图题": "short_answer", "识图题": "short_answer", "简答作图题": "short_answer",
}


@dataclass
class PulledResult:
    ok: bool
    questions: list[Question] = field(default_factory=list)
    note: str = ""
    by_type: dict[str, int] = field(default_factory=dict)

    def count_by_type(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for q in self.questions:
            out[q.qtype] = out.get(q.qtype, 0) + 1
        return out


def _difficulty_label(val: Any) -> str:
    # 学科网 difficulty：0=难，1=易
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "简单"
    if v >= 0.7:
        return "简单"
    if v >= 0.4:
        return "适中"
    return "困难"


def row_to_question(row: dict[str, Any], qtype: str) -> Question | None:
    stem_html = row.get("stem", "") or ""
    if is_image_only_question(stem_html):
        return None
    stem_text, stem_imgs, options = convert_stem_html(stem_html)
    opts = [o.get("text", "") for o in options] if options else []
    # 选项图片与 opts 下标对齐，供 docx 渲染图片选项
    option_imgs = [list(o.get("images") or []) for o in options] if options else []
    answer = convert_answer_html(row.get("answer", "") or "", row.get("type_id"))
    analysis = convert_explanation_html(row.get("explanation") or row.get("more_explanations") or "")
    kpoints = row.get("kpointIds") or row.get("kpoint_ids") or []
    kpoint = str(kpoints[0]) if isinstance(kpoints, list) and kpoints else ""
    if not stem_text and not stem_imgs:
        return None
    return Question(
        number=0, qtype=qtype, stem=stem_text, options=opts, answer=answer.strip(),
        analysis=analysis.strip(), difficulty=_difficulty_label(row.get("difficulty")),
        kpoint=kpoint, source="xueke", confidence=1.0,
        stem_images=list(stem_imgs or []), option_images=option_imgs,
    )


def pull_for_plan(ctx, plan: dict[str, Any], needed: dict[str, int]) -> PulledResult:
    cfg = config.get_xueke_config()
    cookie = cfg.get("cookie")
    if not cookie:
        return PulledResult(ok=False, note="未配置学科网 cookie（请在全局设置或 .env 填写 XKW_COOKIE）")

    # 课程ID：plan / ai_options 覆盖 / 本地映射自动解析
    course_id = plan.get("course_id") or (ctx.ai_options or {}).get("xueke_course_id")
    if not course_id:
        course_id = kpoint_resolver.resolve_course_id(ctx)
    if not course_id:
        return PulledResult(ok=False, note=f"无法解析学科网课程ID（课程：{getattr(ctx, 'course', '')}）")

    # 题源知识点：聚合卷（专题/综合）传多个 kpointId 并集，考点卷传单个；空则按课程+题型宽拉
    kpoint_ids = [k for k in (plan.get("kpoint_ids") or []) if k]
    if not kpoint_ids and plan.get("kpoint_id"):
        kpoint_ids = [plan["kpoint_id"]]
    kpoint_ids = kpoint_ids or None
    type_ids_map: dict[str, Any] = (ctx.ai_options or {}).get("xueke_type_ids", {})
    app_key = cfg.get("app_key") or None
    sign = cfg.get("sign") or None

    questions: list[Question] = []
    notes: list[str] = []
    for qtype, n in needed.items():
        if n <= 0:
            continue
        section = SECTION_BY_NAME.get(qtype)
        # typeId 解析优先级：显式覆盖 → 按 courseId 精确解析（稳定主键）→ 按课程名兜底（旧逻辑）
        tids = (type_ids_map.get(qtype)
                or kpoint_resolver.resolve_type_ids_by_course_id(course_id, qtype)
                or kpoint_resolver.resolve_type_ids(getattr(ctx, "course", ""), qtype))
        if not section:
            notes.append(f"{qtype}: 无 section_type 映射")
            continue
        if not tids:
            notes.append(f"{qtype}: 无法解析 typeId")
            continue
        try:
            rows = pull_questions(course_id=int(course_id), kpoint_ids=kpoint_ids, type_ids=tids,
                                  section_type=section, needed=n, cookie=cookie,
                                  app_key=app_key or "", sign=sign or "")
        except XuekeAuthError as e:
            # 鉴权失败（Cookie 失效/无权限）：记录配置错误以点亮红点，不中断流程（其余走补题/待确认）
            config_errors.record("xueke", "cookie", f"学科网 Cookie 无效或已过期：{e}")
            notes.append(f"{qtype}: {e}")
            continue
        except Exception as e:  # noqa: BLE001
            notes.append(f"{qtype}: 拉题失败 {e}")
            continue
        added = 0
        for r in rows:
            if added >= n:
                break
            q = row_to_question(r, qtype)
            if q is not None:
                questions.append(q)
                added += 1

    # cookie+课程齐全即视为"已尝试真实拉题"；具体缺口由上层补题/待确认处理
    note = "; ".join(notes)
    return PulledResult(ok=True, questions=questions, note=note)
