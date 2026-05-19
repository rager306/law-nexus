---
milestone: M028-yejcai
slice: S03
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Safe Structural Descriptor Remediation Scoring Proof

S03 scores the M028 one-signal enhanced descriptor inputs and compares the result against the immutable M027 baseline.

## Input

Enhanced descriptor manifest:

```text
prd/research/ontology_architecture_requirements/fixtures/safe_structural_descriptor_remediation_inputs.json
```

Selected signal:

```text
safe_source_order_neighborhood_bucket
```

Post-scoring-only labels:

```text
prd/research/ontology_architecture_requirements/fixtures/materialized_descriptor_evaluation_labels.json
```

## Output

Scoring proof JSON:

```text
prd/research/ontology_architecture_requirements/safe_structural_descriptor_remediation_scoring_proof.json
```

Scoring script:

```text
scripts/verify-safe-structural-descriptor-remediation-scoring.py
```

Tests:

```text
tests/test_safe_structural_descriptor_remediation_scoring.py
```

## Runtime boundary

```text
model_id: deepvk/USER-bge-m3
observed_vector_dimension: 1024
managed_api_used: false
network_used: false
raw_vectors_persisted: false
runtime_boundary_confirmed: 1.0
```

## Scoring setup

```text
schema_version: safe-structural-descriptor-remediation-scoring-proof/v1
scoring_mode: local_user_bge_m3_safe_structural_descriptor_similarity_v1
score_count: 36
outcome_classification: improvement
```

Each query descriptor is ranked against all six candidate descriptors. Labels are loaded only after score generation.

## Metrics

M028 enhanced metrics:

```text
mrr: 0.916667
recall_at_1: 0.833333
recall_at_3: 1.0
runtime_boundary_confirmed: 1.0
```

Immutable M027 baseline:

```text
mrr: 0.680555
recall_at_1: 0.5
recall_at_3: 0.833333
runtime_boundary_confirmed: 1.0
```

Deltas vs M027:

```text
delta_vs_m027_mrr: 0.236112
delta_vs_m027_recall_at_1: 0.333333
delta_vs_m027_recall_at_3: 0.166667
delta_vs_m027_runtime_boundary_confirmed: 0.0
```

Interpretation:

```text
safe_source_order_neighborhood_bucket improved the bounded materialized descriptor fixture metrics relative to M027.
```

This is not R035 validation and not product retrieval-quality proof. It is a bounded local scoring improvement over the same controlled materialized descriptor cases.

## Verification coverage

Regression tests cover:

- checked-in proof boundaries;
- all-candidate ranking per case;
- post-scoring-only labels;
- absence of evaluation labels in descriptor inputs;
- metric computation after score generation;
- expected-field leakage rejection;
- injected runtime guardrails;
- managed API and network boundary rejection;
- bad label boundary rejection;
- raw-text fragment rejection.

## Final verification

Final S03 verification evidence:

```text
gsd_exec[1a4d0298-17df-4187-a981-61b581157c9a]
```

Verification chain:

```text
uv run python scripts/verify-safe-structural-descriptor-remediation-scoring.py
uv run pytest tests/test_safe_structural_descriptor_remediation_scoring.py -q
uv run ruff check scripts/verify-safe-structural-descriptor-remediation-scoring.py tests/test_safe_structural_descriptor_remediation_scoring.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
uv run python enhanced scoring marker verification
```

Observed result:

```text
scoring: completed
tests: 13 passed
ruff: passed
architecture verifier: status ok
GSD sync drift: status OK
proof markers: verified
```

LSP diagnostics for scorer and tests reported no diagnostics.

## S04 review focus

S04 should independently review whether this improvement is acceptable as bounded representation evidence or whether it is self-confirming because the label artifact identifies same-order candidates. The review must preserve R035 active/not validated unless a future, broader validation contract is satisfied.

## Non-claims

This proof does not validate R035 and does not prove parser completeness, product retrieval quality, legal-answer correctness, legal interpretation authority, production ETL readiness, graph-vector/HNSW behavior, hybrid retrieval quality, pilot readiness, or managed embedding API authorization.

R035 remains active and not validated. R038 remains active as a standing independent proof-review gate.
