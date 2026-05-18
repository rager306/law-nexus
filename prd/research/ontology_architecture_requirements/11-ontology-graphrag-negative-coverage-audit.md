---
requirement: R035
gate: GATE-ONTOLOGY-GRAPHRAG-INTEGRATION
status: negative-coverage-audit
owner: M020-ujbffl/S04
source_contract: prd/research/ontology_architecture_requirements/08-ontology-graphrag-proof-contract.md
non_authoritative: true
created_at: 2026-05-18
---

# Ontology GraphRAG Negative Coverage Audit

## Purpose

This audit compares the S01 required negative cases with the S02 fixture proof and S03 citation-bound integration proof surfaces before any R035 lifecycle wording update. It is a residual-risk map only; it does not validate R035, satisfy `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`, prove product retrieval quality, prove legal-answer correctness, prove parser completeness, prove FalkorDB production behavior, prove graph-vector/HNSW behavior, or make LLM output authoritative.

## Inputs reviewed

| Input | Review role |
| --- | --- |
| `prd/research/ontology_architecture_requirements/08-ontology-graphrag-proof-contract.md` | S01 required negative case table and proof ceiling. |
| `prd/research/ontology_architecture_requirements/09-ontology-graphrag-fixture-contract.md` | S02 fixture contract and expected fail-closed case classes. |
| `prd/research/ontology_architecture_requirements/10-ontology-graphrag-integration-proof-design.md` | S03 integration proof design and generated-query boundary. |
| `prd/research/ontology_architecture_requirements/ontology_graphrag_proof_cases.json` | Tracked S02 negative and accepted cases. |
| `prd/research/ontology_architecture_requirements/ontology_graphrag_integration_proof.json` | S03 durable report with case traces, diagnostics, query safety, and gate disposition. |
| `scripts/verify-ontology-graphrag-proof.py` | S02 verifier for local fixture shape, diagnostics, redaction, and shared retrieval validator integration. |
| `scripts/verify-ontology-graphrag-integration-proof.py` | S03 verifier for end-to-end summary, query-safety metadata, and report persistence. |
| `tests/test_ontology_graphrag_proof.py` and `tests/test_ontology_graphrag_integration_proof.py` | Existing regression coverage for fixture and integration surfaces. |
| `tests/test_ontology_graphrag_negative_guardrails.py` | S04 guardrail coverage for generated-query omissions and positive overclaim wording. |

## S01 negative case coverage table

