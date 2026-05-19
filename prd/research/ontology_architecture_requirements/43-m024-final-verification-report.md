---
milestone: M024-eb6mo4
slice: S04
status: final-verification
verdict: pass
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-18
---

# M024 Final Verification Report

## Verdict

```text
pass
```

M024 completed its bounded semantic observed retrieval scoring proof. The final outcome is intentionally limited: local semantic scoring over safe token-bag representations runs under the approved `deepvk/USER-bge-m3` boundary, but the strict representative fixture metrics are below threshold. R035 remains active and not validated.

## Scope completed

M024 delivered:

1. semantic scoring contract;
2. safe semantic input manifest;
3. safe input verifier and fail-closed tests;
4. local USER-bge-m3 semantic scorer over safe token-bag strings;
5. observed scalar score/rank proof JSON;
6. independent proof review with remediation;
7. requirement lifecycle updates for R035 and R038.

## Key artifacts

```text
prd/research/ontology_architecture_requirements/39-semantic-observed-retrieval-scoring-contract.md
prd/research/ontology_architecture_requirements/40-semantic-retrieval-safe-inputs-proof.md
prd/research/ontology_architecture_requirements/41-semantic-observed-retrieval-scoring-proof.md
prd/research/ontology_architecture_requirements/42-m024-independent-proof-review.md
prd/research/ontology_architecture_requirements/fixtures/semantic_retrieval_safe_inputs.json
prd/research/ontology_architecture_requirements/semantic_observed_retrieval_scoring_proof.json
scripts/verify-semantic-retrieval-safe-inputs.py
scripts/verify-semantic-observed-retrieval-scoring.py
tests/test_semantic_retrieval_safe_inputs.py
tests/test_semantic_observed_retrieval_scoring.py
```

## Semantic scoring result

```text
status: completed
scoring_mode: local_user_bge_m3_safe_token_similarity_v1
model_id: deepvk/USER-bge-m3
observed_vector_dimension: 1024
```

Metrics:

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

Interpretation:

```text
Safe-token semantic scoring is runnable locally, but it does not meet strict representative retrieval-quality thresholds.
```

## Independent review outcome

First independent review verdict:

```text
REQUEST_CHANGES
```

High findings:

1. Safe input verifier accepted arbitrary raw/prose/path-like `representation_tokens`.
2. Semantic scoring CLI accepted injected runtime/scores JSON as an acceptance-proof path.

Remediation:

- strict safe token grammar and allowed-prefix list added;
- generic absolute path token rejection added;
- negative tests added for Cyrillic raw-query-like token, `/etc/passwd`, generated prose-like token, and Windows path token;
- injected runtime/scores JSON rejected for acceptance proof;
- test-only injected mode cannot write the proof artifact.

Second independent review verdict:

```text
PASS
```

Recorded in:

```text
prd/research/ontology_architecture_requirements/42-m024-independent-proof-review.md
```

## Final verification evidence

Fresh final verification:

```text
gsd_exec[89e13f57-14f5-4c28-9dc7-7d682adc9877]
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
focused tests: 25 passed
ruff: All checks passed
architecture verifier: status=ok
GSD sync drift: status=OK
```

## Requirement outcomes

### R035

Status: active / not validated.

M024 advanced R035 with bounded local semantic scoring evidence, but below-threshold metrics prevent validation. The evidence does not prove product retrieval quality or representative semantic retrieval quality.

### R038

Status: active / applied, not globally closed.

M024 applied the independent proof-review gate and remediated findings before closeout. Future proof-heavy milestones still require independent review.

## Non-claims

M024 does not claim:

- R035 validation;
- representative retrieval-quality validation;
- product retrieval quality;
- legal-answer correctness;
- legal interpretation authority;
- parser completeness;
- parser-to-EvidenceSpan materialization;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- pilot readiness;
- managed embedding API authorization.

## Downstream recommendation

Do not promote safe-token semantic scoring as a retrieval-quality gate. Treat M024 as a bounded negative/partial proof: safe scoring infrastructure exists, but quality requires a future design that can represent semantics without violating raw-text/vector persistence constraints, or an explicitly approved environment for ephemeral raw-text scoring with stronger artifact redaction controls.
