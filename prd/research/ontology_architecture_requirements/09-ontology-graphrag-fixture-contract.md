---
requirement: R035
gate: GATE-ONTOLOGY-GRAPHRAG-INTEGRATION
status: fixture-contract-draft
owner: M020-ujbffl/S02
source_contract: prd/research/ontology_architecture_requirements/08-ontology-graphrag-proof-contract.md
non_authoritative: true
created_at: 2026-05-17
---

# Ontology GraphRAG Fixture Contract

## Purpose

This contract defines the proof-local fixture shape for the S02 ontology-aware retrieval proof. It extends existing retrieval-output validator, real-artifact retrieval, and offline citation retrieval fixture patterns with only the fields needed to prove bounded ontology-filter and temporal-filter behavior.

The fixture contract is not product schema, FalkorDB schema, ontology adoption, retrieval-quality proof, legal-answer proof, or R035 validation. It is a deterministic test surface for later S02/S03 commands.

## Source paths

S02 fixtures may derive from these repository-tracked, redacted inputs:

| Source path | Role | Boundary |
| --- | --- | --- |
| `prd/retrieval/fixtures/real_artifact_retrieval_cases.json` | Real-artifact-derived citation and edition path cases | Use source/evidence IDs and diagnostic expectations; do not copy raw legal text. |
| `prd/retrieval/fixtures/offline_citation_retrieval_cases.json` | Offline deterministic candidate selection cases | Reuse candidate/scoped-no-answer/fail-closed patterns. |
| `scripts/retrieval_output_validator.py` | Shared citation/evidence output validator | Use as the ID-resolution safety boundary; do not fork citation validation. |
| `prd/research/ontology_architecture_requirements/08-ontology-graphrag-proof-contract.md` | M020 proof ceiling and non-claims | Keep fixture proof below broad gate satisfaction unless later integration evidence exists. |

## Fixture envelope

The generated fixture artifact should be a JSON object with this top-level shape:

| Field | Required | Meaning |
| --- | ---: | --- |
| `schema_version` | yes | Stable string, initially `ontology-graphrag-proof-cases/v1`. |
| `proof_id` | yes | Stable proof-local ID, initially `OG-M020-S02-FIXTURE-PROOF`. |
| `non_authoritative` | yes | Must be `true`. |
| `source_inputs` | yes | Repository-relative source fixture and contract paths consumed by the builder. |
| `cases` | yes | Array of ontology GraphRAG proof cases. |
| `redaction` | yes | Boolean boundary proving forbidden payload classes are absent. |
| `non_claims` | yes | Required non-claims copied or narrowed from the S01 proof contract. |

## Case fields

Each `cases[]` entry must use this shape:

| Field | Required | Meaning |
| --- | ---: | --- |
| `case_id` | yes | Stable proof-local case ID, prefix `CASE-M020-OG-`. |
| `case_class` | yes | Closed case class from the table below. |
| `source_case_ids` | yes | IDs of source M013/M014 cases or `[]` for synthetic negative cases derived from the contract. |
| `query` | yes | Safe query metadata only; no raw user prompt or legal text. |
| `ontology_filter` | yes | Proof-local ontology filter metadata. |
| `temporal_filter` | yes | Explicit temporal scope and expected current/historical behavior. |
| `candidate_set` | yes | Candidate IDs and safe source/evidence references used by deterministic selection. |
| `output` | conditional | Retrieval output envelope to send to the shared validator when selection succeeds. |
| `expected_result` | yes | Closed expected result state. |
| `expected_diagnostic_codes` | yes | Stable diagnostic codes expected from verifier. |
| `non_authoritative` | yes | Must be `true`. |

## Query metadata

`query` must contain only safe bounded fields:

| Field | Required | Rule |
| --- | ---: | --- |
| `query_id` | yes | Stable proof-local query ID. |
| `query_kind` | yes | One of `ontology_filter_lookup`, `current_status_lookup`, `scoped_no_answer`, or `negative_guardrail`. |
| `scope_id` | yes | Must match `output.scope.scope_id` when an output envelope exists. |
| `target_record_id` | optional | Stable parser/retrieval record ID when relevant. |
| `target_level` | optional | Bounded structural level such as `document`, `article`, `source_block`, or `legal_unit`. |

`query` must not contain raw legal text, raw prompts, natural-language legal advice, provider payloads, or generated Cypher text. If S03 later introduces generated query candidates, they must live in a separate safety-validated artifact.

## Ontology filter

`ontology_filter` is proof-local metadata, not a final ontology schema. It must contain:

| Field | Required | Rule |
| --- | ---: | --- |
| `filter_id` | yes | Stable ID, prefix `OF-M020-`. |
| `filter_kind` | yes | One of `legal_evidence_core`, `ontology_gate`, `temporal_status`, or `unsupported_gate`. |
| `allowed_values` | yes | Small array of proof-local values such as `DATA-LEGAL-EVIDENCE-CORE`, `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`, or `current_version`. |
| `requested_value` | yes | Value requested by the case. |
| `expected_filter_result` | yes | One of `matched`, `excluded`, or `unsupported`. |

Allowed values must come from existing source-backed registry, requirement, or proof-contract terminology. Unsupported values must produce a diagnostic and must not be silently accepted.

