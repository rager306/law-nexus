---
milestone: M022-5t4bzn
slice: S03
status: proof
requirement_scope:
  - R035
non_authoritative: true
created_at: 2026-05-18
---

# Representative EvidenceSpan Metrics Proof

S03 evaluated bounded representative metrics over the M022 ten-case EvidenceSpan corpus using the approved local/open-weight runtime boundary.

## Artifacts

Fixture:

```text
prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json
```

Evaluator:

```text
scripts/verify-representative-evidence-span-retrieval-metrics.py
```

Proof JSON:

```text
prd/research/ontology_architecture_requirements/representative_evidence_span_retrieval_metrics_proof.json
```

Tests:

```text
tests/test_representative_evidence_span_retrieval_metrics.py
```

## Runtime boundary

```text
model_id: deepvk/USER-bge-m3
runtime_status: confirmed_runtime
observed_vector_dimension: 1024
managed_api_used: false
raw_vectors_persisted: false
network_used: false
```

## Metrics

All bounded representative fixture metrics met the S03 thresholds:

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

## Fixture refinement found by S03

The first S03 evaluator run correctly blocked because the `positive_with_distractor` fixture case had a rank-2 distractor but did not list it in `expected_rejected_candidate_ids`.

The fixture was refined by adding:

```text
CAND-M022-003-DISTRACTOR-ARTICLE
```

to the case's expected rejected candidates. After that refinement, the S02 fixture verifier and S03 metrics evaluator both passed.

## Verification

Final S03 verification evidence:

```text
gsd_exec[6cb688a7-a7fe-4d29-8595-9c3fcc69e931]
```

Command chain:

```bash
uv run python scripts/verify-representative-evidence-span-retrieval-corpus.py
uv run python scripts/verify-representative-evidence-span-retrieval-metrics.py
uv run pytest tests/test_representative_evidence_span_retrieval_corpus.py tests/test_representative_evidence_span_retrieval_metrics.py -q
uv run ruff check scripts/verify-representative-evidence-span-retrieval-corpus.py scripts/verify-representative-evidence-span-retrieval-metrics.py tests/test_representative_evidence_span_retrieval_corpus.py tests/test_representative_evidence_span_retrieval_metrics.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```

Results:

```text
S02 fixture verifier: status=ok
S03 metrics evaluator: status=passed
tests: 15 passed
ruff: All checks passed
architecture verifier: status=ok
GSD sync drift: status=OK
```

## Safety boundary

The proof excludes:

- raw legal text;
- raw query text;
- source excerpts;
- raw vectors or embedding arrays;
- external provider payloads;
- generated answer prose;
- generated query/Cypher text;
- secrets;
- absolute paths;
- `.gsd/exec` paths;
- raw FalkorDB rows.

## Requirement boundary

S03 advances R035 with bounded representative fixture metrics under the local/open-weight runtime boundary. It does not validate R035 because parser completeness, production retrieval quality, legal-answer correctness, graph-vector/HNSW behavior, hybrid retrieval quality, and pilot readiness remain unproven.

## Non-claims

S03 does not claim:

- R035 validation;
- R037 validation;
- product retrieval quality;
- parser completeness;
- legal-answer correctness;
- legal interpretation authority;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- pilot or 1000-document readiness;
- managed embedding API authorization.
