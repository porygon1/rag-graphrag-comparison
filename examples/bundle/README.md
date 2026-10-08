# Stored-artefact export example

[`selection.json`](selection.json) selects necessary scalar fields from the
illustrative [evaluation inputs](../evaluation/README.md). The optional judge
packet is excluded. The example demonstrates field selection and file checksums
without private data.

The generated ZIP belongs under ignored `local/delivery/`. Repeating the export
with identical inputs and code produces identical ZIP bytes. Extract the file
separately, verify both manifests and recalculate the illustrative retrieval
metric with the installed package. No credentials or model requests are needed.

See [export instructions](../../docs/private_bundle.md#public-export-check)
for the command and acceptance checks.
