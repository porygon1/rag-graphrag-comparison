# GraphRAG: native index, context and source evidence

Read [GraphRAG indexing](../notebooks/03_graphrag_index.ipynb) before
[Local Search](../notebooks/03_graphrag_local_search.ipynb). The first notebook
inspects or creates a native index; the second reads its saved responses or queries
that index. Both use the same records for the public RFC example and approved
private inputs.

Use the pinned GraphRAG environment for installation, notebooks and checks:

```shell
uv sync --locked --extra pdf --extra graphrag --extra evaluation
uv run --extra pdf --extra graphrag --extra evaluation jupyter lab
```

The default modes make no model requests and require no Azure credentials.
Private files and executed notebook copies belong under ignored `local/`.

## Index files and bindings

`index_manifest.json` uses schema `graphrag-index-artifacts-v1`. It records
`status`, `graphrag_version`, `run_id`, `condition_id` and `question_set_version`.
Each `artifacts` entry contains a relative `path` inside the run folder and
`sha256`. The notebooks check these file bindings before reading the index.

| Manifest role | File and meaning |
|---|---|
| `chunks` | `chunks.jsonl`: ordered page chunks, including their source IDs, physical page numbers and exact normalised text |
| `chunk_origins` | `chunk_origins.jsonl`: one projected Evidence Unit for each baseline chunk, in the same order |
| `questions` | `questions.jsonl`: unique question IDs and exact question texts; retain recorded cohort and canonical IDs |
| `graph_inputs` | `input/input_records.jsonl`: `input_record_id` and unchanged page `text` |
| `input_projection` | `input_projection.jsonl`: `target_artifact_id`, `source_evidence_unit_ids` and `projection_status` |
| `configuration` | `configuration.json`: GraphRAG version, index method, question-set version, settings and a digest binding the selected Azure resource and deployments |
| `settings` | `settings.yaml`: native settings with environment placeholders for access values |
| `documents`, `text_units`, `entities`, `relationships`, `communities`, `community_reports` | The six corresponding `output/*.parquet` tables, retained in their native formats |
| `vector_file:<relative native file>` | Every file of the complete native `output/lancedb/` store, individually bound by path and checksum |

Keep the complete vector store with its native file layout. A selection of vectors
or Parquet tables alone does not replace the Local Search index. Use the declared
library version when opening these artefacts. Cache, logs, credentials and resolved
secret settings are excluded from exported datasets.

## Page identity and native settings

Each baseline prepared page becomes an input record with ID
`graphrag_input::<chunk_id>`. GraphRAG's JSONL reader preserves that ID through
`documents.id` and `text_units.document_id`. The generated document title is a
display label derived from the input filename; source identity comes from the
input projection ledger.

Local Search's `Sources.id` identifies `text_units.human_readable_id`. The mapping
is therefore:

```text
Sources.id -> TextUnit human-readable ID -> input record ID -> page Evidence Unit
```

Text-content hashes cannot substitute for that mapping because identical text
can occur on different pages. The indexing notebook checks unique input IDs,
unique human-readable TextUnit IDs, matching document references, unchanged text
and one TextUnit for each baseline page input.

The configuration uses GraphRAG 3.1.0 Standard Indexing, Azure completion model
`gpt-4.1-mini`, embedding model `text-embedding-3-small`, 1536-dimensional vectors
and concurrency 5. Token chunking uses `o200k_base`, size 8191 and zero overlap.
The entity types are `organization`, `person`, `geo` and `event`; claim extraction
and prompt overrides are disabled.

Local Search uses community level 2 and response type `Multiple Paragraphs`.
The pinned Local Search defaults use a 12000-token context budget, text-unit
proportion 0.5, community proportion 0.15, 10 mapped entities, 10 relationships
and up to five conversation-history turns. These settings do not prescribe the
actual number of each context carrier returned for a question. Completion
`call_args` remain empty; the Classical-RAG decoding and source-format checker
are separate from this native GraphRAG response contract.

## Responses and source projection

`results_manifest.json` uses schema `graphrag-local-search-artifacts-v1` and binds
three files with relative paths and SHA256:

| Manifest role | File and meaning |
|---|---|
| `native_results` | `native_results.jsonl`: original response strings and complete serialised native contexts |
| `projection_results` | `projection_results.jsonl`: deterministic source projection records and their summaries |
| `index_manifest` | `index_manifest.json`: the exact index used for the query run |

A native result records `question_id`, exact `question_text`, `status`, `response`,
`system_id`, `run_id`, `condition_id`, `question_set_version`, `query_parameters`,
`index_manifest_sha256`, `context_sha256` and `context_data`. Each context carrier
stores its DataFrame `columns`, `index` and ordered `data` values. Missing scalar
values are explicit; non-finite floats use a `special_float` marker. The notebook
converts these stored values into records for projection without sorting them.

Only ordered `sources` entries receive direct page-evidence credit. Entities,
relationships, reports and claims remain indirect context carriers. They can
contribute to the native answer context without becoming extra source positions.
Projection records retain `rank`, `carrier_local_id`, `source_evidence_unit_id`,
`projection_status`, `projection_failure_reason` and
`direct_evidence_credit_allowed`. Unknown IDs, missing edges and ambiguous edges
retain their positions without direct credit. No cosine score is assigned to
GraphRAG Sources, and missing positions are not filled.

Replay checks index and context hashes, question identity, query parameters and
the equality of the recalculated projection with the saved projection. A failed
or empty native query remains an error; it is not converted into a successful
blank answer. The original native citation and response syntax is retained.

## Optional new Azure work

Load the ignored `.env` only when making new requests:

```shell
uv run --extra pdf --extra graphrag --extra evaluation --env-file .env jupyter lab
```

For new indexing, run notebook 01 to prepare chunks, origins, questions and their
input-only manifest. In the indexing notebook, select `prepared_dir`, a distinct
ignored `azure_dir` and `RUN_AZURE_INDEX = True`. No existing graph or answers are
required. The notebook invokes the official `python -m graphrag index` command
with method `standard`. A completed bound index is reused; GraphRAG's native
file cache can reuse completed model work during an unchanged interrupted run.

For new Local Search responses, select the completed ignored index folder and
set `RUN_AZURE_QUERY = True`. Reindexing is unnecessary. Saved successful
responses with matching questions, index binding and query parameters are reused.
Changed inputs or settings require a new run folder. The resource/API-version/
deployment digest excludes the API key, so key rotation preserves the binding.
New model responses are not guaranteed to match earlier responses.

## Private inputs and reference assessment

Use the same notebooks and manifests for approved private files; keep executed
copies and their outputs under ignored `local/`. In Local Search, set
`reference_path` to the matching approved reference file, or to `None` to display
responses and projections without metric calculation. Reference records identify
the question-set version and question IDs and supply shared qrels and
`minimal_evidence_sets`. The notebook uses the existing nDCG function on the first
five projected Source positions. For a valid assessed ranking it also shows
whether those positions contain a complete reference evidence set. An unanswerable
question is outside that primary retrieval assessment.

Preserve IDs, native table/store formats, source order, contexts, responses and
accepted human judgements. Moving approved stored artefacts into a portable
folder requires no model requests. The [stored-artefact exporter](private_bundle.md)
adds field selection and code/version binding; it is separate from indexing
and query generation and never triggers either workflow.

For method details, see thesis Section 2.5 and Appendices F and G.

The controlled conditions use the same notebook and manifest contracts. Structure
inputs retain their stable segment IDs and source intervals. See [controlled
changes](controlled_changes.md) for model selection, entity types and native
embedding-only reuse of G0 or G-ENTITY tables.
