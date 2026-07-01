# Flow Rerun Status Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a user triggers flow rerun, immediately reset backend run progress/current node to the rerun range and add a visible separator line in the flow log.

**Architecture:** Implement the behavior in `backend/engine/runner.py`, because progress, current node, and logs should be authoritative backend state. Add focused unit tests around `runner.rerun()` using `unittest` and `unittest.mock`, avoiding database and thread execution by mocking repository, event, context, and `start()` boundaries.

**Tech Stack:** Python 3, FastAPI backend modules, standard-library `unittest`, `unittest.mock`, existing `engine.runner` / `engine.repo` / `engine.events` services.

---

## File Structure

- Modify: `exam_production_studio/backend/engine/runner.py`
  - Add rerun progress/display mappings.
  - Update `rerun()` to reset current run state before restarting.
  - Add a separator log through existing `_emit()`.
  - Publish a progress event through existing `_set_progress()` behavior.
- Create: `exam_production_studio/backend/tests/test_runner_rerun.py`
  - Unit-test `runner.rerun()` without starting a real backend thread or touching SQLite.
  - Verify progress reset, current node reset, separator log, state update, and restart call.

## Task 1: Add Rerun Status Sync Test

**Files:**
- Create: `exam_production_studio/backend/tests/test_runner_rerun.py`

- [ ] **Step 1: Create the failing unit test**

Create `exam_production_studio/backend/tests/test_runner_rerun.py` with this content:

```python
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from engine import runner  # noqa: E402


class FlowRerunStatusSyncTest(unittest.TestCase):
    def test_rerun_resets_run_progress_and_writes_separator_log(self):
        ctx = SimpleNamespace(project_id="proj_1")
        state = {"stages": ["planning", "mapping", "pull"], "papers_done": [1, 2]}
        saved_states = []
        run_updates = []
        emitted = []
        progress_events = []

        def fake_save_state(_ctx, next_state):
            saved_states.append({
                "stages": list(next_state["stages"]),
                "papers_done": list(next_state["papers_done"]),
            })

        def fake_update_run(run_id, **fields):
            run_updates.append((run_id, fields))

        def fake_emit(_ctx, run_id, node, message, level="info", event="log", **extra):
            emitted.append({
                "run_id": run_id,
                "node": node,
                "message": message,
                "level": level,
                "event": event,
                "extra": extra,
            })

        def fake_publish(project_id, payload):
            progress_events.append((project_id, payload))

        with patch.object(runner, "_build_ctx", return_value=ctx), \
             patch.object(runner, "_load_state", return_value=state), \
             patch.object(runner, "_save_state", side_effect=fake_save_state), \
             patch.object(runner.repo, "latest_run", return_value={"id": "run_1"}), \
             patch.object(runner.repo, "update_run", side_effect=fake_update_run), \
             patch.object(runner.repo, "now", return_value="2026-07-01T12:00:00"), \
             patch.object(runner.events, "publish", side_effect=fake_publish), \
             patch.object(runner, "_emit", side_effect=fake_emit), \
             patch.object(runner, "start", return_value="run_1") as start_mock:
            result = runner.rerun("proj_1", "拉题与补题")

        self.assertEqual(result, "run_1")
        self.assertEqual(saved_states, [{"stages": ["planning", "mapping"], "papers_done": []}])
        self.assertIn(("run_1", {"status": "running", "current_node": "拉题与补题", "progress": 60.0}), run_updates)
        self.assertEqual(emitted, [{
            "run_id": "run_1",
            "node": "拉题与补题",
            "message": "────────── 回退重跑：从「拉题与补题」重新开始 ──────────",
            "level": "warn",
            "event": "log",
            "extra": {},
        }])
        self.assertEqual(progress_events, [("proj_1", {
            "event": "progress",
            "node": "拉题与补题",
            "progress": 60.0,
            "time": "2026-07-01T12:00:00",
        })])
        start_mock.assert_called_once_with("proj_1")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and confirm RED**

Run:

```bash
cd /c/Users/Administrator/Documents/新建文件夹/visible/exam_production_studio
.venv/Scripts/python -m unittest backend.tests.test_runner_rerun -v
```

Expected: FAIL. The failure should show that `repo.latest_run()` / `repo.update_run()` / separator logging / progress publish were not called by `runner.rerun()` yet.

## Task 2: Implement Rerun Status Sync

**Files:**
- Modify: `exam_production_studio/backend/engine/runner.py:85-97`
- Test: `exam_production_studio/backend/tests/test_runner_rerun.py`

- [ ] **Step 1: Add rerun label/progress mappings near `_NODE_KEY`**

In `runner.py`, after `_NODE_KEY`, add:

```python
_RERUN_NODE_LABEL = {
    "load": "读取资料",
    "kpoint": "解析考纲/目录",
    "planning": "生成规划",
    "mapping": "知识点匹配",
    "mesh": "细目表",
    "naming": "确认命名",
    "pull": "拉题与补题",
    "split": "奇偶分卷",
    "assemble": "组卷生成",
    "qc": "质检导出",
}

