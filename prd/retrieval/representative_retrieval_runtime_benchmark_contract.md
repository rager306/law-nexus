---
title: "Representative Retrieval Runtime Benchmark Contract"
status: "contract-draft"
owner: "M016/S03"
gate: "GATE-G011"
contract_version: "representative-retrieval-runtime-benchmark-proof/v1"
proof_level: "runtime-benchmark-contract"
non_authoritative: true
created_at: "2026-05-14"
---

# Representative Retrieval Runtime Benchmark Contract

This contract defines the M016/S03 representative retrieval runtime benchmark proof. The proof consumes the S01 local/open-weight runtime boundary and the S02 redacted representative corpus manifest, then emits one safe deterministic JSON inspection object and a durable proof report. It is a runtime-gated representative benchmark proof, not a product retrieval-quality claim, not a legal-answer correctness claim, and not evidence that `GATE-G011` is closed.

The benchmark proof schema version is `representative-retrieval-runtime-benchmark-proof/v1`. All benchmark inputs, observations, metrics, diagnostics, and report text must remain redacted and proof-local.

## Source artifacts and default inputs

The executable proof CLI is `scripts/verify-representative-retrieval-runtime-benchmark.py`:

```bash
uv run python scripts/verify-representative-retrieval-runtime-benchmark.py
```

Default checked-in inputs are repository-relative paths:

| Purpose | Path | Producer |
| --- | --- | --- |
| S01 runtime boundary contract | `prd/retrieval/local_retrieval_runtime_boundary_contract.md` | M016/S01 |
| S01 runtime boundary proof | `prd/retrieval/local_retrieval_runtime_boundary_proof.md` | M016/S01 |
| S01 runtime diagnostic CLI | `scripts/check-local-retrieval-runtime.py` | M016/S01 |
| S02 corpus contract | `prd/retrieval/representative_retrieval_corpus_contract.md` | M016/S02 |
| S02 representative manifest | `prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json` | M016/S02 |
| S02 representative manifest report | `prd/retrieval/representative_retrieval_corpus_manifest.md` | M016/S02 |
| S03 durable proof report | `prd/retrieval/representative_retrieval_runtime_benchmark_proof.md` | M016/S03 |

The proof CLI must consume S01 runtime diagnostics by invoking or validating the local runtime boundary surface from `scripts/check-local-retrieval-runtime.py`, and must consume S02 manifest data from `prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json`. It must not read ignored `.gsd/`, `.planning/`, `.audits/`, `.gsd/exec`, untracked local corpora, external URLs, managed-provider dashboards, raw source documents, or absolute host paths.

## Executable proof behavior

The proof path is deterministic and fail-closed:

1. Load this contract and validate the requested schema version `representative-retrieval-runtime-benchmark-proof/v1`.
2. Run or validate the S01 local/open-weight runtime diagnostic boundary for `deepvk/USER-bge-m3` with `execution_mode` `local_open_weight`.
3. Load the S02 redacted representative manifest and validate `schema_version` `representative-retrieval-corpus/v1`.
4. Reject malformed, missing, unsafe, non-redacted, or managed-provider inputs before computing metrics.
5. Compute proof-local metrics in memory using only manifest IDs, bounded enums, hashes, safe counts, and deterministic ranking assertions.
6. Emit exactly one compact JSON object to stdout using the schema below.
7. Write or update the durable proof report `prd/retrieval/representative_retrieval_runtime_benchmark_proof.md` with the same safe metric and diagnostic summary.

Per run, the load profile is one local runtime diagnostic invocation plus one manifest JSON read and in-memory metric calculation. The first local model load may take about 30 seconds. Ten parallel runs would be constrained by local model memory and model loading, not by network calls or managed API quotas.

## Status values and failure classes

`benchmark_status` is closed and must be one of:

| Status | Exit behavior | Meaning |
| --- | --- | --- |
| `metrics_confirmed` | exit `0` | S01 runtime boundary is confirmed, S02 manifest is valid and redacted, all required checked-in proof metrics meet threshold `1.0`, and no unsafe artifact is emitted. |
| `blocked_runtime` | non-zero | S01 runtime diagnostics are missing, malformed, timed out, unavailable, non-local, not `confirmed_runtime`, dimension-mismatched, or otherwise unsafe. |
| `blocked_manifest` | non-zero | S02 manifest is missing, malformed, schema-mismatched, non-deterministic, or does not contain required query/candidate IDs. |
| `blocked_metric` | non-zero | Required metric calculation cannot be completed or one or more checked-in proof thresholds are below `1.0`. |
| `blocked_policy_violation` | non-zero | Managed API fallback, GigaChat/GigaEmbeddings use, raw payload persistence, external network use, unsafe paths, or gate overclaim is detected. |
| `blocked_unsafe_artifact` | non-zero | Stdout JSON or durable proof report would contain forbidden payloads, absolute paths, raw rows, secrets, vectors, or generated legal advice. |
| `not_run_contract_only` | non-zero | The command only inspected contract preconditions and did not run the runtime-gated benchmark proof. |

