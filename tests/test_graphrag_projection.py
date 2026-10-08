"""Check Source ordering and evidence credit in GraphRAG Local Search contexts."""

import unittest

from rag_comparison.graphrag_projection import (
    build_text_unit_index,
    project_local_search_context,
)


class LocalSearchProjectionTests(unittest.TestCase):
    def test_source_order_defines_rank_without_sorting(self):
        records, summary = project_local_search_context(
            "Q1",
            {"sources": [{"id": 20}, {"id": 10}]},
            {"10": "input-A", "20": "input-B"},
            {"input-A": ["EU-A"], "input-B": ["EU-B"]},
        )
        self.assertEqual(
            [(row["rank"], row["source_evidence_unit_id"]) for row in records],
            [(1, "EU-B"), (2, "EU-A")],
        )
        self.assertTrue(all(row["direct_evidence_credit_allowed"] for row in records))
        self.assertEqual(summary["projected_position_count"], 2)
        self.assertEqual(summary["distinct_evidence_unit_count"], 2)

    def test_unresolved_sources_keep_positions_and_receive_no_credit(self):
        records, summary = project_local_search_context(
            "Q1",
            {"sources": [{"id": 99}, {"id": 10}, {"id": 20}, {"id": 30}]},
            {"10": "input-A", "20": "input-B", "30": "input-C"},
            {"input-B": ["EU-B1", "EU-B2"], "input-C": ["EU-C"]},
        )
        self.assertEqual([row["rank"] for row in records], [1, 2, 3, 4])
        self.assertEqual(
            [row["projection_status"] for row in records],
            [
                "projection_failed",
                "projection_failed",
                "ambiguous_carrier",
                "projected",
            ],
        )
        self.assertEqual(
            [row["projection_failure_reason"] for row in records],
            ["unknown_text_unit", "missing_evidence_edge", None, None],
        )
        self.assertEqual(
            [row["source_evidence_unit_id"] for row in records],
            [None, None, None, "EU-C"],
        )
        self.assertEqual(
            [row["direct_evidence_credit_allowed"] for row in records],
            [False, False, False, True],
        )
        self.assertEqual(summary["ranked_position_count"], 4)
        self.assertEqual(summary["projection_failure_count"], 2)
        self.assertEqual(summary["ambiguous_carrier_count"], 1)

    def test_indirect_carriers_add_no_evidence_positions(self):
        context = {
            "entities": [{"id": 10}],
            "relationships": [{"id": 10}, {"id": 20}],
            "reports": [{"id": 20}],
            "claims": [{"id": 30}],
        }
        records, summary = project_local_search_context(
            "Q1", context, {"10": "input-A"}, {"input-A": ["EU-A"]}
        )
        self.assertEqual(records, [])
        self.assertEqual(summary["ranked_position_count"], 0)
        self.assertEqual(summary["distinct_evidence_unit_count"], 0)
        self.assertEqual(
            summary["indirect_carrier_counts"],
            {"entities": 1, "relationships": 2, "reports": 1, "claims": 1},
        )

    def test_duplicate_sources_retain_all_rank_positions(self):
        records, summary = project_local_search_context(
            "Q1",
            {"sources": [{"id": 10}, {"id": 10}, {"id": 20}]},
            {"10": "input-A", "20": "input-B"},
            {"input-A": ["EU-A"], "input-B": ["EU-B"]},
        )
        self.assertEqual([row["rank"] for row in records], [1, 2, 3])
        self.assertEqual(
            [row["source_evidence_unit_id"] for row in records],
            ["EU-A", "EU-A", "EU-B"],
        )
        self.assertEqual(summary["projected_position_count"], 3)
        self.assertEqual(summary["distinct_evidence_unit_count"], 2)

    def test_unknown_carrier_or_invalid_source_schema_is_rejected(self):
        contexts = [
            {"documents": []},
            {"sources": {"id": 10}},
            {"sources": [{}]},
            {"sources": [{"id": None}]},
            {"sources": ["10"]},
        ]
        for context in contexts:
            with self.subTest(context=context), self.assertRaises(ValueError):
                project_local_search_context("Q1", context, {}, {})


class TextUnitIndexTests(unittest.TestCase):
    def test_human_readable_ids_identify_each_input_record(self):
        self.assertEqual(
            build_text_unit_index([20, 10], ["input-B", "input-A"]),
            {"20": "input-B", "10": "input-A"},
        )

    def test_duplicate_human_readable_ids_are_rejected(self):
        for human_readable_ids in [[10, 10], [10, "10"]]:
            with self.subTest(ids=human_readable_ids), self.assertRaises(ValueError):
                build_text_unit_index(human_readable_ids, ["input-A", "input-B"])

    def test_index_lists_must_have_equal_length(self):
        for document_ids in [["input-A"], ["input-A", "input-B", "input-C"]]:
            with self.subTest(document_ids=document_ids), self.assertRaises(ValueError):
                build_text_unit_index([10, 20], document_ids)


if __name__ == "__main__":
    unittest.main()
