# Reproduction matrix

The notebooks compute the reported tables, figures and numerical results from
prepared inputs, stored system outputs and accepted assessments. Public examples demonstrate the
same functions with public or illustrative data. Reproducing the thesis results
requires the matching approved private inputs and their manifest bindings.

The [evaluation contract](evaluation_artifacts.md) defines the scalar input roles,
scope identities and validity states. The [Classical-RAG contract](classical_rag_artifacts.md)
and [GraphRAG contract](graphrag_artifacts.md) define the stored system artefacts.
Relative paths and SHA256 preserve these bindings when stored artefacts are
relocated. Offline calculation does not make model requests or revise accepted
human judgements. In the public default, Figure 2 instead uses the saved RFC
baseline retrieval with its source-checked page grades; three pairs give
case-level differences and counts without an aggregate effect. The other
default result surfaces use the illustrative evaluation dataset.

## Reported result surfaces

| Thesis reference | Required inputs | Computation |
|---|---|---|
| Section 3.1, Table 5 | Corpus/preparation inventory; `questions`; separate `gu_reviews` | Source-document and page counts, text-extraction states, baseline chunk count, unique benchmark and user-question populations |
| Section 3.1, Table 6 | Condition configuration, stored-run manifests and accepted case identities | Configuration membership and the number of stored responses per condition |
| Section 3.2, Table 7 | PRIMARY `retrieval`, `references`, `answer_reviews`, `outcomes` and `questions` | Common-valid baseline retrieval pairs; applicable grade distributions, ordinal wins/ties/losses and substantive-answer/abstention counts |
| Section 3.2, Figure 2 | PRIMARY baseline retrieval outcomes | Question-level GraphRAG minus Classical-RAG differences on the same complete pairs, sorted by difference; mean and direction counts |
| Section 3.2, Table 8 | Baseline evidence-completeness and correctness outcomes | Cross-tabulate binary complete-evidence retrieval and ordinal correctness on the common retrieval-valid population |
| Section 3.3, Table 9 | `graph_inventory` and G0 `graph_reviews` | Native row and distinct-ID counts; sampled support categories and resolved provenance with separate denominators |
| Section 3.3, graph inventory text | `graph_inventory` | Community levels, distinct TextUnit identities and median character lengths including whitespace; observed types remain distinct from configured types |
| Section 3.3, question-property diagnostics | `questions` and PRIMARY baseline outcomes | Overlapping numerical, multiple-evidence and exception-sensitive groups; metric-specific common pairs, complete-evidence counts and ordinal ordering |
| Section 3.3, Table 10 and error subcodes | `errors` on their own diagnostic dimensions | Unique-case error-family unions and individual code counts, with each family's applicability, missingness and unresolved states |
| Section 3.4.1, Table 11 and Figure 3 | PRIMARY variant/baseline outcomes and decisions | Each single-factor condition minus its own unchanged baseline; paired retrieval effects and answer/abstention counts |
| Section 3.4.1, Table 12 and Figure 4 | PRIMARY accepted ordinal outcomes | Higher/equal/lower grades, dominance and the valid paired count for each variant and quality dimension |
| Section 3.4.1, Table 13; Appendix A.2 | PRIMARY four-condition outcomes | Post-change versus baseline GraphRAG–Classical-RAG gaps on one four-way-valid population; use signs for ordinal gaps |
| Section 3.4.1, segmentation case | Matching PRIMARY case outcomes and stored segment/source bindings | Retain the selected case's page-evidence scores and correctness transition; distinguish page credit from the actual segment supplied to generation |
| Section 3.4.2, Table 14 | FINAL `retrieval`, `references`, outcomes and decisions | Each configuration's own valid retrieval mean, evidence-completeness count and answer/abstention counts on the FINAL pool |
| Section 3.4.2, Table 15 | FINAL accepted quality outcomes | Own-baseline and cross-FINAL ordinal comparisons; wins favour the first-named configuration |
| Section 3.4.2, paired retrieval text | FINAL outcomes, including supplemental C-EMBED | Common-pair FINAL retrieval contrasts and the C-EMBED versus C-FINAL comparison on the same FINAL pool |
| Section 3.5, Table 16 and category transitions | Separate `gu_reviews` | Six-category counts, paired nominal transitions, correct-set overlap and unique question/reference-boundary counts |
| Appendix E, Figure 5 | Baseline and FINAL quality outcomes | Grade distributions for each condition's applicable population; these are distinct from paired transitions |
| Appendix E, Figure 6 | PRIMARY variant/baseline correctness outcomes | Lower/equal/higher paired grade counts, retaining ties in the denominator |
| Appendix A.3, Table 21 | The appendix's hypothetical ranking and shared relevance pool | Rank discounts, linear DCG, shared ideal DCG and nDCG; compute before rounding display values |
| Appendices G and I, Figures 17 and 22 | The constructed source rankings, pool and minimal evidence set | The two illustrative retrieval-metric calculations; these are examples rather than measured experimental results |

