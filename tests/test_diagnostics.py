"""Check graph sampling, diagnostic validity and nominal GU transitions."""

import copy
import hashlib
import json
from pathlib import Path
import unittest

from rag_comparison.diagnostics import (
    error_summary,
    genuine_user_counts,
    genuine_user_transitions,
    graph_audit_summary,
    question_property_memberships,
    stratified_graph_sample,
)


class GraphSampleTests(unittest.TestCase):
    def test_strata_allocation_and_stable_selection(self):
        records = [
            {"stable_id": f"{label}-{index}", "stratum": label}
            for label, size in [("A", 30), ("B", 10), ("C", 1)]
            for index in range(size)
        ]
        before = copy.deepcopy(records)
        selected = stratified_graph_sample(records, "evaluation-example", "entities")
        reversed_input = stratified_graph_sample(
            list(reversed(records)), "evaluation-example", "entities"
        )
        self.assertEqual(selected, reversed_input)
        self.assertEqual(records, before)
        self.assertEqual(len(selected), 20)
        self.assertEqual(len({row["stable_id"] for row in selected}), 20)
        self.assertEqual(
            {row["audit_stratum"]: row["audit_stratum_allocation"] for row in selected},
            {"A": 14, "B": 5, "C": 1},
        )

    def test_small_population_uses_all_records(self):
        records = [
            {"stable_id": str(index), "stratum": "relationships"} for index in range(3)
        ]
        selected = stratified_graph_sample(
            records, "evaluation-example", "relationships"
        )
        self.assertEqual({row["stable_id"] for row in selected}, {"0", "1", "2"})
        self.assertEqual(
            stratified_graph_sample([], "evaluation-example", "relationships"), []
        )

    def test_entity_coverage_preserves_observed_raw_labels(self):
        records = [
            {"stable_id": f"entity-{label}-{index}", "stratum": f"raw-type-{label}"}
            for label in range(33)
            for index in range(2)
        ]
        selected = stratified_graph_sample(
            records, "evaluation-example", "entities", entity_type_coverage=True
        )
        self.assertEqual(len(selected), 33)
        self.assertEqual(len({row["stratum"] for row in selected}), 33)
        self.assertTrue(all(row["audit_stratum_allocation"] == 1 for row in selected))
        case_labels = [
            {"stable_id": "first", "stratum": "role"},
            {"stable_id": "second", "stratum": "Role"},
        ]
        self.assertEqual(
            {
                row["audit_stratum"]
                for row in stratified_graph_sample(case_labels, "e", "entities")
            },
            {"role", "Role"},
        )

    def test_duplicate_identity_is_rejected(self):
        records = [{"stable_id": "one", "stratum": "A"}] * 2
        with self.assertRaises(ValueError):
            stratified_graph_sample(records, "evaluation-example", "entities")


class CompactGraphSampleTests(unittest.TestCase):
    def test_bound_prefix_selects_the_same_ids_order_and_allocations(self):
        records = [
            {"stable_id": f"{label}-{index}", "stratum": label}
            for label, size in [("A", 30), ("B", 10), ("C", 1)]
            for index in range(size)
        ]
        full = stratified_graph_sample(records, "evaluation-example", "entities")
        compact = stratified_graph_sample(
            [
                {
                    key: value
                    for key, value in row.items()
                    if key in ("stable_id", "stratum")
                }
                for row in full
            ],
            "evaluation-example",
            "entities",
            stratum_sizes={"A": 30, "B": 10, "C": 1},
        )
        self.assertEqual(full, compact)

    def test_larger_valid_hash_prefix_and_extended_coverage_match_full_sample(self):
        records = [
            {"stable_id": f"raw-{label}-{index}", "stratum": f"type-{label}"}
            for label in range(33)
            for index in range(3)
        ]
        sizes = {f"type-{label}": 3 for label in range(33)}
        prefixes = []
        for label in sizes:
            group = [row for row in records if row["stratum"] == label]
            group.sort(
                key=lambda row: hashlib.sha256(
                    f"example|entities|{row['stable_id']}".encode()
                ).hexdigest()
            )
            prefixes.extend(group[:2])
        self.assertEqual(
            stratified_graph_sample(
                records, "example", "entities", entity_type_coverage=True
            ),
            stratified_graph_sample(
                prefixes,
                "example",
                "entities",
                entity_type_coverage=True,
                stratum_sizes=sizes,
            ),
        )

    def test_insufficient_candidates_cannot_silently_undersample(self):
        with self.assertRaisesRegex(ValueError, "enough bound prefix"):
            stratified_graph_sample(
                [{"stable_id": "first", "stratum": "A"}],
                "example",
                "entities",
                stratum_sizes={"A": 30},
            )

    def test_invalid_size_maps_are_rejected(self):
        rows = [{"stable_id": "first", "stratum": "A"}]
        for sizes in [{"B": 1}, {"A": 0}, {"A": -1}, {"A": True}, {"A": 1.5}]:
            with self.subTest(sizes=sizes), self.assertRaises(ValueError):
                stratified_graph_sample(
                    rows, "example", "entities", stratum_sizes=sizes
                )
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            stratified_graph_sample(
                rows + [{"stable_id": "second", "stratum": "A"}],
                "example",
                "entities",
                stratum_sizes={"A": 1},
            )


