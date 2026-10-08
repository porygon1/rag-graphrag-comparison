# Evaluation methods

The evaluation notebooks use reference packages, stored system results and fixed
assessments. The public evaluation dataset has invented evidence IDs, rankings
and grades. Its assessments are explicitly illustrative; they are not human
ratings of the saved RFC responses. Approved private datasets use the same
[file contracts](evaluation_artifacts.md).

## References and cohorts

Reference packages specify required facts, acceptable variants, prohibited facts,
numeric tolerances and minimal sufficient evidence sets. Correctness is assessed
against this reference and its source evidence. Faithfulness is assessed against
the actual complete generation context. Additional reference-corpus evidence does
not supply information that was absent from that context.

The benchmark distinguishes answerable questions (`A`) from questions for which
abstention is expected (`U`). Retrieval, correctness, faithfulness and citation
comparisons use `A`. Correct-answer/abstention behaviour uses `A` and `U`, retaining
their separate counts. Small cohorts are count-only. Genuine User has its own
reference interpretation and nominal assessment categories.

The notebooks read provided reference packages. Question/reference preparation is
described in thesis Appendix D. Draft proposals require source review and explicit
human approval before they become reference inputs.

## Retrieval and shared evidence

Both system paths are assessed on source-native page evidence. Classical RAG
provides its native retrieval order; GraphRAG provides the projected order of its
Sources context. Other graph carriers do not receive direct page-retrieval credit.
Structure segments retain their source-page projection. Page relevance alone
does not prove that a selected segment contains every required fact.

The shared question-level relevance pool assigns one accepted grade, `0`, `1` or
`2`, to each distinct evidence unit. Conflicting grades require an explicit
decision; they are not combined by maximum, average or vote. All conditions in
one evaluation scope use the same pool and ideal denominator.

For the first five positions:

```text
DCG@5 = sum(grade_at_rank_i / log2(i + 1))
nDCG@5 = DCG@5 / IDCG@5
```

Grades are linear. The ideal ranking sorts the distinct pool grades, including
relevant evidence outside the retrieved five. Repeated evidence keeps its rank
position and gains credit only at its first occurrence. Later positions are not
promoted to fill missing or duplicate positions.

The Appendix A.3 example has retrieved grades `[2, 0, 1, 2, 0]` and ideal grades
`[2, 2, 1, 1, 0]`. It produces DCG `3.361353`, IDCG `4.192536` and nDCG `0.801747`.

`Judged@5` divides the number of assessed projected positions by five. A judged
zero is valid evidence of no relevance; an unjudged position is unavailable.
Missing ranks, unsuccessful projections, unjudged units and zero ideal gain
prevent a valid aggregate nDCG observation. `score_question` retains diagnostic
calculations and their validity status; aggregation uses that status.

Evidence Recall@5 is `1` when the unique projected first-five units contain at
least one complete minimal evidence set, otherwise `0`. A missing reference set
is unavailable. Partial overlap is a diagnostic quantity, not binary recall.

## Answer assessments

Accepted assessments describe the unchanged answer. The three quality dimensions
use ordinal grades `0–3`; larger values indicate a better assessment within that
dimension. They are not averaged into a quality score.

| Dimension | Assessment basis | Grade interpretation |
|---|---|---|
| Answer correctness | Required facts, reference evidence, variants, prohibited facts and tolerances | `3`: correct and complete; `2`: correct core with minor issues; `1`: partly correct with material limitations; `0`: wrong, unsupported, contradicted or insufficient, including an answerable abstention |
| Faithfulness | The complete context actually supplied to the generator | `3`: all material claims supported; `2`: supported core with a minor unsupported detail; `1`: partial support with a material unsupported claim; `0`: material contradiction or unsupported answer |
| Citation correctness | Supporting original source evidence identified by the actual citation trace | `3`: required material claims directly supported; `2`: mostly correct with minor issues; `1`: material citation/support limitations; `0`: absent, invalid, contradictory or unsupported required citation |

Thesis Appendix A.1 contains the complete rubrics. Output-format validity and
semantic quality remain separate observations. A present response with a source
format error remains available for content assessment.

On `U`, correctness is `not_applicable_unanswerable`. An abstention on `A` has
correctness `0`. Without a content answer, faithfulness is
`not_applicable_no_answer` and citation is `citation_not_required`. These states
receive no favourable quality grade. A caveated content answer counts as an answer,
not an abstention. Missing native output or a missing accepted review remains
missing rather than receiving an ordinal grade.

Correct behaviour is binary: a substantive answer on `A`, or an abstention on `U`.
This indicates the decision to answer, not necessarily a correct substantive answer.
The behaviour table separates appropriate abstentions, failed abstentions,
over-abstentions and substantive answers; technical failures remain unavailable.

## Applicable populations and paired effects

Every outcome reports its own population:

- `N_total`: questions in the target population;
- `N_app`: questions where the outcome is semantically applicable;
- `k`: complete valid observations, or complete pairs for a contrast;
- `missing = N_app - k`: unavailable observations on an applicable surface.