The research questions use these surfaces together. Retrieval, correctness,
faithfulness, citation correctness and response behaviour remain separate;
no combined quality score or overall graph-quality score is introduced.

## Scope, denominators and rounding

Figures 2–4 retain the thesis point plots, including open markers for incomplete
retrieval coverage in Figure 3. Figures 5–6 use horizontal percentage bars with
case counts, valid-population denominators and ties as reported. Plot layouts,
colours, labels and condition order match the thesis; exports use Arial and
600 dpi. Illustrative examples are labelled separately and may extend effect
axes to keep their example values visible.

PRIMARY and FINAL retain different shared qrels pools and ideal-ranking bases.
Recalculate each baseline on the pool used by its comparison. A condition's
own valid count does not replace the pair intersection, and a four-condition gap
cannot be obtained by subtracting effects calculated on different populations.

`N_total`, `N_app` and valid `k` have distinct meanings. Retrieval comparisons
require all evaluated positions to be present, mapped and judged, with positive
ideal gain. Missing positions remain missing; failed projections retain their
position without receiving direct source-evidence credit. A genuine relevance
grade zero remains a judged observation.

An abstention on an answerable question has correctness zero. Faithfulness and
citation assessment can instead be non-applicable when no substantive answer is
provided. An available response with a source-format error can still have valid
semantic assessments. Diagnostic error dimensions keep their own denominators
and are not inferred from low quality grades.

Compute effects from the question-level values before applying the table's
display precision. Ordinal grades have no numerical spacing: use ordering,
counts and dominance. A figure showing higher/equal/lower grades must retain
the direction declared in its caption. Rounded displayed means are insufficient
inputs for a reported paired difference.

## Accepted graph and user assessments

Graph sampling retains its frozen sampling identifiers, separate from later
accepted-review revisions. Structural reuse references the source graph's
accepted cases. New Local Search traces have their own records; a changed
embedding model does not justify copying another condition's trace grades.
Support, provenance, ambiguity and contradiction remain categorical fields.
Source traceability does not establish full content support.

The user-question evaluation has its own review identity and six nominal
categories. Required Facts and case-specific reference limits guide assessment;
they do not define an automatic all-or-nothing score. Category transitions must
not be converted into ordinal wins, losses or mean grades.

Bootstrap calculations retain the stated resampling definition and parameters.
The reported results remain descriptive because the evidence components and
benchmark construction limit population inference. Confidence intervals,
permutation tests, Wilson intervals and multiple-testing results that are not
reported in the thesis are not additional required result surfaces.

## Method references in the thesis

*From Guidelines to Grounded Answers: Answer Quality and Configuration Effects in
Vector RAG and Microsoft GraphRAG Local Search* (2026), University
of Applied Sciences Technikum Wien.

Preparation and reference packages are described in Sections 2.3–2.4 and Appendix D;
the system paths in Section 2.5 and Appendices C/F/G/H/I; evaluation in Section 2.6
and Appendix A, including the worked nDCG example in A.3, Table 21. Configuration
changes are described in Section 2.8 and Sections 3.4.1–3.4.2, Tables 11–15.
Graph/error diagnostics and genuine-user evaluation are discussed in Sections
3.3/3.5 and Appendix B. Sections 4.1–4.4 discuss the findings and their limits.