`failure_class` is closed and must be one of:

- `none` — valid only with `metrics_confirmed`.
- `runtime_boundary` — S01 diagnostic input is missing, malformed, timed out, unavailable, not local/open-weight, or not confirmed.
- `manifest_input` — S02 manifest input is missing, malformed, unsafe, schema-mismatched, or incomplete.
- `metric_threshold` — metric computation failed or a required threshold was not met.
- `policy_violation` — managed API fallback, GigaChat/GigaEmbeddings use, network use, raw payload persistence, unsafe source, or gate overclaim was detected.
- `unsafe_artifact` — emitted JSON or durable report would persist forbidden content.
- `internal_error` — unexpected local exception after redaction.

Required diagnostic codes include `RRB_RUNTIME_DIAGNOSTIC_MISSING`, `RRB_RUNTIME_DIAGNOSTIC_MALFORMED`, `RRB_RUNTIME_TIMEOUT`, `RRB_RUNTIME_NOT_CONFIRMED`, `RRB_MANIFEST_MISSING`, `RRB_MANIFEST_MALFORMED`, `RRB_MANIFEST_SCHEMA_MISMATCH`, `RRB_MANIFEST_UNSAFE_PAYLOAD`, `RRB_METRIC_THRESHOLD_MISSED`, `RRB_MANAGED_API_FORBIDDEN`, `RRB_GIGACHAT_FORBIDDEN`, `RRB_RAW_TEXT_FORBIDDEN`, `RRB_RAW_QUERY_FORBIDDEN`, `RRB_RAW_VECTOR_FORBIDDEN`, `RRB_PROVIDER_PAYLOAD_FORBIDDEN`, `RRB_RAW_FALKORDB_ROW_FORBIDDEN`, `RRB_UNSAFE_PATH_FORBIDDEN`, `RRB_GATE_OVERCLAIM_FORBIDDEN`, and `RRB_INTERNAL_ERROR_REDACTED`.

Malformed or missing S01 or S02 inputs must be classified as blocker/unsafe rather than successful metrics. Runtime timeout must be `blocked_runtime` with `failure_class` `runtime_boundary` and diagnostic code `RRB_RUNTIME_TIMEOUT`. Malformed diagnostic JSON must be `blocked_runtime` with diagnostic code `RRB_RUNTIME_DIAGNOSTIC_MALFORMED`.

## Stdout JSON schema

The proof CLI must emit exactly one compact JSON object to stdout. The root object must contain these fields:

| Field | Required | Rule |
| --- | --- | --- |
| `schema_version` | yes | Must be exactly `representative-retrieval-runtime-benchmark-proof/v1`. |
| `benchmark_id` | yes | Stable proof-local ID such as `RRB-M016-REPRESENTATIVE-V1`. |
| `benchmark_status` | yes | One closed status from this contract. |
| `failure_class` | yes | One closed failure class from this contract. |
| `diagnostic_codes` | yes | Stable redacted code array; empty only for `metrics_confirmed`. |
| `runtime_boundary_confirmed` | yes | Boolean metric; `true` only when S01 confirms `deepvk/USER-bge-m3`, `local_open_weight`, no managed API, no GigaChat, no network, and safe redaction. |
| `runtime_diagnostic` | yes | Safe summary only: schema, status, model ID, execution mode, vector dimension, booleans, diagnostic codes, and source artifact paths; no raw runtime rows or logs. |
| `manifest` | yes | Safe summary only: manifest schema, corpus ID, query-label count, candidate-reference count, coverage-class count, and source artifact paths. |
| `metrics` | yes | Object containing only the predeclared metric names and numeric/boolean values. |
| `thresholds` | yes | Object containing only the predeclared metric names and required threshold values. |
| `metric_inputs` | yes | Safe proof-local ID inventory using `QRL-M016-*`, `RC-M016-*`, and `COV-M016-*`; no query text or legal text. |
| `source_artifacts` | yes | Repository-relative artifacts used by S03. |
| `redaction` | yes | Redaction booleans listed below. |
| `managed_api_used` | yes | Must be `false`. |
| `giga_chat_used` | yes | Must be `false`. |
| `network_used` | yes | Must be `false` for the checked-in proof path. |
| `non_claims` | yes | Array containing the required non-claims from this contract. |
| `gate` | yes | Must be `GATE-G011` and must state that the gate remains open. |

