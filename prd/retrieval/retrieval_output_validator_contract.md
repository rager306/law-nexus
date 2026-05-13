---
title: "Retrieval Output Validator Contract"
status: "contract-draft"
owner: "M012/S01"
requirement: "R034"
decision_inputs:
  - "D045"
source_inputs:
  - ".gsd/REQUIREMENTS.md#R034"
  - ".gsd/DECISIONS.md#D045"
  - "prd/research/habr_legal_rag_processed_architecture_json_comparison.md"
  - "prd/architecture/architecture_items.jsonl#DATA-LEGAL-EVIDENCE-CORE"
non_authoritative: true
created_at: "2026-05-13"
---

# Retrieval Output Validator Contract

This contract defines the M012 retrieval/answer output ID envelope that S02 must implement against static fixture graph records. It converts the Habr Legal RAG format-first validation lesson into a LegalGraph-specific fail-closed proof without claiming retrieval quality, parser completeness, legal correctness, FalkorDB runtime readiness, or LLM authority.

## Source-Backed Basis

- `R034` requires retrieval and answer outputs to fail closed unless required citation/evidence identifiers resolve to graph-backed source, legal-unit, and edition evidence paths.
- `D045` classifies Habr Legal RAG article ideas as proof-required candidates, not validated architecture or product behavior.
- `EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING` identifies retrieval output ID validation, citation precision, scoped no-answer evaluation, and scale/noise degradation as future proof candidates.
- `DATA-LEGAL-EVIDENCE-CORE` names `LegalAct`, `ActEdition`, `SourceDocument`, `SourceBlock`, `EvidenceSpan`, and `NormStatement` as core source-backed concepts, while explicitly not proving final schema completeness, parser completeness, or legal-answer correctness.
- Current architecture non-claims keep product retrieval quality, parser completeness, legal-answer correctness, FalkorDB runtime/vector/full-text/rerank behavior, generated-Cypher execution authorization, and LLM legal authority out of scope.

## Validation Boundary

The validator accepts or rejects structured output identifiers only. It does not evaluate answer prose, legal reasoning, retrieval ranking, embedding quality, reranker quality, parser completeness, production temporal semantics, or legal correctness.

The S02 implementation must use deterministic static fixtures. It must not require FalkorDB runtime, embeddings, LLM calls, external services, product ETL, browser/UI behavior, or raw legal text.

## Output Envelope

Every retrieval or answer output submitted to the validator MUST be a structured object with these top-level fields:

| Field | Required | Purpose |
| --- | --- | --- |
| `retrieval_output_id` | yes | Stable ID for the output envelope being validated. |
| `output_kind` | yes | One of `retrieval_candidate`, `answer_claim`, or `scoped_no_answer`. |
| `scope` | yes | Explicit scope metadata limiting the validation claim. |
| `citations` | yes | Array of citation/evidence bindings. Empty only for valid `scoped_no_answer`. |
| `answer_claims` | conditional | Required for `answer_claim`; forbidden for pure `retrieval_candidate` unless empty. |

### Scope Metadata

`scope` MUST contain:

| Field | Required | Rule |
| --- | --- | --- |
| `scope_id` | yes | Proof-local scope ID for diagnostics and fixture selection. |
| `query_id` | yes | Stable query or fixture-case ID; not user prompt text. |
| `retrieval_run_id` | yes | Stable proof-local run ID. |
| `as_of_date` | yes | Date used to resolve edition-sensitive evidence. |
| `source_corpus_id` | yes | Fixture corpus identifier. |
| `validator_contract_version` | yes | Contract version, initially `retrieval-output-validator/v1`. |

`scope` MUST NOT contain raw legal text, raw user prompts, secrets, provider payloads, or LLM reasoning.

## Required Citation/Evidence Binding Fields

Each object in `citations` MUST contain all fields below for `retrieval_candidate` and `answer_claim` outputs:

