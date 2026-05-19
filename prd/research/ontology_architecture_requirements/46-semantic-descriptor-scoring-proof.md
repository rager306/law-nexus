---
milestone: M025-50be7n
slice: S03
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Semantic Descriptor Scoring Proof

S03 ran local semantic scoring over the `safe_semantic_descriptor_v1` inputs from S02 and compared the result against the M024 safe-token baseline from S01. The descriptor representation improved all target metrics in this bounded fixture proof, but the result remains an accept candidate pending S04 decision and S05 independent review. It does not validate R035.

## Artifacts

Evaluator:

```text
scripts/verify-semantic-descriptor-scoring.py
```

Proof JSON:

```text
prd/research/ontology_architecture_requirements/semantic_descriptor_scoring_proof.json
```

Tests:

```text
tests/test_semantic_descriptor_scoring.py
```

## Scoring mode

```text
local_user_bge_m3_safe_descriptor_similarity_v1
```

The scorer encodes descriptor token strings only. It does not encode raw legal text or raw query text, and it does not persist raw vectors.

## Runtime boundary

```text
model_id: deepvk/USER-bge-m3
runtime_status: confirmed_runtime
observed_vector_dimension: 1024
managed_api_used: false
raw_vectors_persisted: false
network_used: false
```

## M024 baseline

```text
mrr: 0.875
recall_at_1: 0.75
recall_at_3: 1.0
positive_with_distractor_relevant_first: 0.0
runtime_boundary_confirmed: 1.0
```

## M025 descriptor scoring result

```text
mrr: 1.0
recall_at_1: 1.0
recall_at_3: 1.0
positive_with_distractor_relevant_first: 1.0
runtime_boundary_confirmed: 1.0
```

Deltas versus M024:

```text
delta_mrr: 0.125
delta_recall_at_1: 0.25
delta_recall_at_3: 0.0
delta_positive_with_distractor_relevant_first: 1.0
delta_runtime_boundary_confirmed: 0.0
```

Threshold failures:

```text
none
```

Disposition hint:

```text
accept_candidate_pending_review
```

Diagnostics:

```text
semantic_descriptors_verified
runtime_confirmed
descriptor_scoring_completed
baseline_delta_positive
```

## Verification

Final S03 verification evidence:

```text
gsd_exec[0b091a50-799d-4529-86fb-12f15bcdee76]
```

Command chain:

```bash
uv run python scripts/verify-semantic-descriptor-inputs.py
uv run python scripts/verify-semantic-descriptor-scoring.py
uv run pytest tests/test_semantic_descriptor_inputs.py tests/test_semantic_descriptor_scoring.py -q
uv run ruff check scripts/verify-semantic-descriptor-inputs.py scripts/verify-semantic-descriptor-scoring.py tests/test_semantic_descriptor_inputs.py tests/test_semantic_descriptor_scoring.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```

Results:

```text
descriptor verifier: status=ok
descriptor scorer: status=completed, no threshold failures, accept_candidate_pending_review
focused tests: 29 passed
ruff: All checks passed
architecture verifier: status=ok
GSD sync drift: status=OK
```

## Negative coverage

Focused tests cover:

- checked-in positive-delta proof shape;
- injected metric logic in test-only mode;
- blocked runtime;
- raw vector persistence rejection;
- expected-answer leakage in scores;
- wrong scoring mode;
- missing observed score;
- unsafe descriptor manifest;
- CLI rejection of injected runtime/scores as acceptance proof;
- test-only injected mode cannot write the acceptance proof artifact.

## Interpretation

The first M025 representation change improved local scoring on the representative fixture compared with M024 safe-token inputs. This suggests that bounded typed descriptors are more useful to USER-bge-m3 than ID-heavy token bags for this fixture.

The result still requires S04/S05 scrutiny because descriptor design can be self-confirming if descriptor enums encode fixture expectations too directly. S04 must decide whether to accept, revise, reject, or block this representation change based on the observed metrics and the proof boundaries.

## Non-claims

S03 does not claim:

- R035 validation;
- product retrieval quality;
- legal-answer correctness;
- legal interpretation authority;
- parser completeness;
- parser-to-EvidenceSpan materialization;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- pilot readiness.

## S04 handoff

S04 should evaluate whether `safe_semantic_descriptor_v1` should be accepted for the next cycle. It must specifically review self-confirming risk, descriptor leakage, fixture-derived enum design, and whether the positive deltas are meaningful enough to keep the representation under the bounded non-production scope.