The stdout schema must not contain raw query text, raw legal text, full source excerpts, user prompts, generated legal-answer prose, legal advice, provider payloads, provider trace IDs, credentials, secrets, environment variable values, absolute local paths, raw embedding arrays, vectors, raw FalkorDB rows, managed-API evidence, or stack traces containing any forbidden payload.

## Metrics and thresholds

The checked-in proof path must predeclare exactly these metrics and thresholds:

| Metric | Type | Required threshold | Definition |
| --- | --- | --- | --- |
| `mrr` | number | `1.0` | Mean reciprocal rank over positive proof-local query labels; each expected relevant `RC-M016-*` reference from `query_labels.expected_relevant_reference_ids` must be ranked before distractors for its case. |
| `recall_at_1` | number | `1.0` | Every positive proof-local query label must have an expected relevant `RC-M016-*` reference at rank 1. |
| `recall_at_3` | number | `1.0` | Every positive proof-local query label must have all required relevant `RC-M016-*` references within rank 3 when enough candidates exist. |
| `no_answer_accuracy` | number | `1.0` | Every `scoped_no_answer` query label must avoid selecting a candidate reference as an answer. |
| `ambiguous_rejection_rate` | number | `1.0` | Every `ambiguous_rejection` query label must be rejected rather than ranked as a successful answer. |
| `unsafe_rejection_rate` | number | `1.0` | Every `unsafe_rejection` query label or `candidate_references.reference_role` `unsafe` case must be rejected. |
| `edition_path_mismatch_rejection_rate` | number | `1.0` | Every `edition_path_mismatch` query label or `candidate_references.reference_role` `edition_mismatch` case must be rejected. |
| `runtime_boundary_confirmed` | boolean | `1.0` | S01 local/open-weight runtime diagnostic must be confirmed and safe; boolean `true` is equivalent to threshold `1.0`. |

Positive retrieval and distractor metrics are deterministic proof-local relevance/ranking assertions over `query_labels.expected_relevant_reference_ids` and `candidate_references.reference_role`. They are not product retrieval quality, not production ranker evaluation, not parser completeness evidence, and not legal correctness. The proof may use a deterministic manifest-local ranking fixture or implementation-specific local ranking output only if the emitted metric inputs remain IDs and roles only.

No additional metric may be emitted in the checked-in proof path unless a later contract updates this metric table and its tests.

## Metric input boundaries

Metric computation may read these S2 manifest fields only:

- `schema_version`, `corpus_id`, `source_artifacts`, `coverage_classes`, `query_labels`, `candidate_references`, `s03_handoff`, `diagnostics`, `non_claims`, and redaction/limit flags;
- `query_labels.query_label_id`, `coverage_class_ids`, `query_kind`, `scope_id`, `as_of_date`, `expected_relevant_reference_ids`, `expected_result`, `source_case_ids`, and redaction flags;
- `candidate_references.reference_id`, `candidate_references.reference_role`, `source_family`, `source_artifact`, `source_record_ids`, `evidence_path_ids`, `reference_role`, `provenance`, hashes, and redaction flags.

Metric computation must not read or persist raw query text, raw legal text, user prompts, raw prompts, source excerpts, provider payloads, provider trace IDs, credentials, raw vectors, raw FalkorDB rows, generated legal-answer prose, generated answers, legal advice, untracked files, or absolute paths. Metric output must use manifest IDs only: `QRL-M016-*`, `RC-M016-*`, and `COV-M016-*`.

## Redaction and forbidden payload fields

The `redaction` object must include these boolean fields and safe values on every stdout JSON object and durable proof report summary:

| Field | Required value |
| --- | --- |
| `raw_legal_text_persisted` | `false` |
| `raw_query_text_persisted` | `false` |
| `raw_prompt_persisted` | `false` |
| `raw_vector_persisted` | `false` |
| `provider_payload_persisted` | `false` |
| `raw_falkordb_row_persisted` | `false` |
| `managed_api_evidence_persisted` | `false` |
| `generated_legal_advice_persisted` | `false` |
| `absolute_path_persisted` | `false` |
| `secrets_persisted` | `false` |

