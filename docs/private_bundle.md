# Export stored evaluation artefacts

The exporter selects declared files and fields from an existing dataset, checks
their SHA256 bindings and writes a portable ZIP. It reads stored artefacts without
modifying them and makes no model requests. The [evaluation contract](evaluation_artifacts.md)
defines the input roles; the [reproduction matrix](reproduction_matrix.md) links
reported result surfaces to the required inputs.

## Public export check

Run this example from the repository folder:

```shell
uv run --extra pdf --extra graphrag --extra evaluation python scripts/export_private_bundle.py --input examples/evaluation --output local/delivery/public-fixture.zip --selection examples/bundle/selection.json
```

The [example selection](../examples/bundle/selection.json) keeps necessary scalar
fields from the illustrative evaluation inputs. It contains no private corpus
material or accepted thesis scores. No credentials are needed.

## Select files and fields

For other stored datasets, supply a source folder containing `manifest.json` and
its SHA256-bound files via `--input`, a selection file via `--selection`, and a ZIP
path under ignored `local/` via `--output`. The exporter accepts the evaluation
contract and declared additional roles. The
[`private_bundle_selection.json`](private_bundle_selection.json) profile specifies
the roles and field trees used for the reported-result input contracts.

Every selected file must be declared and intact. JSON and JSONL files require
an explicit allowed field tree. Unknown fields are removed, including nested
objects. Allowed values keep their types, record order, duplicates and nulls.
An explicitly allowed non-JSON file is copied byte-for-byte. Only selected roles
enter the archive. Required inputs depend on the calculation and inspection;
omit logs, credentials, caches and unrelated working files.

The ZIP contains the selected files, portable `manifest.json` and
`package_manifest.json`. The latter binds file sizes and hashes, the source
manifest, field selection and matching repository code. Fixed ZIP metadata and
member ordering make repeated exports of identical inputs and code byte-identical.
Export performs no upload.

## Include calculated results

Use an extracted, field-selected input dataset so that calculations and export
refer to exactly the same `manifest.json`. In ignored copies of notebooks 06,
06a and 06b, set `data_dir` to that dataset and run them in this order:

1. 06 writes `reported_analysis.json`.
2. 06a writes `reported_tables.json` and readable `reported_tables.md`.
3. 06b reads those two output folders and writes the data and PNGs for Figures 2–6.

Use the following relative output folders from `notebooks/`:
`../local/evaluation/reported_example`, `../local/evaluation/reported_tables_example`
and `../local/evaluation/reported_figures_example`. In 06b, set `analysis_dir`
and `tables_dir` to the first two folders. Keep private notebook copies and
their outputs under ignored `local/`; the public notebooks retain their example data.
Before running each private copy, set its kernel working directory to the
repository's `notebooks/` folder. For example, add a first cell with
`%cd "/absolute/path/to/rag-graphrag-comparison/notebooks"`, replacing the path
with your checkout location. This keeps all `../examples/` and `../local/` paths
relative to the same place as in the public notebooks.
These calculations use saved outcomes and accepted assessments, with no question
generation, model request or new assessment.

From the repository folder, include the three bound output folders:

```shell
uv run --extra pdf --extra graphrag --extra evaluation python scripts/export_private_bundle.py --input local/delivery/extracted --output local/delivery/results.zip --selection docs/private_bundle_selection.json --results local/evaluation/reported_example local/evaluation/reported_tables_example local/evaluation/reported_figures_example
```

The `result_roles` selection keeps reported calculations, tables and Figures 2–6.
The archive's `results/` folder contains the readable tables, figure PNGs,
selected calculation JSON and its own manifest. That manifest binds the exported
result files to the exact input manifest. Generated notebook copies, logs,
unreported intervals and additional exploratory plots are excluded.

## Verify after extraction

Extract to an ignored folder outside the source dataset. From the repository
folder, verify file sizes, hashes and the matching code snapshot:

```python
import hashlib
import json
from pathlib import Path

root = Path("local/delivery/extracted")
package = json.loads((root / "package_manifest.json").read_text(encoding="utf-8"))
for name, expected in package["files"].items():
    path = (root / name).resolve()
    assert path.is_relative_to(root.resolve())
    assert path.stat().st_size == expected["size_bytes"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected["sha256"]
for name, expected in package["code"]["files"].items():
    path = Path(name)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
```

For an archive with calculated results, additionally check the result-to-input
binding and selected result files:

```python
from rag_comparison.artifacts import verify_artifacts

results = json.loads((root / "results/manifest.json").read_text(encoding="utf-8"))
assert (
    results["input_manifest_sha256"]
    == hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
)
verify_artifacts(root / "results", results)
```

The notebooks check dataset bindings through `verify_artifacts`. Select the
extracted folder as `data_dir` in the relevant evaluation notebook and keep
model-generation controls false. For the public example, repeat the illustrative
retrieval calculation in 05; other calculations require their declared input roles.
Private executed copies and generated results remain under `local/`.

Relocation must preserve identities, grades, ranks and applicability states.
Compare results using the matching scope, population, direction and display
precision. Offline calculation does not revise accepted human assessments.
A different code hash requires the corresponding repository snapshot or a new,
explicitly checked export; it is not silently ignored.