_RERUN_PROGRESS = {
    "load": 0.0,
    "kpoint": 0.0,
    "planning": 20.0,
    "mapping": 28.0,
    "mesh": 36.0,
    "naming": 44.0,
    "pull": 60.0,
    "split": 60.0,
    "assemble": 60.0,
    "qc": 60.0,
}
```

- [ ] **Step 2: Update `rerun()` to reset run display state and write separator**

Replace `rerun()` with:

```python
def rerun(project_id: str, node: str, paper_no: int | None = None) -> str:
    ctx = _build_ctx(project_id)
    state = _load_state(ctx)
    node_key = _NODE_KEY.get(node, node)
    node_label = _RERUN_NODE_LABEL.get(node_key, node)
    progress = _RERUN_PROGRESS.get(node_key, 0.0)

    if node_key in state["stages"]:
        state["stages"].remove(node_key)
    if paper_no is not None and paper_no in state["papers_done"]:
        state["papers_done"].remove(paper_no)
    if node_key in ("pull", "assemble", "qc", "split") and paper_no is None:
        state["papers_done"] = []
    _save_state(ctx, state)

    run = repo.latest_run(project_id)
    run_id = run["id"] if run else repo.create_run(project_id)
    repo.update_run(run_id, status="running", current_node=node_label, progress=progress)
    _emit(ctx, run_id, node_label, f"────────── 回退重跑：从「{node_label}」重新开始 ──────────", level="warn")
    events.publish(ctx.project_id, {"event": "progress", "node": node_label, "progress": progress,
                                    "time": repo.now()})
    return start(project_id)
```

- [ ] **Step 3: Run the unit test and confirm GREEN**

Run:

```bash
cd /c/Users/Administrator/Documents/新建文件夹/visible/exam_production_studio
.venv/Scripts/python -m unittest backend.tests.test_runner_rerun -v
```

Expected: PASS.

- [ ] **Step 4: Run frontend build to ensure the flow page still builds**

Run:

```bash
cd /c/Users/Administrator/Documents/新建文件夹/visible/exam_production_studio/frontend
npm run build
```

Expected: PASS. Existing Vite chunk-size warnings are acceptable.

- [ ] **Step 5: Commit only relevant files**

Run:

```bash
git -C /c/Users/Administrator/Documents/新建文件夹/visible add exam_production_studio/backend/engine/runner.py exam_production_studio/backend/tests/test_runner_rerun.py
git -C /c/Users/Administrator/Documents/新建文件夹/visible commit -m "feat: sync rerun progress state"
```

Expected: commit contains only `runner.py` and `test_runner_rerun.py`.

## Self-Review

- Spec coverage: Task 1 proves the desired behavior fails first. Task 2 implements the backend source of truth for progress, current node, separator log, progress event, and restart call.
- Placeholder scan: No placeholders or deferred steps remain.
- Type consistency: Test patches existing `runner.repo`, `runner.events`, `_emit`, `_load_state`, `_save_state`, and `start`; implementation uses the same names.
