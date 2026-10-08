# Classical RAG: stored inputs and results

[Notebook 02](../notebooks/02_classical_rag.ipynb) reads stored files and replays
retrieval without model requests. The same records support public examples and approved private results.
All private files and executed notebook copies belong under ignored `local/`.

## Prepare a PDF corpus

Notebook [01](../notebooks/01_data_and_evidence.ipynb) uses the same preparation
for the public RFC and an authorised collection of PDFs. For a corpus, place its
source specification under ignored `local/`, for example
`local/corpus/reference_packages.json`. Set `source_file` to that file and
`input_dir` to a separate ignored output folder in notebook 01. Run private copies
with the kernel working directory set to the repository's `notebooks/` folder.

The source specification extends the public question/reference format with a
`documents` list. PDF paths are relative to the specification. Document IDs must
be unique within the snapshot; list order is retained. `sha256` binds each PDF to
its bytes. `page_count`, when supplied, is checked against the physical PDF pages.

```json
{
  "corpus_snapshot_id": "CORPUS-001",
  "question_set_version": "QUESTIONS-001",
  "documents": [
    {"document_id": "guideline-a", "pdf_file": "pdfs/a.pdf", "sha256": "<PDF SHA256>"},
    {"document_id": "guideline-b", "pdf_file": "pdfs/b.pdf", "sha256": "<PDF SHA256>"}
  ],
  "questions": [
    {
      "question_id": "Q-001",
      "question_text": "<accepted question>",
      "answerability": "answerable",
      "benchmark_role": "primary_answerable",
      "reference_package": {
        "canonical_answer_summary": "<reviewed reference answer>",
        "required_facts": ["<reviewed required fact>"],
        "acceptable_variants": [],
        "prohibited_facts": [],
        "numeric_tolerance": {},
        "minimal_evidence_sets": [["eu::CORPUS-001::guideline-a::p1"]],
        "qrels": {"eu::CORPUS-001::guideline-a::p1": 2},
        "abstention_expected": false,
        "abstention_reason": ""
      }
    }
  ]
}
```

Replace placeholders and illustrative reference values with accepted inputs.
Keep each question's full reference fields as in the public specification.
`canonical_question_id`, when supplied, is preserved; otherwise it equals
`question_id`. `deferred` questions stay outside active generation. A collection
may have no abstention question. Judged pools may cover only part of the corpus:
unjudged pages do not become grade 0. Reference units and minimal evidence sets
must point to eligible pages in this snapshot.

A PDF hash can be calculated with Python's standard library:

```python
import hashlib
from pathlib import Path

pdf = Path("local/corpus/pdfs/a.pdf")
print(hashlib.sha256(pdf.read_bytes()).hexdigest())
```

The notebook retains raw pages and qualifies the text layer, then normalises
whitespace and makes one chunk per eligible page. It performs no OCR or model
request. Image-only OCR blockers and unsupported/empty pages remain explicit in
`raw_pages.jsonl`. Corpus chunk IDs include snapshot, document and physical page;
source Evidence Units use `eu::<snapshot>::<document>::p<page>`. Source-document
hashes/counts and the source-specification hash remain in the prepared manifest.
Keep the original PDFs and accepted specification alongside the prepared data.

Select the resulting folder as `data_dir` in notebook 02 or `prepared_dir` in
notebook 03. Both paths read the same `chunks`, `chunk_origins` and active
`questions` records from `run_manifest.json`. New system runs require their Azure
configuration and a separate run folder; preparation itself creates no vectors,
answers or assessments. The saved RFC replay remains available unchanged.

## Files and identities

`run_manifest.json` uses schema `classical-rag-artifacts-v1`. It identifies the
`system_id`, `condition_id`, `run_id`, `configuration_sha256` and
`question_set_version`. `artifact_kind` distinguishes `illustrative` examples
from actual stored runs. `status` records whether the run is complete.
Each `artifacts` entry has a relative `path` within the run folder and `sha256`.
Paths are resolved relative to the manifest, independently of the original machine.

