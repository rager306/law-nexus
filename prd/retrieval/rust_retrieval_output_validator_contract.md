---
title: "Rust Retrieval Output Validator Contract"
status: "contract-draft"
non_authoritative: true
owner: "M216-8dps6e/S01"
contract_version: "retrieval-output-validator/rust-v1"
prior_art: "prd/archive/retrieval-era/retrieval_output_validator_contract.md"
vocabulary_authority: "prd/temporal-legal-model.md#3"
requirement: "R034"
created_at: "2026-10-09"
---

# Rust Retrieval Output Validator Contract

This contract defines the Rust-only retrieval/answer output ID envelope that the
`ln-query` validator accepts or rejects against a graph-backed identifier
resolution port. It is the Rust reformulation of the archived M012 Python-era
contract and does not claim retrieval quality, legal-answer correctness, parser
completeness, runtime/FalkorDB readiness, or LLM authority. It is
`contract-draft`, `non-authoritative`, and owned by `M216-8dps6e/S01`.

Contract version string: `retrieval-output-validator/rust-v1`, exported as
`ln_query::retrieval_output::VALIDATOR_CONTRACT_VERSION`.

## Boundary

- The deliverable is a deterministic, fail-closed validator plus its contract.
  It accepts or rejects structured retrieval/answer output identifiers only.
- It evaluates no answer prose, legal reasoning, retrieval ranking, embedding or
  reranker quality, parser completeness, production temporal semantics, or legal
  correctness.
- It exposes no product API. Callers are bounded tests and, later, a thin
  offline adapter; there is no product surface, no runtime service, and no
  network or storage dependency here.
- The vocabulary lives in `crates/ln-query/src/retrieval_output.rs`. The module
  is serde-free and adds no crate dependency.

## Vocabulary boundary

The identifier newtypes in this contract (`RetrievalOutputId`, `CitationKey`,
`EvidenceSpanId`, `SourceBlockId`, `SourceDocumentId`, `LegalUnitId`,
`ActEditionId`, `AnswerClaimId`, `OutputScopeId`, and the scope scalar tokens)
are **validator-envelope proof-local tokens**, not production domain entities.
They are the Rust counterparts of the archived M012 envelope field names and
fixture topology.

- No `prd/temporal-legal-model.md` §3 row is created, amended, or promoted by
  this contract.
- In particular the §3 `SourceBlock` row stays `deferred-undefined`: this
  contract does not infer the future `SourceBlock` evidence-domain entity from
  archive terminology, nor from `SourceBlockRecord`. `SourceBlockId` here is an
  envelope field token, and the fixture graph that resolves it is proof-local
  synthetic data, not a production schema.
- The contract asserts no final or production ID format.

## Prior art (not authority)

`prd/archive/retrieval-era/retrieval_output_validator_contract.md` (M012 Python
era) and its fixtures
`prd/archive/retrieval-era/fixtures/retrieval_output_validator_cases.json` are
prior art. Python product code is archive-only (ADR-0004/0007); the archive
contract is not authority. This document re-expresses the same fail-closed
intent in Rust and carries over the fixture topology identifiers so the M012
fixture graph can be reused as the Rust fixture graph.

## Output envelope

Every retrieval or answer output submitted to the validator is a
`RetrievalOutputEnvelope`:

| Field | Required | Left-open shape |
| --- | --- | --- |
| `retrieval_output_id` | yes | `FieldShape<RetrievalOutputId>` |
| `output_kind` | yes | `FieldShape<OutputKind>` |
| `scope` | yes | `ScopeShape` |
| `citations` | yes | `FieldShape<Vec<CitationBinding>>` |
| `answer_claims` | conditional | `FieldShape<Vec<AnswerClaim>>` |
| `extra_field_names` | no | `Vec<BoundedToken>` (observed additional wire field names) |

