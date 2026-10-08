# Public Classical-RAG example

The fixture uses the 20 complete, whitespace-normalised pages of the unmodified
[RFC 2795 PDF](../data/rfc2795.pdf). Source identity, SHA256, redistribution terms
and four illustrative source-reviewed reference packages are documented in the
[data notes](../data/README.md).

Vectors and answers are actual Azure OpenAI outputs for this example. Embeddings
use `text-embedding-3-small`, 1536 dimensions; the returned chat model is
`gpt-4.1-mini-2025-04-14`. Matrix row `i` belongs to physical source page `i + 1`.
Prompts and decoding are bound in [`configuration.json`](configuration.json).
Each of the four queries retrieves five real source pages from the 20-page matrix.

| Question | Retrieved physical pages | Response behaviour | Source format |
|---|---|---|---|
| DEMO-IMPS-Q-001 | 8, 7, 9, 17, 10 | answers | valid |
| DEMO-IMPS-Q-002 | 12, 13, 3, 16, 14 | answers | invalid |
| DEMO-IMPS-Q-003 | 15, 13, 17, 16, 12 | answers | valid |
| DEMO-IMPS-Q-004 | 9, 10, 11, 17, 8 | abstains | valid |

All responses are retained unchanged, including the source-format failure in the
second response. The fourth response is the exact abstention sentence. Technical
completion, source format and semantic quality are distinct recorded properties;
this fixture contains no accepted answer-quality scores.

The first ranking omits reference page 16, so its full three-page reference set
is absent even though its nDCG@5 value is valid. The metric notebook displays these
two quantities separately, using the saved rankings and illustrative reference pool.

[`run_manifest.json`](run_manifest.json) binds the files with relative paths and
SHA256. The [artifact contract](../../docs/classical_rag_artifacts.md) explains
the fields. Default replay requires no credentials or new model requests.

Azure resource values, deployment names and credentials are excluded; the
configuration retains an opaque digest of the operational settings.
