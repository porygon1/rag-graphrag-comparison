"""Convert accepted answer assessments into applicable scientific outcomes."""

from rag_comparison.config import DECISION_LABELS


def answer_outcomes(review: dict) -> dict:
    """Return values and statuses without regrading an accepted assessment.

    assessment_state is accepted or explicitly illustrative. Model proposals
    cannot enter this calculation. cohort is A or U. Missing native output or
    review remains missing; semantic abstention has its own applicability rules.
    """
    if review["assessment_state"] not in {"accepted", "illustrative"}:
        raise ValueError("Only accepted or illustrative assessments can be scored.")
    if review["cohort"] not in {"A", "U"}:
        raise ValueError("Use the benchmark's A or U cohort.")
    fields = (
        "answer_correctness",
        "faithfulness",
        "citation_correctness",
        "correct_behavior",
    )
    if (
        review["technical_status"] != "completed"
        or review["review_status"] != "reviewed"
    ):
        reason = (
            "missing_output"
            if review["technical_status"] != "completed"
            else "missing_human_review"
        )
        return {field: {"value": None, "status": reason} for field in fields}
    grades = review["grades"]
    decision = grades["decision_label"]
    if decision not in DECISION_LABELS:
        raise ValueError("Unknown accepted answer decision.")
    if decision == "no_response_or_parse_failure":
        return {field: {"value": None, "status": "missing_output"} for field in fields}
    content = decision in {"answers", "answers_with_insufficient_caveat"}
    outcomes = {}
    for field in fields[:-1]:
        grade = grades[field]
        not_applicable = (
            (field == "answer_correctness" and review["cohort"] == "U")
            or (field == "faithfulness" and not content)
            or (field == "citation_correctness" and grade == "citation_not_required")
        )
        if not_applicable:
            expected = {
                "answer_correctness": "not_applicable_unanswerable",
                "faithfulness": "not_applicable_no_answer",
                "citation_correctness": "citation_not_required",
            }[field]
            if grade != expected:
                raise ValueError("Assessment grade contradicts its applicability.")
            outcomes[field] = {"value": None, "status": expected}
        else:
            if isinstance(grade, bool) or grade not in (0, 1, 2, 3):
                raise ValueError("Applicable accepted grades must be ordinal 0–3.")
            if field == "answer_correctness" and not content and grade != 0:
                raise ValueError("An answerable abstention has correctness zero.")
            if field == "citation_correctness" and not content:
                raise ValueError("Citation assessment needs a content answer.")
            outcomes[field] = {"value": grade, "status": "valid"}
    correct = (decision == "abstains") == (review["cohort"] == "U")
    outcomes["correct_behavior"] = {"value": int(correct), "status": "valid"}
    return outcomes


def behavior_counts(reviews: list[dict]) -> dict:
    """Count benchmark abstention decisions with technical failures excluded."""
    counts = {"TP": 0, "FN": 0, "FP": 0, "TN": 0}
    missing = 0
    for review in reviews:
        outcome = answer_outcomes(review)["correct_behavior"]
        if outcome["status"] != "valid":
            missing += 1
            continue
        abstains = review["grades"]["decision_label"] == "abstains"
        cell = (
            ("TP" if abstains else "FN")
            if review["cohort"] == "U"
            else ("FP" if abstains else "TN")
        )
        counts[cell] += 1
    tp, fn, fp, tn = (counts[key] for key in ("TP", "FN", "FP", "TN"))
    return {
        **counts,
        "N_total": len(reviews),
        "k": sum(counts.values()),
        "missing": missing,
        "abstention_recall": tp / (tp + fn) if tp + fn else None,
        "over_abstention_rate": fp / (fp + tn) if fp + tn else None,
        "abstention_appropriateness": (tp + tn) / (tp + fn + fp + tn)
        if tp + fn + fp + tn
        else None,
    }
