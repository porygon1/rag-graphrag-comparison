"""Paired outcome contrasts, denominators and evidence-connected bootstrap."""

import math
import random
from collections import defaultdict
from collections.abc import Hashable, Mapping, Sequence

from rag_comparison.config import (
    BOOTSTRAP_ALPHA,
    MIN_AGGREGATE_CASES,
    RESAMPLING_ITERATIONS,
    RESAMPLING_SEED,
)


def outcome_inputs(
    rows: Sequence[dict],
    condition_ids: Sequence[str],
    metric: str,
    question_ids: Sequence[str],
) -> tuple[dict[str, dict[str, float | int | None]], list[str]]:
    """Select valid values and metric-specific semantic NA for a target population.

    The caller binds an accepted or explicitly illustrative input dataset. This
    caller retains responsibility for accepting or rejecting proposed judgements.
    Review flags stay unchanged. Invalid diagnostic values remain missing.
    Duplicate selected records raise ValueError.
    """
    values: dict[str, dict[str, float | int | None]] = {
        condition: dict.fromkeys(question_ids) for condition in condition_ids
    }
    semantic_na = {
        "faithfulness": "not_applicable_no_answer",
        "citation_correctness": "citation_not_required",
    }.get(metric)
    seen = set()
    non_applicable = set()
    for row in rows:
        condition, question = row["condition_id"], row["question_id"]
        if (
            condition not in values
            or question not in values[condition]
            or row["metric"] != metric
        ):
            continue
        key = (condition, question, metric)
        if key in seen:
            raise ValueError("Duplicate selected condition/question/metric outcome.")
        seen.add(key)
        status, value = row.get("status"), row.get("value")
        if status == "valid":
            if value is None:
                raise ValueError("A valid applicable outcome must have a value.")
            values[condition][question] = value
        elif semantic_na is not None and status == semantic_na:
            if value is not None:
                raise ValueError(
                    "A semantically non-applicable outcome must have no value."
                )
            non_applicable.add(question)
    return values, sorted(non_applicable)


def surface_coverage(
    n_total: int,
    n_app: int,
    k: int,
    missing_reasons: Mapping[str, int] | None = None,
) -> dict:
    """Keep total, applicable and valid counts separate for one outcome surface."""

    if not 0 <= k <= n_app <= n_total:
        raise ValueError("Expected 0 <= k <= N_app <= N_total.")
    reasons = {
        str(key): int(value) for key, value in sorted((missing_reasons or {}).items())
    }
    if any(value < 0 for value in reasons.values()):
        raise ValueError("Missing counts must be nonnegative.")
    return {
        "N_total": n_total,
        "N_app": n_app,
        "k": k,
        "missing": n_app - k,
        "coverage": k / n_app if n_app else None,
        "missing_reasons": reasons,
        "claim_coverage_complete": k == n_app,
    }


def connected_components(question_units: Mapping[str, set[str]]) -> dict[str, str]:
    """Connect questions that share evidence, including transitive connections."""

    parents = {question_id: question_id for question_id in question_units}

    def find(item: str) -> str:
        while parents[item] != item:
            parents[item] = parents[parents[item]]
            item = parents[item]
        return item

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root == right_root:
            return
        winner, loser = sorted((left_root, right_root))
        parents[loser] = winner

    owner_by_unit: dict[str, str] = {}
    for question_id in sorted(question_units):
        for unit_id in sorted(question_units[question_id]):
            owner = owner_by_unit.setdefault(unit_id, question_id)
            union(question_id, owner)

    members: dict[str, list[str]] = defaultdict(list)
    for question_id in sorted(question_units):
        members[find(question_id)].append(question_id)
    canonical = {root: min(group) for root, group in members.items()}
    return {
        question_id: canonical[find(question_id)]
        for question_id in sorted(question_units)
    }


def _percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("Percentiles require at least one value.")
    if not 0 <= probability <= 1:
        raise ValueError("probability must be between 0 and 1.")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def paired_resampling(
    differences: Sequence[float],
    *,
    cluster_ids: Sequence[Hashable] | None = None,
    iterations: int = RESAMPLING_ITERATIONS,
    seed: int = RESAMPLING_SEED,
    alpha: float = BOOTSTRAP_ALPHA,
) -> dict:
    """Percentile bootstrap for complete paired question differences.

    Without cluster_ids, sample questions. With IDs, sample whole connected
    components and flatten their questions, preserving unequal component sizes.
    The seeded Python RNG and linear percentile interpolation define the method.
    """

    values = [float(value) for value in differences]
    if any(not math.isfinite(value) for value in values):
        raise ValueError("Paired differences must be finite.")
    if not values:
        raise ValueError("Resampling requires at least one complete pair.")
    if iterations <= 0:
        raise ValueError("iterations must be positive.")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1.")
    if cluster_ids is not None and len(cluster_ids) != len(values):
        raise ValueError("cluster_ids and differences must have equal length.")

    if cluster_ids is None:
        groups = [[value] for value in values]
        unit = "question"
    else:
        grouped: dict[Hashable, list[float]] = {}
        for cluster_id, value in zip(cluster_ids, values, strict=True):
            grouped.setdefault(cluster_id, []).append(value)
        groups = list(grouped.values())
        unit = "inference_component"

    rng = random.Random(seed)
    observed = sum(values) / len(values)
    bootstrap: list[float] = []
    for _ in range(iterations):
        sampled = [groups[rng.randrange(len(groups))] for _ in range(len(groups))]
        flattened = [value for group in sampled for value in group]
        bootstrap.append(sum(flattened) / len(flattened))

    result: dict = {
        "k": len(values),
        "resampling_units": len(groups),
        "resampling_unit": unit,
        "estimate": observed,
        "ci_lower": _percentile(bootstrap, alpha / 2),
        "ci_upper": _percentile(bootstrap, 1 - alpha / 2),
        "iterations": iterations,
        "seed": seed,
    }
    return result


