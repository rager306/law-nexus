---
title: "Local Retrieval Runtime Boundary Contract"
status: "contract-draft"
owner: "M016/S01"
gate: "GATE-G011"
proof_level: "runtime-boundary-contract"
non_authoritative: true
created_at: "2026-05-14"
---

# Local Retrieval Runtime Boundary Contract

This contract defines the M016 local/open-weight retrieval runtime boundary for the representative retrieval benchmark proof. It specifies the only approved runtime model, allowed execution mode, forbidden managed paths, safe JSON diagnostics, pass/fail-closed statuses, redaction constraints, and non-claims that downstream runtime smoke/check commands must preserve.

This contract is a boundary contract, not a runtime pass report. It does not close `GATE-G011`, does not prove production Russian legal retrieval quality, and does not authorize managed embedding API fallback.

## Source artifacts

M016 runtime-boundary work may cite these bounded source artifacts:

- `prd/retrieval/local_retrieval_quality_benchmark_contract.md` — M015 seed benchmark contract, metric boundary, redaction constraints, and fixture-vs-production non-claims.
- `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json` — prior local host runtime evidence for `deepvk/USER-bge-m3`, including observed vector dimension `1024` and the managed-API exclusion policy.
- `.gsd/milestones/M016/M016-CONTEXT.md` — milestone scope requiring local/open-weight runtime proof with compact fail-closed diagnostics and no external network/API dependency.

Downstream scripts must emit repository-relative artifact references only. Durable public proof artifacts must not include absolute local paths, provider payloads, raw legal text, raw vectors, secrets, or generated legal-answer prose.

## Approved runtime boundary

The only approved model for the M016 local retrieval runtime boundary is `deepvk/USER-bge-m3`.

Allowed execution is limited to local/open-weight inference in the current development environment or an equivalent explicitly local environment. The runtime may use locally installed packages and a local model cache when available. It must not require or silently invoke a managed embedding API, hosted LLM API, remote vector service, or external network fetch.

Expected runtime observations:

| Field | Required value |
| --- | --- |
| `model_id` | `deepvk/USER-bge-m3` |
| `execution_mode` | `local_open_weight` |
| `managed_api_used` | `false` |
| `giga_chat_used` | `false` |
| `raw_vectors_persisted` | `false` |
| `raw_legal_text_persisted` | `false` |
| `provider_payload_persisted` | `false` |
| `expected_vector_dimension` | `1024` |

`vector_dimension` may be reported only when observed from a real local runtime check. If the runtime is unavailable, the command must fail closed instead of inventing a dimension.

## Forbidden runtime paths

M016 runtime proof commands must not use, import as a required dependency, configure, or fall back to any managed provider path, including:

- GigaChat, GigaChat API, `GIGACHAT_AUTH_DATA`, or GigaChat credentials;
- GigaEmbeddings as a default, challenger, fallback, or replacement for the approved runtime;
- managed embedding APIs from any provider;
- remote hosted LLM APIs or remote embedding services;
- provider response bodies, provider trace IDs, or provider request payloads as durable artifacts;
- network downloads during the smoke/check command unless a later contract explicitly permits a controlled open-weight acquisition step.

If code detects a configured managed provider credential, it must still keep `managed_api_used` as `false` and must not call the provider. If local runtime dependencies are missing, the command must return a fail-closed diagnostic.

## Runtime status values

Runtime status values are closed and must be one of:

| Status | Exit behavior | Meaning |
| --- | --- | --- |
| `confirmed_runtime` | exit `0` | The approved local/open-weight model executed, produced embeddings, and reported safe diagnostics. |
| `blocked_environment` | non-zero | Required local packages, model cache, CPU/GPU/resource conditions, or runtime permissions are missing or unsafe. |
| `blocked_model_unavailable` | non-zero | The approved model is absent and the command is not allowed to fetch it. |
| `blocked_dimension_mismatch` | non-zero | A real observed vector dimension differs from the approved `1024` boundary. |
| `blocked_policy_violation` | non-zero | A managed API path, raw vector persistence, raw legal text persistence, provider payload, or overclaim was detected. |
| `blocked_unsafe_artifact` | non-zero | A generated artifact would contain forbidden payloads or unsafe references. |
| `not_run_contract_only` | non-zero | The command only validated the contract or environment preconditions and did not execute runtime inference. |

Success requires `confirmed_runtime`. Every other status is fail-closed and must be accompanied by at least one diagnostic code.

## Failure classes and diagnostic codes

Failure classes are closed and must be one of:

- `none` — no failure; valid only with `confirmed_runtime`.
- `environment` — local dependency, cache, hardware, resource, or permission blocker.
- `model_unavailable` — approved model unavailable under the no-network/no-managed-provider policy.
- `dimension_mismatch` — observed dimension differs from `1024`.
- `policy_violation` — forbidden managed path, fallback, raw persistence, or overclaim detected.
- `unsafe_artifact` — output would persist forbidden content or unsafe paths.
- `internal_error` — unexpected local exception after redaction.

