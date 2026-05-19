---
milestone: M021-qk4lze
slice: S05
status: contract
requirement_scope:
  - R035
non_authoritative: true
created_at: 2026-05-18
---

# EvidenceSpan Local Retrieval Metrics Contract

This contract defines the M021/S05 bounded local/open-weight retrieval metrics proof over the S04 EvidenceSpan golden fixture. It is a fixture-level retrieval metrics proof only. It does not prove product retrieval quality, graph-filtered retrieval quality, parser completeness, legal-answer correctness, graph-vector/HNSW behavior, production FalkorDB readiness, or R035 validation.

## Input fixture

S05 consumes:

```text
prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json
```

Expected schema version:

```text
evidence-span-golden-retrieval-cases/v1
```

The S05 proof must run the S04 fixture verifier before trusting fixture contents:

```text
scripts/verify-evidence-span-golden-retrieval-cases.py
```

## Output artifact

S05 writes:

```text
prd/research/ontology_architecture_requirements/evidence_span_local_retrieval_metrics_proof.json
```

Required proof schema version:

```text
evidence-span-local-retrieval-metrics-proof/v1
```

Required compact output fields:

- `schema_version`
- `milestone_id`
- `slice_id`
- `fixture_artifact`
- `runtime_boundary`
- `metrics`
- `thresholds`
- `threshold_passed`
- `diagnostic_codes`
- `mismatch_count`
- `non_authoritative`
- `non_claims`
- `redaction`

## Approved runtime boundary

The approved local/open-weight model boundary is:

```text
deepvk/USER-bge-m3
```

Expected dimension:

```text
1024
```

Runtime boundary must be derived from the existing safe checker:

```text
scripts/check-local-retrieval-runtime.py
```

Allowed runtime statuses:

- `confirmed_runtime`
- `blocked_environment`
- `blocked_model_unavailable`
- `blocked_dimension_mismatch`
- `blocked_policy_violation`
- `blocked_unsafe_artifact`
- `not_run_contract_only`

If the approved runtime is unavailable, S05 must emit blocked diagnostics and must not substitute another model, managed embedding API, GigaChat/GigaEmbeddings, external LLM, remote vector service, or network download.

## Metric semantics

S05 computes fixture-level metrics from the S04 golden-set expected labels and case classes:

| Metric | Meaning | Threshold |
| --- | --- | ---: |
| `mrr` | Mean reciprocal rank over selected positive cases. | 1.0 |
| `recall_at_1` | Positive cases with a relevant expected candidate at rank 1. | 1.0 |
| `recall_at_3` | Positive cases with a relevant expected candidate in top 3. | 1.0 |
| `stale_rejection_rate` | Stale temporal negative cases rejected with diagnostic. | 1.0 |
| `ambiguous_rejection_rate` | Ambiguous cases reported as ambiguous without arbitrary selection. | 1.0 |
| `unsupported_scope_accuracy` | Unsupported scopes reported as unsupported. | 1.0 |
| `no_answer_accuracy` | Scoped no-answer cases remain empty and diagnostic-bearing. | 1.0 |
| `runtime_boundary_confirmed` | Approved local runtime confirmed, or 0.0 if blocked. | 1.0 |

If runtime is blocked, metrics may still be computed as fixture diagnostics, but `threshold_passed` must be false because S05 did not prove local runtime execution.

## Required case mapping

S05 maps S04 case classes as follows:

| S04 case class | S05 role |
| --- | --- |
| `positive_evidence_span` | positive retrieval metric |
| `positive_source_block_marker` | positive retrieval metric |
| `stale_temporal_negative` | stale rejection metric |
| `ambiguous_candidate_set` | ambiguous rejection metric |
| `unsupported_scope` | unsupported-scope metric |
| `scoped_no_answer` | no-answer metric |

## Diagnostics

Allowed diagnostic codes:

- `runtime_confirmed`
- `runtime_blocked`
- `threshold_mismatch`
- `metric_mismatch`
- `stale_temporal_candidate`
- `ambiguous_candidate_set`
- `unsupported_scope`
- `scoped_no_answer`
- `unsafe_fixture_payload`
- `fixture_verifier_failed`
- `managed_api_forbidden`
- `raw_vector_persistence_forbidden`

Diagnostics must be compact and must not include raw legal text, raw query text, raw vectors, provider payloads, secrets, absolute paths, temporary paths, runtime rows, or generated legal-answer prose.

## Redaction and safety

Durable outputs must set these boundaries to true:

- `source_text_excluded`
- `query_text_excluded`
- `raw_vectors_excluded`
- `external_payloads_excluded`
- `secrets_excluded`
- `absolute_paths_excluded`
- `temporary_paths_excluded`
- `gsd_exec_paths_excluded`
- `runtime_rows_excluded`
- `generated_legal_answer_excluded`

The proof must not include fields named `provider_payload`, `embedding_vector`, `raw_legal_text`, `source_excerpt`, `prompt`, `secret`, `vector`, `runtime_row`, or `generated_answer_prose`.

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

## Verification

S05 must pass:

```bash
uv run python scripts/verify-evidence-span-golden-retrieval-cases.py
uv run python scripts/verify-evidence-span-local-retrieval-metrics.py
uv run pytest tests/test_evidence_span_local_retrieval_metrics.py -q
uv run ruff check scripts/verify-evidence-span-local-retrieval-metrics.py tests/test_evidence_span_local_retrieval_metrics.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```
