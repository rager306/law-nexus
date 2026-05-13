---
title: "Offline Citation Retrieval Contract"
status: "contract-draft"
owner: "M014/S01"
gate: "GATE-G008"
source_inputs:
  - "prd/retrieval/real_artifact_retrieval_proof.md"
  - "prd/retrieval/real_artifact_evidence_mapping.md"
  - "prd/parser/consultant_hierarchy_records.jsonl"
  - "prd/parser/parser_staging_graph.json"
non_authoritative: true
created_at: "2026-05-13"
---

# Offline Citation Retrieval Contract

This contract defines the M014 deterministic offline citation-safe retrieval proof. It advances `GATE-G008` by proving that tracked parser artifacts can produce structured retrieval candidate envelopes that compose with the validated M013/M012 output-ID validator path.

This is bounded proof scaffolding. It does not prove product retrieval quality, parser completeness, local embedding quality, legal-answer correctness, production FalkorDB runtime behavior, final graph schema readiness, or legal interpretation authority.

## Source artifacts

M014 may consume only tracked repository-relative artifacts:

- `prd/retrieval/real_artifact_evidence_mapping.md` — M013 mapping from tracked parser artifacts to validator-compatible evidence records.
- `prd/retrieval/fixtures/real_artifact_retrieval_cases.json` — M013 real-artifact validator graph/cases, used as the output-ID guardrail corpus.
- `prd/retrieval/real_artifact_retrieval_proof.md` — M013 bounded proof report and remaining-gate language.
- `scripts/retrieval_output_validator.py` — shared fail-closed output validator.
- `scripts/verify-real-artifact-retrieval-proof.py` — reusable proof CLI pattern.
- `prd/parser/consultant_hierarchy_records.json` — parser source provenance and hierarchy counts.
- `prd/parser/consultant_hierarchy_records.jsonl` — bounded parser hierarchy records with IDs, parent links, source hashes, selectors, and excerpt hashes.
- `prd/parser/parser_staging_graph.json` — bounded staging graph diagnostics and non-runtime graph shape.

The proof must not rescan untracked local directories, fetch external data, call an LLM, run embeddings, load FalkorDB, or cite `.gsd/exec` paths as architecture anchors.

## Query record shape

Each offline retrieval case must contain a structured query record:

| Field | Required | Rule |
| --- | --- | --- |
| `query_id` | yes | Stable proof-local ID such as `QUERY-M014-*`; not user prompt text. |
| `query_kind` | yes | One of `exact_id_lookup`, `marker_lookup`, `scoped_no_answer`, `ambiguous_lookup`, `invalid_candidate`. |
| `scope_id` | yes | Stable proof-local scope that will be copied into validator output scope. |
| `target_level` | conditional | Parser hierarchy level targeted by deterministic selection, such as `article` or `clause`. |
| `target_record_id` | conditional | Exact tracked parser record ID expected for deterministic lookup. |
| `expected_result` | yes | One of `selected`, `scoped_no_answer`, or `rejected`. |

The query record must not contain raw legal text, free-form legal questions, user prompts, generated answer prose, or legal advice.

## Candidate record shape

A selected candidate must be represented as a bounded proof object before it is converted to a validator envelope:

| Field | Required | Rule |
| --- | --- | --- |
| `candidate_id` | yes | Stable proof-local ID such as `CAND-M014-*`. |
| `query_id` | yes | Must match the query record. |
| `source_record_id` | yes | Tracked parser artifact record ID, such as `HIER-CONS-ARTICLE-0001`. |
| `source_path` | yes | Repository-relative parser source path. |
| `source_sha256` | yes | SHA-256 of the source artifact used by the parser record. |
| `excerpt_sha256` | yes | Hash of the source excerpt; raw excerpt text must not be persisted in proof output. |
| `selection_reason` | yes | One of the allowed deterministic reason codes. |
| `validator_output` | yes | Structured output envelope compatible with `scripts/retrieval_output_validator.py`. |

Candidate records are proof-local and non-authoritative. They are not product search results, legal citations, or final production graph records.

## Selection reason codes

Allowed `selection_reason` values are exactly:

- `exact_record_id_match` — query explicitly targets one parser hierarchy record ID and exactly one candidate is selected.
- `marker_level_match` — deterministic parser marker/level criteria select a bounded candidate.
- `scoped_no_candidate` — query produces no candidate within the proof corpus and must emit safe scoped no-answer.
- `ambiguous_candidate_set` — deterministic criteria identify more than one candidate and must fail closed.
- `unresolved_candidate_evidence` — candidate cannot be converted to a complete source/evidence/legal-unit/edition path and must fail closed.
- `unsafe_payload_rejected` — candidate or query carries forbidden payload fields and must fail closed.

No ranking score, embedding distance, LLM confidence, FalkorDB score, or legal relevance score is allowed in M014 candidate selection.

