# Public structure-segmentation example

The saved input records use the 20 pages of the unmodified RFC 2795 PDF.
[Source, SHA256 and redistribution notice](../data/README.md) apply to these
derived text records. `page_inputs/` retains the raw extracted page text alongside
the normalised page chunks, origins and four illustrative questions.

The source-exact CHUNK method produces **44 segments**. The largest has **687
`o200k_base` tokens**, below the configured cap of 800. Every stored segment equals
its original page's `[character_start:character_end]` slice. The ordered segments
cover all original text without overlap; all retain their page Evidence Units.

| File | Meaning |
|---|---|
| `segments.jsonl` | Original segment IDs, source-page IDs, Unicode offsets, token counts and exact text |
| `projection_edges.jsonl` | Segment-to-original-page evidence mapping |
| `graph_inputs.jsonl` | Native GraphRAG input records with the same segment IDs and text |
| `chunks.jsonl` | Pipeline input aliases: `chunk_id` equals the retained `segment_id` |
| `chunk_origins.jsonl` | The same page Evidence Units in the existing pipeline contract |
| `questions.jsonl` | The unchanged illustrative questions |
| `structure_details.jsonl` | Document-confirmed structural boundaries and source handling |
| `run_manifest.json` | Source manifest identity, policy, relative paths and SHA256 |

[Notebook 04a](../../notebooks/04a_structure_chunking.ipynb) computes this population
with the pinned native Docling chunker and reusable source adapter. It saves the
shared inputs under ignored `local/`; no model request is made. Use those inputs
for C-CHUNK, G-CHUNK and C-FINAL through the existing pipeline notebooks.
The stored example contains preparation artefacts, with no variant model answers
or accepted answer-quality scores.

[Notebook 04](../../notebooks/04_controlled_changes.ipynb) reads the saved population
and explains its place in the controlled conditions. The
[structure contract](../../docs/structure_artifacts.md) describes the fields,
source-exact partition and separate kernel setup.
