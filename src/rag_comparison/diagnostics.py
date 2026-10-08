"""Graph diagnostics and nominal assessments. See thesis Sections 2.6 and 3.5."""

import hashlib
import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence

from rag_comparison.config import (
    ERROR_FAMILIES,
    GRAPH_AUDIT_SAMPLE_PER_TYPE,
    GRAPH_FLAGS,
    GRAPH_PROVENANCE_STATUSES,
    GRAPH_SUPPORT_STATUSES,
    GU_CATEGORIES,
    MIN_AGGREGATE_CASES,
    QUESTION_PROPERTIES,
)


def _stratum_allocation(sizes: Mapping[str, int], size: int) -> dict[str, int]:
    """Reserve one per stratum, then allocate proportionally by largest remainder."""
    if size == sum(sizes.values()):
        return dict(sorted(sizes.items()))
    if size < len(sizes):
        raise ValueError("The sample must cover every observed stratum.")

    allocation = {name: 1 for name in sizes}
    remaining = size - len(sizes)
    capacities = {name: count - 1 for name, count in sizes.items()}
    total_capacity = sum(capacities.values())
    quotas = {
        name: remaining * count / total_capacity if total_capacity else 0.0
        for name, count in capacities.items()
    }
    floors = {name: math.floor(quota) for name, quota in quotas.items()}
    for name, count in floors.items():
        allocation[name] += count
    leftover = remaining - sum(floors.values())
    order = sorted(sizes, key=lambda name: (-(quotas[name] - floors[name]), name))
    for name in order:
        if leftover and allocation[name] < sizes[name]:
            allocation[name] += 1
            leftover -= 1
    return dict(sorted(allocation.items()))


