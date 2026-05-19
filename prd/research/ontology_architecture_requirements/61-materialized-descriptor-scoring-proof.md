---
milestone: M027-vxdy7c
slice: S04
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Materialized Descriptor Scoring Proof

S04 scores the S03 materialized-derived safe descriptor inputs with the local open-weight semantic runtime. Evaluation labels are stored separately and loaded only after score generation.

## Inputs

Descriptor inputs:

```text
prd/research/ontology_architecture_requirements/fixtures/materialized_descriptor_inputs.json
```

Post-scoring-only labels:

```text
prd/research/ontology_architecture_requirements/fixtures/materialized_descriptor_evaluation_labels.json
```

## Outputs

Scoring verifier / proof builder:

```text
scripts/verify-materialized-descriptor-scoring.py
```

Scoring proof JSON:

```text
prd/research/ontology_architecture_requirements/materialized_descriptor_scoring_proof.json
```

Tests:

```text
tests/test_materialized_descriptor_scoring.py
```

## Runtime boundary

```text
model_id: deepvk/USER-bge-m3
local_files_only: true
observed_vector_dimension: 1024
managed_api_used: false
network_used: false
raw_vectors_persisted: false
```

No raw vectors are persisted. The scoring proof stores scalar similarity scores only.

## Scoring setup

```text
schema_version: materialized-descriptor-scoring-proof/v1
scoring_mode: local_user_bge_m3_materialized_descriptor_similarity_v1
score_count: 36
query_descriptor_count: 6
candidate_descriptor_count: 6
```

Each query descriptor is ranked against all six candidate descriptors. This avoids the trivial one-query/one-candidate metric path.

Evaluation labels are separate:

```text
post_scoring_only: true
forbidden_as_descriptor_input: true
loaded_after_score_generation: true
```

## Observed metrics

```text
mrr: 0.680555
recall_at_1: 0.5
recall_at_3: 0.833333
runtime_boundary_confirmed: 1.0
```

Deltas:

```text
delta_vs_m024_mrr: -0.194445
delta_vs_m024_recall_at_1: -0.25
delta_vs_m024_recall_at_3: -0.166667
delta_vs_m026_mrr: -0.319445
delta_vs_m026_recall_at_1: -0.5
delta_vs_m026_recall_at_3: -0.166667
```

This is a negative observed result relative to M026 held-out descriptor scoring. The materialized-derived descriptors are not accepted as retrieval-quality evidence.

## Verification coverage

Regression tests cover:

- checked-in proof boundaries;
- all-candidate ranking per case;
- post-scoring-only evaluation labels;
- absence of evaluation labels in descriptor inputs;
- metric computation after score generation;
- rejection of expected fields in scores;
- rejection of injected runtime without test flag;
- rejection of test-only injection writes;
- managed API boundary rejection;
- network boundary rejection;
- bad label boundary rejection;
- expected label leakage rejection;
- unsafe raw-text fragment rejection.

## Final verification

Final S04 verification evidence:

```text
gsd_exec[a5739619-50e0-4017-90fd-54842e3c6954]
```

Verification chain:

```text
uv run python scripts/verify-materialized-descriptor-scoring.py
uv run pytest tests/test_materialized_descriptor_scoring.py -q
uv run ruff check scripts/verify-materialized-descriptor-scoring.py tests/test_materialized_descriptor_scoring.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
uv run python materialized descriptor scoring marker verification
```

Observed result:

```text
scoring verifier: completed
tests: 13 passed
ruff: passed
architecture verifier: status ok
GSD sync drift: status OK
proof markers: verified
```

LSP diagnostics for scorer and tests reported no diagnostics.

## S05 review focus

S05 should independently review whether the negative M027/S04 metrics are an expected consequence of structural descriptors being too coarse, and should decide whether M027 closes as bounded evidence with a remediation recommendation instead of attempting to validate R035.

## Non-claims

This proof does not validate R035 and does not prove parser completeness, product retrieval quality, legal-answer correctness, legal interpretation authority, production ETL readiness, graph-vector/HNSW behavior, hybrid retrieval quality, pilot readiness, or managed embedding API authorization.

R035 remains active and not validated. R038 remains active as a standing independent proof-review gate.