Forbidden field names in emitted JSON, durable proof report structured blocks, fixtures, or tests include `raw_legal_text`, `legal_text`, `source_excerpt`, `query_text`, `raw_query_text`, `prompt`, `user_prompt`, `vector`, `vectors`, `embedding`, `embedding_vector`, `provider_payload`, `provider_response_body`, `managed_api_payload`, `raw_falkordb_row`, `falkordb_row`, `secret`, `token`, `password`, `generated_answer`, and `legal_advice`.

Durable artifacts may store IDs, hashes, bounded enums, booleans, counts, repository-relative paths, metric names, threshold values, and diagnostic codes. They must not store raw payloads, managed-API evidence, raw FalkorDB rows, vectors, secrets, generated answer prose, or legal advice.

## Managed provider and network policy

The proof CLI must not use, call, import as a required execution path, configure, or fall back to any managed provider path. GigaChat, GigaChat API, GigaEmbeddings, `GIGACHAT_AUTH_DATA`, managed embedding APIs, hosted LLM APIs, remote vector stores, provider dashboards, and provider request/response artifacts are forbidden.

If managed-provider credentials are present in the environment, the proof must still keep `managed_api_used` as `false`, `giga_chat_used` as `false`, and `network_used` as `false`; it must not call the provider. If the local runtime is unavailable, the proof must emit a fail-closed runtime blocker instead of falling back to a managed API.

## Durable proof report

The durable proof report `prd/retrieval/representative_retrieval_runtime_benchmark_proof.md` must summarize:

- schema version `representative-retrieval-runtime-benchmark-proof/v1`;
- benchmark status and failure class;
- S01 runtime boundary source paths and safe status summary;
- S02 manifest source path, corpus ID, safe counts, and redaction boundary;
- the exact predeclared metric/threshold table;
- diagnostic codes and failure class when blocked;
- redaction booleans and forbidden payload exclusions;
- explicit non-claims and open `GATE-G011` language.

The report must not copy raw runtime logs, raw legal text, raw query text, vectors, provider payloads, raw FalkorDB rows, secrets, generated answer prose, managed-API evidence, absolute paths, `.gsd/exec` paths, or stack traces containing forbidden material.

## Non-claims

M016/S03 representative retrieval runtime benchmark proof does not prove product retrieval quality.
M016/S03 representative retrieval runtime benchmark proof does not prove production ranker quality.
M016/S03 representative retrieval runtime benchmark proof does not prove parser completeness.
M016/S03 representative retrieval runtime benchmark proof does not prove legal-answer correctness.
M016/S03 representative retrieval runtime benchmark proof does not prove legal interpretation authority.
M016/S03 representative retrieval runtime benchmark proof does not prove production FalkorDB runtime behavior.
M016/S03 representative retrieval runtime benchmark proof does not prove production graph schema readiness.
M016/S03 representative retrieval runtime benchmark proof does not make proof-local IDs production IDs.
M016/S03 representative retrieval runtime benchmark proof does not authorize managed embedding API fallback.
M016/S03 representative retrieval runtime benchmark proof does not authorize GigaChat or GigaEmbeddings runtime use.
M016/S03 representative retrieval runtime benchmark proof does not persist raw legal text, raw query text, raw prompts, vectors, provider payloads, managed-API evidence, raw FalkorDB rows, secrets, or generated legal advice.
M016/S03 representative retrieval runtime benchmark proof does not make LLM output legal authority.
M016/S03 representative retrieval runtime benchmark proof does not close `GATE-G011`; `GATE-G011` remains open until a later milestone validation explicitly closes it.

## Implementation checklist

A downstream implementation of `scripts/verify-representative-retrieval-runtime-benchmark.py` must:

1. validate this contract schema version;
2. invoke or validate `scripts/check-local-retrieval-runtime.py` and require confirmed local/open-weight S01 diagnostics;
3. reject missing, malformed, timed-out, non-local, managed-provider, or unsafe S01 runtime diagnostics as `blocked_runtime`;
4. load `prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json` and require S02 schema `representative-retrieval-corpus/v1`;
5. reject missing, malformed, unsafe, unredacted, or incomplete manifest fields as `blocked_manifest`;
6. compute only the predeclared metrics using manifest IDs and `candidate_references.reference_role`;
7. require every checked-in metric threshold to be `1.0`;
8. emit exactly one safe JSON object to stdout;
9. write the safe durable proof report;
10. exit `0` only for `metrics_confirmed`; every other status must exit non-zero;
11. keep `managed_api_used`, `giga_chat_used`, and `network_used` false;
12. preserve all non-claims and keep `GATE-G011` open.

## Verification hook

T01 verification:

```bash
uv run pytest tests/test_representative_retrieval_runtime_benchmark_contract.py
```
