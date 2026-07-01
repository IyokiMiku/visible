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
