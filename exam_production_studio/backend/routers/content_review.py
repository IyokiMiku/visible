"""内容审阅接口（路线B · E 阶段）。

审阅只改内容不改格式：读题目+质检、图片服务、单题文本编辑、换选项顺序（同步答案）、
AI 重生成单题（沿用原 prompt）、逐题确认、整卷通过（全部确认后触发装配）。
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

from engine import questions_store, repo, review
from ._common import fail, load_ctx, ok

router = APIRouter(prefix="/api/projects", tags=["content-review"])


def _img_src(project_id: str, image: dict) -> dict:
    """给图片条目补一个前端可访问的 src（走 E2 图片服务）。"""
    out = dict(image or {})
    local = out.get("local_path") or out.get("path")
    if local:
        out["src"] = f"/api/projects/{project_id}/content-review/image?name={Path(local).name}"
    return out


def _question_to_dict(project_id: str, q) -> dict:
    d = asdict(q)
    d["stem_images"] = [_img_src(project_id, im) for im in (d.get("stem_images") or [])]
    d["option_images"] = [[_img_src(project_id, im) for im in imgs] for imgs in (d.get("option_images") or [])]
    return d


# ---------- E1：列表 + 详情 ----------
@router.get("/{project_id}/content-review/papers")
def list_review_papers(project_id: str):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    out = []
    for p in repo.get_papers(project_id):
        pno = p["paper_no"]
        pq = questions_store.load_questions(ctx, pno)
        if pq is None:
            continue
        review_state = questions_store.load_review(ctx, pno)
        qc = questions_store.load_qc(ctx, pno) or {}
        issues = qc.get("issues", [])
        out.append({
            "paper_no": pno,
            "topic": pq.meta.get("topic", ""),
            "status": review_state.get("status", ""),
            "score": qc.get("score"),
            "severe": sum(1 for i in issues if i.get("severity") == "严重"),
            "warning": sum(1 for i in issues if i.get("severity") == "警告"),
            "total": len(pq.questions),
            "confirmed": len(review_state.get("confirmed_nos", [])),
        })
    return ok(out)


@router.get("/{project_id}/content-review/{paper_no}")
def get_review_paper(project_id: str, paper_no: int):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    pq = questions_store.load_questions(ctx, paper_no)
    if pq is None:
        return fail("该卷题目数据不存在", status=404)
    qc = questions_store.load_qc(ctx, paper_no) or {}
    review_state = questions_store.load_review(ctx, paper_no)
    return ok({
        "paper_no": paper_no,
        "meta": pq.meta,
        "questions": [_question_to_dict(project_id, q) for q in pq.questions],
        "qc": qc,
        "review": review_state,
    })


# ---------- E2：本地图片服务 ----------
@router.get("/{project_id}/content-review/image")
def get_image(project_id: str, name: str):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    img_dir = (ctx.dir("_临时") / "images").resolve()
    target = (img_dir / name).resolve()
    if not str(target).startswith(str(img_dir)) or not target.exists():
        return fail("图片不存在或路径非法", status=404)
    return FileResponse(str(target))


# ---------- 内部：定位题目 + 取消确认 ----------
def _find_question(pq, number: int):
    for q in pq.questions:
        if q.number == number:
            return q
    return None


def _unconfirm(ctx, paper_no: int, number: int) -> None:
    rs = questions_store.load_review(ctx, paper_no)
    confirmed = [n for n in rs.get("confirmed_nos", []) if n != number]
    rs["confirmed_nos"] = confirmed
    if rs.get("status") == "已通过":
        rs["status"] = "待审"  # 通过后又改动 → 退回待审
    questions_store.update_review(ctx, paper_no, rs)


# ---------- E3：编辑单题文本 ----------
class QuestionEdit(BaseModel):
    stem: str | None = None
    options: list[str] | None = None
    answer: str | None = None
    analysis: str | None = None


@router.put("/{project_id}/content-review/{paper_no}/question/{number}")
def edit_question(project_id: str, paper_no: int, number: int, body: QuestionEdit):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    pq = questions_store.load_questions(ctx, paper_no)
    if pq is None:
        return fail("该卷题目数据不存在", status=404)
    q = _find_question(pq, number)
    if q is None:
        return fail("题目不存在", status=404)
    if body.stem is not None:
        q.stem = body.stem
    if body.options is not None:
        q.options = body.options
    if body.answer is not None:
        q.answer = body.answer
    if body.analysis is not None:
        q.analysis = body.analysis
    questions_store.save_questions(ctx, pq)
    _unconfirm(ctx, paper_no, number)  # 改动后需重新确认
    return ok(_question_to_dict(project_id, q))


# ---------- E4：换选项顺序（同步答案字母） ----------
class ReorderIn(BaseModel):
    order: list[int]  # 新顺序：order[新位置] = 旧下标


@router.post("/{project_id}/content-review/{paper_no}/question/{number}/reorder-options")
def reorder_options(project_id: str, paper_no: int, number: int, body: ReorderIn):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    pq = questions_store.load_questions(ctx, paper_no)
    if pq is None:
        return fail("该卷题目数据不存在", status=404)
    q = _find_question(pq, number)
    if q is None:
        return fail("题目不存在", status=404)
    n = len(q.options)
    if sorted(body.order) != list(range(n)):
        return fail(f"顺序非法：应为 0..{n-1} 的一个排列")

    q.options = [q.options[i] for i in body.order]
    if q.option_images:
        imgs = q.option_images + [[]] * (n - len(q.option_images))
        q.option_images = [imgs[i] for i in body.order]
    # 答案字母重映射：旧下标 oi → 新位置 np（order[np]==oi）
    old_to_new = {oi: np for np, oi in enumerate(body.order)}
    ans = str(q.answer or "").strip().upper()
    if ans and all(c in "ABCD"[:n] for c in ans):
        new_letters = {chr(ord("A") + old_to_new[ord(c) - ord("A")]) for c in ans}
        q.answer = "".join(L for L in "ABCD" if L in new_letters)
    questions_store.save_questions(ctx, pq)
    _unconfirm(ctx, paper_no, number)
    return ok(_question_to_dict(project_id, q))


# ---------- E5：AI 重生成单题（沿用原 prompt，固定题型/题号/知识点） ----------
@router.post("/{project_id}/content-review/{paper_no}/question/{number}/regenerate")
def regenerate_question(project_id: str, paper_no: int, number: int):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    pq = questions_store.load_questions(ctx, paper_no)
    if pq is None:
        return fail("该卷题目数据不存在", status=404)
    q = _find_question(pq, number)
    if q is None:
        return fail("题目不存在", status=404)

    from engine.steps.pull import build_paper_plan
    from shared.ai.fill import ai_fill
    plan = build_paper_plan(ctx, paper_no)
    new_qs = ai_fill(ctx, plan, {q.qtype: 1}, start_number=q.number)
    if not new_qs:
        return fail("AI 重生成失败，请稍后重试")
    nq = new_qs[0]
    # 仅替换内容，保留题号/题型/知识点；重生成文本不带图片
    q.stem, q.options, q.answer, q.analysis = nq.stem, nq.options, nq.answer, nq.analysis
    q.difficulty = nq.difficulty or q.difficulty
    q.source, q.confidence = "ai", nq.confidence
    q.stem_images, q.option_images = [], []
    questions_store.save_questions(ctx, pq)
    _unconfirm(ctx, paper_no, number)
    return ok(_question_to_dict(project_id, q))


# ---------- E6：逐题确认 ----------
@router.post("/{project_id}/content-review/{paper_no}/question/{number}/confirm")
def confirm_question(project_id: str, paper_no: int, number: int):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    pq = questions_store.load_questions(ctx, paper_no)
    if pq is None or _find_question(pq, number) is None:
        return fail("题目不存在", status=404)
    rs = questions_store.load_review(ctx, paper_no)
    confirmed = set(rs.get("confirmed_nos", []))
    confirmed.add(number)
    rs["confirmed_nos"] = sorted(confirmed)
    questions_store.update_review(ctx, paper_no, rs)
    return ok({"confirmed_nos": rs["confirmed_nos"], "total": len(pq.questions)})


# ---------- E7：整卷通过（全部确认后触发装配） ----------
@router.post("/{project_id}/content-review/{paper_no}/approve")
def approve_paper(project_id: str, paper_no: int):
    try:
        ctx = load_ctx(project_id)
    except KeyError:
        return fail("项目不存在", status=404)
    pq = questions_store.load_questions(ctx, paper_no)
    if pq is None:
        return fail("该卷题目数据不存在", status=404)
    nums = {q.number for q in pq.questions}
    rs = questions_store.load_review(ctx, paper_no)
    confirmed = set(rs.get("confirmed_nos", []))
    missing = sorted(nums - confirmed)
    if missing:
        return fail(f"仍有题目未确认：{missing}")

    rs["status"] = "已通过"
    rs["confirmed_nos"] = sorted(nums)
    questions_store.update_review(ctx, paper_no, rs)
    repo.update_paper(project_id, paper_no, status="reviewed")

    # 关闭该卷相关的待确认项
    for item in review.pending(project_id):
        if item.get("paper_no") == paper_no:
            review.confirm(item["id"])

    # 全部待确认已处理 → 自动继续流程（装配 + 归档）
    resumed = False
    if not review.has_pending(project_id):
        from engine import runner
        runner.resume(project_id)
        resumed = True
    return ok({"status": "已通过", "resumed": resumed})