| Field | Required | Resolution rule |
| --- | --- | --- |
| `citation_key` | yes | Must resolve uniquely to exactly one fixture citation binding in the active `scope`. |
| `evidence_span_id` | yes | Must resolve to an active `EvidenceSpan` fixture row. |
| `source_block_id` | yes | Must match the `SourceBlock` reached from `evidence_span_id`. |
| `source_document_id` | yes | Must match the `SourceDocument` reached from `source_block_id`. |
| `legal_unit_id` | yes | Must match the `LegalUnit` reached from `evidence_span_id`. |
| `act_edition_id` | yes | Must match the `ActEdition` reached from `legal_unit_id` and be valid for `scope.as_of_date`. |
| `retrieval_output_id` | yes | Must match the parent envelope ID. |
| `answer_claim_id` | conditional | Required when the citation supports an `answer_claim`; forbidden or null for citation-only retrieval candidates. |

S02 fixtures may use proof-local ID prefixes such as `RET-M012-*`, `CIT-M012-*`, `EV-M012-*`, `SB-M012-*`, `SD-M012-*`, `LU-M012-*`, `ED-M012-*`, and `AC-M012-*`. These prefixes are stable for M012 tests but are not a final production graph schema claim.

## Answer Claim Fields

Each object in `answer_claims` MUST contain:

| Field | Required | Rule |
| --- | --- | --- |
| `answer_claim_id` | yes | Stable claim ID referenced by at least one citation binding. |
| `retrieval_output_id` | yes | Must match parent envelope ID. |
| `claim_kind` | yes | Bounded test value such as `norm_reference`, `status`, `deadline`, or `condition`. |
| `scope_id` | yes | Must match `scope.scope_id`. |
| `supported_citation_keys` | yes | Non-empty array; every key must appear in `citations`. |

`answer_claims` MUST NOT contain free-form legal authority, raw legal text, generated legal advice, provider reasoning, or unvalidated citation labels.

## Allowed Result States

The validator returns exactly one of these states:

| State | Meaning |
| --- | --- |
| `accepted` | All required IDs are present and resolve through the static fixture graph for the given scope. |
| `accepted_scoped_no_answer` | The output is an explicit safe empty result with scoped no-answer metadata and no citations or claims. |
| `rejected` | Any required field, ID resolution, scope, edition, no-answer, or safety rule fails. |

Fallback behavior is always rejection. The validator MUST NOT repair IDs, infer missing citations, choose among ambiguous citations, downgrade wrong-edition evidence, or treat LLM text as evidence.

## Static Fixture Graph Resolution Contract

For every non-empty citation binding, S02 must verify both paths:

```text
citation_key
  -> evidence_span_id
  -> source_block_id
  -> source_document_id
```

```text
evidence_span_id
  -> legal_unit_id
  -> act_edition_id
  -> legal_act_id
```

The binding is valid only when the explicit IDs in the output match the IDs reached by fixture traversal and the reached `act_edition_id` is valid for `scope.as_of_date`.

A fixture row may be synthetic when testing temporal behavior, but it must be labeled as proof fixture data and must not be presented as a production temporal graph or real legal correctness proof.

## Scoped No-Answer Contract

`output_kind = scoped_no_answer` is accepted only when all of the following are true:

- `citations` is an empty array.
- `answer_claims` is absent or an empty array.
- `scope` contains all required scope metadata.
- A diagnostic entry with code `scoped_no_answer` and severity `info` is present or produced.
- The output states no verified evidence exists only within the explicit `scope`; it does not assert global legal absence.

A no-answer output MUST be rejected if it contains unresolved IDs, fabricated citation labels, hidden candidate IDs, answer claims, or unscoped absence language.

## Forbidden Fields and Behaviors

The validator and future callers MUST reject or avoid:

1. Free-form citation authority such as `"according to the law"`, page labels, document names, or citation strings that do not resolve to `citation_key` and graph-backed IDs.
2. LLM-only evidence IDs, including IDs invented in model output and absent from fixture rows.
3. Unresolved citation labels, duplicate/ambiguous `citation_key` values, or best-effort citation matching.
4. Unscoped no-answer claims, global legal absence claims, or no-answer outputs with non-empty citation/claim arrays.
5. Missing, null, empty, malformed, or unknown-namespace values for required IDs.
6. Orphaned evidence paths where an `EvidenceSpan` lacks a matching `SourceBlock`, `SourceDocument`, `LegalUnit`, or `ActEdition` edge.
7. Superseded evidence accepted as current evidence for `scope.as_of_date`.
8. Wrong-edition evidence accepted when `act_edition_id` does not match the legal unit edition valid for `scope.as_of_date`.
9. Raw legal text, raw source excerpts, raw provider bodies, secrets, LLM prompts, LLM reasoning, raw vectors, or raw FalkorDB rows in diagnostics or durable proof artifacts.
10. Any claim that validation success proves retrieval quality, answer correctness, parser completeness, production temporal modeling, or FalkorDB runtime behavior.

## Diagnostic Taxonomy

Diagnostics must be deterministic, typed, compact, and safe for logs/artifacts. S02 must implement at least these codes:

| Code | Severity | Result | Required when |
| --- | --- | --- | --- |
| `missing_required_field` | error | `rejected` | A required envelope, scope, citation, or answer-claim field is absent/null/empty. |
| `malformed_output_shape` | error | `rejected` | The output is not an object or has invalid array/object shapes. |
| `unknown_id_namespace` | error | `rejected` | An ID has a prefix/namespace outside the fixture contract. |
| `unresolved_citation_key` | error | `rejected` | `citation_key` does not resolve in the active scope. |
| `ambiguous_citation_key` | error | `rejected` | `citation_key` resolves to more than one fixture binding. |
| `unresolved_evidence_span` | error | `rejected` | `evidence_span_id` is absent from fixture rows. |
| `orphaned_source_path` | error | `rejected` | Evidence cannot traverse to the declared source block/document path. |
| `orphaned_legal_unit_path` | error | `rejected` | Evidence cannot traverse to the declared legal unit/edition/act path. |
| `id_path_mismatch` | error | `rejected` | Explicit output IDs disagree with fixture traversal. |
| `superseded_evidence` | error | `rejected` | Evidence is superseded for `scope.as_of_date`. |
| `wrong_edition` | error | `rejected` | `act_edition_id` is not the edition valid for the scoped legal unit/date. |
| `answer_claim_without_evidence` | error | `rejected` | An answer claim lacks supporting citation keys. |
| `unsafe_no_answer_shape` | error | `rejected` | A no-answer output is unscoped or contains citations/claims/hidden IDs. |
| `forbidden_payload_field` | error | `rejected` | Raw text, prompt, provider, secret, vector, or runtime-row fields appear. |
| `scoped_no_answer` | info | `accepted_scoped_no_answer` | A scoped empty result is accepted. |

### Diagnostic Payload Fields

Each diagnostic MUST include only safe bounded fields:

| Field | Required | Notes |
| --- | --- | --- |
| `code` | yes | One of the stable diagnostic codes. |
| `severity` | yes | `error`, `warning`, or `info`; errors reject. |
| `result` | yes | `rejected`, `accepted`, or `accepted_scoped_no_answer`. |
| `field_path` | yes | JSON pointer or dotted path such as `citations[0].evidence_span_id`. |
| `retrieval_output_id` | yes | Bounded ID value or `<missing>`. |
| `scope_id` | yes | Bounded scope ID or `<missing>`. |
| `case_id` | yes | Fixture case ID. |
| `safe_id_value` | optional | Bounded offending ID value; no raw legal text. |
| `expected_id` | optional | Bounded expected fixture ID. |
| `resolved_id` | optional | Bounded resolved fixture ID. |
| `fixture_artifact` | optional | Tracked fixture path or fixture name. |

Diagnostics MUST NOT include raw legal text, full source excerpts, prompts, generated answers, credentials, provider bodies, raw vectors, raw FalkorDB rows, or stack traces containing such material.

