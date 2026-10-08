# Structure-aware segments and prepared inputs

[Notebook 04a](../notebooks/04a_structure_chunking.ipynb) applies the CHUNK method
to already prepared page text. It uses Docling `HybridChunker` with the
`o200k_base` tokenizer and a blank German spaCy sentencizer. The source/provenance
adapter is [`rag_comparison.structure`](../src/rag_comparison/structure.py);
method parameters are in [`config.STRUCTURE_POLICY`](../src/rag_comparison/config.py).

## Environment and inputs

Use the **Python (structure)** kernel. The
[Structure setup](usage.md#set-up-the-structure-kernel) installs the pinned
structure packages into `.venv-structure` and registers that kernel with the main
Jupyter environment. Do not combine the structure extra with `pdf` or `graphrag`.
The structure notebook requires neither a PDF parser nor Azure credentials.

The public default uses [structure example inputs](../examples/structure/).
To process the RFC pages, first run notebook 01 and select its prepared inputs
and raw page records. Raw page records retain the extracted line structure;
normalised page chunks remain the authoritative stored text. This step does not
extract the PDF again, use OCR or rewrite its source content.

| Input | Required meaning |
|---|---|
| Normalised page chunks | Ordered `chunk_id`, `corpus_snapshot_id`, `document_id`, `page_number` and whitespace-normalised `text` |
| Raw page records, `raw_pages.jsonl` | `document_id`, `page_number` and exact extracted `text`, including line breaks; each record's whitespace normalisation equals its page chunk text |
| Page origins | Matching `chunk_id`, exactly one `origin_evidence_unit_ids` entry and `projection_status="projected"` |
| Questions | Exact question IDs/texts and any recorded cohort/reference identity, reused unchanged |
| Prepared manifest | Relative file references with SHA256 bindings and the question-set version |

Pages are grouped by document for structure detection. Numbered headings,
lists, repeated page-edge material and contents/history structures inform the
partition; they do not remove stored text. A standalone page split that ignores
the document's confirmed structure does not implement this method.

## Source-exact partition

The notebook passes a configured native HybridChunker, tokenizer and sentence
splitter to the adapter. `merge_peers=True` allows suitable neighbouring content
to share a segment within the 800-token cap. The adapter follows source offsets
when returning the exact text parts and attaches the original page provenance.
It does not replace the native library with a fixed token-window algorithm.

For a normalised page `text`, every stored segment satisfies:

```python
segment["text"] == text[segment["character_start"] : segment["character_end"]]
```

Offsets are zero-based, half-open Unicode code-point indices in the complete
normalised page. They are not byte offsets, raw-PDF coordinates or token indices.
The segments cover the complete page in order: the first start is zero, adjacent
end/start offsets are equal, and the final end is the page's character length.
There are no gaps or overlapping source characters. Each nonempty segment has
at most 800 `o200k_base` tokens and remains within one source page.

The segment identity binds the policy ID, original page chunk ID, character
start/end and full-page text SHA256. Changes to any of these inputs produce a
different identity. Tokenization round trips preserve the segment's Unicode text.

## Outputs and downstream aliases

| Output | Meaning |
|---|---|
| Segment records | `segment_id`, `segment_index_on_page`, `chunking_config_ref`, `encoding_model`, source snapshot/document/page, `source_page_chunk_id`, original `character_start`/`character_end`, `token_count`, `input_text_sha256` and exact `text` |
| Projection ledger | Segment target ID, original source page ID, `source_evidence_unit_ids`, projected status and the same original character offsets |
| Graph input records | Segment ID as `input_record_id`, exact segment text and its source identity |
| Shared prepared inputs | Segments exposed as `chunks.jsonl`, source origins as `chunk_origins.jsonl`, unchanged `questions.jsonl` and a SHA256-bound `run_manifest.json` |

For the shared system input, `chunk_id` is an alias of `segment_id`. It does not
replace `source_page_chunk_id` or reset offsets to zero for every segment.
The origin records retain the page Evidence Unit in `origin_evidence_unit_ids`
so Classical RAG and GraphRAG both project the selected segment to the same
source page. Segment fields and provenance remain available alongside these
aliases.

Select this prepared folder for C-CHUNK, G-CHUNK or C-FINAL in the existing
system notebooks. Both systems use the same ordered segments; G-FINAL instead
uses baseline page segmentation and the G-ENTITY graph. New embeddings, indexes
and responses are written only by the relevant Azure execution sections.
Preparing the segments or replaying stored results makes no model requests.

Raw pages, segments, manifests and executed notebook copies containing private
inputs belong under ignored `local/`. Relocation preserves IDs, text, offsets,
source links and question wording; relative manifest paths and checksums bind
the moved files. A source page's relevance grade does not establish which
Required Facts a particular segment contains. See the
[controlled-change contract](controlled_changes.md#graph-reuse-and-source-evidence)
for the retrieval distinction.

For methodological detail, see thesis Section 2.8 and the segmentation example
and measurement limits in Sections 3.4.1 and 4.4.
