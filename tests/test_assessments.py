"""Scientific applicability and accepted-review authority."""

import copy
import unittest

from rag_comparison.assessments import answer_outcomes, behavior_counts


def review(cohort="A", decision="answers"):
    content = decision != "abstains"
    return {
        "assessment_state": "illustrative",
        "cohort": cohort,
        "technical_status": "completed",
        "review_status": "reviewed",
        "grades": {
            "decision_label": decision,
            "answer_correctness": 3
            if cohort == "A" and content
            else 0
            if cohort == "A"
            else "not_applicable_unanswerable",
            "faithfulness": 3 if content else "not_applicable_no_answer",
            "citation_correctness": 3 if content else "citation_not_required",
        },
    }


class AssessmentTests(unittest.TestCase):
    def test_answerable_abstention_is_zero_with_conditional_na(self):
        result = answer_outcomes(review(decision="abstains"))
        self.assertEqual(result["answer_correctness"], {"value": 0, "status": "valid"})
        self.assertIsNone(result["faithfulness"]["value"])
        self.assertEqual(result["correct_behavior"]["value"], 0)

    def test_unanswerable_content_is_not_correct_abstention(self):
        result = answer_outcomes(review("U", "answers_with_insufficient_caveat"))
        self.assertEqual(
            result["answer_correctness"]["status"], "not_applicable_unanswerable"
        )
        self.assertEqual(result["faithfulness"]["value"], 3)
        self.assertEqual(result["correct_behavior"]["value"], 0)

    def test_technical_failure_is_missing_not_zero_or_abstention(self):
        value = review()
        value["technical_status"] = "failed"
        self.assertTrue(
            all(item["value"] is None for item in answer_outcomes(value).values())
        )
        counts = behavior_counts([value, review("U", "abstains")])
        self.assertEqual((counts["k"], counts["missing"], counts["TP"]), (1, 1, 1))

    def test_model_proposal_and_inconsistent_rubric_are_rejected(self):
        value = review()
        for state in ("proposal", "pending"):
            value["assessment_state"] = state
            with self.assertRaises(ValueError):
                answer_outcomes(value)
        value = review(decision="abstains")
        value["grades"]["answer_correctness"] = 3
        with self.assertRaises(ValueError):
            answer_outcomes(value)

    def test_each_confusion_cell_retains_its_definition(self):
        cases = [
            review("U", "abstains"),
            review("U"),
            review("A", "abstains"),
            review("A"),
        ]
        original = copy.deepcopy(cases)
        counts = behavior_counts(cases)
        self.assertEqual(
            [counts[key] for key in ("TP", "FN", "FP", "TN")], [1, 1, 1, 1]
        )
        self.assertEqual(counts["abstention_appropriateness"], 0.5)
        self.assertEqual(cases, original)
