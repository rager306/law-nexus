---
title: "Retrieval Output Validator Fixture Taxonomy"
status: "fixture-taxonomy-draft"
owner: "M012/S01"
contract: "prd/retrieval/retrieval_output_validator_contract.md"
source_inputs:
  - "prd/retrieval/retrieval_output_validator_contract.md"
  - "prd/architecture/architecture_items.jsonl#DATA-LEGAL-EVIDENCE-CORE"
non_authoritative: true
created_at: "2026-05-13"
---

# Retrieval Output Validator Fixture Taxonomy

This document defines the bounded fixture taxonomy that S02 can turn into tracked JSON fixtures for the retrieval output validator proof. The fixtures are proof scaffolding only: they do not represent product parser output, production FalkorDB rows, retrieval quality, legal correctness, or final graph schema completeness.

## Boundary and Non-Claims

The fixture set is designed to prove deterministic acceptance/rejection of retrieval output identifiers against a tiny static graph. It is intentionally smaller than the product legal graph and contains no raw legal text, prompts, provider payloads, raw vectors, raw FalkorDB rows, or legal advice.

The fixtures only claim that:

1. Required output IDs can be checked against known static records.
2. Source and legal-unit traversal failures can be reported with stable diagnostic codes.
3. Scoped no-answer output can be accepted only as an explicitly scoped empty state.

The fixtures do not claim:

- parser completeness;
- product citation-safe retrieval readiness;
- product retrieval quality;
- legal-answer correctness;
- final production ID format;
- final production temporal model;
- FalkorDB runtime, vector, full-text, or rerank behavior;
- real 44-FZ source evidence quality.

## Target Fixture Format and Path

S02 should use JSON because the validator proof needs deterministic object fields, exact IDs, and simple test assertions. Unless implementation discovers a stronger existing convention, use this tracked path:

```text
prd/retrieval/fixtures/retrieval_output_validator_cases.json
```

The JSON file should contain three top-level sections:

| Section | Purpose |
| --- | --- |
| `fixture_graph` | Minimal static graph records and citation indexes. |
| `cases` | Valid and invalid output envelopes to validate. |
| `expected_diagnostics` | Expected result state and safe diagnostic payload assertions by case ID. |

S02 tests may inline these records if a smaller unit-test convention is preferable, but the source fixture definition must remain in a git-tracked path outside `.gsd/`.

## Minimal Fixture Graph Record Set

The minimal graph represents one legal act with two editions, two source documents, three source blocks, and several evidence spans. IDs use M012 proof-local prefixes only.

### LegalAct Records

| ID | Required fields | Notes |
| --- | --- | --- |
| `LA-M012-44FZ` | `legal_act_id`, `act_key`, `fixture_label` | Synthetic act anchor for path traversal only. |

### ActEdition Records

| ID | Required fields | Notes |
| --- | --- | --- |
| `ED-M012-44FZ-2024-01-01` | `act_edition_id`, `legal_act_id`, `valid_from`, `valid_to`, `status` | Active edition for `as_of_date = 2024-01-01`. |
| `ED-M012-44FZ-2023-01-01` | `act_edition_id`, `legal_act_id`, `valid_from`, `valid_to`, `status` | Superseded/wrong edition for 2024-scoped validation. |

Suggested bounded fields:

```json
{
  "act_edition_id": "ED-M012-44FZ-2024-01-01",
  "legal_act_id": "LA-M012-44FZ",
  "valid_from": "2024-01-01",
  "valid_to": null,
  "status": "active"
}
```

### LegalUnit Records

| ID | Required fields | Notes |
| --- | --- | --- |
| `LU-M012-44FZ-ART-001` | `legal_unit_id`, `act_edition_id`, `legal_act_id`, `unit_key`, `status` | Valid unit for the active 2024 edition. |
| `LU-M012-44FZ-ART-001-OLD` | `legal_unit_id`, `act_edition_id`, `legal_act_id`, `unit_key`, `status` | Superseded unit for wrong-edition and superseded-evidence cases. |

### SourceDocument Records

