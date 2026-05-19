---
milestone: M022-5t4bzn
slice: S04
status: final-verification
requirement_scope:
  - R035
non_authoritative: true
created_at: 2026-05-18
---

# M022 Final Verification Report

M022 completed the representative EvidenceSpan retrieval-quality proof horizon. The milestone passed bounded verification and advanced R035, but R035 remains active and not validated.

## Delivered artifacts

Contract:

```text
prd/research/ontology_architecture_requirements/28-representative-retrieval-quality-contract.md
```

Representative corpus fixture and proof:

```text
prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json
prd/research/ontology_architecture_requirements/29-representative-evidence-span-corpus-proof.md
scripts/verify-representative-evidence-span-retrieval-corpus.py
tests/test_representative_evidence_span_retrieval_corpus.py
```

Representative metrics proof:

```text
prd/research/ontology_architecture_requirements/representative_evidence_span_retrieval_metrics_proof.json
prd/research/ontology_architecture_requirements/30-representative-evidence-span-metrics-proof.md
scripts/verify-representative-evidence-span-retrieval-metrics.py
tests/test_representative_evidence_span_retrieval_metrics.py
```

Lifecycle assessment:

```text
prd/research/ontology_architecture_requirements/31-m022-representative-retrieval-quality-assessment.md
```

## Verification evidence

Final verification command evidence:

```text
gsd_exec[d1d2664b-5423-4889-a5ee-fa0360fa572c]
```

Command chain:

```bash
uv run python scripts/verify-representative-evidence-span-retrieval-corpus.py
uv run python scripts/verify-representative-evidence-span-retrieval-metrics.py
uv run pytest tests/test_representative_evidence_span_retrieval_corpus.py tests/test_representative_evidence_span_retrieval_metrics.py -q
uv run ruff check scripts/verify-representative-evidence-span-retrieval-corpus.py scripts/verify-representative-evidence-span-retrieval-metrics.py tests/test_representative_evidence_span_retrieval_corpus.py tests/test_representative_evidence_span_retrieval_metrics.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
R035 lifecycle marker check
```

Result summary:

```text
S02 fixture verifier: status=ok
S03 metrics evaluator: status=passed
focused tests: 15 passed
ruff: All checks passed
architecture verifier: status=ok
GSD sync drift: status=OK
R035 lifecycle markers: OK
```

## Representative corpus outcome

M022 delivered a ten-case representative EvidenceSpan corpus fixture with these required classes:

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

The fixture uses safe IDs and hashes only. It excludes raw legal text, raw query text, source excerpts, raw vectors, external provider payloads, generated answer prose, generated query/Cypher text, secrets, absolute paths, `.gsd/exec` fixture anchors, and raw FalkorDB rows.

## Metrics outcome

M022/S03 passed all bounded deterministic representative fixture metrics:

```text
mrr: 1.0
recall_at_1: 1.0
recall_at_3: 1.0
distractor_rejection_rate: 1.0
stale_rejection_rate: 1.0
ambiguous_preservation_rate: 1.0
unsupported_scope_accuracy: 1.0
no_answer_accuracy: 1.0
citation_preservation_rate: 1.0
unsafe_rejection_rate: 1.0
runtime_boundary_confirmed: 1.0
```

Runtime boundary:

```text
model_id: deepvk/USER-bge-m3
runtime_status: confirmed_runtime
observed_vector_dimension: 1024
managed_api_used: false
raw_vectors_persisted: false
network_used: false
```

## Requirement outcome

R035 after M022:

```text
active / strongly advanced with representative fixture metrics, not validated
```

R037 after M022 remains unchanged in substance:

```text
active / partially evidenced
```

## Remaining proof gaps

M022 does not close these R035 proof gaps:

- parser-to-EvidenceSpan materialization from real source extraction;
- product retrieval quality over a larger and less curated corpus;
- legal-answer correctness;
- generated-query safety if generated queries become part of product workflows;
- graph-vector/HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB behavior;
- production ingest behavior and resource profile;
- pilot or 1000-document readiness;
- registry extractor integration and regenerated registry outputs.

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

## Closeout verdict

M022 passes its bounded milestone contract. It provides representative fixture and metric evidence for future retrieval-quality planning, but future work must move beyond curated fixture-only evaluation before any product-quality or R035-validation claim is made.
