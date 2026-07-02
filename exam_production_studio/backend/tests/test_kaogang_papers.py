import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from shared.planning import kaogang as kg  # noqa: E402
from engine.steps.planning import build_kaogang_papers  # noqa: E402


def _sample_kp_rows():
    """构造 2 门课程、若干专题的考点行（未编号，待 arrange）。"""
    rows = []
    data = {
        "电工基础": {"直流电路": ["欧姆定律", "基尔霍夫定律"],
                     "交流电路": ["正弦量", "阻抗", "谐振"]},
        "电子技术": {"半导体": ["PN结", "二极管"],
                     "放大电路": ["共射放大"]},
    }
    for course, themes in data.items():
        for theme, points in themes.items():
            for p in points:
                rows.append({"course": course, "theme": theme,
                             "point_name": p, "knowledge": f"理解{p}的原理"})
    return rows


class KaogangPapersTest(unittest.TestCase):
    def setUp(self):
        self.kp = _sample_kp_rows()
        self.summary = kg.arrange_volume_numbers(self.kp, comprehensive_per_course=3)
        self.diff = {"easy": 80, "medium": 10, "hard": 10}

    def test_global_total_covers_three_subtypes(self):
        kp_n = len(self.kp)                       # 考点卷数
        themes = {(r["course"], r["theme"]) for r in self.kp}
        courses = {r["course"] for r in self.kp}
        expected_total = kp_n + len(themes) + len(courses) * 3
        self.assertEqual(self.summary["total_volumes"], expected_total)
        self.assertEqual(self.summary["kpoint_count"], kp_n)

    def test_build_papers_count_and_numbering(self):
        papers = build_kaogang_papers(self.kp, self.diff)
        total = self.summary["total_volumes"]
        # 数量＝全局卷数
        self.assertEqual(len(papers), total)
        # 卷号 1..total 连续无跳号无重复
        nos = sorted(p["paper_no"] for p in papers)
        self.assertEqual(nos, list(range(1, total + 1)))
        # 三类卷都存在
        subtypes = {p["paper_subtype"] for p in papers}
        self.assertSetEqual(subtypes, {"考点训练卷", "专题训练卷", "课程综合卷"})
        # 各类计数
        by = {}
        for p in papers:
            by[p["paper_subtype"]] = by.get(p["paper_subtype"], 0) + 1
        themes = {(r["course"], r["theme"]) for r in self.kp}
        courses = {r["course"] for r in self.kp}
        self.assertEqual(by["考点训练卷"], len(self.kp))
        self.assertEqual(by["专题训练卷"], len(themes))
        self.assertEqual(by["课程综合卷"], len(courses) * 3)

    def test_aggregate_papers_carry_source_texts(self):
        papers = build_kaogang_papers(self.kp, self.diff)
        aggs = [p for p in papers if (p["meta"]).get("is_aggregate")]
        self.assertTrue(aggs)
        for p in aggs:
            self.assertTrue(p["meta"].get("agg_texts"))
            # 每个聚合文本含 knowledge，供映射独立解析
            self.assertTrue(all("knowledge" in t for t in p["meta"]["agg_texts"]))

    def test_theme_paper_aggregates_its_kpoints(self):
        papers = build_kaogang_papers(self.kp, self.diff)
        # 「直流电路」专题含 2 个考点
        theme_papers = [p for p in papers
                        if p["paper_subtype"] == "专题训练卷" and p["theme"] == "直流电路"]
        self.assertEqual(len(theme_papers), 1)
        self.assertEqual(len(theme_papers[0]["meta"]["agg_texts"]), 2)

    def test_course_comprehensive_shares_all_course_points(self):
        papers = build_kaogang_papers(self.kp, self.diff)
        comp = [p for p in papers
                if p["paper_subtype"] == "课程综合卷" and p["module"] == "电工基础"]
        self.assertEqual(len(comp), 3)  # comprehensive_per_course
        course_points = [r for r in self.kp if r["course"] == "电工基础"]
        for p in comp:
            self.assertEqual(len(p["meta"]["agg_texts"]), len(course_points))


if __name__ == "__main__":
    unittest.main()
