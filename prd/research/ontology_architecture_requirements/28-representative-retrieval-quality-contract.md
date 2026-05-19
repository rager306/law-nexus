---
milestone: M022-5t4bzn
slice: S01
status: contract
requirement_scope:
  - R035
non_authoritative: true
created_at: 2026-05-18
---

# Representative Retrieval Quality Contract

This contract defines the M022 representative EvidenceSpan retrieval-quality proof horizon. It expands beyond M021's six-case golden fixture, but remains a bounded local/open-weight evaluation. It does not validate R035 and does not prove product retrieval quality, parser completeness, legal-answer correctness, graph-vector/HNSW behavior, hybrid retrieval quality, production FalkorDB readiness, or pilot readiness.

## Purpose

M021 proved that a small EvidenceSpan/SourceBlock fixture can be loaded, scored, and graph-filtered locally with citation IDs preserved. M022 asks a narrower next question:

```text
Can the retrieval evaluation corpus become more representative without losing citation safety, local/open-weight boundaries, deterministic diagnostics, and non-authoritative lifecycle wording?
```

## Inputs

M022 may consume these tracked M021 artifacts:

```text
prd/research/ontology_architecture_requirements/27-m021-final-verification-report.md
prd/research/ontology_architecture_requirements/26-m021-lifecycle-horizon-assessment.md
prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json
prd/research/ontology_architecture_requirements/evidence_span_local_retrieval_metrics_proof.json
prd/research/ontology_architecture_requirements/graph_filtered_retrieval_integration_proof.json
prd/retrieval/fixtures/offline_citation_retrieval_cases.json
prd/retrieval/fixtures/local_retrieval_quality_benchmark.json
prd/retrieval/fixtures/real_artifact_retrieval_cases.json
prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json
```

M022 must not cite `.gsd/exec` paths as durable source anchors. Command evidence may cite `gsd_exec[...]` IDs in proof reports, but fixtures/manifests must use tracked repo-relative paths.

## Stable source-anchor policy

M021 final verification found that runtime proof reports can be mutable because they include duration fields. Therefore M022 should prefer stable source anchors in this order:

1. Contract and fixture source files that do not change on every runtime run.
2. Existing retrieval fixture files with deterministic content.
3. Final proof reports that summarize runtime evidence without requiring duration-sensitive hash stability.
4. Runtime JSON proof reports only when the verifier explicitly refreshes hashes immediately before checking.

Representative corpus fixtures should not store sha256 anchors to mutable runtime reports unless the verifier owns refresh behavior. Prefer `source_artifact_refs` plus separately verified runtime proof status when possible.

## Output artifacts

Expected S02 fixture or manifest:

```text
prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json
```

Expected S03 metrics proof:

```text
prd/research/ontology_architecture_requirements/representative_evidence_span_retrieval_metrics_proof.json
```

Expected S04 assessment:

```text
prd/research/ontology_architecture_requirements/29-representative-retrieval-quality-assessment.md
```

## Representative corpus requirements

The representative corpus must expand beyond M021's six cases. Minimum target:

```text
at least 10 cases
```

Required case classes:

- `positive_evidence_span`
- `positive_source_block_marker`
- `positive_with_distractor`
- `stale_temporal_negative`
- `ambiguous_candidate_set`
- `unsupported_scope`
- `scoped_no_answer`
- `citation_preservation_boundary`
- `edition_mismatch_negative`
- `unsafe_payload_boundary`

Allowed expected result values:

- `selected`
- `rejected`
- `ambiguous`
- `unsupported`
- `no_answer`
- `boundary_rejected`

Required per-case fields:

- deterministic `case_id` using `CASE-M022-*`;
- deterministic `query_id` using `QUERY-M022-*`;
- `case_class`;
- `query_kind`;
- `query_text_sha256`, never raw query text;
- `scope_id`;
- `as_of_date` where applicable;
- expected candidate IDs or expected rejected IDs;
- expected diagnostic codes;
- source artifact refs using repo-relative tracked paths;
- safe candidate descriptors with EvidenceSpan, SourceBlock, citation key, act edition, source record, and expected label IDs only.

## Metric semantics

M022 metrics are representative-corpus signals only:

| Metric | Meaning |
| --- | --- |
| `mrr` | Mean reciprocal rank over selected positive cases. |
| `recall_at_1` | Positive cases with relevant candidate ranked first. |
| `recall_at_3` | Positive cases with relevant candidate in top 3. |
| `distractor_rejection_rate` | Distractor candidates are not promoted over relevant candidates. |
| `stale_rejection_rate` | Stale temporal candidates are rejected. |
| `ambiguous_preservation_rate` | Ambiguous cases remain ambiguous rather than arbitrarily selected. |
| `unsupported_scope_accuracy` | Unsupported scopes are reported as unsupported. |
| `no_answer_accuracy` | Scoped no-answer cases remain empty and diagnostic-bearing. |
| `citation_preservation_rate` | Selected candidates preserve EvidenceSpan, SourceBlock, citation key, and act edition IDs. |
| `unsafe_rejection_rate` | Unsafe/boundary cases fail closed. |
| `runtime_boundary_confirmed` | Approved local/open-weight runtime remains confirmed or explicit blocked diagnostics are emitted. |

Thresholds are strict for deterministic fixture metrics but must be reported as bounded representative-corpus evidence, not product quality. If a larger future corpus makes strict thresholds unrealistic, that future milestone must define a new threshold contract rather than silently weakening M022.

## Runtime boundary

Allowed model boundary remains:

```text
deepvk/USER-bge-m3
```

Allowed execution mode:

```text
local_open_weight
```

Managed embedding APIs, GigaChat/GigaEmbeddings fallback, hosted LLMs, remote vector services, and network downloads are excluded. If local runtime is unavailable, emit blocked diagnostics; do not substitute another model or provider.

## Diagnostic taxonomy

Allowed diagnostic codes:

- `representative_fixture_verified`
- `runtime_confirmed`
- `runtime_blocked`
- `threshold_mismatch`
- `metric_mismatch`
- `distractor_rank_violation`
- `stale_temporal_candidate`
- `ambiguous_candidate_set`
- `unsupported_scope`
- `scoped_no_answer`
- `citation_binding_missing`
- `unsafe_payload_rejected`
- `source_anchor_missing`
- `invalid_expected_candidate_reference`
- `mutable_source_hash_refresh_required`
- `overclaim_rejected`

## Redaction and safety

Durable M022 artifacts must exclude:

- raw legal text;
- source excerpts;
- raw query text;
- raw vectors or embedding arrays;
- provider payloads;
- generated legal-answer prose;
- generated Cypher or generated query text;
- secrets, tokens, PII;
- absolute paths;
- temporary paths;
- `.gsd/exec` paths;
- raw FalkorDB rows.

Use safe redaction keys such as:

- `source_text_excluded`
- `query_text_excluded`
- `vector_values_excluded`
- `external_payloads_excluded`
- `generated_answer_excluded`
- `generated_query_excluded`
- `secrets_excluded`
- `absolute_paths_excluded`
- `temporary_paths_excluded`
- `gsd_exec_paths_excluded`
- `runtime_rows_excluded`

Avoid key names containing forbidden fragments such as `raw_legal_text`, `provider_payload`, or `embedding_vector`.

## Requirement lifecycle boundary

R035 may be advanced by M022, but must remain active unless a later explicit validation proves the full scope. M022 alone does not validate:

- parser-to-EvidenceSpan materialization from real source extraction;
- product retrieval quality;
- legal-answer correctness;
- graph-vector/HNSW or hybrid retrieval behavior;
- production FalkorDB behavior;
- pilot readiness.

R037 should not be materially changed by M022 unless the milestone adds new ingest/materialization evidence. Representative retrieval corpus work is primarily R035-owned.

## Non-claims

M022 does not claim:

- R035 validation;
- R037 validation;
- product retrieval quality;
- parser completeness;
- legal-answer correctness;
- legal interpretation authority;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- bulk-loader production readiness;
- pilot or 1000-document readiness;
- managed embedding API authorization.

## Verification obligations

Downstream slices must provide:

```bash
uv run python <representative-fixture-verifier>
uv run python <representative-metrics-evaluator>
uv run pytest <representative-tests> -q
uv run ruff check <representative-scripts-and-tests>
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```

Final validation wording should say:

```text
M022 passed bounded representative retrieval-corpus success criteria.
```

It must not say:

```text
R035 is validated.
Product retrieval quality is proven.
```
