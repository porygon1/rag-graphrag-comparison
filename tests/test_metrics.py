"""Check the thesis example and the scientific nDCG@5 contract."""

import json
import unittest
from pathlib import Path

from rag_comparison.metrics import (
    dcg_for_gains,
    evidence_recall,
    ndcg_at_k,
    partial_overlap,
    score_question,
)

THESIS_QRELS = {"A": 2, "B": 0, "C": 1, "D": 2, "E": 0, "F": 1}


class NdcgTests(unittest.TestCase):
    def test_appendix_a3(self):
        """Table 21 includes positive unit F outside the retrieved top five."""
        self.assertAlmostEqual(dcg_for_gains([2, 0, 1, 2, 0]), 3.3613531161467862)
        self.assertAlmostEqual(dcg_for_gains([2, 2, 1, 1, 0]), 4.192536065216308)
        self.assertEqual(ndcg_at_k(["A", "B", "C", "D", "E"], THESIS_QRELS), 0.801747)

    def test_perfect_ranking(self):
        self.assertEqual(ndcg_at_k(["A", "D", "C", "F", "B"], THESIS_QRELS), 1.0)

    def test_duplicate_keeps_its_rank_and_receives_no_second_gain(self):
        # A occupies ranks 1 and 2; gains at ranks 3–5 keep their discounts.
        self.assertEqual(ndcg_at_k(["A", "A", "D", "C", "F"], THESIS_QRELS), 0.910554)

    def test_judged_zero_is_valid_and_unjudged_is_missing(self):
        qrels = THESIS_QRELS | {"G": 0, "H": 0, "I": 0}
        self.assertEqual(ndcg_at_k(["B", "E", "G", "H", "I"], qrels), 0.0)
        self.assertIsNone(ndcg_at_k(["B", "E", "G", "H", "unjudged"], qrels))

    def test_missing_rank_or_projection_is_invalid(self):
        rankings = (["A", "B", "C", "D"], ["A", "B", None, "D", "E"])
        for ranking in rankings:
            with self.subTest(ranking=ranking):
                self.assertIsNone(ndcg_at_k(ranking, THESIS_QRELS))

    def test_no_positive_ideal_gain_is_invalid(self):
        qrels = {unit: 0 for unit in ["A", "B", "C", "D", "E"]}
        self.assertIsNone(ndcg_at_k(["A", "B", "C", "D", "E"], qrels))

    def test_invalid_grade_in_shared_pool_is_rejected(self):
        for grade in [-1, 3]:
            with self.subTest(grade=grade), self.assertRaises(ValueError):
                ndcg_at_k(["A", "B", "C", "D", "E"], THESIS_QRELS | {"F": grade})

    def test_units_beyond_top_five_are_not_scored(self):
        for extra_unit in [None, "unjudged"]:
            with self.subTest(extra_unit=extra_unit):
                self.assertEqual(
                    ndcg_at_k(["A", "B", "C", "D", "E", extra_unit], THESIS_QRELS),
                    0.801747,
                )


class RetrievalStateTests(unittest.TestCase):
    def test_missing_projection_and_judgement_keep_the_top_five_denominator(self):
        result = score_question(
            ["A", None, "unjudged", "B"], THESIS_QRELS, [{"A", "D"}]
        )
        self.assertEqual(result["judged_at_k"], 0.4)
        self.assertEqual(result["missing_position_count"], 1)
        self.assertEqual(result["projection_failure_count"], 1)
        self.assertEqual(result["unjudged_unit_ids"], ["unjudged"])
        self.assertEqual(
            result["metric_validity_status"],
            "missing_ranked_positions+projection_failures_present+unjudged_positions_present",
        )
        self.assertEqual(result["dcg"], 2.0)
        self.assertIsNone(ndcg_at_k(["A", None, "unjudged", "B"], THESIS_QRELS))

    def test_duplicates_are_judged_but_have_no_second_gain(self):
        result = score_question(["A", "A", "D", "C", "F"], THESIS_QRELS, [{"A", "D"}])
        self.assertEqual(result["judged_at_k"], 1.0)
        self.assertEqual(result["metric_validity_status"], "fully_judged")
        self.assertEqual(result["ndcg_at_k"], 0.910554)
        self.assertEqual(result["evidence_recall_at_k"], 1.0)

    def test_partial_overlap_is_not_binary_evidence_recall(self):
        sets = [{"A", "D"}, {"C", "F"}]
        self.assertEqual(evidence_recall(sets, {"A", "C"}), 0.0)
        self.assertEqual(partial_overlap(sets, {"A", "C"}), 0.5)
        self.assertEqual(evidence_recall(sets, {"C", "F"}), 1.0)
        self.assertIsNone(evidence_recall([], {"A"}))
        self.assertIsNone(partial_overlap([], {"A"}))
        with self.assertRaises(ValueError):
            evidence_recall([set()], {"A"})


class AppendixFixtureTests(unittest.TestCase):
    def test_reference_sets_match_the_cited_appendices(self):
        path = (
            Path(__file__).parents[1]
            / "examples/evaluation/thesis_metric_examples.jsonl"
        )
        cases = {
            row["case_id"]: row
            for row in map(json.loads, path.read_text(encoding="utf-8").splitlines())
        }
        expected = {
            "appendix_A3": (["A", "B", "C", "D", "E"], [], 0.801747, None),
            "appendix_G_graph": (["A", "D", "B", "E", "C"], [["A"]], 0.870, 1.0),
            "appendix_I_classical": (["A", "C", "D", "B", "E"], [["A"]], 0.866, 1.0),
        }
        for name, (ranking, required, score, recall) in expected.items():
            with self.subTest(case=name):
                case = cases[name]
                self.assertEqual(case["ranked_units"], ranking)
                self.assertEqual(case["qrels"], THESIS_QRELS)
                self.assertEqual(case["minimal_evidence_sets"], required)
                self.assertEqual(
                    round(
                        ndcg_at_k(ranking, case["qrels"]),
                        6 if name == "appendix_A3" else 3,
                    ),
                    score,
                )
                self.assertEqual(
                    evidence_recall([set(s) for s in required], set(ranking)), recall
                )


if __name__ == "__main__":
    unittest.main()