## Positive Examples

### Valid Retrieval Candidate

```json
{
  "retrieval_output_id": "RET-M012-VALID-001",
  "output_kind": "retrieval_candidate",
  "scope": {
    "scope_id": "SCOPE-M012-44FZ-2024-001",
    "query_id": "Q-M012-VALID-001",
    "retrieval_run_id": "RUN-M012-001",
    "as_of_date": "2024-01-01",
    "source_corpus_id": "CORPUS-M012-FIXTURE",
    "validator_contract_version": "retrieval-output-validator/v1"
  },
  "citations": [
    {
      "retrieval_output_id": "RET-M012-VALID-001",
      "citation_key": "CIT-M012-001",
      "evidence_span_id": "EV-M012-001",
      "source_block_id": "SB-M012-001",
      "source_document_id": "SD-M012-44FZ-CONSULTANT",
      "legal_unit_id": "LU-M012-44FZ-ART-001",
      "act_edition_id": "ED-M012-44FZ-2024-01-01"
    }
  ]
}
```

Expected result: `accepted` when the fixture graph resolves both required paths exactly.

### Valid Answer Claim

```json
{
  "retrieval_output_id": "RET-M012-ANSWER-001",
  "output_kind": "answer_claim",
  "scope": {
    "scope_id": "SCOPE-M012-44FZ-2024-001",
    "query_id": "Q-M012-ANSWER-001",
    "retrieval_run_id": "RUN-M012-002",
    "as_of_date": "2024-01-01",
    "source_corpus_id": "CORPUS-M012-FIXTURE",
    "validator_contract_version": "retrieval-output-validator/v1"
  },
  "answer_claims": [
    {
      "answer_claim_id": "AC-M012-001",
      "retrieval_output_id": "RET-M012-ANSWER-001",
      "claim_kind": "norm_reference",
      "scope_id": "SCOPE-M012-44FZ-2024-001",
      "supported_citation_keys": ["CIT-M012-001"]
    }
  ],
  "citations": [
    {
      "retrieval_output_id": "RET-M012-ANSWER-001",
      "answer_claim_id": "AC-M012-001",
      "citation_key": "CIT-M012-001",
      "evidence_span_id": "EV-M012-001",
      "source_block_id": "SB-M012-001",
      "source_document_id": "SD-M012-44FZ-CONSULTANT",
      "legal_unit_id": "LU-M012-44FZ-ART-001",
      "act_edition_id": "ED-M012-44FZ-2024-01-01"
    }
  ]
}
```

Expected result: `accepted` when the answer claim references only resolved citation keys and all citation paths match fixture traversal.

### Valid Scoped No-Answer

```json
{
  "retrieval_output_id": "RET-M012-NOANSWER-001",
  "output_kind": "scoped_no_answer",
  "scope": {
    "scope_id": "SCOPE-M012-44FZ-2024-001",
    "query_id": "Q-M012-NOANSWER-001",
    "retrieval_run_id": "RUN-M012-003",
    "as_of_date": "2024-01-01",
    "source_corpus_id": "CORPUS-M012-FIXTURE",
    "validator_contract_version": "retrieval-output-validator/v1"
  },
  "citations": [],
  "answer_claims": [],
  "diagnostics": [
    {
      "code": "scoped_no_answer",
      "severity": "info",
      "result": "accepted_scoped_no_answer",
      "field_path": "citations",
      "retrieval_output_id": "RET-M012-NOANSWER-001",
      "scope_id": "SCOPE-M012-44FZ-2024-001",
      "case_id": "CASE-M012-SCOPED-NOANSWER"
    }
  ]
}
```

Expected result: `accepted_scoped_no_answer`; this states only that the fixture scope has no verified evidence for the query.

## Negative Examples

### LLM-Invented Evidence ID

