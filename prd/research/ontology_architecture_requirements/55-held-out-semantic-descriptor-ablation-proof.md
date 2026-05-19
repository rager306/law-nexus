---
milestone: M026-1uqmzc
slice: S04
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Held-out Semantic Descriptor Ablation Proof

S04 stress-tests the M026 held-out all-1.0 scoring result by ablating the `query_intent` descriptor signal before any bounded acceptance decision.

## Inputs

Source descriptor manifest:

```text
prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_inputs.json
```

Source scoring proof:

```text
prd/research/ontology_architecture_requirements/held_out_semantic_descriptor_scoring_proof.json
```

Ablation proof JSON:

```text
prd/research/ontology_architecture_requirements/held_out_semantic_descriptor_ablation_proof.json
```

Ablation verifier:

```text
scripts/verify-held-out-semantic-descriptor-ablation.py
```

Regression tests:

```text
tests/test_held_out_semantic_descriptor_ablation.py
```

## Ablation performed

Ablation scope:

```text
held_out_query_intent_only
```

Changed signal:

```text
query_intent
```

The script neutralized non-neutral query intents to:

```text
locate_evidence_span
```

Changed fields count:

```text
4
```

The candidate descriptors, evaluation labels, metrics policy, local runtime model, scoring mode, and expected vector dimension were fixed.

## Result

Dependency diagnosis:

```text
held_out_success_survives_ablation
```

Current metrics:

```text
mrr: 1.0
recall_at_1: 1.0
recall_at_3: 1.0
runtime_boundary_confirmed: 1.0
```

Ablated metrics:

```text
mrr: 1.0
recall_at_1: 1.0
recall_at_3: 1.0
runtime_boundary_confirmed: 1.0
```

Metric deltas after ablation:

```text
mrr: 0.0
recall_at_1: 0.0
recall_at_3: 0.0
runtime_boundary_confirmed: 0.0
```

This means the held-out all-1.0 scoring result does not depend on the `query_intent` descriptor signal alone.

## Provenance and invariants

The proof records:

```text
source_descriptor_manifest_sha256
source_scoring_proof_sha256
evaluation_labels_sha256
score_digest.current_scores_sha256
score_digest.ablated_scores_sha256
```

Fixed invariants:

```text
ablation_changes_one_signal_at_a_time: true
changed_signal: query_intent
candidate_descriptors_fixed: true
evaluation_labels_fixed: true
metrics_policy_fixed: true
runtime_model_fixed: deepvk/USER-bge-m3
expected_vector_dimension_fixed: 1024
scoring_mode_fixed: local_user_bge_m3_held_out_descriptor_similarity_v1
temporary_manifest_persisted: false
```

## Verification

Final S04 verification evidence:

```text
gsd_exec[b0fb84ba-c378-4b82-a7ba-3fee80f25af8]
```

Verification chain:

```text
uv run python scripts/verify-held-out-semantic-descriptor-inputs.py
uv run python scripts/verify-held-out-semantic-descriptor-scoring.py
uv run python scripts/verify-held-out-semantic-descriptor-ablation.py
uv run pytest tests/test_held_out_semantic_descriptor_inputs.py tests/test_held_out_semantic_descriptor_scoring.py tests/test_held_out_semantic_descriptor_ablation.py -q
uv run ruff check scripts/verify-held-out-semantic-descriptor-inputs.py scripts/verify-held-out-semantic-descriptor-scoring.py scripts/verify-held-out-semantic-descriptor-ablation.py tests/test_held_out_semantic_descriptor_inputs.py tests/test_held_out_semantic_descriptor_scoring.py tests/test_held_out_semantic_descriptor_ablation.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
uv run python held-out ablation proof marker verification
```

Observed result:

```text
held-out descriptor verifier: status ok
held-out scoring: status completed
held-out ablation: status ok
regression tests: 31 passed
ruff: passed
architecture verifier: status ok
GSD sync drift: status OK
proof markers: verified
```

LSP diagnostics for the ablation verifier reported no diagnostics.

## S05 handoff

S05 must independently review:

- held-out independence from M022/M025 acceptance evidence;
- post-scoring-only label separation;
- query-intent ablation provenance;
- score digest and fixed-invariant evidence;
- stale artifact markers;
- R035/product-quality/legal-correctness overclaims.

The S04 result strengthens bounded evidence, but M026 still must not close without S05 independent review.

## Non-claims

This proof does not validate R035 and does not prove held-out semantic retrieval quality, product retrieval quality, legal-answer correctness, parser completeness, parser-to-EvidenceSpan materialization, graph-vector/HNSW behavior, hybrid retrieval quality, production readiness, pilot readiness, or managed embedding API authorization.

R035 remains active and not validated. R038 remains active as a standing independent proof-review gate.
