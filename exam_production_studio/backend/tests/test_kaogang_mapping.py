import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from engine.steps import mapping as step_mapping  # noqa: E402
from engine.steps.planning import build_kaogang_papers  # noqa: E402
from shared.planning import kaogang as kg  # noqa: E402


def _papers():
    kp = [
        {"course": "电工", "theme": "直流", "point_name": "欧姆定律", "knowledge": "欧姆定律"},
        {"course": "电工", "theme": "直流", "point_name": "基尔霍夫", "knowledge": "基尔霍夫"},
        {"course": "电工", "theme": "交流", "point_name": "正弦量", "knowledge": "正弦量"},
    ]
    kg.arrange_volume_numbers(kp, comprehensive_per_course=3)
    return build_kaogang_papers(kp, {"easy": 80, "medium": 10, "hard": 10})


# 假知识点解析：考点名 → 固定 id，方便验证聚合并集
_FAKE = {"欧姆定律": ([101], "AI匹配"), "基尔霍夫": ([102], "AI匹配"), "正弦量": ([103], "AI匹配")}


def _fake_resolve(text, course, nodes=None):
    for name, res in _FAKE.items():
        if name in text:
            return res
    return [], "AI生成"


class KaogangMappingPersistTest(unittest.TestCase):
    def test_persists_kpoint_ids_and_aggregates_union(self):
        papers = _papers()
        tmp = Path(tempfile.mkdtemp())
        ctx = SimpleNamespace(project_id="p1", province="省", exam_category="考类",
                              course="电工", dir=lambda name: tmp)
        persisted = {}

        def fake_update(project_id, paper_no, **fields):
            persisted[paper_no] = fields

        with patch("shared.xueke_api.kpoint_resolver.resolve_layered", side_effect=_fake_resolve), \
                patch("shared.planning.kaogang_mapping.render_mapping", return_value=tmp / "m.xlsx"), \
                patch("engine.archive.export_planning_artifact", return_value=None), \
                patch.object(step_mapping.repo, "update_paper", side_effect=fake_update):
            _path, low_conf = step_mapping._gen_mapping_kaogang(ctx, papers)

        # 每张卷都落库 kpoint_ids
        self.assertEqual(len(persisted), len(papers))

        by_no = {p["paper_no"]: p for p in papers}
        # 考点卷：单值
        kp_papers = [p for p in papers if p["paper_subtype"] == "考点训练卷"]
        for p in kp_papers:
            ids = persisted[p["paper_no"]]["kpoint_ids"]
            self.assertEqual(len(ids), 1)

        # 专题卷「直流」：聚合欧姆定律+基尔霍夫 = {101,102}
        zhiliu = [p for p in papers if p["paper_subtype"] == "专题训练卷" and p["theme"] == "直流"][0]
        self.assertEqual(set(persisted[zhiliu["paper_no"]]["kpoint_ids"]), {"101", "102"})

        # 课程综合卷（3 份）：并集去重 = {101,102,103}
        comp = [p for p in papers if p["paper_subtype"] == "课程综合卷"]
        self.assertEqual(len(comp), 3)
        for p in comp:
            self.assertEqual(set(persisted[p["paper_no"]]["kpoint_ids"]), {"101", "102", "103"})

        self.assertEqual(low_conf, [])

    def test_aggregate_independent_of_filtered_kpoints(self):
        """底层考点卷被卷号范围筛掉后，聚合卷仍能凭 agg_texts 解析出题源。"""
        papers = _papers()
        # 模拟范围筛选：只保留专题卷 + 综合卷（去掉全部考点卷）
        aggs = [p for p in papers if p["meta"].get("is_aggregate")]
        tmp = Path(tempfile.mkdtemp())
        ctx = SimpleNamespace(project_id="p1", province="省", exam_category="考类",
                              course="电工", dir=lambda name: tmp)
        persisted = {}

        with patch("shared.xueke_api.kpoint_resolver.resolve_layered", side_effect=_fake_resolve), \
                patch("shared.planning.kaogang_mapping.render_mapping", return_value=tmp / "m.xlsx"), \
                patch("engine.archive.export_planning_artifact", return_value=None), \
                patch.object(step_mapping.repo, "update_paper",
                             side_effect=lambda pid, pno, **f: persisted.__setitem__(pno, f)):
            step_mapping._gen_mapping_kaogang(ctx, aggs)

        zhiliu = [p for p in aggs if p["paper_subtype"] == "专题训练卷" and p["theme"] == "直流"][0]
        self.assertEqual(set(persisted[zhiliu["paper_no"]]["kpoint_ids"]), {"101", "102"})


if __name__ == "__main__":
    unittest.main()
