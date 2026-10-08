# Evaluation inputs and results

Notebooks 05a, 05b, 06, 06a and 06b share an evaluation dataset through
`manifest.json`.
The public folder is `examples/evaluation/`; approved private inputs belong under
ignored `local/`, for example `local/evaluation/accepted/`. Both use schema
`evaluation-inputs-v1` and the same core functions.

The public dataset contains invented rankings and assessments. Its
`metadata.dataset_kind` is `illustrative`. It does not assign human quality
grades to the saved RFC answers. An approved dataset has kind `accepted` and
retains its evaluation, review and acceptance identities.

## Manifest and evaluation scopes

The manifest has `schema_version`, `metadata` and `artifacts`. Every artifact
reference contains a relative `path` within the dataset folder and the file's
`sha256`. `rag_comparison.artifacts.verify_artifacts` checks all referenced bytes
and prevents paths outside that folder.

| Metadata field | Meaning |
|---|---|
| `dataset_kind` | `illustrative` or `accepted` |
| `scopes` | The PRIMARY and FINAL outcome scopes represented by the dataset |
| `evaluation_ids` | Evaluation identity by scope, including the separate GU identity |
| `review_revision_ids` | Accepted review revision by scope; GU keeps its own revision |
| `acceptance_ids` | Explicit acceptance identity by scope; illustrative examples use `null` |
| `conditions_by_scope` | Conditions whose outcome records belong to each scope |
| `main_conditions_by_scope` | Conditions shown in the main comparison |
| `supplemental_conditions` | Additional conditions needed for a specific reported comparison |
| `graph_review_reference_conditions_by_scope` | Source conditions needed to interpret reused structural graph assessments |
| `graph_audit_reuse` | Source condition and artifact types whose structural assessments are reused |
| `technical_diagnostic_conditions` | Conditions with the supplied native technical-diagnostic records |

Subset metadata is included when that subset is supplied. An illustrative
dataset does not invent an acceptance identity or an additional reviewed source.

PRIMARY contains C0, G0 and the five single-factor changes. The main FINAL
comparison contains C0, G0, C-FINAL and G-FINAL. C-EMBED may additionally be
included for the supplementary comparison in thesis Section 3.4.2. A referenced
source graph is not thereby an additional FINAL outcome condition.

PRIMARY and FINAL have separate shared qrels and question-level IDCG bases.
Retain their scope on every reference, retrieval, review and outcome record.
Evaluation IDs alone do not identify all reviewed inputs; revision, acceptance
identity and file hashes belong to the binding.

GU is a separate population, with its identity in the GU entries of
`evaluation_ids`, `review_revision_ids` and `acceptance_ids`. It is not merged
into the PRIMARY/FINAL scalar-outcome population.

## Artifact roles and record fields

Files use UTF-8 JSON Lines, one record per line. The shared contracts are:

| Manifest role | Required record meaning |
|---|---|
| `questions` | Unique `question_id`, A/U `cohort`, `review_triggers` and optional `diagnostic_tags` |
| `references` | Unique `(scope, question_id)`; shared `qrels` map, `minimal_evidence_sets` and `question_units` for connected components |
| `retrieval` | Unique `(scope, condition_id, question_id)`; `ranked_units` list in unchanged position order |
| `answer_reviews` | `scope`, `case_id`, question/condition IDs, `cohort`, `assessment_state`, `review_status`, `technical_status` and `grades`; accepted data retains `acceptance_id` and `review_revision` |
| `outcomes` | Scalar `scope`, condition/question IDs, `metric`, `value`, `status` and `human_final_validated`; retain recorded validity and revision fields |
| `graph_reviews` | `scope`, condition and artifact type, unique `audit_item_id`, review `status`, and four flat categorical fields: `support_status`, `provenance_status`, `contradiction_flag`, `ambiguity_flag` |
| `graph_population` | Condition, `artifact_type`, unique `stable_id` within that condition/type, and raw sampling `stratum`; metadata for inventory and selection |
| `errors` | `scope`, condition ID, `case_id`, `cohort`, diagnostic `dimension`, validity `status` and `codes`; retain `question_id` when supplied; each dimension has its own population and applicability |
| `gu_reviews` | Question/condition IDs, nominal `category` and `review_status`; accepted records retain separate review/acceptance identities and available answerability/reference-limit metadata |

