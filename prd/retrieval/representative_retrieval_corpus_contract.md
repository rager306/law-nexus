---
title: "Representative Retrieval Corpus Contract"
status: "contract-draft"
owner: "M016/S02"
gate: "GATE-G011"
contract_version: "representative-retrieval-corpus/v1"
proof_level: "static-manifest-contract"
non_authoritative: true
created_at: "2026-05-13"
---

# Representative Retrieval Corpus Contract

This contract defines the M016/S02 representative retrieval corpus manifest that S03 must consume for runtime benchmarking. It is a deterministic, repository-tracked, redacted corpus contract over bounded proof artifacts; it is not a production retrieval corpus, not a legal-answer corpus, and not evidence that `GATE-G011` is closed.

The manifest contract version is `representative-retrieval-corpus/v1`. Proof-local identifiers must use stable M016 namespaces, including `CORPUS-M016-*`, `QRL-M016-*`, `RC-M016-*`, and `COV-M016-*`. These IDs are proof-local labels and must not be promoted to production IDs.

## Source artifacts

The manifest builder may consume only tracked repository-relative source artifacts:

- `prd/retrieval/local_retrieval_quality_benchmark_contract.md` — M015 seed benchmark boundary, metric semantics, local/open-weight boundary, and open `GATE-G011` language.
- `prd/retrieval/retrieval_output_validator_contract.md` — M012 output ID envelope, citation/evidence validation boundary, and fail-closed diagnostics.
- `prd/retrieval/offline_citation_retrieval_contract.md` — M014 deterministic offline retrieval shape and citation-safe candidate/no-answer/ambiguous case classes.
- `prd/retrieval/real_artifact_evidence_mapping.md` — M013 tracked parser-artifact provenance, evidence-path mapping, and redaction rules.
- `prd/retrieval/fixtures/offline_citation_retrieval_cases.json` — tracked seed cases used only as bounded source case references, not raw legal text.
- `prd/retrieval/fixtures/real_artifact_retrieval_cases.json` — tracked source-backed validator cases used only as bounded provenance and ID-path references.
- `prd/parser/consultant_hierarchy_records.json` — Consultant source family summary and source SHA-256 provenance.
- `prd/parser/consultant_hierarchy_records.jsonl` — bounded hierarchy record IDs, parent links, selectors, and excerpt hashes.
- `prd/parser/parser_staging_graph.json` — bounded staging graph shape and diagnostic counts.
- `prd/parser/garant_44fz_metadata.json` — Garant ODT source-family metadata when present in the repository; if absent, T02 must emit a safe missing-source-family diagnostic rather than inventing Garant evidence.

The builder must not read `.gsd/`, `.planning/`, `.audits/`, untracked local corpora, absolute host paths, external URLs, managed provider dashboards, `.gsd/exec` outputs, or raw source documents. It must not fetch external data, call a managed GigaChat/GigaChat API, call a managed embedding API, call any managed LLM API, run FalkorDB, persist raw FalkorDB rows, or inspect untracked source directories.

## Manifest artifact and builder paths

T02 must create exactly these repository-relative paths:

| Purpose | Path |
| --- | --- |
| Manifest artifact | `prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json` |
| Human-readable proof report | `prd/retrieval/representative_retrieval_corpus_manifest.md` |
| Builder/check CLI | `scripts/build_representative_retrieval_corpus_manifest.py` |
| Contract/manifest tests | `tests/test_representative_retrieval_corpus_manifest.py` |

The builder check surface must support:

```bash
uv run python scripts/build_representative_retrieval_corpus_manifest.py --check
```

On success, `--check` must emit compact safe JSON containing manifest version, corpus ID, source artifact count, query-label count, candidate/reference count, coverage-class count, and diagnostic code inventory. On mismatch or unsafe input, it must exit non-zero and name only safe field paths and repository-relative artifact paths.

## Manifest schema

The manifest root object must contain these required fields:

| Field | Required | Rule |
| --- | --- | --- |
| `schema_version` | yes | Must be exactly `representative-retrieval-corpus/v1`. |
| `corpus_id` | yes | Stable proof-local ID such as `CORPUS-M016-REPRESENTATIVE-V1`. |
| `created_by` | yes | Static builder identifier, not a user name, host path, or secret. |
| `source_artifacts` | yes | Array of source artifact descriptors using repository-relative paths and SHA-256 values. |
| `coverage_classes` | yes | Array of coverage declarations using `COV-M016-*` IDs and closed class names. |
| `query_labels` | yes | Array of redacted query-label records using `QRL-M016-*` IDs. |
| `candidate_references` | yes | Array of redacted candidate/reference records using `RC-M016-*` IDs. |
| `s03_handoff` | yes | Runtime benchmark handoff metadata and non-claim flags. |
| `diagnostics` | yes | Compact safe diagnostics; empty only when all checks pass. |
| `non_claims` | yes | Explicit open-gate and legal-authority non-claims. |

The manifest must be deterministic: stable key order, stable sorted arrays by ID, stable hashes, and no timestamps except source artifact metadata already present in tracked inputs. The manifest must remain useful at 10x corpus size by storing hashes, IDs, selectors, counts, and labels rather than raw payloads.

## Coverage classes

The manifest must be more representative than M015 seed fixtures while remaining bounded to tracked artifacts. Required coverage classes are:

- `source_family_consultant_wordml` — Consultant WordML/XML-derived tracked parser artifacts are represented through IDs, hashes, selectors, and source-family labels only.
- `source_family_garant_odt_metadata` — Garant ODT metadata is represented only if tracked metadata exists; absent metadata must produce a safe diagnostic and must not be filled from raw ODT text.
- `legal_unit_path_coverage` — source document, source block, evidence span, legal unit, act edition, and legal act path IDs are covered where available.
- `positive_retrieval` — at least one query label expects one or more relevant candidate references.
- `distractor_retrieval` — at least one query label includes valid evidence that should not outrank relevant candidates.
- `scoped_no_answer` — at least one query label expects no candidate only within an explicit proof scope.
- `ambiguous_rejection` — at least one query label is intentionally ambiguous and must fail closed rather than choose arbitrarily.
- `unsafe_rejection` — at least one query label or candidate reference represents forbidden payload shape by safe labels only and must be rejected.
- `edition_path_mismatch` — at least one case exercises wrong-edition or mismatched path rejection using bounded IDs.
- `environment_runtime_handoff_boundary` — S03 receives enough local/open-weight runtime boundary metadata to benchmark without assuming managed APIs or production readiness.

Additional coverage classes may be added only when deterministic, source-anchored, redacted, and covered by tests. Coverage IDs must use `COV-M016-*`.

## Query-label shape

Each `query_labels` record must contain:

| Field | Required | Rule |
| --- | --- | --- |
| `query_label_id` | yes | Stable `QRL-M016-*` ID; never raw query text. |
| `coverage_class_ids` | yes | Non-empty array of `COV-M016-*` IDs. |
| `query_kind` | yes | One of `positive_retrieval`, `distractor_retrieval`, `scoped_no_answer`, `ambiguous_rejection`, `unsafe_rejection`, `edition_path_mismatch`, or `environment_runtime_handoff_boundary`. |
| `query_label_sha256` | yes | Hash of the bounded synthetic/query label; raw query labels and prompts must not be persisted. |
| `scope_id` | yes | Stable proof-local scope copied to S03 diagnostics. |
| `as_of_date` | conditional | Required when edition/path semantics are exercised. |
| `expected_relevant_reference_ids` | yes | Array of `RC-M016-*` IDs; empty only for no-answer, ambiguous, unsafe, or environment-boundary cases. |
| `expected_result` | yes | One of `metrics_candidate`, `scoped_no_answer`, `rejected`, or `environment_boundary`. |
| `source_case_ids` | yes | Prior proof case IDs or tracked source record IDs used as provenance. |
| `redaction` | yes | Object proving no raw text, raw prompt, raw vector, provider payload, or raw FalkorDB row is persisted. |

Query-label records must not include raw legal text, raw query text, user prompts, generated legal-answer prose, provider payloads, legal advice, raw vectors, or raw FalkorDB rows.

## Candidate/reference shape

Each `candidate_references` record must contain:

| Field | Required | Rule |
| --- | --- | --- |
| `reference_id` | yes | Stable `RC-M016-*` ID. |
| `source_family` | yes | One of `consultant_wordml`, `garant_odt_metadata`, or another tracked source-family value added by a future contract. |
| `source_artifact` | yes | Repository-relative tracked artifact path. |
| `source_sha256` | yes | SHA-256 of the tracked source artifact or source-family metadata. |
| `source_record_ids` | yes | Bounded source IDs such as parser hierarchy IDs, validator case IDs, or evidence path IDs. |
| `evidence_path_ids` | conditional | Source document, source block, evidence span, legal unit, act edition, and legal act IDs when available. |
| `excerpt_sha256` | conditional | Hash of source excerpt or bounded label when available; never the excerpt text. |
| `reference_role` | yes | One of `relevant`, `distractor`, `no_answer_boundary`, `ambiguous`, `unsafe`, `edition_mismatch`, or `environment_boundary`. |
| `provenance` | yes | Source contract/artifact IDs and derivation notes. |
| `redaction` | yes | Explicit no-raw-payload booleans. |

Candidate/reference records are proof-local and non-authoritative. They are not product search results, legal citations, final graph records, or evidence that parser coverage is complete.

## Provenance

Every manifest record must be traceable to tracked repository-relative artifacts through safe IDs, hashes, selectors, and case IDs. Provenance may include:

- source contract path;
- source fixture path;
- source parser artifact path;
- source artifact SHA-256;
- source case ID;
- parser hierarchy record ID;
- bounded selector metadata;
- evidence path IDs from the validator fixture graph.

Provenance must not include absolute paths, `.gsd/exec` paths, local machine usernames, raw ODT/XML/WordML text, raw legal excerpts, raw prompt text, provider request/response bodies, raw vectors, raw FalkorDB rows, or secrets.

## Redaction

Each query label and candidate reference must include explicit redaction booleans or an equivalent checked shape proving:

| Field | Required value |
| --- | --- |
| `raw_legal_text_persisted` | `false` |
| `raw_query_text_persisted` | `false` |
| `raw_prompt_persisted` | `false` |
| `raw_vector_persisted` | `false` |
| `provider_payload_persisted` | `false` |
| `raw_falkordb_row_persisted` | `false` |
| `generated_legal_advice_persisted` | `false` |
| `absolute_path_persisted` | `false` |

Durable artifacts may store hashes, stable IDs, bounded enums, repository-relative paths, counts, and diagnostic codes. They must not store raw legal text, source excerpts, raw query prompts, vectors, provider payloads, secrets, raw FalkorDB rows, generated legal advice, or authoritative answer prose.

## Forbidden payloads

The builder, manifest, proof report, diagnostics, and tests must reject or avoid:

- raw legal text or full source excerpts;
- raw query text, raw query prompts, or user prompts;
- managed GigaChat or GigaChat API request/response payloads;
- managed embedding API request/response payloads;
- credentials, tokens, secrets, PII, or local usernames;
- raw embedding arrays, vector arrays, vector dimensions as payload substitutes, or serialized vectors;
- raw FalkorDB rows, runtime response bodies, or query result dumps;
- generated legal advice, generated answer prose, or legal interpretation authority;
- absolute paths, `.gsd/exec` references, `.planning/` references, `.audits/` references, or untracked corpus references;
- product-facing retrieval quality claims;
- any statement that `GATE-G011` is closed by S02.

## Diagnostics

Diagnostics must be deterministic, categorical, compact, and safe. Required diagnostic fields are:

| Field | Required | Purpose |
| --- | --- | --- |
| `code` | yes | Stable diagnostic code. |
| `severity` | yes | `info`, `warning`, or `error`. |
| `field_path` | conditional | Safe JSON pointer or dotted path for malformed/unsafe fields. |
| `artifact_path` | yes | Repository-relative path such as the manifest or source artifact. |
| `corpus_id` | conditional | `CORPUS-M016-*` ID when available. |
| `query_label_id` | conditional | `QRL-M016-*` ID when available. |
| `reference_id` | conditional | `RC-M016-*` ID when available. |
| `coverage_class_id` | conditional | `COV-M016-*` ID when available. |
| `source_case_id` | conditional | Bounded prior proof case ID when available. |

