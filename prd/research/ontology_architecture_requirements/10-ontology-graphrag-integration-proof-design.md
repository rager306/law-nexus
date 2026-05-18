---
requirement: R035
gate: GATE-ONTOLOGY-GRAPHRAG-INTEGRATION
status: integration-proof-design
owner: M020-ujbffl/S03
source_contracts:
  - prd/research/ontology_architecture_requirements/08-ontology-graphrag-proof-contract.md
  - prd/research/ontology_architecture_requirements/09-ontology-graphrag-fixture-contract.md
  - prd/06_m002_cypher_safety_contract.md
non_authoritative: true
created_at: 2026-05-18
---

# Ontology GraphRAG Integration Proof Design

## Purpose

This note defines the S03 bounded integration proof flow for the ontology GraphRAG proof spine. It connects the S02 fixture surface to a deterministic proof command that applies ontology filters, temporal filters, citation/evidence validation, and generated-query safety boundaries without claiming product retrieval quality or legal-answer correctness.

The proof is intentionally non-authoritative. It proves only that tracked, redacted fixture records can pass through a citation-bound integration path with safe diagnostics.

## Inputs

| Input | Role | Boundary |
| --- | --- | --- |
| `prd/research/ontology_architecture_requirements/ontology_graphrag_proof_cases.json` | S02 proof cases carrying ontology filter, temporal filter, candidate set, and optional retrieval output envelopes. | Fixture-local IDs only; no raw legal text, raw prompts, raw vectors, or provider payloads. |
| `scripts/verify-ontology-graphrag-proof.py` | S02 verifier behavior for fixture shape, ontology/temporal local diagnostics, and shared citation validator integration. | Reused as the deterministic fixture authority; S03 does not fork citation validation. |
| `scripts/retrieval_output_validator.py` | Shared citation/evidence identifier validation. | Authority for accepted retrieval output envelopes and scoped no-answer safety. |
| `prd/06_m002_cypher_safety_contract.md` | Generated-query safety policy. | Policy reference only for S03 because generated query execution is avoided. |

## End-to-end flow steps

1. **Load tracked S02 fixtures.** Read only repository-relative fixture JSON and reject malformed, missing, or non-object roots.
2. **Assert proof envelope.** Require `non_authoritative: true`, known S02 schema/proof IDs, redaction boundary fields, and the S02 case array.
3. **Apply ontology filter gate.** For each case, compare `ontology_filter.requested_value` with `ontology_filter.allowed_values` and report `ontology_filter_matched` or `unsupported_ontology_filter` without silently widening the allowed ontology vocabulary.
4. **Apply temporal filter gate.** Respect each case's `temporal_filter.mode`, `as_of_date`, and `expected_temporal_result`. Current-only wrong-edition or inactive evidence is rejected or excluded with `temporal_filter_excluded`/`wrong_edition` diagnostics.
5. **Validate citation/evidence IDs.** For cases with an `output` envelope, call the shared retrieval output validator so accepted results retain citation keys, evidence span IDs, source block IDs, source document IDs, legal unit IDs, and edition IDs.
6. **Enforce candidate ambiguity and payload safety.** Reject ambiguous candidate sets without arbitrary tie-breaking and reject forbidden payload fields such as raw legal text, prompts, provider payloads, raw vectors, raw graph rows, secrets, and generated legal advice.
7. **Record query safety disposition.** S03 avoids generated query execution. No generated Cypher, FalkorDB query text, or query-like candidate is executed or persisted. The proof records `generated_query_execution_avoided: true` and cites M002 as the required validator if a later slice introduces generated candidates.
8. **Emit compact diagnostics.** Write a tracked JSON manifest with counts, result states, filter trace summary, citation validation status, diagnostic code inventory, non-authoritative flag, redaction status, and gate disposition.

## Generated-query decision

S03 intentionally avoids generated query execution.

Rationale:

- The slice goal can be proven with deterministic fixture cases from S02.
- M002 requires generated candidates to be validated before any execution-like step, including evidence-path and temporal constraints.
- Introducing generated Cypher would add provider/output variability and a larger safety surface that is unnecessary for the citation-bound integration spine.

If a later task introduces query-like candidates, they must be treated as opaque candidate strings, validated through an M002-compatible deterministic validator, and rejected before execution unless they are read-only, schema-grounded, evidence-returning, temporally constrained, and bounded by `LIMIT`.

## Proof ceiling

The S03 proof ceiling is **fixture-backed integration proof** for the narrow subset: ontology filter handling, temporal filter handling, citation/evidence ID preservation, scoped no-answer handling, and fail-closed diagnostics.

It does not prove runtime FalkorDB behavior, graph-vector/HNSW behavior, hybrid retrieval, product retrieval quality, legal-answer correctness, parser completeness, ontology quality, generated-Cypher generation quality, BFO/GOST/OWL/Common Logic conformance, or pilot-scale readiness.

## Expected diagnostics

The proof command should expose these safe diagnostic surfaces:

- `schema_version` and `proof_id`;
- repository-relative fixture and report paths;
- total, accepted, rejected, blocked, and mismatch counts;
- `result_states` counts;
- `filter_trace_summary` with ontology matched, unsupported filter, temporal excluded, ambiguous candidate, and scoped no-answer counts;
- `citation_validation_status` with validated, failed, skipped, and missing-citation counts;
- `query_safety` with generated query execution avoided and M002 validator requirement for future query candidates;
- `diagnostic_code_inventory` using stable proof-local or shared-validator codes;
- `redaction_ok` and `non_authoritative` booleans;
- `gate_disposition` stating the bounded proof passed or failed while R035 and the broader gate remain open until later evidence.

## Non-claims

This design does not validate R035.
This design does not satisfy `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` by itself.
This design does not prove product retrieval quality.
This design does not prove legal-answer correctness.
This design does not prove parser completeness.
This design does not prove FalkorDB production behavior.
This design does not prove graph-vector, HNSW, or hybrid retrieval behavior.
This design does not prove generated-Cypher safety beyond requiring the M002 policy before any future generated-query execution.
This design does not prove BFO, GOST, OWL, Common Logic, LKIF, RusLegalCore, Akoma Ntoso, LegalDocML, or FRBR conformance.
This design does not prove 1000-document or pilot-scale readiness.
This design does not make LLM output legal authority.

## Verification expectation

The design note is verified by content assertions for: flow steps, proof ceiling, generated-query decision, non-claims, expected diagnostics, citation/evidence validation, ontology filter handling, and temporal filter handling.