Error-dimension identities are `answer`, `citation`, `retrieval`, `projection`
and `technical`. A missing diagnostic surface has no supplied records; it is
not evidence of an error-free assessed population.

`ranked_units` contains evidence IDs; `null` preserves a position with a failed
projection. An absent returned position leaves an incomplete ranking. Repeated
IDs retain their positions. A `qrels` map gives one grade `0–2` per distinct
evidence unit. Minimal evidence sets contain original evidence IDs, not rank
numbers or graph carrier IDs.

The `grades` object in an answer review contains `decision_label`,
`answer_correctness`, `faithfulness` and `citation_correctness`, plus diagnostic
answer/citation codes when present. `assessment_state` is either `accepted` or
explicitly `illustrative`; model proposals are separate records.
`review_status="reviewed"` and `technical_status="completed"` allow assessment
scoring. Applicable quality grades are integers `0–3`. Non-applicable grades use
their named states: `not_applicable_unanswerable`, `not_applicable_no_answer` or
`citation_not_required`.

For an accepted scalar row, `status="valid"` makes its value eligible for the
specified outcome. An illustrative row has the same calculation fields, but
the dataset kind and assessment state explicitly identify its demonstration
role. The field `human_final_validated` in an illustrative dataset is not a
claim that its invented cases received human annotation.

Graph review statuses are `valid`, `unresolved` or `missing`. Provenance grade
`unresolved` remains a valid categorical judgement and differs from an unresolved
review. Support grade `not_assessable` is semantically non-applicable.

Error statuses are `valid`, `not_applicable`, `unresolved` or `missing`. Do not
derive error codes from low quality grades. Supply accepted taxonomy decisions
on the correct dimension. Retrieval failure predicates and native format or
technical diagnostics remain separate records with their own valid denominators.

GU categories are `correct`, `partially_correct`, `incorrect`,
`appropriate_abstention`, `inappropriate_abstention` and `technical_failure`.
A reviewed technical-failure category still counts as an assessed case; a missing
GU review does not. GU categories are not ordinal PRIMARY answer grades.

## Offline calculations

Select the dataset folder in each evaluation notebook. Its manifest is checked
before records are read. Notebook 05a scores answer assessments and forms
outcome-specific pairs. Notebook 05b calculates graph, error and nominal GU
diagnostics. Notebook 06 recalculates retrieval and presents paired results;
06a and 06b produce the reported tables and figures. Scope and denominator
labels remain separate.

The accepted inputs remain fixed. Scalar rows provide the recorded outcome and
validity basis; recalculated applicable values can be checked against them.
An invalid recorded observation remains unavailable for aggregation even when
its partial retrieval calculation yields a number. Relative file references,
scope identities and ordered evidence IDs are preserved when relocating inputs.

Generated analysis files and executed private notebook copies belong under
ignored `local/evaluation/` or another ignored `local/` folder. The output
`analysis_manifest.json` binds generated files and input identity with schema
`evaluation-outputs-v1`. The input manifest and source files remain unchanged. Saved shared-notebook outputs must
contain only the public example.

The [reproduction matrix](reproduction_matrix.md) maps the reported results to
their inputs; [export instructions](private_bundle.md) describe packaging.
Moving stored inputs and recalculating outcomes requires no Azure model request.

## Optional judge packets

The scalar evaluation dataset does not require corpus text, full responses or
credentials. The optional Azure judge uses a separate bound evidence packet:
unchanged answer, complete native generation context, reference package,
reference-corpus evidence and citation trace. A `judge_packets` artifact role
may bind supplied packets; it is optional and is not a scalar-outcome input.

Requests and configuration hashes identify proposal reuse. New proposals are
saved in a separate ignored output folder and are never auto-accepted.
A person records reviewed grades with the appropriate applicability states and
an explicit acceptance identity before adding them to an accepted dataset.
Public illustrative grades retain their `illustrative` state.

See [Evaluation methods](evaluation_methods.md) for the rubrics, pairs and
diagnostic interpretation, and the [Classical-RAG](classical_rag_artifacts.md) and
[GraphRAG](graphrag_artifacts.md) contracts for the full native system artifacts.