`FieldShape<T>` distinguishes four wire states so fail-closed rules can be
stated exactly: `Value(T)` (present), `ExplicitNull` (present but null),
`Missing` (absent), `WrongShape` (present with an invalid JSON shape). This is
how the validator separates a missing field from an explicit null.

`OutputKind` is closed: `retrieval_candidate`, `answer_claim`,
`scoped_no_answer`.

## Scope metadata

`scope` must carry all six fields. The validator resolves a complete scope from
an `ObservedScope` (the left-open wire form); a missing, null, or wrong-shaped
field is rejected, never repaired.

| Field | Rust type | Rule |
| --- | --- | --- |
| `scope_id` | `OutputScopeId` | Proof-local scope ID for diagnostics and fixture selection. |
| `query_id` | `ln_query::domain::QueryId` | Stable query/fixture-case ID; never user prompt text. |
| `retrieval_run_id` | `RetrievalRunId` | Stable proof-local run ID. |
| `as_of_date` | `ScopeAsOfDate` | Opaque scope selector for edition-sensitive resolution; not a temporal anchor claim. |
| `source_corpus_id` | `SourceCorpusId` | Fixture corpus identifier. |
| `validator_contract_version` | `ValidatorContractVersion` | Must equal `VALIDATOR_CONTRACT_VERSION`. |

`scope` must not carry raw legal text, raw user prompts, secrets, provider
payloads, vectors, runtime rows, or LLM reasoning.

## Citation binding

`CitationBinding` carries the required binding fields as `FieldShape<T>` so that
absence and explicit null are distinct:

| Field | Rust type | Rule |
| --- | --- | --- |
| `retrieval_output_id` | `FieldShape<RetrievalOutputId>` | Must match the parent envelope ID. |
| `citation_key` | `FieldShape<CitationKey>` | Must resolve uniquely in the active scope. |
| `evidence_span_id` | `FieldShape<EvidenceSpanId>` | Must resolve to an active evidence span. |
| `source_block_id` | `FieldShape<SourceBlockId>` | Must match the source block reached from `evidence_span_id`. |
| `source_document_id` | `FieldShape<SourceDocumentId>` | Must match the source document reached from the block. |
| `legal_unit_id` | `FieldShape<LegalUnitId>` | Must match the legal unit reached from `evidence_span_id`. |
| `act_edition_id` | `FieldShape<ActEditionId>` | Must match the edition reached and be valid for `scope.as_of_date`. |
| `answer_claim_id` | `FieldShape<AnswerClaimId>` | Required when supporting an answer claim; forbidden or null for citation-only candidates. |

## Resolution paths

For every non-empty citation binding the validator verifies both paths against
the resolution port:

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

The binding is valid only when the explicit IDs in the output match the IDs
reached by traversal and when the reached `act_edition_id` is the edition valid
for the scoped legal unit at `scope.as_of_date`. Superseded evidence is rejected
before the edition check.

`AnswerClaim` supports a claim by referencing `supported_citation_keys`; every
key must appear in `citations` and resolve. `ClaimKind` is closed:
`norm_reference`, `status`, `deadline`, `condition`.

## Verdicts

Exactly one verdict per outcome:

| Verdict | Meaning |
| --- | --- |
| `accepted` | All required IDs resolve through the graph for the scope. |
| `accepted_scoped_no_answer` | An explicit safe empty result with complete scope and no citations or claims. |
| `rejected` | Any required field, resolution, scope, edition, no-answer, or safety rule fails. |

Fallback is always rejection. The validator never repairs IDs, infers missing
citations, chooses among ambiguous citations, downgrades wrong-edition evidence,
or treats LLM text as evidence.

## Diagnostic taxonomy (closed, 16 codes)