```json
{
  "retrieval_output_id": "RET-M012-BAD-LLM-ID",
  "output_kind": "retrieval_candidate",
  "scope": { "scope_id": "SCOPE-M012-44FZ-2024-001", "query_id": "Q-M012-BAD", "retrieval_run_id": "RUN-M012-BAD", "as_of_date": "2024-01-01", "source_corpus_id": "CORPUS-M012-FIXTURE", "validator_contract_version": "retrieval-output-validator/v1" },
  "citations": [
    { "retrieval_output_id": "RET-M012-BAD-LLM-ID", "citation_key": "CIT-M012-001", "evidence_span_id": "the_model_says_article_1", "source_block_id": "SB-M012-001", "source_document_id": "SD-M012-44FZ-CONSULTANT", "legal_unit_id": "LU-M012-44FZ-ART-001", "act_edition_id": "ED-M012-44FZ-2024-01-01" }
  ]
}
```

Expected result: `rejected` with `unknown_id_namespace` or `unresolved_evidence_span`.

### Wrong Edition

```json
{
  "retrieval_output_id": "RET-M012-BAD-EDITION",
  "output_kind": "retrieval_candidate",
  "scope": { "scope_id": "SCOPE-M012-44FZ-2024-001", "query_id": "Q-M012-BAD-EDITION", "retrieval_run_id": "RUN-M012-BAD", "as_of_date": "2024-01-01", "source_corpus_id": "CORPUS-M012-FIXTURE", "validator_contract_version": "retrieval-output-validator/v1" },
  "citations": [
    { "retrieval_output_id": "RET-M012-BAD-EDITION", "citation_key": "CIT-M012-001", "evidence_span_id": "EV-M012-001", "source_block_id": "SB-M012-001", "source_document_id": "SD-M012-44FZ-CONSULTANT", "legal_unit_id": "LU-M012-44FZ-ART-001", "act_edition_id": "ED-M012-44FZ-2023-01-01" }
  ]
}
```

Expected result: `rejected` with `wrong_edition` or `id_path_mismatch`.

### Unsafe No-Answer

```json
{
  "retrieval_output_id": "RET-M012-BAD-NOANSWER",
  "output_kind": "scoped_no_answer",
  "scope": { "scope_id": "SCOPE-M012-44FZ-2024-001", "query_id": "Q-M012-BAD-NOANSWER", "retrieval_run_id": "RUN-M012-BAD", "as_of_date": "2024-01-01", "source_corpus_id": "CORPUS-M012-FIXTURE", "validator_contract_version": "retrieval-output-validator/v1" },
  "citations": [
    { "citation_key": "unresolved human label" }
  ]
}
```

Expected result: `rejected` with `unsafe_no_answer_shape` and possibly `unresolved_citation_key`.

## S02-Testable Validation Criteria

S02 can translate this contract into tests by asserting:

1. A valid retrieval candidate with all required IDs resolves both fixture paths and returns `accepted`.
2. A valid answer claim requires `answer_claim_id`, references resolved `supported_citation_keys`, and returns `accepted`.
3. A scoped no-answer with empty `citations` and `answer_claims` returns `accepted_scoped_no_answer` with `scoped_no_answer` diagnostic.
4. Missing `retrieval_output_id`, `evidence_span_id`, `source_block_id`, `source_document_id`, `legal_unit_id`, `act_edition_id`, `citation_key`, or required scope metadata returns `rejected` with `missing_required_field`.
5. Unknown ID prefixes return `rejected` with `unknown_id_namespace`.
6. Unresolved citation labels return `rejected` with `unresolved_citation_key`.
7. Duplicate citation bindings in one scope return `rejected` with `ambiguous_citation_key`.
8. Unknown evidence IDs return `rejected` with `unresolved_evidence_span`.
9. Evidence rows without source traversal return `rejected` with `orphaned_source_path`.
10. Evidence rows without legal-unit/edition traversal return `rejected` with `orphaned_legal_unit_path`.
11. Explicit IDs that disagree with fixture traversal return `rejected` with `id_path_mismatch`.
12. Superseded evidence for the scoped date returns `rejected` with `superseded_evidence`.
13. Wrong edition for the scoped date returns `rejected` with `wrong_edition`.
14. Answer claims with no supporting citation keys return `rejected` with `answer_claim_without_evidence`.
15. No-answer outputs with citations, claims, unresolved IDs, or missing scope return `rejected` with `unsafe_no_answer_shape`.
16. Outputs or diagnostics containing raw legal text, prompts, provider bodies, secrets, vectors, or raw runtime rows return `rejected` with `forbidden_payload_field`.
17. All rejected cases fail closed without repairs, inferred IDs, fallback legal explanations, or accepted partial evidence.
18. Diagnostic payloads contain only the allowed bounded fields and never raw legal text.

