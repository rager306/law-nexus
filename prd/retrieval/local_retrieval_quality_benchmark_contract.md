---
title: "Local Retrieval Quality Benchmark Contract"
status: "contract-draft"
owner: "M015/S01"
gate: "GATE-G011"
proof_level: "static-check"
non_authoritative: true
created_at: "2026-05-13"
---

# Local Retrieval Quality Benchmark Contract

This contract defines the M015 bounded local/open-weight retrieval quality benchmark proof. It advances `GATE-G011` by defining deterministic fixture-level quality measurements over tracked proof artifacts while preserving the distinction between seed benchmark evidence and product retrieval quality.

This contract does not close `GATE-G011`. It does not prove product retrieval quality, parser completeness, legal-answer correctness, production FalkorDB runtime behavior, local embedding production suitability, or legal interpretation authority.

## Source artifacts

M015 may consume only tracked repository-relative inputs:

- `prd/retrieval/offline_citation_retrieval_proof.md` — M014 executable offline citation retrieval proof and non-claims.
- `prd/retrieval/fixtures/offline_citation_retrieval_cases.json` — deterministic M014 candidate/no-answer/ambiguous corpus.
- `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json` — host-local `deepvk/USER-bge-m3` runtime baseline and explicit quality boundary.
- `prd/architecture/product_readiness_blockers.md` — current open `GATE-G011` readiness boundary.

The proof must not fetch external data, call a managed embedding API, call an LLM, generate legal answer prose, persist raw embedding vectors, run GigaEmbeddings, or inspect untracked local corpora.

## Benchmark query shape

Each benchmark query must be a structured proof object:

| Field | Required | Rule |
| --- | --- | --- |
| `benchmark_query_id` | yes | Stable proof-local ID such as `QR-M015-*`; never raw user prompt text. |
| `query_kind` | yes | One of `positive_retrieval`, `distractor_retrieval`, `scoped_no_answer`, `ambiguous_retrieval`, `unsafe_payload`. |
| `query_text_sha256` | yes | Hash of the bounded synthetic/query label text; raw query text must not be persisted. |
| `scope_id` | yes | Stable proof-local scope ID copied to diagnostics. |
| `expected_relevant_candidate_ids` | yes | IDs expected to rank in the relevant set; empty only for no-answer or unsafe cases. |
| `expected_result` | yes | One of `metrics_pass`, `scoped_no_answer`, `rejected`. |

Query records must not include raw legal text, user prompts, generated legal-answer prose, provider payloads, or legal advice.

## Candidate shape

Each benchmark candidate must be a bounded proof object:

| Field | Required | Rule |
| --- | --- | --- |
| `candidate_id` | yes | Stable proof-local ID such as `BQ-M015-*`. |
| `source_case_id` | yes | M014 or M013 fixture case ID used as provenance. |
| `source_record_ids` | yes | Tracked parser/evidence IDs inherited from prior proof fixtures. |
| `relevance_label` | yes | One of the allowed relevance labels. |
| `score_input_id` | yes | Stable ID for deterministic scoring; not raw text or vector content. |
| `source_artifact` | yes | Repository-relative source artifact path. |

Candidates must not persist raw source excerpts, raw embeddings, vector arrays, FalkorDB rows, legal-answer prose, or legal advice.

## Relevance labels

Allowed `relevance_label` values are exactly:

- `relevant` — candidate is expected to satisfy the benchmark query.
- `distractor` — candidate is valid evidence but should rank below relevant candidates.
- `ambiguous` — multiple candidates cannot be ranked deterministically and must fail closed or be reported separately.
- `no_answer` — no candidate is expected within the explicit benchmark scope.
- `unsafe` — payload or case shape is intentionally unsafe and must be rejected.

## Metric semantics

M015 benchmark metrics are fixture-level quality signals only:

- `mrr` — mean reciprocal rank over positive retrieval queries.
- `recall_at_1` — fraction of positive retrieval queries with a relevant candidate at rank 1.
- `recall_at_3` — fraction of positive retrieval queries with a relevant candidate in the top 3.
- `no_answer_accuracy` — fraction of scoped no-answer queries that return no candidates and emit safe no-answer diagnostics.
- `ambiguous_rejection_rate` — fraction of ambiguous cases rejected without arbitrary tie-breaking.
- `unsafe_rejection_rate` — fraction of unsafe payload cases rejected before metric promotion.

The benchmark must never present these metrics as production Russian legal retrieval quality. They are seed-fixture metrics over a tracked corpus.

## Threshold contract

The seed benchmark thresholds are intentionally strict but bounded:

