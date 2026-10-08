"""Check paired populations, ordinal effects and descriptive uncertainty."""

import unittest

from rag_comparison.evaluation import (
    connected_components,
    outcome_inputs,
    paired_intervention_change,
    paired_resampling,
    paired_system_gap_shift,
    surface_coverage,
)


class OutcomeSelectionTests(unittest.TestCase):
    @staticmethod
    def row(condition, question, status, value, metric="faithfulness"):
        return {
            "condition_id": condition,
            "question_id": question,
            "metric": metric,
            "status": status,
            "value": value,
        }

    def test_missing_and_invalid_diagnostic_values_stay_missing(self):
        rows = [
            self.row("C0", "Q1", "valid", 0),
            self.row("C0", "Q2", "missing_output", None),
            self.row("G0", "Q1", "invalid_retrieval", 0.8),
        ]
        values, non_applicable = outcome_inputs(
            rows, ["C0", "G0"], "faithfulness", ["Q1", "Q2"]
        )
        self.assertEqual(
            values, {"C0": {"Q1": 0, "Q2": None}, "G0": {"Q1": None, "Q2": None}}
        )
        self.assertEqual(non_applicable, [])

    def test_only_metric_specific_na_reduces_applicability(self):
        rows = [
            self.row("C0", "Q1", "not_applicable_no_answer", None),
            self.row("G0", "Q2", "citation_not_required", None, "citation_correctness"),
            self.row("G0", "Q3", "citation_not_required", None),
        ]
        _, faith_na = outcome_inputs(
            rows, ["C0", "G0"], "faithfulness", ["Q1", "Q2", "Q3"]
        )
        _, citation_na = outcome_inputs(
            rows, ["C0", "G0"], "citation_correctness", ["Q1", "Q2", "Q3"]
        )
        self.assertEqual(faith_na, ["Q1"])
        self.assertEqual(citation_na, ["Q2"])

    def test_subset_and_repeated_condition_request_preserve_only_selected_ids(self):
        rows = [
            self.row("C0", "Q1", "valid", 1),
            self.row("C0", "Q2", "not_applicable_no_answer", None),
            self.row("G0", "Q1", "not_applicable_no_answer", None),
            self.row("C0", "Q1", "valid", 3, "answer_correctness"),
        ]
        values, na = outcome_inputs(rows, ["C0", "C0"], "faithfulness", ["Q1"])
        self.assertEqual(values, {"C0": {"Q1": 1}})
        self.assertEqual(na, [])

    def test_duplicate_selected_records_are_rejected(self):
        row = self.row("C0", "Q1", "valid", 1)
        with self.assertRaises(ValueError):
            outcome_inputs([row, dict(row)], ["C0"], "faithfulness", ["Q1"])
        values, _ = outcome_inputs([row, dict(row)], ["G0"], "faithfulness", ["Q1"])
        self.assertEqual(values, {"G0": {"Q1": None}})

    def test_contradictory_applicable_or_na_values_are_rejected(self):
        for status, value in [("valid", None), ("not_applicable_no_answer", 0)]:
            with self.subTest(status=status), self.assertRaises(ValueError):
                outcome_inputs(
                    [self.row("C0", "Q1", status, value)],
                    ["C0"],
                    "faithfulness",
                    ["Q1"],
                )


