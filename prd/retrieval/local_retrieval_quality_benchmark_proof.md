---
title: "Local Retrieval Quality Benchmark Proof"
status: "bounded-evidence"
owner: "M015/S02"
gate: "GATE-G011"
proof_level: "unit-test + CLI proof"
non_authoritative: true
created_at: "2026-05-13"
---

# Local Retrieval Quality Benchmark Proof

This report records the M015 executable local/open-weight retrieval quality benchmark proof. It advances `GATE-G011` with bounded seed-benchmark evidence over tracked fixtures and S10 `deepvk/USER-bge-m3` host-local runtime boundary metadata.

This report does not close `GATE-G011`. It does not prove product retrieval quality, parser completeness, legal-answer correctness, production FalkorDB runtime behavior, production graph schema readiness, managed embedding fallback safety, GigaEmbeddings readiness, or legal interpretation authority.

## Proof inputs

The proof uses only tracked repository-relative inputs:

- `prd/retrieval/local_retrieval_quality_benchmark_contract.md`
- `prd/retrieval/fixtures/local_retrieval_quality_benchmark.json`
- `scripts/build-local-retrieval-quality-benchmark.py`
- `scripts/verify-local-retrieval-quality-benchmark.py`
- `tests/test_local_retrieval_quality_benchmark_contract.py`
- `tests/test_local_retrieval_quality_benchmark_fixture.py`
- `tests/test_local_retrieval_quality_benchmark_cli.py`
- `prd/retrieval/fixtures/offline_citation_retrieval_cases.json`
- `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json`

The proof does not fetch external data, call a managed embedding API, call an LLM, run GigaEmbeddings, persist raw embedding vectors, persist raw legal text, generate legal answer prose, or inspect untracked corpora.

## Executable command

The proof command is:

```bash
uv run python scripts/verify-local-retrieval-quality-benchmark.py
```

The slice-level verification command is:

```bash
uv run pytest tests/test_local_retrieval_quality_benchmark_cli.py tests/test_local_retrieval_quality_benchmark_report.py -q && uv run python scripts/verify-local-retrieval-quality-benchmark.py
```

## Proof result

Fresh proof output:

```json
{"diagnostic_code_inventory":["ambiguous_rejected","model_runtime_available","scoped_no_answer","unsafe_payload_rejected"],"fixture_path":"prd/retrieval/fixtures/local_retrieval_quality_benchmark.json","managed_api_used":false,"metrics":{"ambiguous_rejection_rate":1.0,"mrr":1.0,"no_answer_accuracy":1.0,"recall_at_1":1.0,"recall_at_3":1.0,"unsafe_rejection_rate":1.0},"mismatch_count":0,"model_id":"deepvk/USER-bge-m3","model_status":"available","non_authoritative":true,"observed_vector_dimension":1024,"positive_query_count":2,"raw_vectors_persisted":false,"schema_version":"local-retrieval-quality-benchmark-proof/v1","threshold_passed":true,"total_cases":6}
```

Summary:

| Field | Value |
| --- | ---: |
| `total_cases` | 6 |
| `positive_query_count` | 2 |
| `mrr` | 1.0 |
| `recall_at_1` | 1.0 |
| `recall_at_3` | 1.0 |
| `no_answer_accuracy` | 1.0 |
| `ambiguous_rejection_rate` | 1.0 |
| `unsafe_rejection_rate` | 1.0 |
| `threshold_passed` | true |
| `mismatch_count` | 0 |

## Case coverage

The benchmark fixture covers these deterministic case classes:

- `positive_exact_relevance` — relevant candidate ranks first.
- `positive_with_distractor` — relevant candidate ranks above a distractor candidate.
- `scoped_no_answer_quality` — scoped no-answer is counted as safe no-answer behavior.
- `ambiguous_retrieval_rejected` — ambiguous candidate set is rejected without arbitrary ranking.
- `unsafe_payload_rejected` — unsafe payload class is rejected before metric promotion.
- `environment_boundary` — model/runtime boundary is recorded without raw vectors or managed APIs.

## Metric inventory

The proof computes only fixture-level metrics:

- `mrr`
- `recall_at_1`
- `recall_at_3`
- `no_answer_accuracy`
- `ambiguous_rejection_rate`
- `unsafe_rejection_rate`

All thresholds are `1.0` for this seed benchmark. These metrics are deterministic regression signals over a small tracked fixture, not production Russian legal retrieval quality.

## Model boundary

M015 records `deepvk/USER-bge-m3` as the only allowed local/open-weight baseline, inherited from S10 host-local runtime evidence.

- `model_id`: `deepvk/USER-bge-m3`
- `model_status`: `available`
- `observed_vector_dimension`: `1024`
- `managed_api_used`: `false`
- `raw_vectors_persisted`: `false`
- runtime evidence source: `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json`

This model boundary does not prove production retrieval quality or target-hardware reliability. GigaEmbeddings remains blocked/gated and is not promoted by this proof.

## Diagnostic inventory

The proof emitted only bounded diagnostic codes:

- `ambiguous_rejected`
- `model_runtime_available`
- `scoped_no_answer`
- `unsafe_payload_rejected`

Diagnostics are limited to safe IDs, field paths, metrics, case/query/candidate IDs, and repository-relative proof artifact paths. They do not persist raw legal text, raw query text, source excerpts, provider payloads, secrets, PII, embedding vectors, raw FalkorDB rows, generated answer prose, or legal advice.

## GATE-G011 status

This proof advances `GATE-G011` by demonstrating:

- deterministic fixture-level retrieval metrics over tracked proof cases;
- positive relevance and distractor ordering behavior;
- scoped no-answer, ambiguous rejection, and unsafe rejection accounting;
- local/open-weight model boundary metadata from S10 without managed API use or raw vector persistence.

`GATE-G011` remains open because this seed benchmark does not establish product retrieval quality, representative corpus coverage, target-hardware runtime reliability, broad Russian legal recall/relevance, parser completeness, or legal-answer correctness.

## Non-claims

M015 local retrieval quality benchmark proof does not prove product retrieval quality.
M015 local retrieval quality benchmark proof does not prove parser completeness.
M015 local retrieval quality benchmark proof does not prove legal-answer correctness.
M015 local retrieval quality benchmark proof does not prove legal interpretation authority.
M015 local retrieval quality benchmark proof does not prove production FalkorDB runtime behavior.
M015 local retrieval quality benchmark proof does not prove production graph schema readiness.
M015 local retrieval quality benchmark proof does not allow managed embedding API fallback.
M015 local retrieval quality benchmark proof does not promote GigaEmbeddings.
M015 local retrieval quality benchmark proof does not close GATE-G011.
M015 local retrieval quality benchmark proof does not close GATE-G008.
M015 local retrieval quality benchmark proof does not make LLM output legal authority.
M015 local retrieval quality benchmark proof does not make proof-local fixture metrics production metrics.

## S03 handoff

S03 may register this report as bounded evidence for `GATE-G011` progress in the architecture registry. The registry item should remain `bounded-evidence` and must preserve the non-claims above. Any architecture edge to `GATE-G011` should be phrased as bounded by or advancing the gate, not satisfying or closing it.
