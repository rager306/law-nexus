---
milestone: M026-1uqmzc
slice: S03
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Held-out Semantic Descriptor Scoring Proof

S03 scores the M026 held-out safe descriptor inputs with local `deepvk/USER-bge-m3` and computes metrics only after scoring with a separate post-scoring evaluation-label artifact.

## Inputs

Held-out descriptor inputs:

```text
prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_inputs.json
```

Post-scoring evaluation labels:

```text
prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_evaluation_labels.json
```

Scoring verifier:

```text
scripts/verify-held-out-semantic-descriptor-scoring.py
```

Scoring proof JSON:

```text
prd/research/ontology_architecture_requirements/held_out_semantic_descriptor_scoring_proof.json
```

Regression tests:

```text
tests/test_held_out_semantic_descriptor_scoring.py
```

## Label-separation boundary

Evaluation labels are explicitly separate from descriptor/scoring inputs:

```text
post_scoring_only: true
forbidden_as_descriptor_input: true
label_count: 5
```

The descriptor input fixture does not contain:

```text
expected_candidate_ids
expected_rejected_candidate_ids
expected_label
expected_result
selection_reason
rank
```

Metric labels are loaded only after scoring and are used only for metric computation.

## Runtime boundary

```text
model_id: deepvk/USER-bge-m3
local_files_only: true
observed_vector_dimension: 1024
managed_api_used: false
network_used: false
raw_vectors_persisted: false
```

## Metrics

Held-out scoring result:

```text
mrr: 1.0
recall_at_1: 1.0
recall_at_3: 1.0
runtime_boundary_confirmed: 1.0
```

Delta vs M024 baseline:

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

## Verification

Final S03 verification evidence:

```text
gsd_exec[8ab932f4-cd77-46bf-8b7b-bd4859cea505]
```

Verification chain:

```text
uv run python scripts/verify-held-out-semantic-descriptor-inputs.py
uv run python scripts/verify-held-out-semantic-descriptor-scoring.py
uv run pytest tests/test_held_out_semantic_descriptor_inputs.py tests/test_held_out_semantic_descriptor_scoring.py -q
uv run ruff check scripts/verify-held-out-semantic-descriptor-inputs.py scripts/verify-held-out-semantic-descriptor-scoring.py tests/test_held_out_semantic_descriptor_inputs.py tests/test_held_out_semantic_descriptor_scoring.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
uv run python held-out scoring proof marker verification
```

Observed result:

```text
held-out descriptor verifier: status ok
held-out scoring: status completed
regression tests: 24 passed
ruff: passed
architecture verifier: status ok
GSD sync drift: status OK
proof markers: verified
```

LSP diagnostics for the scoring verifier reported no diagnostics.

## S04 handoff

S04 must run a perturbation or ablation proof before M026 can be accepted. It should change one descriptor signal at a time and record:

```text
changed_fields_recorded: true
source_digest_recorded: true
score_digest_recorded: true
candidate_descriptors_fixed_unless_declared: true
fixture_fixed_unless_declared: true
metrics_policy_fixed_unless_declared: true
dependency_diagnosis_required: true
```

The S03 all-1.0 result is promising bounded evidence but must not be accepted without S04 ablation and S05 independent review.

## Non-claims

This proof does not validate R035 and does not prove held-out semantic retrieval quality, product retrieval quality, legal-answer correctness, parser completeness, parser-to-EvidenceSpan materialization, graph-vector/HNSW behavior, hybrid retrieval quality, production readiness, pilot readiness, or managed embedding API authorization.

R035 remains active and not validated. R038 remains active as a standing independent proof-review gate.