Diagnostic codes must be stable, compact strings such as `LRR_MODEL_CACHE_MISSING`, `LRR_DEPENDENCY_MISSING`, `LRR_DIMENSION_MISMATCH`, `LRR_MANAGED_API_FORBIDDEN`, `LRR_RAW_VECTOR_FORBIDDEN`, `LRR_RAW_TEXT_FORBIDDEN`, `LRR_PROVIDER_PAYLOAD_FORBIDDEN`, `LRR_UNSAFE_PATH_FORBIDDEN`, and `LRR_INTERNAL_ERROR_REDACTED`.

## Safe JSON diagnostic schema

Runtime smoke/check commands must emit one compact JSON object to stdout or a tracked proof report. The object must use this shape:

| Field | Required | Rule |
| --- | --- | --- |
| `schema_version` | yes | Stable schema string such as `local-retrieval-runtime-boundary/v1`. |
| `model_id` | yes | Must be `deepvk/USER-bge-m3`. |
| `execution_mode` | yes | Must be `local_open_weight` when inference is attempted. |
| `runtime_status` | yes | One closed status from this contract. |
| `failure_class` | yes | One closed failure class from this contract. |
| `diagnostic_codes` | yes | Array of stable redacted diagnostic codes; empty only for `confirmed_runtime`. |
| `vector_dimension` | conditional | Integer `1024` only when observed from the approved local runtime. |
| `dependency_versions` | conditional | Safe package-name/version map for local packages only, with no paths or environment values. |
| `source_artifacts` | yes | Repository-relative source artifacts used for boundary decisions. |
| `redaction` | yes | Object with booleans proving forbidden payload classes were not emitted. |
| `managed_api_used` | yes | Must be `false`. |
| `giga_chat_used` | yes | Must be `false`. |
| `network_used` | yes | Must be `false` for the smoke/check command. |
| `non_claims` | yes | Array containing the non-claims required by this contract. |

The schema must not include raw query text, raw legal text, full excerpts, user prompts, secrets, credentials, absolute local paths, raw embedding arrays, provider request/response payloads, raw FalkorDB rows, or generated legal advice.

### Redaction object

The `redaction` object must include these boolean fields, all set to `true` on every emitted diagnostic object:

- `raw_legal_text_excluded`
- `raw_query_text_excluded`
- `raw_vectors_excluded`
- `provider_payloads_excluded`
- `secrets_excluded`
- `absolute_paths_excluded`
- `legal_advice_excluded`

## Pass and fail-closed semantics

A runtime proof command passes only when all of these are true:

1. `runtime_status` is `confirmed_runtime`.
2. `model_id` is `deepvk/USER-bge-m3`.
3. Local inference actually ran without managed API calls.
4. Observed `vector_dimension` is `1024`.
5. `managed_api_used`, `giga_chat_used`, `network_used`, `raw_vectors_persisted`, and `raw_legal_text_persisted` are all `false`.
6. Redaction booleans are all `true`.
7. The emitted non-claims include product-quality, legal-authority, parser-completeness, and gate-closure limits.

The command must fail closed with a non-zero exit when any required observation is missing, when local runtime execution cannot be proven, when a forbidden runtime path is reachable as fallback, or when any output would persist unsafe payloads.

## Safe artifact references

Safe artifacts may reference only repository-relative paths and stable proof IDs. `.gsd` source evidence may be cited as source provenance, but runtime smoke/check tests must not require ignored `.gsd` files as fixtures. Public proof outputs under `prd/retrieval/` should summarize `.gsd` evidence without copying raw logs or absolute log paths.

Forbidden durable references include:

- absolute paths such as home-directory or temporary execution paths;
- `.gsd/exec` paths;
- raw runtime log bodies;
- provider request IDs, response IDs, payload bodies, or authorization metadata;
- full source excerpts or generated legal answer text;
- raw vectors, vector arrays, or database rows.

## Non-claims

M016 local retrieval runtime boundary does not prove product retrieval quality.
M016 local retrieval runtime boundary does not prove representative corpus quality.
M016 local retrieval runtime boundary does not prove parser completeness.
M016 local retrieval runtime boundary does not prove legal-answer correctness.
M016 local retrieval runtime boundary does not prove legal interpretation authority.
M016 local retrieval runtime boundary does not prove production FalkorDB runtime behavior.
M016 local retrieval runtime boundary does not close GATE-G011 by itself.
M016 local retrieval runtime boundary does not authorize managed embedding API fallback.
M016 local retrieval runtime boundary does not authorize GigaChat or GigaEmbeddings runtime use.
M016 local retrieval runtime boundary does not persist raw legal text, raw query text, raw vectors, provider payloads, secrets, or legal advice.
M016 local retrieval runtime boundary does not make LLM output legal authority.

## Downstream implementation checklist

A downstream runtime smoke/check command must:

1. load this contract and the approved model boundary;
2. verify no managed API or GigaChat fallback is configured as an execution path;
3. probe local dependency versions without exposing paths or environment values;
4. execute `deepvk/USER-bge-m3` locally only when the model and dependencies are available safely;
5. observe and validate vector dimension `1024` when inference runs;
6. emit the safe JSON diagnostic schema;
7. exit `0` only for `confirmed_runtime` and non-zero for every fail-closed status;
8. avoid persisting raw text, vectors, provider payloads, secrets, or generated legal advice;
9. preserve the non-claims and keep `GATE-G011` open unless later milestone validation explicitly closes it.

## Verification hook

T01 verification:

```bash
uv run pytest tests/test_local_retrieval_runtime_boundary_contract.py -q
```