| ID | Required fields | Notes |
| --- | --- | --- |
| `SD-M012-44FZ-CONSULTANT` | `source_document_id`, `source_corpus_id`, `fixture_label`, `status` | Bounded source document anchor; no provider body or raw text. |
| `SD-M012-44FZ-GARANT` | `source_document_id`, `source_corpus_id`, `fixture_label`, `status` | Secondary bounded source anchor for ambiguity/orphan tests only. |

### SourceBlock Records

| ID | Required fields | Notes |
| --- | --- | --- |
| `SB-M012-001` | `source_block_id`, `source_document_id`, `block_key`, `status` | Valid block reached from `EV-M012-001`. |
| `SB-M012-002` | `source_block_id`, `source_document_id`, `block_key`, `status` | Valid block reached from `EV-M012-002`. |
| `SB-M012-ORPHAN` | `source_block_id`, `source_document_id`, `block_key`, `status` | Deliberately orphaned by pointing to a missing document ID in invalid graph variant. |

The `block_key` may be a synthetic locator such as `fixture-block-001`; it must not contain raw legal text.

### EvidenceSpan Records

| ID | Required fields | Notes |
| --- | --- | --- |
| `EV-M012-001` | `evidence_span_id`, `source_block_id`, `source_document_id`, `legal_unit_id`, `act_edition_id`, `status` | Primary valid evidence span. |
| `EV-M012-002` | `evidence_span_id`, `source_block_id`, `source_document_id`, `legal_unit_id`, `act_edition_id`, `status` | Secondary valid span for multi-citation positive tests. |
| `EV-M012-SUPERSEDED` | `evidence_span_id`, `source_block_id`, `source_document_id`, `legal_unit_id`, `act_edition_id`, `status`, `superseded_by` | Must reject for 2024-scoped validation. |
| `EV-M012-ORPHAN-SOURCE` | `evidence_span_id`, `source_block_id`, `source_document_id`, `legal_unit_id`, `act_edition_id`, `status` | Deliberately points to a missing or mismatched source path. |
| `EV-M012-ORPHAN-LEGAL` | `evidence_span_id`, `source_block_id`, `source_document_id`, `legal_unit_id`, `act_edition_id`, `status` | Deliberately points to a missing legal unit or edition path. |

Suggested bounded valid row:

```json
{
  "evidence_span_id": "EV-M012-001",
  "source_block_id": "SB-M012-001",
  "source_document_id": "SD-M012-44FZ-CONSULTANT",
  "legal_unit_id": "LU-M012-44FZ-ART-001",
  "act_edition_id": "ED-M012-44FZ-2024-01-01",
  "status": "active"
}
```

### Citation Binding Index

The fixture graph should include citation bindings separate from output envelopes so the validator can detect unresolved and ambiguous `citation_key` values.

| Citation key | Scope ID | Evidence span | Expected behavior |
| --- | --- | --- | --- |
| `CIT-M012-001` | `SCOPE-M012-44FZ-2024-001` | `EV-M012-001` | Resolves uniquely and accepts when explicit IDs match. |
| `CIT-M012-002` | `SCOPE-M012-44FZ-2024-001` | `EV-M012-002` | Resolves uniquely for multi-citation or answer-claim tests. |
| `CIT-M012-AMBIG` | `SCOPE-M012-44FZ-2024-001` | `EV-M012-001` and `EV-M012-002` | Resolves ambiguously and must reject. |
| `CIT-M012-SUPERSEDED` | `SCOPE-M012-44FZ-2024-001` | `EV-M012-SUPERSEDED` | Resolves to superseded evidence and must reject. |

## Shared Scope Records

All non-no-answer cases should use bounded scope objects with no raw user prompts:

| ID | Required fields | Notes |
| --- | --- | --- |
| `SCOPE-M012-44FZ-2024-001` | `scope_id`, `query_id`, `retrieval_run_id`, `as_of_date`, `source_corpus_id`, `validator_contract_version` | Active positive and negative validation scope. |
| `SCOPE-M012-44FZ-2023-001` | same fields | Optional wrong-edition regression scope if S02 needs explicit old-date coverage. |

Canonical 2024 scope:

```json
{
  "scope_id": "SCOPE-M012-44FZ-2024-001",
  "query_id": "Q-M012-FIXTURE-001",
  "retrieval_run_id": "RUN-M012-FIXTURE-001",
  "as_of_date": "2024-01-01",
  "source_corpus_id": "CORPUS-M012-FIXTURE",
  "validator_contract_version": "retrieval-output-validator/v1"
}
```

