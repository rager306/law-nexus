---
milestone: M026-1uqmzc
slice: S05
task: T02
status: final-cycle-closeout
decision: accept_bounded
non_authoritative: true
created_at: 2026-05-19
---

# M026 Final Held-out Closeout

## Decision

```text
accept_bounded
```

The M026 held-out `safe_semantic_descriptor_v1` proof cycle is accepted only as bounded local descriptor-scoring evidence for future proof iterations. This does not validate R035 and does not establish product retrieval quality.

## Rationale

M026 extended M025 by moving from remediated descriptor scoring over prior controlled cases to M026-only held-out safe descriptor cases.

The proof chain established:

- held-out contract with M022/M025 acceptance ID reuse forbidden;
- M026-only safe descriptor inputs;
- post-scoring-only evaluation labels separated from descriptor/scoring inputs;
- local `deepvk/USER-bge-m3` scoring with observed vector dimension 1024;
- held-out all-1.0 metrics;
- query-intent ablation with zero metric deltas;
- independent review PASS.

## Metrics

Held-out scoring metrics:

```text
mrr: 1.0
recall_at_1: 1.0
recall_at_3: 1.0
runtime_boundary_confirmed: 1.0
```

Delta vs M024 safe-token baseline:

```text
delta_vs_m024_mrr: 0.125
delta_vs_m024_recall_at_1: 0.25
delta_vs_m024_recall_at_3: 0.0
delta_vs_m024_runtime_boundary_confirmed: 0.0
```

Delta vs M025 bounded descriptor result:

```text
delta_vs_m025_mrr: 0.0
delta_vs_m025_recall_at_1: 0.0
delta_vs_m025_recall_at_3: 0.0
delta_vs_m025_runtime_boundary_confirmed: 0.0
```

## Ablation result

S04 query-intent ablation diagnosis:

```text
held_out_success_survives_ablation
```

Ablation changed only:

```text
query_intent
```

Fixed invariants included:

```text
candidate_descriptors_fixed: true
evaluation_labels_fixed: true
metrics_policy_fixed: true
runtime_model_fixed: deepvk/USER-bge-m3
expected_vector_dimension_fixed: 1024
scoring_mode_fixed: local_user_bge_m3_held_out_descriptor_similarity_v1
temporary_manifest_persisted: false
```

## Independent review

Independent review artifact:

```text
prd/research/ontology_architecture_requirements/56-m026-independent-proof-review.md
```

Verdict:

```text
PASS
```

Findings:

```text
No findings.
```

## Accepted future use

The M026 held-out descriptor setup may be reused as bounded local scoring evidence for future proof cycles when all of these remain true:

- local/open-weight runtime only;
- `deepvk/USER-bge-m3` or explicitly re-baselined local successor;
- no managed embedding API or network scoring;
- no raw legal text, raw query text, or raw vectors in durable artifacts;
- evaluation labels remain post-scoring-only;
- expected labels/candidate IDs/ranks/selection reasons are not descriptor or scoring inputs;
- perturbation/ablation proof runs before acceptance;
- independent review runs before any requirement lifecycle promotion.

## Rejected interpretation

This decision must not be read as any of the following:

- R035 validation;
- product retrieval-quality proof;
- legal-answer correctness proof;
- legal interpretation authority;
- parser completeness proof;
- parser-to-EvidenceSpan materialization proof;
- graph-vector or HNSW behavior proof;
- hybrid retrieval-quality proof;
- production FalkorDB readiness;
- pilot readiness;
- managed embedding API authorization.

## Requirement lifecycle

R035 remains:

```text
active / not validated
```

R038 remains:

```text
active standing independent proof-review gate
```

M026 advances bounded proof discipline and held-out local descriptor evidence. It does not close ontology architecture validation.

## Recommended next direction

Future work should move from safe descriptor-only proof toward broader evidence while preserving the same proof discipline:

1. Add a larger held-out safe descriptor set with more varied structural cases.
2. Add one additional ablation dimension, such as `citation_granularity` or `document_scope`, one signal at a time.
3. Separately plan a parser-to-EvidenceSpan materialization proof before any product retrieval-quality claim.
4. Keep independent review mandatory for any requirement-promotion decision.
