"""流程编排（阶段五 engine/runner，设计文档 §3.6/§5.y）。

按类型 flow_nodes 调度 steps；写 runs/flow_logs；事件推送；命中待确认暂停；支持 resume/rerun。

暂停策略：AI_MATCH / RULE_CONFLICT 为阻塞型（暂停，等待确认后 resume 继续）；
AI_GENERATE / QC_FAIL 记入待确认队列但不阻塞流程到达 done（可事后复核）。
"""
from __future__ import annotations

import json
import threading
import traceback
from typing import Any

from engine import events, repo, review
from engine.context import ProjectContext
from engine.drivers import get_driver
from shared import config_errors
from shared.config_errors import ConfigError
from shared.ai.llm import LLMNotConfigured

BLOCKING_TYPES = {"AI_MATCH", "RULE_CONFLICT", "AI_GENERATE", "QC_FAIL"}

_controls: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _state_path(ctx: ProjectContext):
    p = ctx.dir("运行记录") / "state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_state(ctx: ProjectContext) -> dict[str, Any]:
    sp = _state_path(ctx)
    if sp.exists():
        try:
            return json.loads(sp.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return {"stages": [], "papers_done": []}


def _save_state(ctx: ProjectContext, state: dict[str, Any]) -> None:
    _state_path(ctx).write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def _emit(ctx: ProjectContext, run_id: str, node: str, message: str, level: str = "info",
          event: str = "log", **extra: Any) -> None:
    repo.add_log(ctx.project_id, run_id, node, message, level)
    payload = {"event": event, "node": node, "message": message, "level": level,
               "time": repo.now(), **extra}
    events.publish(ctx.project_id, payload)


def _set_progress(ctx: ProjectContext, run_id: str, node: str, progress: float) -> None:
    repo.update_run(run_id, current_node=node, progress=progress)
    events.publish(ctx.project_id, {"event": "progress", "node": node, "progress": progress,
                                    "time": repo.now()})


def _should_pause(project_id: str) -> bool:
    with _lock:
        return bool(_controls.get(project_id, {}).get("pause"))


# ---------- 公共控制 ----------
def start(project_id: str) -> str:
    with _lock:
        _controls[project_id] = {"pause": False}
    run = repo.latest_run(project_id)
    rid = run["id"] if run and run["status"] in ("running", "review", "paused") else repo.create_run(project_id)
    t = threading.Thread(target=_safe_run, args=(project_id, rid), daemon=True)
    t.start()
    with _lock:
        _controls[project_id]["thread"] = t
    return rid


def resume(project_id: str) -> str:
    return start(project_id)


def pause(project_id: str) -> None:
    with _lock:
        _controls.setdefault(project_id, {})["pause"] = True


def rerun(project_id: str, node: str, paper_no: int | None = None) -> str:
    ctx = _build_ctx(project_id)
    state = _load_state(ctx)
    node_key = _NODE_KEY.get(node, node)
    if node_key in state["stages"]:
        state["stages"].remove(node_key)
    if paper_no is not None and paper_no in state["papers_done"]:
        state["papers_done"].remove(paper_no)
    if node_key in ("pull", "assemble", "qc", "split") and paper_no is None:
        state["papers_done"] = []
    _save_state(ctx, state)
    return start(project_id)


# ---------- 内部执行 ----------
def _build_ctx(project_id: str) -> ProjectContext:
    row = repo.get_project(project_id)
    if not row:
        raise KeyError(f"项目不存在: {project_id}")
    ctx = ProjectContext.from_row(row)
    ctx.ensure_dirs()
    return ctx


_NODE_KEY = {
    "读取资料": "load", "解析考纲": "kpoint", "解析目录": "kpoint",
    "生成规划": "planning", "知识点匹配": "mapping", "细目表": "mesh",
    "拉题与补题": "pull", "奇偶分卷": "split", "质检导出": "qc",
}


def _safe_run(project_id: str, run_id: str) -> None:
    try:
        _run(project_id, run_id)
    except Exception as e:  # noqa: BLE001
        # 只有「配置类」异常才记录到红点标记；普通 bug/文件错等不点亮红点
        if isinstance(e, ConfigError):
            config_errors.record(e.group, e.field, e.message)
        elif isinstance(e, LLMNotConfigured):
            config_errors.record("llm", "api_key", str(e))
        try:
            ctx = _build_ctx(project_id)
            _emit(ctx, run_id, "", f"流程异常：{e}\n{traceback.format_exc()}", level="error", event="error")
        except Exception:
            pass
        repo.update_run(run_id, status="failed", finished_at=repo.now())
        repo.set_project_status(project_id, "failed")


def _run(project_id: str, run_id: str) -> None:
    ctx = _build_ctx(project_id)
    driver = get_driver(ctx)
    state = _load_state(ctx)

    if review.has_pending(project_id):
        _emit(ctx, run_id, "", "存在未处理的待确认事项，请先在「待确认事项」处理后再继续。", level="warn", event="blocked")
        repo.update_run(run_id, status="review")
        repo.set_project_status(project_id, "review")
        return

    repo.update_run(run_id, status="running")
    repo.set_project_status(project_id, "running")
    _emit(ctx, run_id, "", f"开始执行（类型：{driver.type}，流程：{' → '.join(driver.flow_nodes)}）")

    # ---- 前置阶段 ----
    pre_stages = [
        ("load", "读取资料", lambda: _emit(ctx, run_id, "读取资料", "已加载配置/规范/资源")),
        ("kpoint", "解析考纲/目录", lambda: _emit(ctx, run_id, "知识点数量", f"产出：{driver.kpoint_count(ctx).name}")),
        ("planning", "生成规划", lambda: _stage_planning(ctx, run_id, driver)),
        ("mapping", "知识点匹配", lambda: _stage_mapping(ctx, run_id, driver, state)),
    ]
    if driver_need_mesh(driver):
        pre_stages.append(("mesh", "细目表", lambda: _stage_mesh(ctx, run_id, driver)))
    pre_stages.append(("naming", "确认命名", lambda: driver.confirm_naming(ctx, {})))

    for i, (key, label, fn) in enumerate(pre_stages):
        if key in state["stages"]:
            continue
        if _should_pause(project_id):
            return _do_pause(ctx, run_id, label)
        result = fn()
        # 阶段产生阻塞型待确认 → 暂停（标记本阶段已完成，避免 resume 后重复入队）
        if isinstance(result, dict) and result.get("blocked"):
            state["stages"].append(key)
            _save_state(ctx, state)
            repo.update_run(run_id, status="review", current_node=label)
            repo.set_project_status(project_id, "review")
            _emit(ctx, run_id, label, f"命中待确认（{result.get('rtype')}），流程暂停，等待人工处理。",
                  level="warn", event="review", count=result.get("count", 1))
            return
        state["stages"].append(key)
        _save_state(ctx, state)
        _set_progress(ctx, run_id, label, round(20 + i * 8, 1))

    # ---- 逐卷阶段 ----
    papers = repo.get_papers(project_id)
    total = len(papers) or 1
    for idx, paper in enumerate(papers):
        pno = paper["paper_no"]
        if pno in state["papers_done"]:
            continue
        if _should_pause(project_id):
            return _do_pause(ctx, run_id, "拉题与补题")
        _emit(ctx, run_id, "拉题与补题", f"第{pno}卷：拉题 + 不足AI补题")
        pq, pull_reviews = driver.produce_questions(ctx, pno)
        blocked = _enqueue_reviews(ctx, run_id, "拉题与补题", pull_reviews)

        if driver_need_split(driver):
            _emit(ctx, run_id, "奇偶分卷", f"第{pno}卷：奇偶拆分为教师/学生各2份")
            paths = driver.assemble(ctx, pno, pq)  # 双析驱动内部走 split
        else:
            paths = driver.assemble(ctx, pno, pq)
        repo.update_paper(project_id, pno, docx_paths=[str(p) for p in paths], status="pulled")

        _emit(ctx, run_id, "质检导出", f"第{pno}卷：逐卷质检")
        qc_result, qc_reviews = driver.qc(ctx, pno, pq)
        blocked = _enqueue_reviews(ctx, run_id, "质检导出", qc_reviews) or blocked
        repo.update_paper(project_id, pno,
                          status="qc_passed" if qc_result.passed else "pending_review",
                          qc_report_path=str(qc_result.report_path or ""))

        # 本卷产物已生成并落库后再判断是否暂停，避免恢复时丢失已完成工作
        state["papers_done"].append(pno)
        _save_state(ctx, state)
        _set_progress(ctx, run_id, "质检导出", round(60 + (idx + 1) / total * 40, 1))

        if blocked:
            repo.update_run(run_id, status="review", current_node="待确认")
            repo.set_project_status(project_id, "review")
            _emit(ctx, run_id, "待确认", f"第{pno}卷命中阻塞型待确认（AI补题/质检），流程暂停，等待人工处理。",
                  level="warn", event="review")
            return

    # ---- 完成 ----
    config_errors.clear()  # 正常完成 → 清除运行时配置错误标记
    repo.update_run(run_id, status="done", current_node="完成", progress=100.0, finished_at=repo.now())
    repo.set_project_status(project_id, "done")
    _emit(ctx, run_id, "完成", "全部卷生成完毕。", event="done")

    # 成品归档到本地输出目录（默认 桌面/生成结果）；失败不影响出卷结果
    try:
        from engine import archive
        dest = archive.archive_project(ctx)
        _emit(ctx, run_id, "完成", f"成品已归档到：{dest}")
    except Exception as e:  # noqa: BLE001
        _emit(ctx, run_id, "完成", f"归档到输出目录失败：{e}", level="warn")


def _do_pause(ctx: ProjectContext, run_id: str, node: str) -> None:
    repo.update_run(run_id, status="paused", current_node=node)
    repo.set_project_status(ctx.project_id, "running")
    _emit(ctx, run_id, node, "流程已暂停。", level="warn", event="paused")


def _enqueue_reviews(ctx: ProjectContext, run_id: str, node: str, reviews: list[dict[str, Any]]) -> bool:
    """入队待确认，返回是否包含阻塞型（需暂停流程）。"""
    blocking = False
    for r in reviews:
        review.enqueue(ctx, run_id, node, r["type"], r.get("paper_no"),
                       r.get("confidence", 0.0), r.get("payload", {}))
        if r["type"] in BLOCKING_TYPES:
            blocking = True
        events.publish(ctx.project_id, {"event": "review", "node": node, "type": r["type"],
                                        "paper_no": r.get("paper_no"), "time": repo.now()})
    return blocking


# ---- 阶段封装（返回 dict 表示阻塞）----
def _stage_planning(ctx, run_id, driver):
    path, rows = driver.gen_planning(ctx, ctx.plan_source)
    _emit(ctx, run_id, "生成规划", f"规划表：{path.name}（共 {len(rows)} 卷）")


def _stage_mapping(ctx, run_id, driver, state):
    path, low_conf = driver.gen_mapping(ctx)
    _emit(ctx, run_id, "知识点匹配", f"映射表：{path.name}")
    match_enabled = ctx.ai_options.get("match", True)
    if low_conf and match_enabled:
        run = repo.latest_run(ctx.project_id)
        rid = run["id"] if run else run_id
        review.enqueue(ctx, rid, "知识点匹配", "AI_MATCH", None, 0.0,
                       {"reason": "部分考点未解析出 kpointId（低于信度阈值），需人工确认",
                        "papers": [r.get("paper_no") for r in low_conf]})
        return {"blocked": True, "rtype": "AI_MATCH", "count": len(low_conf)}


def _stage_mesh(ctx, run_id, driver):
    paths = driver.gen_mesh(ctx) or []
    _emit(ctx, run_id, "细目表", f"细目表：{', '.join(p.name for p in paths)}")


def driver_need_mesh(driver) -> bool:
    from engine import registry
    return registry.get(driver.type).need_mesh


def driver_need_split(driver) -> bool:
    from engine import registry
    return registry.get(driver.type).need_split