def stratified_graph_sample(
    records: Sequence[dict],
    evaluation_id: str,
    artifact_type: str,
    *,
    entity_type_coverage: bool = False,
    stratum_sizes: Mapping[str, int] | None = None,
) -> list[dict]:
    """Select graph records without replacement using stable_id and stratum.

    Use entity types, community levels or A/U as strata; relationships use one
    stratum. Standard samples contain at most GRAPH_AUDIT_SAMPLE_PER_TYPE items.
    Entity-type coverage can increase this size to one item per observed raw
    type label. Raw labels retain their case. See thesis Appendix B.1.

    With stratum_sizes, records contain the bound smallest-hash prefix of each
    stratum. Actual population sizes determine allocation; enough candidates
    must remain for each allocation. Selection and display ordering are unchanged.
    """
    ids = [str(record["stable_id"]) for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Graph stable IDs must be unique within an artifact type.")
    if entity_type_coverage and artifact_type != "entities":
        raise ValueError("Extended type coverage applies only to entities.")

    strata: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        strata[str(record["stratum"])].append(record)
    sizes = {name: len(group) for name, group in strata.items()}
    if stratum_sizes is not None:
        if set(stratum_sizes) != set(strata) or any(
            isinstance(count, bool) or not isinstance(count, int) or count <= 0
            for count in stratum_sizes.values()
        ):
            raise ValueError("Actual stratum sizes must match positive integer counts.")
        if any(len(strata[name]) > count for name, count in stratum_sizes.items()):
            raise ValueError("Candidate counts cannot exceed actual stratum sizes.")
        sizes = dict(stratum_sizes)
    size = min(GRAPH_AUDIT_SAMPLE_PER_TYPE, sum(sizes.values()))
    if entity_type_coverage:
        size = max(size, len(strata))
    allocation = _stratum_allocation(sizes, size)
    if any(len(strata[name]) < count for name, count in allocation.items()):
        raise ValueError("Each stratum must retain enough bound prefix candidates.")

    def hash_order(record: dict, display: bool = False) -> tuple[str, str]:
        prefix = f"{evaluation_id}|{artifact_type}"
        if display:
            prefix += "|display"
        stable_id = str(record["stable_id"])
        digest = hashlib.sha256(f"{prefix}|{stable_id}".encode("utf-8")).hexdigest()
        return digest, stable_id

    selected = []
    for name in sorted(strata):
        ordered = sorted(strata[name], key=hash_order)
        selected.extend(ordered[: allocation[name]])
    return [
        {
            **record,
            "audit_stratum": str(record["stratum"]),
            "audit_stratum_allocation": allocation[str(record["stratum"])],
        }
        for record in sorted(selected, key=lambda record: hash_order(record, True))
    ]


def graph_audit_summary(reviews: Sequence[dict]) -> dict:
    """Summarize one artifact type in one condition, with separate denominators.

    Each record has audit_item_id, status (valid, unresolved or missing), and
    four categorical fields. Accepted provenance 'unresolved' is a valid grade;
    an unresolved review is a missing assessment. Support 'not_assessable' is NA.
    """
    ids = [review["audit_item_id"] for review in reviews]
    if len(ids) != len(set(ids)):
        raise ValueError("Graph audit item IDs must be unique.")
    statuses = Counter(review["status"] for review in reviews)
    if set(statuses) - {"valid", "unresolved", "missing"}:
        raise ValueError("Unknown graph review status.")
    valid = [review for review in reviews if review["status"] == "valid"]
    dimensions = {}
    for field, allowed in (
        ("support_status", GRAPH_SUPPORT_STATUSES),
        ("provenance_status", GRAPH_PROVENANCE_STATUSES),
        ("contradiction_flag", GRAPH_FLAGS),
        ("ambiguity_flag", GRAPH_FLAGS),
    ):
        counts = Counter(review[field] for review in valid)
        if set(counts) - set(allowed):
            raise ValueError(f"Unknown graph assessment in {field}.")
        not_applicable = counts.get("not_assessable", 0)
        dimensions[field] = {
            "N_total": len(reviews),
            "N_app": len(reviews) - not_applicable,
            "k": len(valid) - not_applicable,
            "not_applicable": not_applicable,
            "unresolved": statuses["unresolved"],
            "missing": statuses["missing"],
            "counts": {value: counts[value] for value in allowed},
        }
    return {
        "sample_N_total": len(reviews),
        "k_reviewed": len(valid),
        "missing_reviews": len(reviews) - len(valid),
        "dimensions": dimensions,
    }


def error_summary(
    records: Sequence[dict],
    *,
    cohort: str,
    families: Mapping[str, Sequence[str]] = ERROR_FAMILIES,
) -> dict:
    """Count distinct codes and family unions on one diagnostic validity basis.

    Records contain case_id, codes and status: valid, not_applicable, unresolved
    or missing. Supply separate records for answer, citation, retrieval,
    projection and technical diagnostics. Unknown assessments are not zero errors.
    A rates require MIN_AGGREGATE_CASES; U is count-only. See thesis Section 3.3.
    """
    if cohort not in {"A", "U"}:
        raise ValueError("Error diagnostics require cohort A or U.")
    ids = [record["case_id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Diagnostic case IDs must be unique.")
    statuses = Counter(record["status"] for record in records)
    if set(statuses) - {"valid", "not_applicable", "unresolved", "missing"}:
        raise ValueError("Unknown diagnostic validity status.")
    allowed_codes = {code for codes in families.values() for code in codes}
    valid_codes = [
        set(record["codes"]) for record in records if record["status"] == "valid"
    ]
    if any(codes - allowed_codes for codes in valid_codes):
        raise ValueError("Unknown error code on the selected diagnostic basis.")
    k = len(valid_codes)
    code_counts = {
        code: sum(code in codes for codes in valid_codes)
        for code in sorted(allowed_codes)
    }
    family_counts = {
        family: sum(bool(codes & set(members)) for codes in valid_codes)
        for family, members in families.items()
    }
    show_rates = cohort == "A" and k >= MIN_AGGREGATE_CASES
    return {
        "N_total": len(records),
        "N_app": len(records) - statuses["not_applicable"],
        "N_not_app": statuses["not_applicable"],
        "k_valid": k,
        "N_unknown": statuses["unresolved"],
        "missing": statuses["missing"],
        "known_with_error": sum(bool(codes) for codes in valid_codes),
        "known_without_taxonomy_error": sum(not codes for codes in valid_codes),
        "code_counts": code_counts,
        "family_counts": family_counts,
        "code_rates": {
            code: count / k if show_rates else None
            for code, count in code_counts.items()
        },
        "family_rates": {
            family: count / k if show_rates else None
            for family, count in family_counts.items()
        },
    }


def question_property_memberships(questions: Sequence[dict]) -> dict[str, list[str]]:
    """Select overlapping A-question groups from their review_triggers metadata."""
    ids = [question["question_id"] for question in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("Question IDs must be unique.")
    return {
        name: sorted(
            question["question_id"]
            for question in questions
            if question["cohort"] == "A" and marker in question["review_triggers"]
        )
        for name, marker in QUESTION_PROPERTIES.items()
    }


def genuine_user_counts(
    categories: Mapping[str, str | None], question_ids: Sequence[str]
) -> dict:
    """Count the six nominal GU categories; None denotes a missing accepted review."""
    if len(question_ids) != len(set(question_ids)) or set(categories) - set(
        question_ids
    ):
        raise ValueError("GU category inputs must match unique question IDs.")
    values = [categories.get(question_id) for question_id in question_ids]
    known = Counter(value for value in values if value is not None)
    if set(known) - set(GU_CATEGORIES):
        raise ValueError("Unknown genuine-user category.")
    k = sum(known.values())
    return {
        "N_total": len(question_ids),
        "N_app": len(question_ids),
        "k": k,
        "missing_human_reviews": len(question_ids) - k,
        "categories": {category: known[category] for category in GU_CATEGORIES},
    }


def genuine_user_transitions(
    left: Mapping[str, str | None],
    right: Mapping[str, str | None],
    question_ids: Sequence[str],
) -> dict:
    """Count nominal paired transitions, without ordering categories as wins or losses."""
    genuine_user_counts(left, question_ids)
    genuine_user_counts(right, question_ids)
    cases = [
        {
            "question_id": question_id,
            "left_category": left[question_id],
            "right_category": right[question_id],
        }
        for question_id in sorted(question_ids)
        if left.get(question_id) is not None and right.get(question_id) is not None
    ]
    counts = Counter((case["left_category"], case["right_category"]) for case in cases)
    return {
        "N_total": len(question_ids),
        "N_app": len(question_ids),
        "common_k": len(cases),
        "missing_pairs": len(question_ids) - len(cases),
        "same_category": sum(
            case["left_category"] == case["right_category"] for case in cases
        ),
        "cases": cases,
        "category_transitions": [
            {"left_category": a, "right_category": b, "count": count}
            for (a, b), count in sorted(counts.items())
        ],
    }