def _configuration_contrast(
    states: Mapping[str, Mapping[str, float | int | None]],
    *,
    question_ids: Sequence[str],
    scale: str,
    cluster_by_question: Mapping[str, Hashable],
    non_applicable_question_ids: Sequence[str],
    gap_shift: bool,
    iterations: int,
    seed: int,
) -> dict:
    """Form complete pairs; missing states reduce k and only semantic NA reduces N_app."""

    ids = list(question_ids)
    if len(ids) != len(set(ids)):
        raise ValueError("The target population contains duplicate question IDs.")
    if scale not in {"continuous", "binary", "ordinal"}:
        raise ValueError("scale must be continuous, binary or ordinal.")
    not_applicable = set(non_applicable_question_ids)
    if not_applicable - set(ids):
        raise ValueError(
            "Non-applicable questions must belong to the target population."
        )
    if set(ids) - set(cluster_by_question):
        raise ValueError("Question clusters are missing.")
    paired_ids = []
    missing_states = {}
    changes = {}
    for qid in ids:
        if qid in not_applicable:
            continue
        missing = [name for name, values in states.items() if values.get(qid) is None]
        if missing:
            missing_states[qid] = missing
            continue
        values: dict[str, float | int] = {}
        for name, outcomes in states.items():
            value = outcomes[qid]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(f"Invalid outcome for {qid}.")
            if scale == "ordinal" and value not in (0, 1, 2, 3):
                raise ValueError("Ordinal outcomes must be in 0..3.")
            if scale == "binary" and value not in (0, 1):
                raise ValueError("Binary outcomes must be 0 or 1.")
            values[name] = value

        def difference(left: str, right: str) -> float:
            delta = values[right] - values[left]
            return (
                float((delta > 0) - (delta < 0)) if scale == "ordinal" else float(delta)
            )

        changes[qid] = (
            difference("c_variant", "g_variant")
            - difference("c_reference", "g_reference")
            if gap_shift
            else difference("reference", "variant")
        )
        paired_ids.append(qid)

    k = len(paired_ids)
    result: dict = {
        **surface_coverage(
            len(ids),
            len(ids) - len(not_applicable),
            k,
            {"incomplete_required_states": len(missing_states)},
        ),
        "k_gap" if gap_shift else "k_s": k,
        "scale": scale,
        "not_applicable_question_ids": sorted(not_applicable),
        "missing_states_by_question": missing_states,
        "paired_question_ids": paired_ids,
        "question_changes": changes,
        "paired_outcomes": {
            name: {qid: values[qid] for qid in paired_ids}
            for name, values in states.items()
        },
        "change_counts": {
            "positive": sum(value > 0 for value in changes.values()),
            "zero": sum(value == 0 for value in changes.values()),
            "negative": sum(value < 0 for value in changes.values()),
        },
        "aggregation_status": "count_only_k_below_20"
        if k < MIN_AGGREGATE_CASES
        else "estimable",
        "standard": None,
        "cluster": None,
    }
    if k >= MIN_AGGREGATE_CASES:
        differences = [changes[qid] for qid in paired_ids]
        result["standard"] = paired_resampling(
            differences, iterations=iterations, seed=seed
        )
        result["cluster"] = paired_resampling(
            differences,
            cluster_ids=[cluster_by_question[qid] for qid in paired_ids],
            iterations=iterations,
            seed=seed,
        )
    return result


def paired_intervention_change(
    reference: Mapping[str, float | int | None],
    variant: Mapping[str, float | int | None],
    *,
    question_ids: Sequence[str],
    scale: str,
    cluster_by_question: Mapping[str, Hashable],
    non_applicable_question_ids: Sequence[str] = (),
    iterations: int = RESAMPLING_ITERATIONS,
    seed: int = RESAMPLING_SEED,
) -> dict:
    """Compare variant minus reference; ordinal changes use win/tie/loss signs.

    Use C0 as reference and G0 as variant for the baseline architecture contrast.
    Counts remain available below MIN_AGGREGATE_CASES; no aggregate or CI is formed."""

    return _configuration_contrast(
        {"reference": reference, "variant": variant},
        question_ids=question_ids,
        scale=scale,
        cluster_by_question=cluster_by_question,
        non_applicable_question_ids=non_applicable_question_ids,
        gap_shift=False,
        iterations=iterations,
        seed=seed,
    )


def paired_system_gap_shift(
    c_reference: Mapping[str, float | int | None],
    g_reference: Mapping[str, float | int | None],
    c_variant: Mapping[str, float | int | None],
    g_variant: Mapping[str, float | int | None],
    *,
    question_ids: Sequence[str],
    scale: str,
    cluster_by_question: Mapping[str, Hashable],
    non_applicable_question_ids: Sequence[str] = (),
    iterations: int = RESAMPLING_ITERATIONS,
    seed: int = RESAMPLING_SEED,
) -> dict:
    """Form each architecture gap first, then its shift on the same complete four-way set.

    For ordinal grades each G-minus-C gap is a sign, so its shift can be -2..2.
    For a G-only intervention pass C0 as both C states. See thesis Appendix A.2.
    """

    return _configuration_contrast(
        {
            "c_reference": c_reference,
            "g_reference": g_reference,
            "c_variant": c_variant,
            "g_variant": g_variant,
        },
        question_ids=question_ids,
        scale=scale,
        cluster_by_question=cluster_by_question,
        non_applicable_question_ids=non_applicable_question_ids,
        gap_shift=True,
        iterations=iterations,
        seed=seed,
    )
