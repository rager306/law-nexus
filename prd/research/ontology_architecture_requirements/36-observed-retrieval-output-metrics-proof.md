---
milestone: M023-9rfkrs
slice: S03
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-18
---

# Observed Retrieval Output Metrics Proof

S03 created a separate observed-output artifact and verified metrics by comparing observed ranked/rejected candidate IDs and observed diagnostics against expected fixture fields. This remediates the M022 self-confirming metrics gap at the safe-ID proof layer.

## Artifacts

Observed output artifact:

```text
prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_outputs.json
```

Evaluator:

```text
scripts/verify-observed-retrieval-output-metrics.py
```

Proof JSON:

```text
prd/research/ontology_architecture_requirements/observed_retrieval_output_metrics_proof.json
```

Tests:

```text
tests/test_observed_retrieval_output_metrics.py
```

## Retrieval mode boundary

Observed outputs use this retrieval mode:

```text
safe_id_provenance_rule_retrieval_v1
```

This mode compares safe IDs and provenance-bound diagnostics. It is deliberately not a product semantic retrieval proof and not a legal-answer proof.

## Runtime boundary

The evaluator also confirms the approved local/open-weight runtime boundary:

```text
model_id: deepvk/USER-bge-m3
runtime_status: confirmed_runtime
observed_vector_dimension: 1024
managed_api_used: false
raw_vectors_persisted: false
network_used: false
```

Runtime confirmation remains necessary but insufficient. Metrics are accepted only when the observed-output artifact is present and passes anti-self-confirming checks.

## Metrics

The observed-output evaluator passed these bounded metrics:

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

## Anti-self-confirming checks

The evaluator rejects observed-output artifacts that:

- are missing entirely;
- omit observed ranked candidate IDs for selected cases;
- include expected fixture fields such as `expected_candidate_ids`, `expected_diagnostic_codes`, `expected_label`, or `rank`;
- use an unsupported retrieval mode;
- set `derived_from_expected_fixture_fields` to anything other than `false`;
- omit query/source provenance refs;
- contain unsafe raw text, provider payloads, vectors, generated answer/query text, absolute paths, or `.gsd/exec` durable anchors.

## Verification

Final S03 verification evidence:

```text
gsd_exec[05585f38-ebe6-4aed-aaad-6db66daad046]
```

Command chain:

```bash
uv run python scripts/verify-observed-retrieval-provenance.py
uv run python scripts/verify-observed-retrieval-output-metrics.py
uv run pytest tests/test_observed_retrieval_provenance.py tests/test_observed_retrieval_output_metrics.py -q
uv run ruff check scripts/verify-observed-retrieval-provenance.py scripts/verify-observed-retrieval-output-metrics.py tests/test_observed_retrieval_provenance.py tests/test_observed_retrieval_output_metrics.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```

Results:

```text
provenance verifier: status=ok
observed-output evaluator: status=passed
focused tests: 17 passed
ruff: All checks passed
architecture verifier: status=ok
GSD sync drift: status=OK
```

## What this proves

S03 proves that M023 now has an observed-output artifact and an evaluator that compares observed safe-ID outputs to expected fixture answers instead of computing metrics directly from fixture ranks/labels.

## What this does not prove

S03 does not prove:

- model semantic retrieval quality;
- product retrieval quality;
- legal-answer correctness;
- parser completeness;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- R035 validation.

## S04 handoff

S04 must run an independent proof review. The reviewer should specifically check whether `safe_id_provenance_rule_retrieval_v1` is adequately described as a bounded safe-ID observed-output proof and not overstated as semantic model retrieval.
