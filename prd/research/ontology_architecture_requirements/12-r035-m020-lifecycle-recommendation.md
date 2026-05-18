---
requirement: R035
gate: GATE-ONTOLOGY-GRAPHRAG-INTEGRATION
milestone: M020-ujbffl
slice: S05
status: lifecycle-recommendation
recommendation: remains-active-with-bounded-m020-note
non_authoritative: true
created_at: 2026-05-17
---

# R035 M020 Lifecycle Recommendation

## Decision

R035 should **remain active** after M020. The supported lifecycle outcome is **not** broad validation of R035 and **not** closure of `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`.

The requirement may receive only a narrow M020 lifecycle note: M020 produced bounded, fixture-backed integration evidence for the ontology GraphRAG subset covering ontology filter handling, temporal filter handling, citation or evidence identifier preservation, scoped no-answer handling, fail-closed diagnostics, redaction safety, and overclaim guardrails.

Recommended lifecycle wording for the later `.gsd/REQUIREMENTS.md` update:

> M020-ujbffl produced bounded fixture-backed integration evidence for the `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` subset: ontology and temporal filters over proof-local source-backed cases, citation/evidence ID preservation, scoped no-answer behavior, fail-closed diagnostics, redaction safety, generated-query execution avoided, and overclaim guardrails. R035 remains active; this does not validate R035 broadly, satisfy the full gate, prove product retrieval quality, legal-answer correctness, parser completeness, FalkorDB production behavior, graph-vector/HNSW behavior, generated-Cypher runtime safety, formal ontology conformance, or pilot-scale readiness.

## Evidence Used

| Evidence | What it supports | Boundary |
| --- | --- | --- |
| `.gsd/milestones/M020-ujbffl/slices/S02/S02-SUMMARY.md` | S02 created deterministic source-backed proof fixtures with ontology and temporal filter behavior, evidence identifier preservation, and non-authoritative fail-closed cases. | Fixture-local proof only; it does not establish production retrieval quality, broader ontology coverage, or R035 validation. |
| `.gsd/milestones/M020-ujbffl/slices/S03/S03-SUMMARY.md` | S03 connected the S02 fixture surface to bounded citation/evidence validation and produced a durable integration proof report. | Fixture-backed integration proof only; generated query execution was intentionally avoided. |
| `.gsd/milestones/M020-ujbffl/slices/S04/S04-SUMMARY.md` | S04 added negative guardrails, overclaim checks, and lifecycle-safe verification, and explicitly directed S05 to keep R035 active. | Verification-only hardening; it does not convert the proof into runtime-smoke, product, or pilot evidence. |
| `prd/research/ontology_architecture_requirements/08-ontology-graphrag-proof-contract.md` | Establishes that R035 remains active unless S05 can point to tracked evidence for the exact M020 subset, and that even a subset note must not imply broad validation. | The contract itself is not proof and does not satisfy the gate. |
| `prd/research/ontology_architecture_requirements/10-ontology-graphrag-integration-proof-design.md` | Defines the S03 proof ceiling as fixture-backed integration proof for ontology filters, temporal filters, citation/evidence preservation, scoped no-answer handling, and fail-closed diagnostics. | Explicitly does not validate R035 or satisfy the full gate by itself. |
| `prd/research/ontology_architecture_requirements/11-ontology-graphrag-negative-coverage-audit.md` | Confirms required negative cases are covered or bounded before lifecycle wording changes and forbids broad promotion language. | Residual risks remain because the proof spine is fixture-backed and non-authoritative. |
| `prd/research/ontology_architecture_requirements/ontology_graphrag_integration_proof.json` | Records `proof_level=fixture-backed integration proof`, `gate_disposition=bounded_fixture_integration_passed_gate_remains_open`, `r035_lifecycle_disposition=remains_active_bounded_s03_evidence_only`, `non_authoritative=true`, `redaction_ok=true`, and `generated_query_execution_avoided=true`. | Counts and diagnostics prove only the bounded proof fixture/report behavior. |

## Proof Level

The exact supported proof level is **fixture-backed integration proof** for the M020 subset.

This is stronger than a static research note or isolated unit assertion because S03 consumes the proof cases, validates citation/evidence identifiers, reports gate disposition, and preserves negative diagnostics. It is weaker than runtime-smoke, benchmark validation, production observation, legal-answer quality validation, parser completeness validation, FalkorDB production validation, or pilot-scale validation.