## Case Inventory

Each case below should have a stable `case_id`, one output envelope, an expected result state, and expected diagnostic code assertions. Invalid cases must fail closed without ID repair, fallback matching, or accepted partial evidence.

### Valid Cases

| Case ID | Output kind | Purpose | Expected result | Expected diagnostics |
| --- | --- | --- | --- | --- |
| `CASE-M012-VALID-RETRIEVAL` | `retrieval_candidate` | One citation resolves through `EvidenceSpan -> SourceBlock -> SourceDocument` and `EvidenceSpan -> LegalUnit -> ActEdition -> LegalAct`. | `accepted` | No `error` diagnostics. |
| `CASE-M012-VALID-ANSWER-CLAIM` | `answer_claim` | One answer claim references `CIT-M012-001`; citation includes matching `answer_claim_id`. | `accepted` | No `error` diagnostics. |
| `CASE-M012-SCOPED-NOANSWER` | `scoped_no_answer` | Explicit empty state with complete scope, empty `citations`, and empty `answer_claims`. | `accepted_scoped_no_answer` | `scoped_no_answer` with `severity = info`. |

Minimum valid retrieval citation fields:

```json
{
  "retrieval_output_id": "RET-M012-VALID-001",
  "citation_key": "CIT-M012-001",
  "evidence_span_id": "EV-M012-001",
  "source_block_id": "SB-M012-001",
  "source_document_id": "SD-M012-44FZ-CONSULTANT",
  "legal_unit_id": "LU-M012-44FZ-ART-001",
  "act_edition_id": "ED-M012-44FZ-2024-01-01"
}
```

### Required Invalid Cases

| Case ID | Mutation from valid output | Expected result | Primary diagnostic | Safe payload focus |
| --- | --- | --- | --- | --- |
| `CASE-M012-MISSING-EVIDENCE-SPAN-ID` | Remove `citations[0].evidence_span_id`. | `rejected` | `missing_required_field` | `field_path = citations[0].evidence_span_id`, `retrieval_output_id`, `scope_id`, `case_id`. |
| `CASE-M012-UNRESOLVED-EVIDENCE-SPAN-ID` | Set `evidence_span_id = EV-M012-DOES-NOT-EXIST`. | `rejected` | `unresolved_evidence_span` | `safe_id_value = EV-M012-DOES-NOT-EXIST`. |
| `CASE-M012-AMBIGUOUS-CITATION-KEY` | Set `citation_key = CIT-M012-AMBIG`. | `rejected` | `ambiguous_citation_key` | `safe_id_value = CIT-M012-AMBIG`; do not include raw citation labels. |
| `CASE-M012-ORPHANED-SOURCE-BLOCK` | Use `EV-M012-ORPHAN-SOURCE` or a graph variant where `SB-M012-ORPHAN` cannot reach its declared `SourceDocument`. | `rejected` | `orphaned_source_path` | `expected_id` and `resolved_id` may include bounded IDs only. |
| `CASE-M012-SUPERSEDED-EVIDENCE-SPAN` | Use `CIT-M012-SUPERSEDED` / `EV-M012-SUPERSEDED` in 2024 scope. | `rejected` | `superseded_evidence` | Include `safe_id_value = EV-M012-SUPERSEDED` and optionally `expected_id = EV-M012-001`. |
| `CASE-M012-WRONG-ACT-EDITION` | Keep valid `EV-M012-001` but set output `act_edition_id = ED-M012-44FZ-2023-01-01`. | `rejected` | `wrong_edition` or `id_path_mismatch` | Prefer `wrong_edition` when date validity is checked before generic path mismatch. |
| `CASE-M012-SCOPED-NOANSWER` | Valid scoped no-answer, listed above as accepted empty state. | `accepted_scoped_no_answer` | `scoped_no_answer` | Confirms no-answer is not an error when safely scoped. |

### Additional Contract-Coverage Invalid Cases

These cases are not the minimum task list, but S02 should include them if implementation scope allows because they map directly to the contract taxonomy.