Semantic non-applicability reduces `N_app`. Technical or assessment missingness
reduces `k`. Pairing happens separately for every outcome. System-level valid
counts need not equal the paired intersection. No values are imputed.

The baseline contrast is G0 minus C0. A configuration contrast is variant minus
its own baseline. Numeric outcomes use the mean question-level difference;
binary outcomes use the difference in rates on those same complete pairs.
Ordinal outcomes use wins, ties and losses, with `D = (W - L) / k`; ties remain
in the denominator. Transition matrices retain the original `0–3` levels.

For symmetric CHUNK and EMBED comparisons, first form each question's G-minus-C
gap, then subtract the baseline gap on the complete four-condition intersection.
For ordinal outcomes, each gap is a sign before subtraction. The G-only ENTITY
change is a system-specific comparison. FINAL has its own shared pool and IDCG
basis; its nDCG baseline values are not interchangeable with PRIMARY values.

Question-level and evidence-component bootstrap use 10,000 draws and seed
`20260825`. Components join questions sharing evidence, including transitive
connections. Whole components are sampled with replacement and their questions
are pooled with their original weights. Fewer than 20 complete pairs produce
counts only. Bootstrap outputs are descriptive; they do not establish a new
significance or superiority claim. Few, unequal components limit interpretation.

## Graph and error diagnostics

Graph selection uses at most 20 cases per artifact type, without replacement,
and all cases for smaller populations. Strata are raw entity-type labels,
community levels, A/U trace roles, or one relationship stratum. Reserve one item
per nonempty stratum, distribute the remainder proportionally by largest
remainder, and break ties by stratum name. Within strata, SHA256 of evaluation
ID, artifact type and stable ID determines selection; stable ID breaks hash ties.

Extended entity coverage selects one entity per observed raw type label when
the ordinary sample cannot cover them all. Observed raw labels are not limited
to the configured entity-type list. G-EMBED uses G0's structural assessments;
G-FINAL uses G-ENTITY's structural assessments and its own new Local Search
trace assessments. Structural reuse does not transfer a trace judgement.

Support counts distinguish `supported`, `partially_supported`, `unsupported`
and `not_assessable`. The support denominator excludes `not_assessable`.
Provenance counts retain `resolved`, `partially_resolved` and `unresolved` as
valid categories on the whole assessed sample. Contradiction and ambiguity are
separate flags. Sample counts and the full graph inventory are different
populations. These diagnostics do not estimate overall graph quality.

Error records retain each diagnostic dimension's applicability and validity.
Repeated occurrences of a code count once per case. An error family counts the
union of its member codes per case, not their sum. A quality grade below `3`
does not automatically imply a taxonomy error. Unresolved assessments remain
unknown, not zero errors. `A` rates use valid cases and require at least 20;
`U` uses counts. Retrieval missing ranks, projection failures, source-format
errors and missing native answers retain their separate meanings.

Numerical, multi-evidence and exception-sensitive groups use the stored
`review_triggers`. Memberships may overlap. These are descriptive slices rather
than additional independent test populations.

## Genuine User and qualitative diagnosis

Genuine User uses six nominal categories: `correct`, `partially_correct`,
`incorrect`, `appropriate_abstention`, `inappropriate_abstention` and
`technical_failure`. Counts and paired transition tables preserve the categories
without assigning a shared direction score. A `technical_failure` category is
an assessed outcome; a missing review is unavailable. Keep this population and
its reference limitations separate from PRIMARY and FINAL.

Qualitative mechanism diagnosis follows required fact → source evidence →
selected context → answer → assessment. A stored observation can be directly
supported, plausible, or not resolvable from the available artifacts. An observed
context difference does not by itself establish an exclusive causal mechanism.
The methods and limits are discussed in thesis Sections 2.6, 2.9, 3.3–3.5 and 4.

## Optional Azure assessment proposals

Notebook 05a has an optional, explicitly enabled Azure judge step. Keep it
disabled for the default examples and offline calculations. It creates an
`AzureOpenAI` client and calls `responses.create` directly using
`AZURE_OPENAI_JUDGE_DEPLOYMENT` and the structured output schema. The deployment
must support this API and schema. The operational output limit is defined in
`config.py`; the returned model is recorded with each proposal.

Each request binds an unchanged answer, its complete native generation context,
reference package, reference-corpus evidence and citation trace. The model
returns a proposal containing the case ID, decision, three grades, a short
rationale and evidence references. Source texts are evidence data. Correctness
and contextual faithfulness use their respective evidence bases; graph carriers
alone do not earn direct citation credit.

Proposals and request/configuration hashes are saved under ignored `local/`.
Matching completed proposals can be reused. A person must review the evidence
and record accepted decisions before they enter `answer_outcomes`. A proposal
cannot pass as an accepted or illustrative assessment. New answers require
their own bound reviews; replacing an answer does not preserve its acceptance.