| S01 negative case | Status | Evidence | Rationale and residual risk |
| --- | --- | --- | --- |
| Inactive or wrong-edition evidence leaks into current-status retrieval | Covered | `CASE-M020-OG-INACTIVE-OR-WRONG-EDITION-EXCLUDED`; diagnostics `temporal_filter_excluded`, `wrong_edition`; S03 trace rejects the case. | The tracked fixture and integration report fail closed for wrong edition under `current_only`. Residual risk: this is fixture-backed, not proof of complete temporal conflict handling over production data. |
| Output lacks required citation or evidence identifiers | Covered | `CASE-M020-OG-MISSING-CITATION-OR-EVIDENCE-ID`; shared validator diagnostic `missing_required_field`; S03 citation status records one missing-citation failure. | Citation or evidence ID loss is delegated to the shared retrieval output validator rather than a forked checker. Residual risk: only tracked proof-local envelopes are covered. |
| Ontology filter references unsupported gate or class | Covered | `CASE-M020-OG-UNSUPPORTED-ONTOLOGY-FILTER`; diagnostic `unsupported_ontology_filter`; actual result `blocked_unsupported_filter`. | Unsupported ontology vocabulary is blocked instead of widened silently. Residual risk: the allowed vocabulary remains proof-local and is not a final ontology schema. |
| Generated query omits evidence path or temporal constraint | Covered by S04 guardrail | S03 records `generated_query_execution_avoided: true`; S04 test `test_generated_query_missing_evidence_path_and_temporal_constraint_fails_closed` expects `E_EVIDENCE_REQUIRED` and `E_TEMPORAL_REQUIRED`. | S03 had a safe avoidance boundary, but no executable negative assertion for unsafe generated candidates. S04 closes that test gap by failing closed when optional generated-query candidates omit `EvidenceSpan`/`SourceBlock` or as-of temporal predicates. Residual risk: this is a compact guardrail, not a complete M002 generated-Cypher validator. |
| Candidate set is ambiguous | Covered | `CASE-M020-OG-AMBIGUOUS-CANDIDATE-SET`; diagnostic `ambiguous_candidate_set`; result `rejected`. | The verifier rejects multiple ontology-and-temporal matches without arbitrary tie-breaking. Residual risk: ambiguity detection is fixture-shaped and does not prove production ranking quality. |
| Scoped no-answer contains hidden citations or global legal absence wording | Covered | `CASE-M020-OG-SCOPED-NO-ANSWER`; diagnostic `scoped_no_answer`; shared validator result `accepted_scoped_no_answer`; no citations in trace. | Scoped no-answer stays explicit and citation-free. Residual risk: wording checks are bounded to the validator shape and do not exhaustively lint all future prose. |
| Raw legal text, prompts, provider payloads, raw vectors, raw FalkorDB rows, secrets, or legal advice appear in artifacts | Covered | `CASE-M020-OG-FORBIDDEN-PAYLOAD-FIELD`; S02/S03 redaction checks; S03 redacts forbidden mismatch paths; S04 generated-query tests assert raw query text is not persisted in failure summary. | Forbidden payload keys are detected and durable reports avoid unsafe payload echoing. Residual risk: string-content scanning is intentionally conservative and should remain paired with schema-level forbidden-field checks. |
| Proof report claims product retrieval quality, legal correctness, parser completeness, FalkorDB production behavior, graph-vector/HNSW behavior, pilot readiness, or LLM authority | Covered by S04 guardrail | S01/S02/S03 non-claims are present; S03 gate disposition keeps R035 active; S04 test `test_positive_overclaim_wording_fails_gate_disposition_without_mutating_non_claims` expects `overclaim_wording_detected`. | Before S04, overclaim safety was mostly documented through non-claims and gate disposition. S04 adds an executable positive-wording guardrail for optional proof report claims. Residual risk: phrase matching is a fail-closed supplement, not a natural-language proof of all possible future wording. |

## Diagnostic inventory observed

The S02/S03 proof spine exposes stable diagnostics for the already tracked cases:

- `ontology_filter_matched`
- `temporal_filter_excluded`
- `wrong_edition`
- `unsupported_ontology_filter`
- `missing_required_field`
- `ambiguous_candidate_set`
- `scoped_no_answer`
- `forbidden_payload_field`

S04 extends the negative-check surface with generated-query and wording diagnostics when optional unsafe inputs are present:

- `E_EVIDENCE_REQUIRED`
- `E_TEMPORAL_REQUIRED`
- `E_WRITE_OPERATION`
- `overclaim_wording_detected`

## Unsafe wording risks

The safe lifecycle wording remains narrow:

- acceptable: bounded fixture-backed integration proof for ontology filter handling, temporal filter handling, citation/evidence ID preservation, scoped no-answer handling, and fail-closed diagnostics;
- not acceptable: R035 broadly validated, full gate satisfied, product retrieval quality proven, legal correctness proven, parser completeness proven, FalkorDB production behavior proven, graph-vector/HNSW behavior proven, pilot readiness proven, or LLM output treated as legal authority.

## Residual risks before lifecycle update

1. The proof spine is still fixture-backed and non-authoritative; it should not be promoted to runtime-smoke or production evidence.
2. The generated-query guardrail is a compact S04 regression surface, not the full M002 validator implementation.
3. The overclaim wording guardrail detects explicit positive claims but does not replace human review of final S05 lifecycle prose.
4. The S05 recommendation must keep R035 active unless it cites exactly bounded evidence and leaves unrelated R035 gates open.

## Audit conclusion

All S01 required negative cases are named and have a fail-closed surface after S04 guardrails. No case is marked not applicable. The generated-query and overclaim rows were the main gaps relative to an executable negative proof surface; they are now covered as S04 guardrail tests while preserving the proof ceiling and non-authoritative boundary.
