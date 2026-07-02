import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from engine.context import parse_range  # noqa: E402
from engine.steps import planning as step_planning  # noqa: E402


def _raw_kp_rows():
    return [
        {"course": "电工", "theme": "直流", "point_name": "欧姆定律", "knowledge": "欧姆定律"},
        {"course": "电工", "theme": "直流", "point_name": "基尔霍夫", "knowledge": "基尔霍夫"},
        {"course": "电工", "theme": "交流", "point_name": "正弦量", "knowledge": "正弦量"},
    ]


def _ctx(paper_range):
    tmp = Path(tempfile.mkdtemp())
    return SimpleNamespace(
        project_id="p1", paper_type="kaogang_100", province="省", exam_category="考类",
        course="电工", paper_range=paper_range,
        selected_papers=lambda total=None: parse_range(paper_range, total),
        dir=lambda name: tmp,
    )


class GenKaogangRangeTest(unittest.TestCase):
    def _run(self, paper_range):
        captured = {}
        with patch.object(step_planning, "_find_uploaded_plan", return_value=Path("dummy.xlsx")), \
                patch.object(step_planning.kg, "parse_10col", return_value=_raw_kp_rows()), \
                patch.object(step_planning.kg, "render_10col", return_value=Path("out.xlsx")), \
                patch.object(step_planning.repo, "replace_papers",
                             side_effect=lambda pid, rows: captured.__setitem__("rows", rows)):
            _path, rows = step_planning._gen_kaogang(_ctx(paper_range), "upload",
                                                     {"easy": 80, "medium": 10, "hard": 10})
        self.assertEqual(rows, captured["rows"])
        return rows

    def test_all_yields_full_global_count(self):
        rows = self._run("all")
        # 3 考点 + 2 专题(直流/交流) + 1 课程*3 综合 = 8
        self.assertEqual(len(rows), 8)
        nos = sorted(r["paper_no"] for r in rows)
        self.assertEqual(nos, list(range(1, 9)))

    def test_range_filters_by_global_number(self):
        # 只要 1-3（三张考点卷）
        rows = self._run("1-3")
        self.assertEqual(sorted(r["paper_no"] for r in rows), [1, 2, 3])
        self.assertTrue(all(r["paper_subtype"] == "考点训练卷" for r in rows))

    def test_range_can_select_aggregate_volumes(self):
        # 4-5 = 两张专题卷；6-8 = 三张综合卷
        rows = self._run("4,5,6,7,8")
        subs = {r["paper_no"]: r["paper_subtype"] for r in rows}
        self.assertEqual(subs[4], "专题训练卷")
        self.assertEqual(subs[5], "专题训练卷")
        self.assertEqual(subs[6], "课程综合卷")
        self.assertEqual(subs[8], "课程综合卷")


if __name__ == "__main__":
    unittest.main()