Required diagnostic codes include `missing_source_artifact`, `manifest_schema_mismatch`, `unsafe_payload_field`, `coverage_class_missing`, `source_family_missing`, `query_label_mismatch`, `candidate_reference_mismatch`, `edition_path_mismatch`, `managed_api_forbidden`, `raw_vector_forbidden`, `raw_falkordb_row_forbidden`, and `gate_overclaim_forbidden`.

Diagnostics must not include raw legal text, raw query text, provider payloads, secrets, raw vectors, raw FalkorDB rows, generated answer prose, legal advice, stack traces containing such material, absolute paths, or `.gsd/exec` references.

## Explicit limits

This contract intentionally limits S02 to a representative redacted manifest, not a runtime benchmark. S02 does not compute retrieval quality metrics, does not run embeddings, does not call FalkorDB, does not evaluate legal-answer correctness, does not parse raw ODT/WordML documents, does not generate legal advice, and does not close any readiness gate.

Local/open-weight runtime benchmarking belongs to S03. Managed GigaChat, managed GigaChat API, managed embedding API fallback, and managed-provider payload persistence are excluded. If a runtime is unavailable, S03 must report a blocked/local-runtime boundary; it must not silently fall back to a managed API.

## S03 handoff

The manifest `s03_handoff` object must contain:

| Field | Required | Rule |
| --- | --- | --- |
| `manifest_path` | yes | `prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json`. |
| `builder_check_command` | yes | `uv run python scripts/build_representative_retrieval_corpus_manifest.py --check`. |
| `schema_version` | yes | `representative-retrieval-corpus/v1`. |
| `corpus_id` | yes | `CORPUS-M016-*`. |
| `allowed_runtime_model_boundary` | yes | Local/open-weight only; expected baseline may reference `deepvk/USER-bge-m3` when S03 has local evidence. |
| `managed_api_allowed` | yes | Must be `false`. |
| `managed_embedding_api_fallback_allowed` | yes | Must be `false`. |
| `raw_payload_persistence_allowed` | yes | Must be `false`. |
| `gate_g011_status` | yes | Must state `open`. |
| `quality_claim_scope` | yes | Must state manifest-readiness only, not product retrieval quality. |

S03 may consume the manifest to choose runtime benchmark labels and candidate references. S03 must not infer raw legal text, user prompts, vectors, provider payloads, raw FalkorDB rows, production retrieval quality, legal correctness, or closed gate status from the manifest.

## Non-claims

M016/S02 representative retrieval corpus contract does not prove product retrieval quality.
M016/S02 representative retrieval corpus contract does not prove parser completeness.
M016/S02 representative retrieval corpus contract does not prove legal-answer correctness.
M016/S02 representative retrieval corpus contract does not prove legal interpretation authority.
M016/S02 representative retrieval corpus contract does not prove production FalkorDB runtime behavior.
M016/S02 representative retrieval corpus contract does not prove production graph schema readiness.
M016/S02 representative retrieval corpus contract does not prove local embedding quality.
M016/S02 representative retrieval corpus contract does not compute runtime benchmark metrics.
M016/S02 representative retrieval corpus contract does not allow managed GigaChat API fallback.
M016/S02 representative retrieval corpus contract does not allow managed embedding API fallback.
M016/S02 representative retrieval corpus contract does not persist raw legal text, raw query prompts, vectors, provider payloads, raw FalkorDB rows, or generated legal advice.
M016/S02 representative retrieval corpus contract does not close GATE-G011; `GATE-G011` remains open until later validation explicitly confirms full gate criteria.
M016/S02 representative retrieval corpus contract does not close GATE-G008.
M016/S02 representative retrieval corpus contract does not make LLM output legal authority.
M016/S02 representative retrieval corpus contract does not make proof-local IDs production IDs.

## Verification hook

T01 verification:

```bash
uv run pytest tests/test_representative_retrieval_corpus_contract.py -q
```

T02 manifest verification must add the builder check:

```bash
uv run python scripts/build_representative_retrieval_corpus_manifest.py --check
```
