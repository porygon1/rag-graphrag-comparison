# Illustrative evaluation inputs

This dataset contains invented evidence IDs, relevance grades, rankings and
assessment values for 28 benchmark cases. It uses the same calculation
functions and file contracts as accepted private inputs. It contains **no human
quality ratings of the saved RFC model answers** and no private thesis results.

PRIMARY has seven conditions. FINAL has four main conditions and C-EMBED for
the supplemental comparison, with its own expanded shared relevance pool.
Correctness and retrieval use the 24 A cases; behaviour also uses four U cases.
The six nominal Genuine User categories form a separate 24-question example.

Examples include repeated source units, missing rank positions, failed projection,
answerable abstention, technical failure and semantic non-applicability. These
states remain distinct in calculations. Graph and error assessments have their
own denominators. Error dimensions use the same `answer`, `citation`, `retrieval`,
`projection` and `technical` identities as the calculation contract; this small
fixture supplies no separate projection-error assessment. The extended entity example uses 22 observed raw labels to
demonstrate deterministic type coverage beyond the configured nine-type list.

[`manifest.json`](manifest.json) binds each ordered JSONL file by relative path
and SHA256. Dataset kind is `illustrative` and acceptance identities are null.
No record is represented as an actual human-accepted corpus judgement.
The [input contract](../../docs/evaluation_artifacts.md) describes all roles.

[`judge_packets.jsonl`](judge_packets.jsonl) is a separate optional packet for
the public RFC example. It retains one actual unchanged C0 answer and its complete
native context, with reference-corpus pages in a separate evidence scope. It
contains no generated proposal or accepted grade. The optional Azure step saves
new proposals under ignored `local/` for human review.

Read [answer and paired outcomes](../../notebooks/05a_answer_and_paired_outcomes.ipynb),
[diagnostics](../../notebooks/05b_diagnostic_assessments.ipynb) and
[result surfaces](../../notebooks/06_reported_results_and_limits.ipynb). Their
default execution makes no model requests. The result plot labels its input
kind and valid case counts explicitly. Figure 2 in notebook 06b uses the
separately bound saved RFC baseline results from notebook 05; the remaining
default figures use this illustrative dataset.

The three constructed appendix records retain the cited rankings and relevance
pools. Appendix A.3 supplies no minimal evidence set, so Evidence Recall is
unavailable there. Figures 17 and 22 use the single-page set `{A}`; their
Evidence Recall remains 1. These records are hypothetical, not study judgements.