| Metric | Minimum |
| --- | ---: |
| `mrr` | 1.0 |
| `recall_at_1` | 1.0 |
| `recall_at_3` | 1.0 |
| `no_answer_accuracy` | 1.0 |
| `ambiguous_rejection_rate` | 1.0 |
| `unsafe_rejection_rate` | 1.0 |

A future broader benchmark may lower or stratify thresholds only with a new contract, larger corpus, and explicit non-claim review.

## Environment and model diagnostics

The only local/open-weight baseline allowed for M015 is `deepvk/USER-bge-m3`, because S10 records it as host-local bounded runtime evidence with observed dimension `1024`.

M015 diagnostics must record:

| Field | Required | Purpose |
| --- | --- | --- |
| `model_id` | yes | Expected `deepvk/USER-bge-m3` or `fixture-only` when runtime is unavailable. |
| `model_status` | yes | `available`, `blocked_environment`, or `not_used_fixture_mode`. |
| `observed_vector_dimension` | conditional | `1024` only when runtime evidence is used. |
| `managed_api_used` | yes | Must be `false`. |
| `raw_vectors_persisted` | yes | Must be `false`. |
| `runtime_evidence_source` | yes | Repository-relative S10 proof path or fixture-mode explanation. |

If runtime is unavailable, the proof must emit safe `blocked_environment` diagnostics. It must not silently pass as runtime proof.

## Benchmark case classes

The seed corpus must include:

- `positive_exact_relevance` — a relevant candidate ranks first.
- `positive_with_distractor` — relevant candidate ranks above distractor candidates.
- `scoped_no_answer_quality` — no candidate is expected and no-answer is counted correctly.
- `ambiguous_retrieval_rejected` — ambiguous candidate set is rejected without arbitrary tie-breaking.
- `unsafe_payload_rejected` — forbidden payload case is rejected before metrics are promoted.
- `environment_boundary` — model/runtime availability is recorded safely.

## Diagnostic shape

Diagnostics must be compact safe objects with these fields:

| Field | Required | Purpose |
| --- | --- | --- |
| `code` | yes | Stable diagnostic code. |
| `severity` | yes | `info`, `warning`, or `error`. |
| `benchmark_case_id` | yes | Proof case ID. |
| `benchmark_query_id` | conditional | Query ID when available. |
| `candidate_id` | conditional | Candidate ID when available. |
| `metric` | conditional | Metric that failed or was computed. |
| `field_path` | conditional | Unsafe/malformed field. |
| `proof_artifact` | yes | Repository-relative artifact path. |

Diagnostics must not include raw legal text, raw query text, source excerpts, provider payloads, secrets, PII, embedding vectors, raw FalkorDB rows, generated answer prose, or legal advice.

## Redaction and forbidden payloads

The proof must reject or avoid durable payloads containing:

- raw legal text or full source excerpts;
- raw query prompts or user prompts;
- credentials, tokens, secrets, or PII;
- raw embedding arrays or vectors;
- managed embedding API payloads or provider response bodies;
- raw FalkorDB runtime rows;
- generated legal advice or authoritative answer prose;
- product-facing retrieval quality claims.

## GATE-G011 status

M015 can advance `GATE-G011` only as bounded seed-benchmark evidence. `GATE-G011` remains open unless a final milestone validation explicitly confirms that the benchmark scope, corpus size, runtime evidence, and metrics satisfy the full local embedding quality gate.

## Non-claims

M015 local retrieval quality benchmark does not prove product retrieval quality.
M015 local retrieval quality benchmark does not prove parser completeness.
M015 local retrieval quality benchmark does not prove legal-answer correctness.
M015 local retrieval quality benchmark does not prove legal interpretation authority.
M015 local retrieval quality benchmark does not prove production FalkorDB runtime behavior.
M015 local retrieval quality benchmark does not prove production graph schema readiness.
M015 local retrieval quality benchmark does not allow managed embedding API fallback.
M015 local retrieval quality benchmark does not promote GigaEmbeddings.
M015 local retrieval quality benchmark does not close GATE-G011 unless final milestone validation explicitly confirms full gate criteria.
M015 local retrieval quality benchmark does not close GATE-G008.
M015 local retrieval quality benchmark does not make LLM output legal authority.

## S02 handoff

S02 should implement a proof CLI that:

1. loads the benchmark fixture;
2. validates case shape and redaction constraints;
3. computes deterministic fixture-level metrics;
4. records `deepvk/USER-bge-m3` runtime availability or fixture-only/blocked diagnostics safely;
5. compares metrics against this threshold contract;
6. emits compact JSON summary counts and diagnostic inventory;
7. exits non-zero on stale fixtures, unsafe payloads, unexpected metrics, malformed cases, or overclaiming report language.

## Verification hook

T01 verification:

```bash
uv run pytest tests/test_local_retrieval_quality_benchmark_contract.py -q
```