class DiagnosticTests(unittest.TestCase):
    def test_graph_semantic_na_and_unresolved_review_are_separate(self):
        records = [
            {
                "audit_item_id": "first",
                "status": "valid",
                "support_status": "supported",
                "provenance_status": "unresolved",
                "contradiction_flag": "no",
                "ambiguity_flag": "yes",
            },
            {
                "audit_item_id": "second",
                "status": "valid",
                "support_status": "not_assessable",
                "provenance_status": "resolved",
                "contradiction_flag": "no",
                "ambiguity_flag": "no",
            },
            {"audit_item_id": "third", "status": "unresolved"},
            {"audit_item_id": "fourth", "status": "missing"},
        ]
        result = graph_audit_summary(records)
        support = result["dimensions"]["support_status"]
        self.assertEqual(
            (support["N_total"], support["N_app"], support["k"]), (4, 3, 1)
        )
        self.assertEqual(
            (support["not_applicable"], support["unresolved"], support["missing"]),
            (1, 1, 1),
        )
        provenance = result["dimensions"]["provenance_status"]
        self.assertEqual(provenance["counts"]["unresolved"], 1)
        self.assertEqual(provenance["k"], 2)

    def test_error_codes_are_record_unions_with_explicit_unknowns(self):
        families = {"Content": ["omission", "incorrect"], "Behaviour": ["abstention"]}
        records = [
            {
                "case_id": "first",
                "codes": ["omission", "omission", "incorrect"],
                "status": "valid",
            },
            {"case_id": "second", "codes": [], "status": "valid"},
            {"case_id": "third", "codes": ["omission"], "status": "unresolved"},
            {"case_id": "fourth", "codes": [], "status": "not_applicable"},
            {"case_id": "fifth", "codes": [], "status": "missing"},
        ]
        result = error_summary(records, cohort="A", families=families)
        self.assertEqual(
            (result["N_total"], result["N_app"], result["k_valid"]), (5, 4, 2)
        )
        self.assertEqual(
            (result["N_unknown"], result["missing"], result["N_not_app"]), (1, 1, 1)
        )
        self.assertEqual(
            result["code_counts"], {"abstention": 0, "incorrect": 1, "omission": 1}
        )
        self.assertEqual(result["family_counts"], {"Content": 1, "Behaviour": 0})
        self.assertIsNone(result["family_rates"]["Content"])

    def test_small_samples_and_u_are_count_only(self):
        records = [
            {
                "case_id": str(index),
                "codes": ["omission"] if index < 5 else [],
                "status": "valid",
            }
            for index in range(20)
        ]
        families = {"Content": ["omission"]}
        self.assertEqual(
            error_summary(records, cohort="A", families=families)["family_rates"][
                "Content"
            ],
            0.25,
        )
        self.assertIsNone(
            error_summary(records, cohort="U", families=families)["family_rates"][
                "Content"
            ]
        )
        self.assertIsNone(
            error_summary(records[:19], cohort="A", families=families)["family_rates"][
                "Content"
            ]
        )

    def test_duplicate_cases_cannot_change_the_denominator(self):
        records = [{"case_id": "first", "codes": [], "status": "valid"}] * 2
        with self.assertRaises(ValueError):
            error_summary(records, cohort="A", families={"Content": ["omission"]})

    def test_question_properties_overlap_and_exclude_u(self):
        questions = [
            {
                "question_id": "first",
                "cohort": "A",
                "review_triggers": ["numeric_tolerance", "exception_sensitive"],
            },
            {
                "question_id": "second",
                "cohort": "A",
                "review_triggers": ["multi_evidence_and_semantics_assumed"],
            },
            {
                "question_id": "third",
                "cohort": "U",
                "review_triggers": ["numeric_tolerance"],
            },
        ]
        groups = question_property_memberships(questions)
        self.assertEqual(groups["Numerical"], ["first"])
        self.assertEqual(groups["Exception-sensitive"], ["first"])
        self.assertEqual(groups["Multi-evidence"], ["second"])


