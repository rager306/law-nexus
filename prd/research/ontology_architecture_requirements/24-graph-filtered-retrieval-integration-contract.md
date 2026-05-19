---
milestone: M021-qk4lze
slice: S06
status: contract
requirement_scope:
  - R035
  - R037
non_authoritative: true
created_at: 2026-05-18
---

# Graph-Filtered Retrieval Integration Contract

This contract defines the M021/S06 bounded graph-filtered retrieval integration proof. S06 composes prior ingest and retrieval evidence into one runtime flow using safe IDs only. It does not prove product retrieval quality, graph-vector/HNSW behavior, hybrid vector search, parser completeness, legal-answer correctness, production FalkorDB readiness, pilot readiness, or R035 validation.

## Inputs

S06 consumes these tracked artifacts:

```text
prd/research/ontology_architecture_requirements/falkordb_csv_ingest_proof.json
prd/research/ontology_architecture_requirements/falkordb_bulk_loader_proof.json
prd/research/ontology_architecture_requirements/19-falkordb-loader-recommendation.md
prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json
prd/research/ontology_architecture_requirements/evidence_span_local_retrieval_metrics_proof.json
prd/research/ontology_architecture_requirements/23-evidence-span-local-retrieval-metrics-proof.md
```

S06 must run the S04 fixture verifier and S05 metrics evaluator before trusting retrieval baseline inputs.

## Output artifact

S06 writes:

```text
prd/research/ontology_architecture_requirements/graph_filtered_retrieval_integration_proof.json
```

Expected schema version:

```text
graph-filtered-retrieval-integration-proof/v1
```

## Loader choice

Use `LOAD CSV` or direct safe fixture materialization for iterative graph setup. S03 proved tiny bulk-loader viability, but S06 needs inspectable iterative filter behavior and optional reruns; therefore `LOAD CSV` remains the preferred S06 setup path unless the verifier creates a unique graph per run.

Any bulk-loader use must preserve the S03 boundary: create-new-graph semantics only, not idempotent update proof.

## Graph fixture shape

The runtime graph may contain only compact proof-local entities such as:

- `RetrievalCandidate`
- `EvidenceSpan`
- `SourceBlock`
- `LegalUnit`
- `ActEdition`
- `RetrievalScope`

Required safe properties:

- `candidate_id`
- `evidence_span_id`
- `source_block_id`
- `citation_key`
- `source_record_id`
- `act_edition_id`
- `case_class`
- `expected_label`
- `temporal_status`
- `scope_id`
- `ontology_class`

Forbidden graph/proof payloads:

- raw legal text;
- source excerpts;
- raw query text;
- raw vectors or embeddings;
- provider payloads;
- generated Cypher from an LLM;
- generated legal-answer prose;
- secrets;
- absolute paths;
- temporary paths;
- raw FalkorDB rows.

## Required phases

S06 proof JSON must include phase statuses for:

| Phase | Purpose |
| --- | --- |
| `s04_fixture_verification` | S04 golden fixture accepted. |
| `s05_baseline_verification` | S05 fixture-level metrics accepted. |
| `graph_runtime` | FalkorDB runtime started or blocked. |
| `graph_materialization` | Safe fixture graph created and counts verified. |
| `ontology_temporal_filter` | Positive and stale/temporal routes executed. |
| `citation_preservation` | EvidenceSpan, SourceBlock, citation, legal unit, and act edition IDs preserved. |
| `baseline_comparison` | Graph-filtered safe IDs compared against S04/S05 expectations. |
| `negative_routes` | Ambiguous, unsupported-scope, stale, and scoped no-answer routes checked. |
| `cleanup` | Runtime cleanup completed or reported. |
| `overclaim_safety` | Non-claim boundary checked. |

Allowed phase statuses:

- `passed`
- `blocked`
- `failed_closed`
- `not_run`

## Required graph-filter routes

S06 must check these route classes:

| Route | Required result |
| --- | --- |
| `positive_evidence_span_filter` | Selects the expected EvidenceSpan candidate and preserves citation IDs. |
| `positive_source_block_filter` | Selects the expected SourceBlock marker candidate and preserves citation IDs. |
| `stale_temporal_filter` | Rejects wrong-edition or stale candidate. |
| `ambiguous_candidate_filter` | Preserves ambiguity rather than selecting arbitrarily. |
| `unsupported_scope_filter` | Returns unsupported diagnostic for unverified scope. |
| `scoped_no_answer_filter` | Returns scoped no-answer diagnostic with no hidden citations. |

## Baseline comparison

S06 compares graph-filtered results against:

```text
prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json
prd/research/ontology_architecture_requirements/evidence_span_local_retrieval_metrics_proof.json
```

The comparison is over safe IDs only:

- selected candidate IDs;
- rejected candidate IDs;
- diagnostic codes;
- citation binding IDs;
- case classes;
- metric pass/fail boundary.

It must not compare raw text similarity, vector distance, generated answer prose, or legal reasoning.

## Diagnostics

Allowed diagnostic codes:

- `graph_runtime_confirmed`
- `graph_runtime_blocked`
- `graph_materialization_failed`
- `count_mismatch`
- `positive_filter_passed`
- `stale_temporal_candidate_rejected`
- `ambiguous_candidate_preserved`
- `unsupported_scope_preserved`
- `scoped_no_answer_preserved`
- `citation_binding_preserved`
- `baseline_comparison_passed`
- `fixture_verifier_failed`
- `metrics_baseline_failed`
- `unsafe_payload_rejected`
- `overclaim_rejected`

## Redaction

S06 durable outputs must set these redaction boundaries to true:

- `source_text_excluded`
- `query_text_excluded`
- `vector_values_excluded`
- `external_payloads_excluded`
- `generated_query_excluded`
- `generated_answer_excluded`
- `secrets_excluded`
- `absolute_paths_excluded`
- `temporary_paths_excluded`
- `gsd_exec_paths_excluded`
- `runtime_rows_excluded`

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

## Verification

S06 must pass:

```bash
uv run python scripts/verify-evidence-span-golden-retrieval-cases.py
uv run python scripts/verify-evidence-span-local-retrieval-metrics.py --timeout 120
uv run python scripts/verify-graph-filtered-retrieval-integration.py
uv run pytest tests/test_graph_filtered_retrieval_integration.py -q
uv run ruff check scripts/verify-graph-filtered-retrieval-integration.py tests/test_graph_filtered_retrieval_integration.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```
