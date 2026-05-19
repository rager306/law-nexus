---
milestone: M025-50be7n
slice: S06
task: T02
status: final-cycle-closeout
decision: accept_bounded
non_authoritative: true
created_at: 2026-05-19
---

# M025 Final Cycle Closeout

## Decision

```text
accept_bounded
```

The remediated `safe_semantic_descriptor_v1` representation is accepted for bounded future local semantic scoring iteration. This is not R035 validation and not product retrieval-quality acceptance.

## Rationale

M025 started from the M024 safe-token semantic scoring baseline:

```text
mrr: 0.875
recall_at_1: 0.75
recall_at_3: 1.0
positive_with_distractor_relevant_first: 0.0
runtime_boundary_confirmed: 1.0
```

The remediated descriptor representation produced:

```text
mrr: 1.0
recall_at_1: 1.0
recall_at_3: 1.0
positive_with_distractor_relevant_first: 1.0
runtime_boundary_confirmed: 1.0
```

Measured deltas:

```text
delta_mrr: 0.125
delta_recall_at_1: 0.25
delta_recall_at_3: 0.0
delta_positive_with_distractor_relevant_first: 1.0
delta_runtime_boundary_confirmed: 0.0
```

The original S03 metric improvement was not accepted immediately because S04 found self-confirming descriptor risk. S05 remediated that risk by:

- deriving descriptors from pre-registered non-answer structural fields;
- replacing outcome-like enum values with neutral structural values;
- proving descriptor projection invariance under expected-answer and `selection_reason` perturbation;
- proving a structural-control mutation changes descriptors;
- proving positive-with-distractor success survives neutralization of the suspicious query-intent value;
- rerunning descriptor scoring against the same local runtime, fixture, and metrics.

S06 independent review initially requested changes for proof provenance issues, then passed after remediation.

## Decision evidence

S05 remediation proof note:

```text
prd/research/ontology_architecture_requirements/49-semantic-descriptor-derivation-remediation-proof.md
```

Independent review:

```text
prd/research/ontology_architecture_requirements/50-m025-remediation-independent-review.md
```

Derivation remediation proof JSON:

```text
prd/research/ontology_architecture_requirements/semantic_descriptor_derivation_remediation_proof.json
```

Distractor ablation proof JSON:

```text
prd/research/ontology_architecture_requirements/semantic_descriptor_distractor_ablation_proof.json
```

Scoring proof JSON:

```text
prd/research/ontology_architecture_requirements/semantic_descriptor_scoring_proof.json
```

## Accepted future use

The representation may be reused as a bounded local scoring input format for future proof cycles when all of the following remain true:

- local/open-weight model only;
- `deepvk/USER-bge-m3` or explicitly re-baselined local successor;
- no managed embedding API or network scoring;
- no raw legal text, raw query text, or raw vectors in durable artifacts;
- no expected-answer fields, ranks, candidate labels, diagnostic expectations, or `selection_reason` as descriptor inputs;
- descriptor changes are measured against an explicit baseline;
- independent review runs before requirement lifecycle promotion.

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

M025 advances bounded proof discipline and provides a safer descriptor iteration candidate. It does not close ontology architecture validation.

## Next-cycle recommendations

Future cycles should test generalization beyond the current bounded fixture before any requirement-promotion discussion:

1. Add new held-out safe descriptor cases not used in descriptor design.
2. Preserve one representation change per cycle.
3. Keep perturbation invariance and ablation proof requirements.
4. Require independent review to look for fixture-derived/self-confirming signals before acceptance.
