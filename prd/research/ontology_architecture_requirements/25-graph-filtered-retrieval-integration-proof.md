---
milestone: M021-qk4lze
slice: S06
status: proof
requirement_scope:
  - R035
  - R037
non_authoritative: true
created_at: 2026-05-18
---

# Graph-Filtered Retrieval Integration Proof

S06 composed the S02/S03 ingest horizon, S04 EvidenceSpan golden fixture, and S05 local retrieval metrics into one bounded graph-filtered runtime proof. The verifier materialized safe fixture IDs in a unique local FalkorDB graph, applied ontology/temporal/scoped filters, preserved citation bindings, and compared selected IDs against the S04/S05 baseline.

This is not R035 validation and does not prove product retrieval quality, graph-vector/HNSW behavior, hybrid vector search, parser completeness, legal-answer correctness, production FalkorDB readiness, bulk-loader production readiness, or pilot readiness.

## Artifacts

Contract:

```text
prd/research/ontology_architecture_requirements/24-graph-filtered-retrieval-integration-contract.md
```

Proof JSON:

```text
prd/research/ontology_architecture_requirements/graph_filtered_retrieval_integration_proof.json
```

Verifier:

```text
scripts/verify-graph-filtered-retrieval-integration.py
```

Tests:

```text
tests/test_graph_filtered_retrieval_integration.py
```

## Runtime result

Proof schema:

```text
graph-filtered-retrieval-integration-proof/v1
```

Runtime summary:

```json
{
  "graph_runtime": "passed",
  "container_status": "started",
  "cleanup_status": "deleted",
  "candidate_count": 5,
  "evidence_span_count": 4,
  "source_block_count": 4,
  "legal_unit_count": 3,
  "scope_count": 6,
  "baseline_threshold_passed": true
}
```

## Phase outcomes

All S06 phases passed:

- `s04_fixture_verification`
- `s05_baseline_verification`
- `graph_runtime`
- `graph_materialization`
- `ontology_temporal_filter`
- `citation_preservation`
- `baseline_comparison`
- `negative_routes`
- `cleanup`
- `overclaim_safety`

## Route outcomes

| Route | Result |
| --- | --- |
| `positive_evidence_span_filter` | Selected `CAND-M021-S04-EV-ARTICLE-0001`. |
| `positive_source_block_filter` | Selected `CAND-M021-S04-SB-ARTICLE-0001-MARKER`. |
| `stale_temporal_filter` | Selected no stale candidate. |
| `ambiguous_candidate_filter` | Preserved both ambiguous candidates. |
| `unsupported_scope_filter` | Preserved unsupported-scope diagnostic boundary. |
| `scoped_no_answer_filter` | Preserved scoped no-answer diagnostic boundary. |

Citation preservation was checked for the positive candidates. The proof preserved these safe IDs:

- `candidate_id`
- `evidence_span_id`
- `source_block_id`
- `citation_key`
- `act_edition_id`

No raw legal text, raw query text, vector values, provider payloads, generated query text, generated legal-answer prose, secrets, absolute paths, temporary paths, `.gsd/exec` paths, or runtime rows are persisted.

## Verification

Final S06 verification evidence:

```text
gsd_exec[45f4732b-b015-4fbe-b15f-4dac0190f4a9]
```

Command chain:

```bash
uv run python scripts/verify-evidence-span-golden-retrieval-cases.py
uv run python scripts/verify-evidence-span-local-retrieval-metrics.py --timeout 120
uv run python scripts/verify-graph-filtered-retrieval-integration.py --timeout 120 --readiness-timeout 3
uv run pytest tests/test_graph_filtered_retrieval_integration.py -q
uv run ruff check scripts/verify-graph-filtered-retrieval-integration.py tests/test_graph_filtered_retrieval_integration.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```

Results:

```text
S04 fixture verifier: status=ok
S05 metrics evaluator: threshold_passed=true, mismatch_count=0
S06 verifier: all phases passed, baseline comparison passed, cleanup deleted
pytest: 6 passed
ruff: All checks passed
architecture verifier: status=ok, failure_count=0
GSD sync drift: status=OK, diagnostics=8, failed=0
```

## Requirement boundary

S06 materially advances R035 because graph filtering, temporal/stale handling, citation ID preservation, and baseline comparison now run in one bounded local FalkorDB flow over safe fixture IDs.

R035 remains active for S07 lifecycle assessment because this proof is still fixture-scoped and does not validate full ontology architecture readiness, product retrieval quality, parser completeness, production FalkorDB behavior, legal-answer correctness, graph-vector/HNSW behavior, or pilot scale.

R037 remains active/partially evidenced: S06 uses prior ingest evidence and graph materialization mechanics, but does not prove larger ingestion, skip/error accounting, resource profile, or production data loading.

## Non-claims

S06 does not claim:

- R035 validation;
- product retrieval quality;
- graph-vector or HNSW behavior;
- hybrid vector search quality;
- parser completeness;
- legal-answer correctness;
- legal interpretation authority;
- production FalkorDB readiness;
- bulk-loader production readiness;
- pilot or 1000-document readiness.
