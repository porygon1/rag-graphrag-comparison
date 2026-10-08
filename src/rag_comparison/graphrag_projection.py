"""Project GraphRAG Local Search Sources onto page-based evidence units."""

from collections.abc import Mapping, Sequence

DIRECT_EVIDENCE_CARRIER = "sources"
INDIRECT_CARRIERS = ("entities", "relationships", "reports", "claims")
KNOWN_CARRIERS = frozenset((DIRECT_EVIDENCE_CARRIER, *INDIRECT_CARRIERS))


def project_local_search_context(
    question_id: str,
    context_data: Mapping[str, list[dict[str, object]] | None],
    text_unit_index: Mapping[str, str],
    projection_edges: Mapping[str, Sequence[str]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Preserve Source positions and credit only uniquely mapped evidence.

    context_data contains carrier record lists. Each Source id identifies a
    TextUnit by human_readable_id, which maps to its GraphRAG input record.
    projection_edges maps that input record to its evidence-unit IDs.

    Unknown Sources, missing edges and multiple evidence units retain their
    original rank without direct credit. Repeated Sources also retain their
    positions. Entities, relationships, reports and claims are indirect carriers;
    they add no evidence positions. Unknown carriers or malformed Sources raise
    ValueError. See thesis Section 2.5 for the source-native comparison.
    """
    unknown = set(context_data) - KNOWN_CARRIERS
    if unknown:
        raise ValueError(f"Unknown Local Search carriers: {sorted(unknown)}.")

    sources = context_data.get(DIRECT_EVIDENCE_CARRIER)
    if sources is None:
        sources = []
    if not isinstance(sources, list):
        raise ValueError("The Sources carrier must contain a list of records.")

    records: list[dict[str, object]] = []
    for rank, source in enumerate(sources, start=1):
        if not isinstance(source, dict) or source.get("id") is None:
            raise ValueError("Each Source record must contain an id.")
        source_id = str(source["id"])
        input_record_id = text_unit_index.get(source_id)
        evidence_unit_ids = projection_edges.get(input_record_id or "", [])

        status = "projected"
        failure_reason: str | None = None
        evidence_unit_id: str | None = None
        if input_record_id is None:
            status, failure_reason = "projection_failed", "unknown_text_unit"
        elif not evidence_unit_ids:
            status, failure_reason = "projection_failed", "missing_evidence_edge"
        elif len(evidence_unit_ids) > 1:
            status = "ambiguous_carrier"
        else:
            evidence_unit_id = evidence_unit_ids[0]

        records.append(
            {
                "question_id": question_id,
                "rank": rank,
                "carrier_local_id": source_id,
                "source_evidence_unit_id": evidence_unit_id,
                "projection_status": status,
                "projection_failure_reason": failure_reason,
                "direct_evidence_credit_allowed": status == "projected",
            }
        )

    projected = [row for row in records if row["projection_status"] == "projected"]
    summary = {
        "question_id": question_id,
        "ranked_position_count": len(records),
        "projected_position_count": len(projected),
        "projection_failure_count": sum(
            row["projection_status"] == "projection_failed" for row in records
        ),
        "ambiguous_carrier_count": sum(
            row["projection_status"] == "ambiguous_carrier" for row in records
        ),
        "distinct_evidence_unit_count": len(
            {row["source_evidence_unit_id"] for row in projected}
        ),
        "indirect_carrier_counts": {
            carrier: len(context_data.get(carrier) or [])
            for carrier in INDIRECT_CARRIERS
            if context_data.get(carrier)
        },
    }
    return records, summary


def build_text_unit_index(
    human_readable_ids: Sequence[str | int], document_ids: Sequence[str]
) -> dict[str, str]:
    """Map unique TextUnit human-readable IDs to their GraphRAG input record IDs.

    Both sequences must have equal length. IDs are stored as strings; content
    hashes are not used because identical text can occur on different pages.
    """
    index = {
        str(human_readable_id): str(document_id)
        for human_readable_id, document_id in zip(
            human_readable_ids, document_ids, strict=True
        )
    }
    if len(index) != len(human_readable_ids):
        raise ValueError("TextUnit human_readable_id values must be unique.")
    return index