## Non-Claims

This contract does not prove or claim:

- Product retrieval quality.
- Parser completeness.
- Citation-safe retrieval readiness for production.
- Legal-answer correctness.
- LLM legal authority.
- Generated-Cypher execution authorization or generated-Cypher safety closure.
- FalkorDB loading, runtime, vector, full-text, reranking, or production-scale behavior.
- Production temporal graph completeness or amendment/legal-effect modeling.
- Final production ID format or final graph schema.
- Multi-document Consultant expansion, Garant regression, or multi-source readiness.

## S02 Implementation Handoff

S02 should implement the validator as a small deterministic module plus tests over tracked or inline fixtures. Preferred path candidates, in order of least surprise for the current repository layout, are:

1. `scripts/retrieval_output_validator.py` with tests in `tests/test_retrieval_output_validator.py`.
2. `scripts/verify-retrieval-output-validator.py` as a proof/check CLI with tests in `tests/test_retrieval_output_validator.py`.
3. `legalgraph/retrieval/output_validator.py` with tests in `tests/test_retrieval_output_validator.py`, only if a package namespace already exists when S02 starts.

Expected fixture source is `prd/retrieval/fixtures/retrieval_output_validator_cases.json` unless S02 deliberately keeps smaller inline fixtures in the test file. Runtime fixtures must be git-tracked project files; `.gsd/` artifacts are planning evidence only, not runtime inputs.

S02 must preserve these stable diagnostic codes from this contract: `missing_required_field`, `malformed_output_shape`, `unknown_id_namespace`, `unresolved_citation_key`, `ambiguous_citation_key`, `unresolved_evidence_span`, `orphaned_source_path`, `orphaned_legal_unit_path`, `id_path_mismatch`, `superseded_evidence`, `wrong_edition`, `answer_claim_without_evidence`, `unsafe_no_answer_shape`, `forbidden_payload_field`, and `scoped_no_answer`.

For handoff/search compatibility with the R034 validation text and S01 verification command, the required scenario keywords are: `missing_id`, `unresolved_evidence`, `ambiguous_citation`, `orphan_source_block`, `superseded_evidence`, `wrong_edition`, and `scoped_no_answer`. These are scenario labels, not replacement diagnostic codes; map them as follows: `missing_id` -> `missing_required_field`, `unresolved_evidence` -> `unresolved_evidence_span`, `ambiguous_citation` -> `ambiguous_citation_key`, and `orphan_source_block` -> `orphaned_source_path`.

Non-claims to carry into S02 proof artifacts:

- Does not prove product retrieval quality.
- Does not prove parser completeness.
- Does not prove FalkorDB runtime behavior.
- Does not prove generated-Cypher safety.
- Does not prove legal-answer correctness.

## S02 Implementation Notes

- Use tracked fixtures under `prd/retrieval/` or another git-tracked project path; do not depend on `.gsd/` as a runtime fixture source.
- Keep fixture legal text absent or bounded by pre-approved hash/excerpt conventions; IDs and topology are enough for this proof.
- Emit compact deterministic diagnostics for CLI/check-mode use.
- Preserve `R034` and D045 boundaries in test names and proof artifact language.
- Treat every invalid case as a rejection even if a human could infer the intended citation.