| Case ID | Mutation from valid output | Expected result | Primary diagnostic |
| --- | --- | --- | --- |
| `CASE-M012-MISSING-SCOPE-AS-OF-DATE` | Remove `scope.as_of_date`. | `rejected` | `missing_required_field` |
| `CASE-M012-UNKNOWN-ID-NAMESPACE` | Set `evidence_span_id = MODEL-SAYS-ARTICLE-1`. | `rejected` | `unknown_id_namespace` |
| `CASE-M012-UNRESOLVED-CITATION-KEY` | Set `citation_key = CIT-M012-DOES-NOT-EXIST`. | `rejected` | `unresolved_citation_key` |
| `CASE-M012-SOURCE-PATH-MISMATCH` | Use `EV-M012-001` but set `source_block_id = SB-M012-002`. | `rejected` | `id_path_mismatch` |
| `CASE-M012-ORPHANED-LEGAL-UNIT` | Use `EV-M012-ORPHAN-LEGAL`. | `rejected` | `orphaned_legal_unit_path` |
| `CASE-M012-ANSWER-CLAIM-WITHOUT-EVIDENCE` | Add an answer claim with empty `supported_citation_keys`. | `rejected` | `answer_claim_without_evidence` |
| `CASE-M012-UNSAFE-NOANSWER-WITH-CITATION` | Use `output_kind = scoped_no_answer` with a non-empty `citations` array. | `rejected` | `unsafe_no_answer_shape` |
| `CASE-M012-FORBIDDEN-RAW-TEXT-FIELD` | Add `raw_legal_text`, `prompt`, `provider_payload`, `vector`, or `falkordb_row` field. | `rejected` | `forbidden_payload_field` |

## Expected Diagnostic Payload Shape

Every case should assert that diagnostics contain only bounded safe fields:

```json
{
  "code": "unresolved_evidence_span",
  "severity": "error",
  "result": "rejected",
  "field_path": "citations[0].evidence_span_id",
  "retrieval_output_id": "RET-M012-BAD-UNRESOLVED-EV",
  "scope_id": "SCOPE-M012-44FZ-2024-001",
  "case_id": "CASE-M012-UNRESOLVED-EVIDENCE-SPAN-ID",
  "safe_id_value": "EV-M012-DOES-NOT-EXIST",
  "fixture_artifact": "prd/retrieval/fixtures/retrieval_output_validator_cases.json"
}
```

Diagnostics must not include source excerpts, user prompt text, generated answer prose, provider bodies, credentials, raw vectors, raw runtime rows, or stack traces that may contain those values.

## Suggested JSON Skeleton

S02 may adapt field names locally, but the fixture should preserve these conceptual sections:

```json
{
  "schema_version": "retrieval-output-validator-fixtures/v1",
  "non_authoritative": true,
  "fixture_graph": {
    "legal_acts": [],
    "act_editions": [],
    "legal_units": [],
    "source_documents": [],
    "source_blocks": [],
    "evidence_spans": [],
    "citation_bindings": []
  },
  "cases": [
    {
      "case_id": "CASE-M012-VALID-RETRIEVAL",
      "description": "Valid retrieval candidate with exact source and legal-unit paths.",
      "output": {},
      "expected_result": "accepted",
      "expected_diagnostic_codes": []
    }
  ]
}
```

## S02 Acceptance Checklist

S02 implementation can treat the fixture taxonomy as satisfied when tests prove all of the following over tracked or inline fixtures:

1. Valid retrieval output returns `accepted`.
2. Valid answer claim output returns `accepted`.
3. Valid scoped no-answer returns `accepted_scoped_no_answer` with `scoped_no_answer` info diagnostic.
4. Missing `evidence_span_id` returns `missing_required_field`.
5. Unknown evidence span returns `unresolved_evidence_span`.
6. Ambiguous citation key returns `ambiguous_citation_key`.
7. Orphaned source path returns `orphaned_source_path`.
8. Superseded evidence span returns `superseded_evidence`.
9. Wrong act edition returns `wrong_edition` or an explicitly justified `id_path_mismatch`.
10. Fixture diagnostics remain compact and safe, with no raw legal text or secrets.
11. Test and artifact language continues to describe these records as bounded proof fixtures, not production parser output or legal evidence.