## Temporal filter

`temporal_filter` must contain:

| Field | Required | Rule |
| --- | ---: | --- |
| `as_of_date` | yes | ISO date string used for edition-sensitive validation. |
| `mode` | yes | One of `current_only`, `historical_allowed`, or `not_applicable`. |
| `expected_temporal_result` | yes | One of `included`, `excluded_inactive`, `wrong_edition`, or `not_applicable`. |
| `evidence_edition_id` | optional | Expected active edition ID when output exists. |

Temporal filtering remains proof-local. It does not prove full temporal conflict policy, same-date conflict resolution, or legal collision reasoning.

## Candidate set

`candidate_set` must be an array of safe candidate objects:

| Field | Required | Rule |
| --- | ---: | --- |
| `candidate_id` | yes | Stable proof-local candidate ID. |
| `source_record_id` | optional | Parser/retrieval source record ID. |
| `citation_key` | optional | Citation key when candidate has an output envelope. |
| `evidence_span_id` | optional | Evidence ID when candidate has an output envelope. |
| `act_edition_id` | optional | Edition ID used by temporal filter. |
| `ontology_values` | yes | Small array of proof-local ontology values attached to the candidate. |
| `selection_reason` | yes | Safe reason such as `ontology_and_temporal_match`, `inactive_version_excluded`, or `unsupported_filter_rejected`. |

Candidate objects must not contain raw source excerpts, legal advice, raw vectors, raw graph rows, or provider payloads.

## Expected result states

`expected_result` is closed:

| State | Meaning |
| --- | --- |
| `accepted` | Ontology filter and temporal filter match; shared validator accepts citation/evidence output. |
| `rejected` | Case fails filter, temporal, citation, shape, payload, or ambiguity checks. |
| `accepted_scoped_no_answer` | Case has explicit scoped no-answer behavior and shared validator accepts only safe empty output. |
| `blocked_unsupported_filter` | Requested ontology gate or class is unsupported and must not be treated as accepted evidence. |

## Required case classes

The first S02 fixture set should cover at least:

| Case class | Expected result | Required diagnostic behavior |
| --- | --- | --- |
| `valid_ontology_temporal_citation` | `accepted` | No error diagnostics; citation/evidence IDs validate. |
| `inactive_or_wrong_edition_excluded` | `rejected` | Emits `temporal_filter_excluded` or shared validator `wrong_edition`. |
| `unsupported_ontology_filter` | `blocked_unsupported_filter` | Emits `unsupported_ontology_filter`. |
| `missing_citation_or_evidence_id` | `rejected` | Emits shared validator missing-field diagnostic. |
| `ambiguous_candidate_set` | `rejected` | Emits `ambiguous_candidate_set`; no arbitrary tie-break. |
| `scoped_no_answer` | `accepted_scoped_no_answer` | Emits `scoped_no_answer` and no hidden citations. |
| `forbidden_payload_field` | `rejected` | Emits `forbidden_payload_field` or equivalent unsafe-payload diagnostic. |

## Diagnostic codes

S02 verifier diagnostics should reuse existing shared-validator codes where possible and add only small proof-local codes when needed:

| Code | Use |
| --- | --- |
| `ontology_filter_matched` | Informational accepted filter match. |
| `unsupported_ontology_filter` | Requested ontology filter is not in `allowed_values`. |
| `temporal_filter_excluded` | Candidate was excluded because current-only temporal scope rejected it. |
| `ambiguous_candidate_set` | Multiple candidates match and no deterministic safe selection is allowed. |
| `forbidden_payload_field` | Fixture or output includes a forbidden raw payload field. |
| shared validator codes | Use `missing_required_field`, `wrong_edition`, `id_path_mismatch`, `orphaned_source_path`, `unsafe_no_answer_shape`, and related existing codes without renaming. |

Every diagnostic must identify case ID, rule, safe field path, and remediation hint. It must not include raw legal text, prompts, provider payloads, vectors, raw graph rows, secrets, or legal advice.

## Redaction boundary

The fixture artifact and verifier output must prove these payload classes are excluded:

- raw legal text;
- raw query text;
- raw prompts;
- generated legal advice;
- raw vectors;
- provider payloads;
- raw FalkorDB rows;
- secrets;
- absolute local paths;
- `.gsd/exec` proof paths.

## Non-claims

This fixture contract does not validate R035.
This fixture contract does not satisfy `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`.
This fixture contract does not prove product retrieval quality.
This fixture contract does not prove legal-answer correctness.
This fixture contract does not prove parser completeness.
This fixture contract does not prove FalkorDB production behavior.
This fixture contract does not prove graph-vector, HNSW, or hybrid retrieval behavior.
This fixture contract does not prove generated-Cypher safety.
This fixture contract does not prove BFO, GOST, OWL, Common Logic, LKIF, RusLegalCore, Akoma Ntoso, LegalDocML, or FRBR conformance.
This fixture contract does not prove 1000-document or pilot-scale readiness.
This fixture contract does not make LLM output legal authority.

## Verification expectation

The T01 contract itself is verified by content assertions only. T02 must implement builder and verifier commands that check this fixture shape, generate the JSON fixture, and report deterministic counts and diagnostics.
