# Using the repository

Run the commands below from the repository root. The default notebooks use
public examples and saved artefacts without new model requests. The
[reading path](../README.md#follow-the-investigation) lists the six stations.

## Main environment

Use Python 3.13.7 and [uv](https://docs.astral.sh/uv/). From this repository folder:

```shell
uv sync --locked --extra pdf --extra graphrag --extra evaluation
uv run --extra pdf --extra graphrag --extra evaluation jupyter lab
```

All default examples run without private data, credentials or model services.
Keep `--extra pdf --extra graphrag --extra evaluation` in subsequent main-environment
commands. Use the main Python kernel except for notebook 04a, which needs the
structure kernel below.

### Set up the structure kernel

The pinned structure packages use a separate environment because their Pillow
and Typer requirements conflict with the PDF/GraphRAG environment. Both environments
install `rag_comparison`; notebook imports use the installed package.

From the repository folder, use PowerShell:

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-structure'
uv sync --locked --extra structure
uv run --extra structure python -c 'import tiktoken; tiktoken.get_encoding("o200k_base")'
uv run --extra structure python -m ipykernel install --prefix .venv --name rag-structure --display-name 'Python (structure)'
Remove-Item Env:\UV_PROJECT_ENVIRONMENT
uv run --extra pdf --extra graphrag --extra evaluation jupyter lab
```

Select **Python (structure)** for notebook 04a. The tokenizer command caches the
public `o200k_base` vocabulary on first use; it makes no model request. The
structure method uses a blank German spaCy pipeline with a rule-based sentencizer.
Notebook 01 supplies the prepared normalised and raw page text.
See [structure inputs and outputs](structure_artifacts.md).

On Linux, use `UV_PROJECT_ENVIRONMENT=.venv-structure uv ...` for the structure
commands, then launch Jupyter without that prefix. The interpreter is
`.venv-structure/bin/python`. For full-source Pyright checks, use that environment's
`lib/python3.13/site-packages` as an additional search path; the supplied
configuration names the Windows `Lib/site-packages` location.

Authorised PDF collections use the same preparation in notebook 01. Select a
private document specification and output folder, then pass the prepared folder
to both system paths. The [PDF corpus input contract](classical_rag_artifacts.md#prepare-a-pdf-corpus)
defines document identities, hashes and accepted questions/references.

## Configure Azure for the pipeline steps

Model calls use Azure OpenAI, including GraphRAG's native Azure provider.
Copy [`.env.example`](../.env.example) to the ignored `.env` file and fill in your
resource endpoint, API key, supported API version and deployment names. Deployment
names are your resource's identifiers and may differ from model names.

```shell
uv run --extra pdf --extra graphrag --extra evaluation --env-file .env jupyter lab
```

Keep access values out of notebook cells, saved outputs and metadata. New model
requests use explicit controls, all disabled by default:

| Step | Notebook control |
|---|---|
| Classical embeddings and answers | `RUN_AZURE` |
| GraphRAG indexing | `RUN_AZURE_INDEX` |
| GraphRAG Local Search queries | `RUN_AZURE_QUERY` |
| Assessment proposals for human review | `RUN_AZURE_JUDGE` |

The default RFC preparation in notebook 01 writes its input manifest under
`local/classical_rag/rfc2795-inputs/`, including raw pages for segmentation. For a new
Classical run, select that folder as `data_dir`, choose an ignored output folder
and enable `RUN_AZURE`. The generation mode starts from page chunks, source
origins and questions; completed matching checkpoints and answers are reused.

GraphRAG indexing takes the prepared inputs. Local Search takes a completed index.
Their [artefact contract](graphrag_artifacts.md) defines the native tables,
complete vector-store binding and saved-query reuse. For variants, follow the
[controlled-change workflow](controlled_changes.md#prepare-and-execute-a-condition).
EMBED and FINAL use `AZURE_OPENAI_EMBEDDING_LARGE_DEPLOYMENT`; small-embedding
conditions use `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`.

Notebook 05a creates optional assessment proposals through the deployment in
`AZURE_OPENAI_JUDGE_DEPLOYMENT`. It binds the unchanged answer, full native context,
reference evidence and citation trace. A person must review and accept a proposal
before it enters scoring. See [evaluation methods](evaluation_methods.md).

## From stored answers to reported results

The same notebooks can inspect approved private inputs under ignored `local/`.
Use executed notebook copies there and keep all model controls `False`.
The shared notebook sources retain public-example outputs only.

For system inspection, select a stored run in notebook 02 or the matching index
and query folders in notebooks 03. The
[Classical-RAG](classical_rag_artifacts.md) and
[GraphRAG](graphrag_artifacts.md) contracts bind inputs, rankings, contexts,
unchanged answers and the required index files. Local Search's `reference_path`
can select approved reference evidence or be `None` for inspection without metrics.

For result calculation, notebooks 05a, 05b, 06 and 06a select a dataset through
`manifest.json`. The public default is `examples/evaluation/`; private datasets
supply accepted reviews and scoped retrieval/reference inputs. PRIMARY
covers baselines and single-factor changes. FINAL has its own shared relevance
pool, so its retrieval baseline values must be calculated on that pool. Genuine
User remains a separate nominal evaluation. Run 06b after 06 and 06a with their
matching output folders.

File hashes are checked before calculation. Each outcome retains its applicable
and valid population; missing inputs are not scored as valid zero observations.
The [evaluation input contract](evaluation_artifacts.md) and
[method description](evaluation_methods.md) specify these rules.

### Data availability

The study corpus and experiment data are not publicly available. Public examples
use RFC 2795 and illustrative evaluation inputs.

## Reuse the evaluation core

The evaluation functions can also be imported into other Python projects:

```python
from rag_comparison.metrics import ndcg_at_k

qrels = {"A": 2, "B": 0, "C": 1, "D": 2, "E": 0, "F": 1}
score = ndcg_at_k(["A", "B", "C", "D", "E"], qrels)
print(score)  # 0.801747
```

`qrels` are relevance judgements for distinct evidence units in the shared pool.
The function uses linear grades `0/1/2` and `TOP_K=5`. Repeated units keep their
positions and receive gain once. An incomplete or unjudged ranking, failed
projection or zero ideal gain returns `None`.

## Check the implementation

Tests check metric calculations, source mappings and evaluation logic against known examples.
They are optional for running the notebooks and useful after modifying the code.

```shell
uv run --extra pdf --extra graphrag --extra evaluation python -m unittest discover -s tests -v
uv run --extra pdf --extra graphrag --extra evaluation ruff check .
uv run --extra pdf --extra graphrag --extra evaluation ruff format --check .
uv run --extra pdf --extra graphrag --extra evaluation pyright
```

The main environment skips structure tests when their optional packages are
absent. Run those checks in the structure environment:

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-structure'
uv run --extra structure python -m unittest discover -s tests -p test_structure.py -v
Remove-Item Env:\UV_PROJECT_ENVIRONMENT
```

Scientific dependencies are pinned in `pyproject.toml` and `uv.lock`. The metric,
assessment and paired-statistic functions use the Python standard library;
the system and structure notebooks call their pinned package APIs directly.