## Case classes

The seed corpus must include these case classes:

- `valid_exact_record_candidate` — exact parser record lookup yields one candidate and validator accepts the envelope.
- `valid_marker_level_candidate` — deterministic marker/level lookup yields one candidate and validator accepts the envelope.
- `scoped_no_candidate` — no matching candidate exists in the proof corpus and output is accepted only as explicit scoped no-answer.
- `ambiguous_candidate_set` — multiple candidate records satisfy selection criteria and the proof rejects the case without choosing arbitrarily.
- `unresolved_candidate_evidence` — selected candidate lacks a complete validator evidence path and fails closed.
- `unsafe_candidate_payload` — candidate/query includes forbidden payload classes and fails closed.

Additional case classes may be added only if they are deterministic, source-anchored, and redaction-safe.

## Validator envelope handoff

Selected candidates must be converted to validator-compatible output envelopes using the existing M013/M012 output-ID validator. The proof must reuse `scripts/retrieval_output_validator.py` rather than creating a parallel citation-safety validator.

For selected candidates, the envelope must include:

- `retrieval_output_id` with proof-local `RET-M014-*` or a documented adapter namespace if the validator is not extended yet;
- `scope` containing `scope_id`, `query_id`, `retrieval_run_id`, `as_of_date`, `source_corpus_id`, and `validator_contract_version`;
- `citations` with `citation_key`, `evidence_span_id`, `source_block_id`, `source_document_id`, `legal_unit_id`, `act_edition_id`, and matching `retrieval_output_id`;
- empty `answer_claims` unless a future milestone explicitly plans answer-claim proof.

M014 should prefer extending the shared validator to accept M014 proof-local prefixes only if needed and only while preserving `unknown_id_namespace` rejection.

## No-answer behavior

Scoped no-answer is safe only when all are true:

- selection produced no candidate within the explicit proof corpus;
- output kind is `scoped_no_answer`;
- `citations` is empty;
- `answer_claims` is absent or empty;
- diagnostics include a bounded `scoped_no_candidate` or validator `scoped_no_answer` signal;
- proof report states that this is not a global legal absence claim.

No-answer must not hide parser gaps, unresolved evidence, ambiguous candidate sets, or unsafe payloads.

## Diagnostic shape

Offline retrieval diagnostics must use compact safe fields:

| Field | Required | Purpose |
| --- | --- | --- |
| `code` | yes | Stable diagnostic/reason code. |
| `severity` | yes | `info`, `warning`, or `error`. |
| `case_id` | yes | Proof case ID. |
| `query_id` | yes | Query record ID. |
| `candidate_id` | conditional | Candidate ID when a candidate exists. |
| `source_record_id` | conditional | Tracked parser record ID when safe. |
| `field_path` | conditional | Field that caused rejection or mismatch. |
| `proof_artifact` | yes | Repository-relative proof artifact path. |

Diagnostics must not include raw legal text, source excerpts, prompts, provider payloads, secrets, vectors, raw FalkorDB rows, generated answer prose, or legal advice.

## Redaction and forbidden payloads

The proof must reject or avoid durable payloads containing:

- raw legal text or full source excerpts;
- user prompts or LLM/provider payloads;
- credentials, tokens, secrets, or PII;
- raw embedding arrays or vectors;
- raw FalkorDB rows or runtime response bodies;
- generated legal advice or authoritative answer prose;
- product-facing relevance/ranking claims.

## Non-claims

M014 offline retrieval proof does not prove product retrieval quality.
M014 offline retrieval proof does not prove parser completeness.
M014 offline retrieval proof does not prove legal-answer correctness.
M014 offline retrieval proof does not prove legal interpretation authority.
M014 offline retrieval proof does not prove production FalkorDB runtime behavior.
M014 offline retrieval proof does not prove production graph schema readiness.
M014 offline retrieval proof does not prove local embedding quality.
M014 offline retrieval proof does not close GATE-G008 unless final milestone validation explicitly confirms full gate criteria.
M014 offline retrieval proof does not close GATE-G011.
M014 offline retrieval proof does not make LLM output legal authority.
M014 offline retrieval proof does not make proof-local IDs production IDs.

## S02 handoff

S02 should consume this contract and the seed corpus to implement the executable proof. The proof command should:

1. load tracked offline retrieval cases;
2. select candidates deterministically using only allowed selection reason codes;
3. build validator-compatible output envelopes;
4. run the shared output validator;
5. compare expected selection and validator outcomes;
6. emit compact safe summary counts and diagnostic inventories;
7. exit non-zero on stale artifacts, unexpected outcomes, unsafe payloads, or malformed cases.

## Verification hook

T01 verification:

```bash
uv run pytest tests/test_offline_citation_retrieval_contract.py -q
```