| Code | Severity | Verdict |
| --- | --- | --- |
| `malformed_output_shape` | error | `rejected` |
| `missing_required_field` | error | `rejected` |
| `unknown_id_namespace` | error | `rejected` |
| `unresolved_citation_key` | error | `rejected` |
| `ambiguous_citation_key` | error | `rejected` |
| `unresolved_evidence_span` | error | `rejected` |
| `orphaned_source_path` | error | `rejected` |
| `orphaned_legal_unit_path` | error | `rejected` |
| `id_path_mismatch` | error | `rejected` |
| `superseded_evidence` | error | `rejected` |
| `wrong_edition` | error | `rejected` |
| `answer_claim_without_evidence` | error | `rejected` |
| `citation_without_evidence` | error | `rejected` |
| `unsafe_no_answer_shape` | error | `rejected` |
| `forbidden_payload_field` | error | `rejected` |
| `scoped_no_answer` | info | `accepted_scoped_no_answer` |

`DiagnosticSeverity` is closed: `error`, `warning`, `info`. Every current code is
`error` except `scoped_no_answer` (`info`); the `warning` variant exists for a
future advisory code and must never, by itself, reject.

## Bounded diagnostic fields

`OutputDiagnostic` carries only bounded, log-safe fields: `code`, `severity`,
`verdict`, `field_path`, `retrieval_output_id`, `scope_id`, and the optional
`safe_id_value`, `expected_id`, `resolved_id`. Severity and verdict are derived
from the code so they cannot disagree.

Diagnostics must never include raw legal text, source excerpts, prompts,
generated answers, credentials, provider bodies, vectors, runtime rows, or stack
traces carrying such material. A value that cannot be represented as a bounded
token is redacted to a sentinel rather than echoed.

## Deterministic rule order

The validator evaluates rules in this fixed order and reports one primary code
per rule; the first failing rule determines the primary diagnostic:

1. envelope shape (`malformed_output_shape`)
2. missing required fields (`missing_required_field`)
3. forbidden payload fields (`forbidden_payload_field`)
4. unknown ID namespace (`unknown_id_namespace`)
5. citation key resolution (`unresolved_citation_key` / `ambiguous_citation_key`)
6. evidence span resolution (`unresolved_evidence_span`)
7. superseded evidence (`superseded_evidence`)
8. source path traversal (`orphaned_source_path` / `id_path_mismatch`)
9. legal path traversal (`orphaned_legal_unit_path` / `id_path_mismatch`)
10. edition validity for `scope.as_of_date` (`wrong_edition`)
11. answer claims (`answer_claim_without_evidence`)
12. citation without evidence (`citation_without_evidence`)
13. unsafe no-answer shape (`unsafe_no_answer_shape`)
14. scoped no-answer acceptance (`scoped_no_answer`, info)

Given identical input the validator returns an identical verdict and identical
diagnostics in identical order (determinism). It borrows the envelope and never
mutates it (no-repair invariant).

## Fail-closed rules

The validator must not repair IDs, infer missing citations, choose among
ambiguous citation keys, downgrade wrong-edition or superseded evidence, perform
best-effort matching, or promote LLM output to evidence. Any unresolved,
ambiguous, orphaned, mismatched, superseded, wrong-edition, unknown-namespace,
missing, null, wrong-shaped, or forbidden-payload condition yields `rejected`.

## Non-claims

This contract is a bounded, synthetic-fixture proof of contract behavior. It does
not prove or claim product retrieval quality, parser completeness, citation-safe
production retrieval readiness, legal-answer correctness, LLM legal authority,
generated-Cypher execution authorization, runtime/FalkorDB/vector/rerank
behavior, production temporal graph completeness, or a final production ID
format. The Python archive is prior art, not authority.

## Implementation handoff

- Vocabulary and closed dictionaries: `crates/ln-query/src/retrieval_output.rs`.
- Resolution port and validator: added in this slice (T02/T03).
- Tests: `crates/ln-query/tests/retrieval_output_validator.rs`.
- Verify: `cargo test -p ln-query --offline --test retrieval_output_validator`,
  plus `cargo fmt --all --check` and the workspace offline check.
