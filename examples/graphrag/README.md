# Public GraphRAG example

This example uses the same 20 complete, whitespace-normalised pages and four
illustrative questions as [Classical RAG](../classical_rag/README.md). The
[data notes](../data/README.md) document the unmodified RFC 2795 PDF, source
identity, SHA256 and redistribution notice.

The index and responses are actual Azure outputs from GraphRAG 3.1.0 Standard
Indexing and native Local Search. Completion uses `gpt-4.1-mini`; embedding uses
`text-embedding-3-small`, with 1536-dimensional vectors. The saved configuration
and native placeholder settings bind this example's software contract.

| Native table | Rows |
|---|---:|
| Documents | 20 |
| TextUnits | 20 |
| Entities | 137 |
| Relationships | 216 |
| Communities | 20 |
| Community reports | 20 |

The six Parquet tables and complete native LanceDB store remain in `output/`.
Inputs, page origins and the input projection ledger preserve the shared source
identity. All bound files have relative paths and SHA256 in
[`index_manifest.json`](index_manifest.json).

| Question | First five source pages | Full Sources count | nDCG@5 | Complete reference set |
|---|---|---:|---:|---|
| DEMO-IMPS-Q-001 | 7, 16, 10, 8, 17 | 12 | 0.887915 | true |
| DEMO-IMPS-Q-002 | 13, 12, 3, 4, 16 | 12 | 1.000000 | true |
| DEMO-IMPS-Q-003 | 15, 4, 17, 1, 3 | 12 | 1.000000 | true |
| DEMO-IMPS-Q-004 | 11, 4, 1, 10, 17 | 13 | not applicable | not applicable |

These calculations use the illustrative source-reviewed qrels and minimal
evidence sets. The fourth question has no primary retrieval qrels. No accepted
answer-quality scores are assigned to the model responses.

[`native_results.jsonl`](native_results.jsonl) retains all four original response
strings and the complete returned native context tables. Reports, relationships,
claims, entities and Sources keep their columns, row order and recorded values.
The displayed top five source positions are an evaluation boundary; the native
response uses its mixed context. Only Sources are projected to direct page evidence.

[`projection_results.jsonl`](projection_results.jsonl) stores that projection;
[`results_manifest.json`](results_manifest.json) binds the native results,
projection and exact index manifest. The [artifact contract](../../docs/graphrag_artifacts.md)
explains these fields and reuse checks.

Both GraphRAG notebooks default to reading these files without credentials or
model requests. New indexing and new queries have separate explicit Azure
controls and write under ignored `local/`. Logs, cache, resolved access settings,
resource values and deployment names are excluded from this example.