class GenuineUserTests(unittest.TestCase):
    def test_nominal_categories_and_missing_pairs(self):
        ids = ["first", "second", "third", "fourth"]
        left = {
            "first": "correct",
            "second": "appropriate_abstention",
            "third": "technical_failure",
        }
        right = {
            "first": "partially_correct",
            "second": "correct",
            "third": "technical_failure",
            "fourth": "incorrect",
        }
        result = genuine_user_counts(left, ids)
        self.assertEqual((result["N_total"], result["N_app"], result["k"]), (4, 4, 3))
        self.assertEqual(result["missing_human_reviews"], 1)
        self.assertEqual(result["categories"]["technical_failure"], 1)
        self.assertEqual(len(result["categories"]), 6)
        paired = genuine_user_transitions(left, right, ids)
        self.assertEqual(
            (paired["common_k"], paired["missing_pairs"], paired["same_category"]),
            (3, 1, 1),
        )
        self.assertEqual(sum(row["count"] for row in paired["category_transitions"]), 3)
        self.assertIn(
            {
                "left_category": "appropriate_abstention",
                "right_category": "correct",
                "count": 1,
            },
            paired["category_transitions"],
        )
        self.assertNotIn("wins", paired)

    def test_unknown_categories_and_foreign_questions_are_rejected(self):
        for categories in [{"first": "excellent"}, {"other": "correct"}]:
            with self.subTest(categories=categories), self.assertRaises(ValueError):
                genuine_user_counts(categories, ["first"])


class PublicErrorExampleTests(unittest.TestCase):
    def test_table_10_consumes_recorded_public_diagnostic_dimensions(self):
        root = Path(__file__).parents[1]
        data = [
            json.loads(row)
            for row in (root / "examples/evaluation/errors.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        notebook = json.loads(
            (root / "notebooks/06a_reported_tables.ipynb").read_text(encoding="utf-8")
        )
        cell = "".join(notebook["cells"][12]["source"])
        tables = {}
        namespace = {
            "data": {"errors": data},
            "error_summary": error_summary,
            "show": lambda title, rows: tables.update({title: rows}),
        }
        exec(
            compile(cell[cell.index("dimensions = {") :], "table_10", "exec"), namespace
        )
        families = {
            "Answer Content": "answer",
            "Answer Behaviour": "answer",
            "Citation": "citation",
        }
        for row in tables["Table 10: error families"]:
            if row["Family"] not in families:
                continue
            expected_cases = {
                record["case_id"]
                for record in data
                if record["scope"] == "PRIMARY"
                and record["cohort"] == "A"
                and record["condition_id"] == row["Condition"]
                and record["dimension"] == families[row["Family"]]
            }
            with self.subTest(family=row["Family"], condition=row["Condition"]):
                self.assertGreater(len(expected_cases), 0)
                self.assertEqual(row["N_total"], len(expected_cases))
                self.assertGreater(row["Valid k"], 0)


if __name__ == "__main__":
    unittest.main()