## Runtime Prerequisite Diagnostics

Runtime prerequisite diagnostics are separate boundary checks. They may inform future proof readiness, but they do **not** promote R035, close `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`, validate product retrieval quality, validate parser completeness, prove legal-answer correctness, or prove FalkorDB production behavior.

| Diagnostic | Current disposition | Boundary |
| --- | --- | --- |
| Local retrieval / embedding runtime prerequisite | `confirmed_runtime` for the approved local/open-weight retrieval runtime boundary, recorded only as a non-secret status class. | Bounded prerequisite diagnostic only; it does not validate R035, product retrieval quality, representative corpus quality, parser completeness, legal-answer correctness, production FalkorDB behavior, or `GATE-G011`. It must not persist secrets, provider payloads, raw legal text, raw queries, raw vectors, or environment-specific absolute paths. |
| LegalGraph-shaped FalkorDB local runtime proof | `blocked/follow-up` prerequisite in this environment unless a fresh local smoke proof is obtained and reviewed separately. | Separate FalkorDB runtime-smoke work only; blocked/unavailable status is not negative R035 evidence and not R035 validation. A future passing smoke may prove only bounded synthetic graph mechanics unless explicitly backed by stronger product/runtime evidence. |

## Non-Claims

This recommendation does **not** claim any of the following:

- R035 is broadly validated.
- `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` is fully satisfied.
- Product retrieval quality is proven.
- Legal-answer correctness is proven.
- Parser completeness is proven.
- FalkorDB production behavior is proven.
- Graph-vector, HNSW, hybrid retrieval, or single-transaction graph-plus-vector semantics are proven.
- Generated-Cypher runtime safety is proven beyond the existing policy boundary; M020 avoided generated-query execution.
- BFO, GOST, OWL, Common Logic, LKIF, RusLegalCore, Akoma Ntoso, LegalDocML, or FRBR conformance is proven.
- 1000-document or pilot-scale readiness is proven.
- LLM output is legal authority.

## Remaining R035 Gates and Follow-Up Owners

R035 remains active because the following gates remain open or outside the M020 proof subset:

| Remaining gate or proof area | Required future evidence before promotion |
| --- | --- |
| Full `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` satisfaction | Integration proof over the intended retrieval surface, retrieval benchmark evidence, generated-query safety checks if query generation is introduced, runtime smoke where applicable, citation validation, negative tests, query/filter traces, benchmark metrics, and failed-query diagnostics. |
| Product retrieval quality / `GATE-G011` relation | Representative retrieval quality metrics and acceptance criteria under local/open-weight constraints, not just proof-local fixture behavior. |
| Real parser and retrieval readiness / `GATE-G008` relation | Real-source parser/retrieval readiness evidence beyond fixture-local source-backed cases. |
| FalkorDB production behavior / `GATE-G015` relation | Runtime migration/load/query-plan evidence when ontology claims depend on production-like graph behavior. |
| Graph-vector, HNSW, hybrid retrieval, and graph-plus-vector semantics | Dedicated runtime-smoke or stronger evidence with safe diagnostics and no raw vectors or raw legal text. |
| Formal ontology or standards conformance | Primary-standard review and bounded formal mapping for any Akoma Ntoso, FRBR, LKIF, RusLegalCore, BFO, GOST, OWL, or Common Logic promotion. |
| Generated-Cypher execution | Read-only, evidence-returning, temporal-aware generated-query safety proof before execution-like behavior is promoted. |
| Pilot or 1000-document readiness | Repeatable corpus manifest, run logs, anomaly triage, metrics, quality sampling, and failure diagnostics. |

## Recommendation for S05 Requirement Update

When S05 updates `.gsd/REQUIREMENTS.md`, keep R035 under **Active**. Update only the validation or notes text to cite M020 as bounded subset advancement.

The update should include these terms or equivalents:

- `M020-ujbffl`
- `bounded fixture-backed integration evidence`
- `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION subset`
- `ontology and temporal filters`
- `citation/evidence ID preservation`
- `generated-query execution avoided`
- `overclaim guardrails`
- `R035 remains active`
- explicit non-claims for product retrieval quality, legal correctness, parser completeness, FalkorDB production behavior, graph-vector/HNSW behavior, formal ontology conformance, and pilot-scale readiness

Do not move R035 to Validated unless future evidence closes all unrelated R035 gates and the full gate contract, not just this M020 subset.