| Manifest role | File / required meaning |
|---|---|
| `configuration` | JSON with model/dimension, retrieval depth, decoding and the exact prompts used |
| `chunks` | JSONL: `chunk_id`, `corpus_snapshot_id`, `document_id`, `page_number`, `text`; exact normalised page text |
| `chunk_origins` | JSONL: `chunk_id`, snapshot/document identity, `origin_evidence_unit_ids`, `projection_status`; exactly one projected Evidence Unit per baseline chunk |
| `questions` | JSONL: unique `question_id`, exact `question_text`; retain canonical IDs/cohort when present |
| `index_matrix` | NumPy `.npy`, loaded with `allow_pickle=False`; finite unit-length Float32 rows, shape `(number_of_chunks, 1536)` |
| `index_sidecar` | JSON: ordered `item_ids`, `dimension`, `embedding_model`, `normalization_status`, `index_family`, `run_id`; row `i` belongs to `item_ids[i]` |
| `query_embeddings` | JSONL: question identity and text, `technical_status`, `vector`, `embedding_model`; completed vectors have 1536 finite, nonzero values |
| `retrieval` | JSONL: question identity, `technical_status`, `index_sha256`, ordered `hits` and complete `context` |
| `answers` | JSONL: question identity, `technical_status`, `answer_text`, actual `generation_model`, format/behaviour fields; retain recorded usage and other provenance fields |

Query, retrieval and answer records share `question_id`, `system_id`, `run_id`,
`configuration_sha256` and `question_set_version`. Retain additional recorded
identifiers, including condition, canonical question, cohort, attempt and source
references. A hit contains `rank`, `score`, `chunk_id`, `evidence_unit_id`,
`projection_status`, `document_id`, `page` and the full `text`. Source and chunk
files keep the matrix-row order; ranking keeps score ties in that order.

For a new generation, an input-only `run_manifest.json` may use schema
`classical-rag-inputs-v1`, `artifact_kind="inputs"`, `question_set_version`, and
only the `chunks`, `chunk_origins` and `questions` artifact references. Each reference
still has a relative path and SHA256. With `RUN_AZURE = True`, the notebook reads
these inputs and creates the missing system artefacts in its separate output folder.
The replay mode requires the stored-run roles listed above.

The configuration hash retains the recorded configuration identity, rather than
current credentials. Native records may bind a configuration source file; keep
that identity when relocating files and hash the parameter snapshot separately
in `artifacts.configuration`. Model names describe the required model families;
deployment names are private Azure inputs. The supplied RFC fixture is an actual
Azure run with illustrative questions and populated model identifiers. A small constructed calculation in the notebook explains cosine scores and
stable ties.

## Replay and missingness

Select the run folder in the notebook and keep `RUN_AZURE = False`. The notebook
checks referenced file hashes, row/ID bindings, ranked hits, full contexts and
stored answer-format fields. It reads neither `.env` nor Azure credentials.
Ranks, source IDs, texts and contexts must match exactly. Float32 score replay
uses an absolute tolerance of 1e-6; stored score values are never replaced.

Completed records are replayed. Recorded technical failures and absent responses
remain unavailable; they are not converted to an empty successful answer or zero
quality score. Source-format validity does not imply semantic correctness.
The evaluation station handles applicability and outcome-specific denominators.

The public RFC example contains 20 page chunks and four five-place rankings.
The metric notebook uses these stored rankings with the source-reviewed example
qrels and minimal evidence sets. The supplied abstention question is outside the
primary retrieval assessment; it does not receive an artificial zero score.

## Reuse stored artefacts

Keep existing matrices, vectors, rankings, contexts and answers. Moving them into
a run folder and updating relative references needs no Azure execution. Preserve
record values, IDs, order, data types, missingness, additional provenance and exact
question wording. Field renaming, when needed, must be lossless and documented.
Original files remain unchanged. Accepted human judgements are separate fixed
inputs for evaluation; packaging cannot regenerate those decisions.

The run manifest binds this station's files. The [stored-artefact exporter](private_bundle.md)
adds field selection, code/version binding and file checksums across stations.
Export is a separate step and never triggers generation.

## Azure generation and restart

The optional notebook section writes a separate ignored run folder. It copies the
selected input records, stores configuration, creates embeddings through
`AzureOpenAI`, normalises the document matrix, and retains retrieved text and
actual chat responses. Input/configuration changes require a separate output folder.

`document_batches/` and `query_batches/` contain checkpoint JSON and raw Float32
NumPy batches. The checkpoint binds ordered IDs/text hashes, model, dimension and
batch size. Committed batch checksums are checked before reuse. A failed embedding
batch does not advance progress; completed saved answers are skipped on restart.
The saved configuration also binds the Azure endpoint, API version and deployment
names through a digest; changing these settings requires a new directory. The API
key is excluded, so key rotation does not invalidate existing results. Saved answers
must match the current run/configuration and the exact retrieval-file hash, with
unique question IDs and complete coverage before a completed manifest is written.
An interrupted generation has no completed manifest. Errors propagate visibly.

The SDK uses at most one transient-error retry. There is no answer-repair request.
New model responses are not guaranteed to match previous responses, even with a
fixed seed. No generation is needed for offline replay or private export.

For methodological detail, see thesis Section 2.5, Table 3 and Appendix C, Table 25.
