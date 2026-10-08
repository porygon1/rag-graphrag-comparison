# Controlled configuration changes

[Notebook 04](../notebooks/04_controlled_changes.ipynb) compares the configured
factors and their baseline references. New execution and stored-result inspection
use the existing [Classical-RAG](../notebooks/02_classical_rag.ipynb),
[GraphRAG indexing](../notebooks/03_graphrag_index.ipynb) and
[Local Search](../notebooks/03_graphrag_local_search.ipynb) notebooks.
All effective parameters are defined in
[`rag_comparison.config`](../src/rag_comparison/config.py).

## Conditions and unchanged settings

Every embedding has 1536 dimensions. `small` and `large` below mean
`text-embedding-3-small` and `text-embedding-3-large`. Page segmentation retains
one complete normalised nonempty page without overlap. Structure segmentation
retains exact parts of those same pages, with at most 800 `o200k_base` tokens,
within page boundaries and without overlap.

| Condition ID | Reference | Segmentation | Embedding | Entity types | Index consequence |
|---|---|---|---|---|---|
| `C0` | Baseline | Page | small | — | Embed pages and queries; exact cosine retrieval |
| `G0` | Baseline | Page | small | Four baseline types | Standard graph indexing |
| `C-CHUNK-STRUCT-800-0` | C0 | Structure | small | — | Embed segments and queries |
| `G-CHUNK-STRUCT-800-0` | G0 | Structure | small | Four baseline types | Rebuild graph from the same segments |
| `C-EMBED-LARGE-1536` | C0 | Page | large | — | Regenerate document and query vectors |
| `G-EMBED-LARGE-1536` | G0 | Page | large | Four baseline types | Retain G0 graph tables; regenerate vectors |
| `G-ENTITY-POLICY-PROCESS-ROLE` | G0 | Page | small | Nine types | Re-extract records and rebuild graph |
| `C-FINAL` | C0 | Structure | large | — | Embed segments and queries |
| `G-FINAL` | G0 | Page | large | Nine types | Retain G-ENTITY graph tables; regenerate vectors |

The five single-factor conditions each start from their own unchanged baseline.
C-FINAL combines CHUNK and EMBED. G-FINAL combines EMBED and ENTITY, retaining
baseline page segmentation. The longer IDs remain in manifests and stored records;
the thesis uses the short labels C-CHUNK, G-CHUNK, C-EMBED, G-EMBED and G-ENTITY.

The four baseline entity types are `organization`, `person`, `geo` and `event`.
The extended list adds `policy`, `process`, `role`, `technical_system` and
`information_artifact`. ENTITY changes the type list only; it adds no descriptions,
examples or few-shot instructions to the extraction prompt.

Retrieval depth, model dimension, source-evidence definition and native generation
contracts remain unchanged. Classical RAG passes five complete ranked chunks or
segments to its German context-only prompt. Its generation model and decoding
remain `gpt-4.1-mini`, temperature 0, top-p 1, seed 42 and maximum 1024 output
tokens. GraphRAG retains Standard Indexing, native Local Search, community level 2,
`Multiple Paragraphs`, and its native prompt and decoding contract. The two answer
paths have different contexts and citation rules.

## Prepare and execute a condition

1. Run notebook 01 to obtain normalised page chunks, source origins, questions and
   the prepared input manifest. The raw extracted page text is retained for the
   structure method.
2. For C-CHUNK, G-CHUNK or C-FINAL, run notebook 04a in the structure kernel.
   It creates one shared segment population and an input-only manifest usable by
   both system paths. See [Structure artefacts](structure_artifacts.md).
3. Select the required condition and its matching prepared input folder in the
   existing system notebook. Choose a distinct ignored output folder. The
   baseline public example folders are stored runs for C0 and G0, not variant runs.
4. For G-EMBED, select a completed G0 index as the source. For G-FINAL, select
   a completed G-ENTITY index. The indexing notebook preserves the source tables
   and runs only `generate_text_embeddings`.
5. Enable the relevant Azure control only when making new requests:
   `RUN_AZURE`, `RUN_AZURE_INDEX` or `RUN_AZURE_QUERY`. Local Search uses the
   completed index for the selected GraphRAG condition.

The small model reads the deployment name from
`AZURE_OPENAI_EMBEDDING_DEPLOYMENT`; the large model reads
`AZURE_OPENAI_EMBEDDING_LARGE_DEPLOYMENT`. Both use the selected Azure resource,
API version and dimensions 1536. The generation deployment remains
`AZURE_OPENAI_CHAT_DEPLOYMENT`. Configure the ignored `.env` as described in the
[usage guide](usage.md#configure-azure-for-the-pipeline-steps).

Offline inspection uses the stored run's configuration identity, model, inputs
and condition ID. Select an actual stored variant folder and keep all execution
controls false. A baseline run cannot be relabelled as a variant, and an absent
variant result cannot be inferred from the configuration table. Model responses
are stored unchanged.

## Graph reuse and source evidence

G-EMBED and G-FINAL preserve these six nonvector tables in their native format:
`documents`, `text_units`, `entities`, `relationships`, `communities` and
`community_reports`. Their file checksums must match the selected source graph.
The changed embeddings cover `text_unit_text`, `entity_description` and
`community_full_content`, followed by query embeddings from the same changed
model. No new entity or relationship extraction occurs in these two conditions.
The complete native vector store belongs to the new condition's index.

CHUNK uses the page-evidence projection even though the generator receives
smaller text segments. Several segments can refer to the same source page.
Their ranks and text are retained; repeated page evidence receives retrieval
gain only at its first occurrence. Page relevance does not prove that an
individual segment contains every required fact.

For stored-file details, see the [Classical-RAG contract](classical_rag_artifacts.md)
and [GraphRAG contract](graphrag_artifacts.md). Preserve recorded condition IDs,
source keys, ranks, contexts, responses and accepted human judgements when
moving approved private files. Private files and executed notebook copies remain
under ignored `local/`.

## Execution settings and interpretation

Batch size, concurrency, retry limits and checkpoint storage are execution
settings. They do not define additional scientific conditions. The baseline
GraphRAG concurrency is 5; ENTITY index extraction uses 25. GraphRAG variant
retries use the configured limit of 7. Native chunking size 8191 and zero overlap
are checked to preserve each prepared input text without an additional split.

The primary contrasts compare each single-factor condition with its own baseline.
Symmetric CHUNK and EMBED comparisons use a common four-configuration valid
intersection for the architecture-gap shift. ENTITY has no corresponding
Classical-RAG factor.

FINAL selection is a qualitative, outcome-informed engineering decision.
Selection and evaluation use the same benchmark; these combinations do not
provide independent holdout confirmation, an optimal configuration or isolated
interaction effects. Primary and FINAL retrieval analyses use their respective
shared qrels pools and question-level ideal denominators. nDCG values from the
two pool versions are not interchangeable. Single-configuration valid counts
and paired intersections must also remain distinct.

For methodological detail, see thesis Section 2.8, Sections 3.4.1–3.4.2,
Tables 11–15, Appendix A.2 and the graph-audit reuse rules in Appendix B.1.
