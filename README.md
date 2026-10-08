# From Guidelines to Grounded Answers

**Comparing Classical RAG and Microsoft GraphRAG Local Search**

Code repository for the master's thesis *From Guidelines to Grounded Answers*
(2026).

[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?style=flat&logo=python&logoColor=white)](#run-the-public-example)
[![uv managed](https://img.shields.io/badge/uv-managed-DE5FE9?style=flat&logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Jupyter notebooks](https://img.shields.io/badge/Jupyter-Notebooks-F37626?style=flat&logo=jupyter&logoColor=white)](#follow-the-investigation)
[![Azure OpenAI](https://img.shields.io/badge/Azure-OpenAI-0078D4?style=flat)](docs/usage.md#configure-azure-for-the-pipeline-steps)

[Reading path](#follow-the-investigation) ·
[Run the example](#run-the-public-example) ·
[Methods](docs/evaluation_methods.md)

This repository compares Classical RAG and Microsoft GraphRAG Local Search for
question answering over guidelines. It covers document preparation, retrieval
and answer generation, controlled configuration changes, and evaluation against
shared source-page evidence.

Classical RAG retrieves text chunks by cosine similarity. GraphRAG Local Search
uses a graph of entities, relationships and source text. Each system retains its
native context, prompt and citation rules; retrieval and answer quality are
evaluated separately.

## Follow the investigation

The six stations connect the methods to their inputs, intermediate artefacts and
calculations. Read them in order; select **Restart Kernel and Run All Cells** to
execute a notebook from a clean state.

| Station | Notebooks | What becomes visible |
|---|---|---|
| **1. Data and evidence** | [Pages and references](notebooks/01_data_and_evidence.ipynb) | PDF extraction, page identity, prepared text and reference evidence. |
| **2. Classical RAG** | [Vector retrieval and answers](notebooks/02_classical_rag.ipynb) | Embeddings, ranked source text, full generation context, actual answers and source markers. |
| **3. GraphRAG Local Search** | [Indexing](notebooks/03_graphrag_index.ipynb), [Local Search](notebooks/03_graphrag_local_search.ipynb) | Native graph tables, mixed context and the projection of ordered Sources onto page evidence. |
| **4. Controlled changes** | [Conditions](notebooks/04_controlled_changes.ipynb), [Structure-aware segments](notebooks/04a_structure_chunking.ipynb) | The five single-factor conditions, two FINAL combinations and shared source-exact segments. |
| **5. Evaluation** | [Retrieval metrics](notebooks/05_retrieval_metrics.ipynb), [Answer and paired outcomes](notebooks/05a_answer_and_paired_outcomes.ipynb), [Diagnostics](notebooks/05b_diagnostic_assessments.ipynb) | Metric calculations, reference rubrics, applicable populations, paired effects, graph/error diagnostics and genuine-user categories. |
| **6. Results and limits** | [Paired comparisons](notebooks/06_reported_results_and_limits.ipynb), [Tables](notebooks/06a_reported_tables.ipynb), [Figures](notebooks/06b_reported_figures.ipynb) | PRIMARY/FINAL calculations, reported tables and figures, and their interpretation limits. |

The notebooks import small reusable functions from
[`src/rag_comparison`](src/rag_comparison/). Experiment settings are centralised in
[`config.py`](src/rag_comparison/config.py). The
[reproduction matrix](docs/reproduction_matrix.md) connects each reported result
to its required inputs and calculation.

## Run the public example

The public pipeline uses the 20-page **RFC 2795: The Infinite Monkey Protocol
Suite**, a specification for a fictional network of monkeys and typewriters.
[Example data](examples/data/README.md) documents the unchanged PDF and questions.
Saved embeddings, graph artefacts, contexts and answers show both system paths
without new model requests. The baseline retrieval plot uses these saved runs
and source-checked RFC page grades. Configuration and answer-quality plots use
illustrative inputs; they do not rate the saved RFC answers.

Use Python 3.13.7 and [uv](https://docs.astral.sh/uv/). From the repository root:

```shell
uv sync --locked --extra pdf --extra graphrag --extra evaluation
uv run --extra pdf --extra graphrag --extra evaluation jupyter lab
```

Default examples require no private data or Azure credentials. Use the main
Python kernel except for notebook 04a, which needs the
[structure kernel](docs/usage.md#set-up-the-structure-kernel). Read the
[usage guide](docs/usage.md) for complete environment setup, new Azure runs,
reusing stored results, and optional implementation checks.

## Documentation

| Topic | Guide |
|---|---|
| **Getting started** | [Installation, Azure configuration, reuse and checks](docs/usage.md) |
| **Pipeline workflows** | [Classical RAG](docs/illustrations/classical-rag-workflow.pdf), [GraphRAG Local Search](docs/illustrations/graphrag-workflow.pdf); [figure sources](docs/illustrations/README.md) |
| **Experiment configurations** | [Baselines, controlled changes and FINAL conditions](docs/controlled_changes.md) |
| **Evaluation methods** | [Retrieval, answer quality, paired comparisons and diagnostics](docs/evaluation_methods.md) |
| **Data and artifact formats** | [Classical RAG](docs/classical_rag_artifacts.md), [GraphRAG](docs/graphrag_artifacts.md), [structure-aware segments](docs/structure_artifacts.md), [evaluation inputs](docs/evaluation_artifacts.md) |
| **Reproducing the results** | [Thesis results and required calculations](docs/reproduction_matrix.md); [exporting stored artefacts](docs/private_bundle.md) |

## Data availability

The study corpus and experiment data are not publicly available. Public examples
use RFC 2795 and illustrative evaluation inputs. Reproducing the thesis results
requires the matching approved inputs described in the
[reproduction matrix](docs/reproduction_matrix.md).

## License and citation

Original code and documentation use the [MIT License](LICENSE), which permits
commercial use with the copyright and license notices retained. Third-party
libraries and the [RFC source](examples/data/README.md#source-permission) retain
their own terms. The license does not grant rights to private corpus or result data.

Use [CITATION.cff](CITATION.cff) to cite `rag-graphrag-comparison`, version 0.1.0.
The [thesis method references](docs/reproduction_matrix.md#method-references-in-the-thesis)
identify the corresponding sections and appendices.
