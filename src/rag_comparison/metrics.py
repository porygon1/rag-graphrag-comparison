"""Retrieval metrics. See thesis Section 2.6 and Appendix A.3 for details."""

import math
from collections.abc import Mapping, Sequence

from rag_comparison.config import TOP_K


def dcg_for_gains(gains: Sequence[int]) -> float:
    """Sum linear relevance gains with a logarithmic discount by rank."""
    return sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, start=1))


def ndcg_at_k(
    ranked_units: Sequence[str | None], qrels: Mapping[str, int]
) -> float | None:
    """Score the first TOP_K evidence positions using a shared relevance pool.

    qrels maps distinct evidence IDs to accepted grades 0, 1 or 2. None in
    ranked_units marks a failed evidence projection. Duplicate IDs keep their
    rank positions but contribute gain only at their first occurrence.

    Return the score rounded to six decimals.
    Return None for incomplete ranks, failed projections, unjudged units or
    a pool without positive ideal gain. Invalid relevance grades raise ValueError.
    """
    result = score_question(ranked_units, qrels, [])
    return (
        result["ndcg_at_k"]
        if result["metric_validity_status"] == "fully_judged"
        else None
    )


def score_question(
    ranked_units: Sequence[str | None],
    qrels: Mapping[str, int],
    minimal_evidence_sets: Sequence[set[str]],
    top_k: int = TOP_K,
) -> dict:
    """Describe one question's first top_k positions without dropping missing ranks.

    The sequence order is the rank. None marks an unsuccessful source projection.
    Duplicates remain judged positions but contribute gain at their first occurrence.
    Qrels use grades 0/1/2 and the complete shared pool defines ideal gain.

    nDCG and evidence-set overlap remain visible as diagnostic calculations when
    ranks are invalid. Aggregation requires fully_judged and positive ideal gain;
    use ndcg_at_k when only a valid score is needed. Judged always divides by top_k.
    """
    if top_k <= 0:
        raise ValueError("top_k must be positive.")
    if any(grade not in (0, 1, 2) for grade in qrels.values()):
        raise ValueError("Relevance grades must be 0, 1 or 2.")
    units = list(ranked_units[:top_k])
    judged_count = 0
    projection_failure_count = 0
    unjudged_unit_ids = []
    seen: set[str] = set()
    dcg = 0.0
    for position, unit in enumerate(units, start=1):
        if unit is None:
            projection_failure_count += 1
            continue
        grade = qrels.get(unit)
        if grade is None:
            unjudged_unit_ids.append(unit)
            continue
        judged_count += 1
        if unit not in seen:
            dcg += grade / math.log2(position + 1)
        seen.add(unit)

    missing_position_count = max(0, top_k - len(units))
    positive_gains = sorted(
        (grade for grade in qrels.values() if grade > 0), reverse=True
    )
    idcg = dcg_for_gains(positive_gains[:top_k])
    retrieved = {unit for unit in units if unit is not None}
    failures = []
    if missing_position_count:
        failures.append("missing_ranked_positions")
    if projection_failure_count:
        failures.append("projection_failures_present")
    if unjudged_unit_ids:
        failures.append("unjudged_positions_present")
    validity = (
        "fully_judged" if not failures and judged_count == top_k else "+".join(failures)
    )
    return {
        "ndcg_at_k": round(dcg / idcg, 6) if idcg > 0 else None,
        "dcg": dcg,
        "idcg": idcg,
        "judged_at_k": round(judged_count / top_k, 6),
        "evidence_recall_at_k": evidence_recall(minimal_evidence_sets, retrieved),
        "partial_overlap_at_k": partial_overlap(minimal_evidence_sets, retrieved),
        "ranked_position_count": len(units),
        "missing_position_count": missing_position_count,
        "projection_failure_count": projection_failure_count,
        "unjudged_unit_ids": unjudged_unit_ids,
        "metric_validity_status": validity,
    }


def evidence_recall(
    minimal_evidence_sets: Sequence[set[str]], retrieved_units: set[str]
) -> float | None:
    """Return 1 when any complete minimal evidence set is retrieved, otherwise 0.

    Return None when no minimal evidence sets are supplied. Partial evidence is
    not binary recall; an empty required set is an invalid reference.
    """
    if not minimal_evidence_sets:
        return None
    if any(not required for required in minimal_evidence_sets):
        raise ValueError("Minimal evidence sets must not be empty.")
    return (
        1.0
        if any(required <= retrieved_units for required in minimal_evidence_sets)
        else 0.0
    )


def partial_overlap(
    minimal_evidence_sets: Sequence[set[str]], retrieved_units: set[str]
) -> float | None:
    """Return the largest retrieved fraction of a required set, for diagnosis only."""
    if not minimal_evidence_sets:
        return None
    if any(not required for required in minimal_evidence_sets):
        raise ValueError("Minimal evidence sets must not be empty.")
    return round(
        max(
            len(required & retrieved_units) / len(required)
            for required in minimal_evidence_sets
        ),
        6,
    )