class PairedOutcomeTests(unittest.TestCase):
    def test_missing_reduces_pairs_and_only_na_reduces_applicability(self):
        ids = ["Q1", "Q2", "Q3", "Q4", "Q5"]
        result = paired_intervention_change(
            {"Q1": 0.2, "Q2": 0.5, "Q3": 0.0, "Q4": None, "Q5": None},
            {"Q1": 0.3, "Q2": 0.4, "Q3": None, "Q4": 0.7, "Q5": None},
            question_ids=ids,
            scale="continuous",
            cluster_by_question={qid: qid for qid in ids},
            non_applicable_question_ids=["Q5"],
        )
        self.assertEqual((result["N_total"], result["N_app"], result["k"]), (5, 4, 2))
        self.assertEqual(result["paired_question_ids"], ["Q1", "Q2"])
        self.assertEqual(
            result["missing_states_by_question"],
            {"Q3": ["variant"], "Q4": ["reference"]},
        )
        self.assertEqual(
            result["change_counts"], {"positive": 1, "zero": 0, "negative": 1}
        )
        self.assertIsNone(result["standard"])

    def test_ordinal_counts_use_signs_and_keep_ties_in_the_denominator(self):
        ids = [f"Q{i}" for i in range(20)]
        reference = {qid: [0, 2, 3, 1][i % 4] for i, qid in enumerate(ids)}
        variant = {qid: [3, 2, 2, 2][i % 4] for i, qid in enumerate(ids)}
        result = paired_intervention_change(
            reference,
            variant,
            question_ids=ids,
            scale="ordinal",
            cluster_by_question={qid: qid for qid in ids},
            iterations=40,
        )
        self.assertEqual(
            result["change_counts"], {"positive": 10, "zero": 5, "negative": 5}
        )
        self.assertEqual(result["standard"]["estimate"], 0.25)
        self.assertNotIn("permutation_p_two_sided", result["standard"])

    def test_four_states_share_the_same_complete_population(self):
        ids = [f"Q{i}" for i in range(30)]
        states = [{qid: value for qid in ids} for value in (0.1, 0.3, 0.4, 0.8)]
        for position, state in enumerate(states):
            state.pop(ids[position])
        result = paired_system_gap_shift(
            *states,
            question_ids=ids,
            scale="continuous",
            cluster_by_question={qid: qid for qid in ids},
            non_applicable_question_ids=[ids[4]],
            iterations=40,
        )
        self.assertEqual(
            (result["N_total"], result["N_app"], result["k_gap"]), (30, 29, 25)
        )
        self.assertEqual(result["paired_question_ids"], ids[5:])
        self.assertTrue(
            all(
                list(values) == ids[5:] for values in result["paired_outcomes"].values()
            )
        )
        self.assertAlmostEqual(result["standard"]["estimate"], 0.2)

    def test_ordinal_gap_is_the_shift_between_architecture_signs(self):
        ids = [f"Q{i}" for i in range(20)]
        c0, g0, gv = ({qid: grade for qid in ids} for grade in (1, 0, 3))
        result = paired_system_gap_shift(
            c0,
            g0,
            c0,
            gv,
            question_ids=ids,
            scale="ordinal",
            cluster_by_question={qid: qid for qid in ids},
            iterations=40,
        )
        self.assertEqual(set(result["question_changes"].values()), {2.0})
        self.assertEqual(result["standard"]["estimate"], 2.0)

    def test_sixteen_robustness_cases_remain_count_only(self):
        ids = [f"U{i}" for i in range(16)]
        reference = {qid: 0 for qid in ids}
        variant = {qid: 1 for qid in ids}
        result = paired_intervention_change(
            reference,
            variant,
            question_ids=ids,
            scale="binary",
            cluster_by_question={qid: qid for qid in ids},
        )
        self.assertEqual(result["aggregation_status"], "count_only_k_below_20")
        self.assertEqual(result["change_counts"]["positive"], 16)
        self.assertIsNone(result["standard"])
        self.assertIsNone(result["cluster"])

    def test_invalid_scale_values_and_duplicate_population_are_rejected(self):
        for scale, value in [
            ("binary", 0.5),
            ("ordinal", 4),
            ("continuous", float("nan")),
            ("binary", True),
        ]:
            with self.subTest(scale=scale, value=value), self.assertRaises(ValueError):
                paired_intervention_change(
                    {"Q1": 0},
                    {"Q1": value},
                    question_ids=["Q1"],
                    scale=scale,
                    cluster_by_question={"Q1": "Q1"},
                )
        with self.assertRaises(ValueError):
            paired_intervention_change(
                {"Q1": 0},
                {"Q1": 1},
                question_ids=["Q1", "Q1"],
                scale="binary",
                cluster_by_question={"Q1": "Q1"},
            )


class CoverageAndUncertaintyTests(unittest.TestCase):
    def test_coverage_keeps_total_applicable_and_valid_counts(self):
        result = surface_coverage(5, 4, 2, {"missing_human_review": 2})
        self.assertEqual(
            (result["N_total"], result["N_app"], result["k"], result["missing"]),
            (5, 4, 2, 2),
        )
        self.assertEqual(result["coverage"], 0.5)
        self.assertFalse(result["claim_coverage_complete"])
        self.assertIsNone(surface_coverage(5, 0, 0)["coverage"])
        with self.assertRaises(ValueError):
            surface_coverage(5, 4, 5)

    def test_evidence_components_are_transitive_with_isolated_questions(self):
        result = connected_components(
            {"Q3": {"E2"}, "Q2": {"E1", "E2"}, "Q1": {"E1"}, "Q4": set()}
        )
        self.assertEqual(result, {"Q1": "Q1", "Q2": "Q1", "Q3": "Q1", "Q4": "Q4"})

    def test_cluster_bootstrap_flattens_unequal_groups_and_is_seeded(self):
        first = paired_resampling(
            [1, 0, -1], cluster_ids=["A", "A", "B"], iterations=200, seed=17
        )
        second = paired_resampling(
            [1, 0, -1], cluster_ids=["A", "A", "B"], iterations=200, seed=17
        )
        self.assertEqual(first, second)
        self.assertEqual(first["estimate"], 0.0)
        self.assertEqual((first["ci_lower"], first["ci_upper"]), (-1.0, 0.5))
        self.assertEqual((first["k"], first["resampling_units"]), (3, 2))
        self.assertEqual(first["resampling_unit"], "inference_component")
        with self.assertRaises(ValueError):
            paired_resampling([1, 0], cluster_ids=["A"])
        with self.assertRaises(ValueError):
            paired_resampling([float("inf")])


if __name__ == "__main__":
    unittest.main()
