---
milestone: M024-eb6mo4
slice: S03
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-18
---

# Semantic Observed Retrieval Scoring Proof

S03 ran local/open-weight semantic scoring over the safe token-bag representations produced in S02. The scoring completed under the approved `deepvk/USER-bge-m3` runtime boundary, persisted only rounded scalar similarity scores/ranks, and honestly reported below-threshold fixture metrics.

## Artifacts

Evaluator:

```text
scripts/verify-semantic-observed-retrieval-scoring.py
```

Proof JSON:

```text
prd/research/ontology_architecture_requirements/semantic_observed_retrieval_scoring_proof.json
```

Tests:

```text
tests/test_semantic_observed_retrieval_scoring.py
```

## Scoring mode

```text
local_user_bge_m3_safe_token_similarity_v1
```

The scorer encodes safe representation strings only. It does not encode raw legal text or raw query text, and it does not persist raw vectors.

## Runtime boundary

```text
model_id: deepvk/USER-bge-m3
runtime_status: confirmed_runtime
observed_vector_dimension: 1024
managed_api_used: false
raw_vectors_persisted: false
network_used: false
```

## Metric outcome

Semantic scoring completed, but strict fixture thresholds were not all met:

```text
mrr: 0.875
recall_at_1: 0.75
recall_at_3: 1.0
positive_with_distractor_relevant_first: 0.0
runtime_boundary_confirmed: 1.0
```

Threshold failures:

```text
mrr
recall_at_1
positive_with_distractor_relevant_first
```

Diagnostics:

```text
semantic_inputs_verified
runtime_confirmed
semantic_scoring_completed
metric_mismatch
```

This is a useful bounded result: safe token-bag semantic scoring is runnable locally, but it does not meet the strict representative fixture ranking thresholds.

## Verification

Final S03 verification evidence:

```text
gsd_exec[9f27bc24-0a17-4912-9321-6287778240ad]
```

Command chain:

```bash
uv run python scripts/verify-semantic-retrieval-safe-inputs.py
uv run python scripts/verify-semantic-observed-retrieval-scoring.py
uv run pytest tests/test_semantic_retrieval_safe_inputs.py tests/test_semantic_observed_retrieval_scoring.py -q
uv run ruff check scripts/verify-semantic-retrieval-safe-inputs.py scripts/verify-semantic-observed-retrieval-scoring.py tests/test_semantic_retrieval_safe_inputs.py tests/test_semantic_observed_retrieval_scoring.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```

Results:

```text
safe input verifier: status=ok
semantic scorer: status=completed with metric_mismatch
focused tests: 19 passed
ruff: All checks passed
architecture verifier: status=ok
GSD sync drift: status=OK
```

## Negative coverage

Focused tests cover:

- checked-in proof shape and threshold failures;
- perfect injected scores comparison;
- blocked runtime;
- raw vector persistence rejection;
- expected answer leakage in scores;
- wrong scoring mode;
- missing score;
- unsafe safe-input manifest.

## What this proves

S03 proves that local USER-bge-m3 can score safe token-bag query/candidate representations and produce observed scalar similarities/ranks without raw text or raw vector persistence.

## What this does not prove

S03 does not prove:

- representative semantic retrieval quality at the strict thresholds;
- product retrieval quality;
- legal-answer correctness;
- parser-to-EvidenceSpan materialization;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- R035 validation.

## S04 handoff

S04 independent review should specifically check whether below-threshold metrics are reported honestly, whether safe token-bag scoring is not overstated, and whether tests are non-vacuous despite injected-score unit paths.
