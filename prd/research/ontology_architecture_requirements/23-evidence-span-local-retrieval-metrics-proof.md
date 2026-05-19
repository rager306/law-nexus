---
milestone: M021-qk4lze
slice: S05
status: proof
requirement_scope:
  - R035
non_authoritative: true
created_at: 2026-05-18
---

# EvidenceSpan Local Retrieval Metrics Proof

S05 measured bounded fixture-level local/open-weight retrieval metrics over the S04 EvidenceSpan golden fixture. The approved local runtime boundary was confirmed for `deepvk/USER-bge-m3` with observed vector dimension `1024`, and the S05 metric thresholds passed.

This is still not product retrieval quality, graph-filtered retrieval quality, legal-answer correctness, parser completeness, production FalkorDB readiness, graph-vector/HNSW behavior, pilot readiness, or R035 validation.

## Artifacts

Contract:

```text
prd/research/ontology_architecture_requirements/22-evidence-span-local-retrieval-metrics-contract.md
```

Input fixture:

```text
prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json
```

Proof JSON:

```text
prd/research/ontology_architecture_requirements/evidence_span_local_retrieval_metrics_proof.json
```

Evaluator:

```text
scripts/verify-evidence-span-local-retrieval-metrics.py
```

Tests:

```text
tests/test_evidence_span_local_retrieval_metrics.py
```

## Runtime boundary

Approved model:

```text
deepvk/USER-bge-m3
```

Runtime result:

```json
{
  "runtime_status": "confirmed_runtime",
  "model_id": "deepvk/USER-bge-m3",
  "observed_vector_dimension": 1024,
  "managed_api_used": false,
  "raw_vectors_persisted": false,
  "network_used": false
}
```

The evaluator uses the existing local runtime checker and normalizes its output so durable S05 proof does not persist provider payload fields or raw vectors.

## Metrics

Final proof summary:

```json
{
  "schema_version": "evidence-span-local-retrieval-metrics-proof/v1",
  "threshold_passed": true,
  "mismatch_count": 0,
  "diagnostic_codes": [
    "ambiguous_candidate_set",
    "runtime_confirmed",
    "scoped_no_answer",
    "stale_temporal_candidate",
    "unsupported_scope"
  ],
  "metrics": {
    "mrr": 1.0,
    "recall_at_1": 1.0,
    "recall_at_3": 1.0,
    "stale_rejection_rate": 1.0,
    "ambiguous_rejection_rate": 1.0,
    "unsupported_scope_accuracy": 1.0,
    "no_answer_accuracy": 1.0,
    "runtime_boundary_confirmed": 1.0
  }
}
```

The metrics are computed from S04 fixture expected labels/case classes after the S04 verifier accepts the fixture. They are seed fixture metrics, not broader product retrieval metrics.

## Verification

Final S05 verification evidence:

```text
gsd_exec[1fd76203-8a64-43f3-9391-f7590d63dd3e]
```

Command chain:

```bash
uv run python scripts/verify-evidence-span-golden-retrieval-cases.py
uv run python scripts/verify-evidence-span-local-retrieval-metrics.py --timeout 120
uv run pytest tests/test_evidence_span_local_retrieval_metrics.py -q
uv run ruff check scripts/verify-evidence-span-local-retrieval-metrics.py tests/test_evidence_span_local_retrieval_metrics.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```

Results:

```text
S04 fixture verifier: status=ok, case_count=6, candidate_count=5
S05 metrics evaluator: threshold_passed=true, mismatch_count=0
pytest: 6 passed
ruff: All checks passed
architecture verifier: status=ok, failure_count=0
GSD sync drift: status=OK, diagnostics=8, failed=0
```

## Failure handling proven by tests

The focused tests verify:

- checked-in proof is safe and passing;
- CLI passes with injected confirmed runtime;
- blocked runtime fails thresholds without fallback;
- threshold mismatch is reported;
- unsafe payload fields are rejected;
- managed API and raw vector persistence flags prevent runtime confirmation.

## Requirement boundary

S05 advances R035 by proving that the S04 golden fixture can be evaluated under the approved local/open-weight runtime boundary with perfect seed-fixture metrics. R035 remains active because the proof is still fixture-level and does not compose graph filters, FalkorDB ingest, retrieval, and citation preservation in one flow. S06 owns that integration comparison.

## Non-claims

S05 does not claim:

- product retrieval quality;
- graph-filtered retrieval quality;
- production FalkorDB readiness;
- parser completeness;
- legal-answer correctness;
- legal interpretation authority;
- final legal hierarchy correctness;
- graph-vector/HNSW behavior;
- pilot or 1000-document readiness;
- managed embedding API authorization;
- R035 validation.
