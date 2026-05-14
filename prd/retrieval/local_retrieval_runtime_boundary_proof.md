---
title: "Local Retrieval Runtime Boundary Proof"
status: "runtime-observed"
owner: "M016/S01"
gate: "GATE-G011"
proof_level: "runtime-boundary-proof"
non_authoritative: true
created_at: "2026-05-14"
---

# Local Retrieval Runtime Boundary Proof

This report records the current M016/S01 local/open-weight retrieval runtime boundary observation for `deepvk/USER-bge-m3`. It is a runtime boundary proof only: it proves whether the approved local runtime can execute safely in this environment and whether the smoke/check command emits fail-closed redacted diagnostics.

This report does not close `GATE-G011` and does not replace later representative retrieval benchmark, corpus, parser, legal-answer, or production FalkorDB validation.

## Source artifacts

- `scripts/check-local-retrieval-runtime.py` — runtime smoke/check command that emits compact JSON diagnostics and fails closed unless the approved local runtime is confirmed.
- `tests/test_local_retrieval_runtime_check_cli.py` — CLI behavior tests for confirmed, unavailable, policy-violation, dimension-mismatch, and unsafe-output cases.
- `prd/retrieval/local_retrieval_runtime_boundary_contract.md` — approved boundary contract for model, execution mode, safe diagnostics, redaction, and non-claims.
- `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json` — bounded prior source evidence for the approved model and `1024` observed dimension, cited only as repository-relative provenance.

## Runtime check command

Current smoke/check command:

```bash
uv run python scripts/check-local-retrieval-runtime.py --allow-unavailable
```

`--allow-unavailable` is used for automation friendliness only. It relaxes the process exit code for fail-closed unavailable-runtime diagnostics; it does not convert fail-closed runtime statuses into success statuses. The runtime status remains authoritative.

## Current observed output

The current observed output is one compact JSON object on stdout:

```json
{"dependency_versions":{"sentence-transformers":"5.4.1","torch":"2.11.0","transformers":"4.51.0"},"diagnostic_codes":[],"execution_mode":"local_open_weight","expected_vector_dimension":1024,"failure_class":"none","giga_chat_used":false,"managed_api_used":false,"model_id":"deepvk/USER-bge-m3","network_used":false,"non_claims":["does_not_prove_product_retrieval_quality","does_not_prove_representative_corpus_quality","does_not_prove_parser_completeness","does_not_prove_legal_answer_correctness","does_not_prove_legal_interpretation_authority","does_not_prove_production_falkordb_runtime_behavior","does_not_close_GATE_G011","does_not_authorize_managed_embedding_api_fallback","does_not_authorize_gigachat_or_gigaembeddings_runtime_use"],"provider_payload_persisted":false,"raw_legal_text_persisted":false,"raw_vectors_persisted":false,"redaction":{"absolute_paths_excluded":true,"legal_advice_excluded":true,"provider_payloads_excluded":true,"raw_legal_text_excluded":true,"raw_query_text_excluded":true,"raw_vectors_excluded":true,"secrets_excluded":true},"runtime_status":"confirmed_runtime","schema_version":"local-retrieval-runtime-boundary/v1","source_artifacts":["prd/retrieval/local_retrieval_runtime_boundary_contract.md",".gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json","pyproject.toml"],"vector_dimension":1024}
```

Observed status summary:

| Field | Current observed value |
| --- | --- |
| `schema_version` | `local-retrieval-runtime-boundary/v1` |
| `model_id` | `deepvk/USER-bge-m3` |
| `execution_mode` | `local_open_weight` |
| `runtime_status` | `confirmed_runtime` |
| `failure_class` | `none` |
| `vector_dimension` | `1024` |
| `managed_api_used` | `false` |
| `giga_chat_used` | `false` |
| `network_used` | `false` |
| `raw_vectors_persisted` | `false` |
| `raw_legal_text_persisted` | `false` |
| `provider_payload_persisted` | `false` |

## Safe diagnostic inventory

The runtime command emits closed, redacted diagnostics. The current observation has no diagnostic codes because the runtime was confirmed. Fail-closed diagnostics remain part of the supported inventory for unavailable or unsafe runtime cases:

| Diagnostic code | Failure class | Meaning |
| --- | --- | --- |
| `LRR_DEPENDENCY_MISSING` | `environment` | Required local package is unavailable. |
| `LRR_S10_METADATA_MALFORMED` | `environment` | Bounded prior model metadata is missing or malformed. |
| `LRR_MODEL_CACHE_MISSING` | `model_unavailable` | Approved local model cache is absent and the command must not fetch it. |
| `LRR_LOCAL_INFERENCE_FAILED_REDACTED` | `environment` | Local inference failed after redacting implementation details. |
| `LRR_DIMENSION_MISMATCH` | `dimension_mismatch` | Real observed dimension differs from the approved `1024` boundary. |
| `LRR_MANAGED_API_FORBIDDEN` | `policy_violation` | Managed API configuration was detected and not used. |
| `LRR_NOT_RUN_CONTRACT_ONLY` | `environment` | Preconditions were checked without runtime inference. |
| `LRR_INTERNAL_ERROR_REDACTED` | `unsafe_artifact` | Unexpected local exception was reduced to safe output. |

Safe dependency inventory observed in this environment:

| Package | Observed version |
| --- | --- |
| `sentence-transformers` | `5.4.1` |
| `torch` | `2.11.0` |
| `transformers` | `4.51.0` |

These package names and versions are safe to report because they contain no paths, credentials, provider payloads, raw legal text, raw vectors, or environment values.

## Model boundary

The approved runtime model boundary is exactly `deepvk/USER-bge-m3` with `execution_mode` set to `local_open_weight` and expected vector dimension `1024`.

The smoke/check command must not silently substitute GigaChat, GigaEmbeddings, any managed embedding API, a remote hosted LLM, a remote vector service, or a network download. If the approved model is unavailable locally, the command must emit a fail-closed status such as `blocked_model_unavailable` instead of using a fallback.

## Redaction boundary

The report and command output exclude unsafe payload classes:

| Redaction flag | Current value |
| --- | --- |
| `raw_legal_text_excluded` | `true` |
| `raw_query_text_excluded` | `true` |
| `raw_vectors_excluded` | `true` |
| `provider_payloads_excluded` | `true` |
| `secrets_excluded` | `true` |
| `absolute_paths_excluded` | `true` |
| `legal_advice_excluded` | `true` |

Durable artifacts must not persist raw legal source text, raw query text, embedding arrays, provider request or response payloads, secrets, absolute local paths, raw FalkorDB rows, or generated legal-answer prose.

## Non-claims and open boundaries

Runtime availability alone does not prove product retrieval quality.
Runtime availability alone does not prove representative corpus quality.
Runtime availability alone does not prove parser completeness.
Runtime availability alone does not prove legal-answer correctness.
Runtime availability alone does not prove legal interpretation authority.
Runtime availability alone does not prove production FalkorDB runtime behavior.
Runtime availability alone does not close `GATE-G011`.
Runtime availability alone does not authorize managed embedding API fallback.
Runtime availability alone does not authorize GigaChat or GigaEmbeddings runtime use.
Runtime availability alone does not make LLM output legal authority.

## Handoff contract for S03

S03 may use this report as evidence that the approved local/open-weight runtime boundary can currently execute in this environment and can emit safe compact diagnostics. S03 must still treat product retrieval quality as unproven until representative benchmark execution validates query fixtures, corpus coverage, parser completeness, retrieval metrics, and answer-boundary behavior.

S03 must preserve these handoff rules:

1. Use `deepvk/USER-bge-m3` locally only; do not add managed provider fallback.
2. Treat `runtime_status` as authoritative even when `--allow-unavailable` returns process exit `0` for automation.
3. Keep raw legal text, raw query text, vectors, provider payloads, secrets, absolute paths, and generated legal advice out of durable artifacts.
4. Report `vector_dimension` only when observed from real local inference.
5. Keep `GATE-G011` open unless a later milestone validation explicitly closes it with representative retrieval evidence.
6. Do not infer production FalkorDB behavior from this local runtime smoke/check.

## Verification hook

Report verification:

```bash
uv run pytest tests/test_local_retrieval_runtime_boundary_contract.py tests/test_local_retrieval_runtime_check_cli.py tests/test_local_retrieval_runtime_boundary_report.py -q
uv run python scripts/check-local-retrieval-runtime.py --allow-unavailable
```
