---
source_gap_analysis: "prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md"
source_registry:
  - "prd/architecture/architecture_items.jsonl"
  - "prd/architecture/architecture_edges.jsonl"
  - "prd/architecture/architecture_report.md"
status: "planning taxonomy"
verification_note: "This ladder is a planning and proof-gating artifact. It does not validate parser completeness, legal correctness, ontology conformance, FalkorDB production behavior, retrieval quality, or LLM authority."
---

# Ontology Adoption Ladder

## 1. Purpose and boundary

This ladder stages how LegalGraph Nexus may use external ontology standards and research-derived ontology requirements without replacing the current project-local LegalGraph core prematurely.

The current architecture registry is a derived, non-authoritative planning graph. It records requirements, evidence, gaps, and gates, but it is not runtime/product proof. Therefore this ladder treats Akoma Ntoso / LegalDocML, FRBR, LKIF, RusLegalCore, BFO, GOST R 59798-2021, OWL 2, Common Logic, ontology GraphRAG, and large-pilot claims as reference, compatibility, candidate, deferred, or proof-gated layers unless a future gate supplies source-backed and runtime-backed evidence.

Central rule:

> Keep the project-local LegalGraph core as the internal contract. Promote external standards only through explicit evidence, non-claims, and promotion criteria.

Source-priority boundary:

> The current source priority remains Consultant-first under D040, D041, and D042. Garant remains a deferred/supporting source path, not a co-primary driver for current parser or ontology planning. RusLawOD is reference/future-corpus material only: it is not the primary corpus, does not supersede Consultant-first evidence, and must not change corpus priority unless a future explicit human decision and named proof gate promote it.

## 2. Adoption levels

| Level | Name | Meaning | Typical status |
|---|---|---|---|
| L0 | Core contract | Project-local canonical records and guardrails that downstream work may depend on now. | Adopted planning core, still non-product unless backed by implementation proof. |
| L1 | Compatibility projection | Optional export/import or mapping shape that preserves the L0 core and does not replace it. | Compatibility target. |
| L2 | Reference identity layer | A standard used to name, compare, or audit identity concepts without claiming full conformance. | Reference layer. |
| L3 | Candidate semantic layer | A proposed semantic ontology or extraction layer that may enrich graph meaning after evaluation. | Candidate hypothesis. |
| L4 | Formal alignment layer | A formal upper ontology, logic, or standards-conformance layer used for long-term interoperability. | Proof-gated formal alignment. |
| L5 | Deferred proof area | A valuable claim or capability that is explicitly not current scope until source/runtime/legal proof exists. | Deferred gate. |
| L6 | Rejected-as-is assumption | A research or prior-art assumption that conflicts with current evidence, source priority, or capability boundaries. | Not adopted as stated. |

## 3. Level definitions

### L0 — Core contract

**Meaning.** The internal LegalGraph contract that should remain stable while standards are evaluated around it. Current planning vocabulary includes `SourceDocument`, `SourceBlock`, `LegalUnit`, `ActEdition`, `EvidenceSpan`, and candidate `NormStatement` records, plus source-of-truth, temporal, provenance, citation, and non-authoritative-answer guardrails.

**Allowed evidence.** Project requirements, architecture registry items and edges, verifier output for registry consistency, source-backed parser records, bounded fixture proofs, real-document parser evidence, retrieval output ID validation, and explicit GSD summaries that state their boundaries.

**Non-claims.** L0 does not claim full product implementation, legal correctness, full parser coverage, production graph scale, ontology conformance, generated-Cypher safety beyond proven gates, or authoritative legal advice.

**Promotion criteria into L0.** A concept may become L0 only when it has stable record semantics, source-span or source-document provenance, temporal behavior, validation rules, downstream consumer need, and at least bounded implementation/proof evidence. Legal or semantic assertions require review/proof status and failure behavior.

**Current examples.** Source-backed legal units and provenance, temporal edition/status semantics, evidence spans, citation-bound retrieval outputs, and non-authoritative LLM answer boundaries.

### L1 — Compatibility projection

**Meaning.** A mapping or projection to an external standard for interoperability, import/export, comparison, or future migration. It must be optional and reversible enough that L0 remains the internal source of truth.

**Allowed evidence.** Mapping tables, fixture transformations, export/import smoke tests, schema comparison notes, and examples showing that source identifiers and evidence spans survive the projection.

**Non-claims.** L1 does not claim that the external standard is the canonical internal model, that all source documents can be represented losslessly, or that the project is conformant to the standard.

**Promotion criteria.** Promotion requires round-trip or one-way projection tests on representative current sources, documented loss/caveat fields, preserved legal-unit IDs and source spans, and no breakage of L0 consumers.

**Current examples.** Akoma Ntoso / LegalDocML-compatible structural output and optional FRBR-shaped export of act/version/source-file identity.

### L2 — Reference identity layer

**Meaning.** A standard used as an analytic lens for identity, naming, temporal grouping, or provenance separation. It clarifies concepts but does not by itself impose full implementation conformance.

**Allowed evidence.** Conceptual mapping notes, registry gap analysis, source examples showing identity separation, and bounded tests that distinguish abstract act, edition/version, manifestation/file, and item/source instance.

**Non-claims.** L2 does not prove full FRBR, Akoma Ntoso, or LegalDocML compliance; does not settle all Russian legal identity edge cases; and does not validate inactive/superseded filtering beyond specific gates.

**Promotion criteria.** Promotion to L0/L1 requires stable IDs, edition/version rules, collision handling, source provenance, and regression tests over real project source types.

**Current examples.** FRBR-like distinction between `LegalAct`/Work, `ActEdition`/Expression, `SourceDocument`/Manifestation or Item boundary, and `LegalUnit` within an edition.

### L3 — Candidate semantic layer

**Meaning.** A proposed ontology layer that enriches legal meaning, such as obligations, permissions, prohibitions, hierarchy, competence, interpretation, or domain-specific legal classes.

**Allowed evidence.** Labeled examples, source-span provenance, extraction evaluation, precision/recall reports, ambiguity handling, negation tests, review workflows, and bounded graph-query examples.

**Non-claims.** L3 does not make extracted norms legally authoritative, does not validate legal correctness, does not prove machine-learning extractor quality, and does not allow unreviewed semantic assertions to override source text.

**Promotion criteria.** Promotion requires an explicit proof gate with source-span provenance for every assertion, negative tests for negation and ambiguous modal verbs, confidence/review status, legal-domain review criteria, and deterministic fallback/fail-closed behavior.

**Current examples.** LKIF/deontic mapping, `NormStatement`, obligation/permission/prohibition extraction, RusLegalCore scope proposals, legal source hierarchy, judicial interpretation links, and collision-maxim explanations.

### L4 — Formal alignment layer

**Meaning.** A high-rigor alignment to formal ontology, logic, or standards frameworks for interoperability and reasoning. This layer should review and constrain models only after the L0/L1/L3 evidence path is stable.

**Allowed evidence.** Primary-source standards review, formal mapping documents, conformance tests, reasoner/procedure smoke evidence where relevant, failure-mode notes, and documented scope exclusions.

**Non-claims.** L4 does not claim BFO, GOST R 59798-2021, OWL 2, or Common Logic conformance without primary-source verification and executable checks. It also does not block parser or retrieval proof unless the milestone explicitly makes it a gate.

**Promotion criteria.** Promotion requires verified standard text, a bounded conformance subset, explicit examples, tool/runtime compatibility proof, and a rollback path if formal alignment conflicts with source-backed legal evidence.

**Current examples.** BFO/GOST alignment review, OWL 2/Common Logic research, formal category checks, and long-term interoperability constraints.

### L5 — Deferred proof area

**Meaning.** A capability, source assumption, runtime behavior, or scale claim that may matter later but lacks current proof or is outside the current milestone’s scope.

**Allowed evidence.** Research notes, gap analysis, planned gate definitions, smoke-test designs, and explicit caveats that the claim is unproven.

**Non-claims.** L5 does not count as adopted architecture, product readiness, production performance, source coverage, or legal validation.

**Promotion criteria.** Promotion requires a named gate, success/failure criteria, representative real inputs, diagnostics, and recorded evidence that closes the specific uncertainty.

**Current examples.** 1,000-document pilot, production-scale FalkorDB behavior, graph-vector execution details, HNSW behavior, full ontology GraphRAG quality, complete parser coverage, and generated-Cypher safety beyond existing bounded gates.

### L6 — Rejected-as-is assumption

**Meaning.** A research, prior-art, or tool-specific assumption that must not be adopted in its current form because it conflicts with current source priority, proof boundaries, capability evidence, or project guardrails.

**Allowed evidence.** Gap analysis, memory/gotcha records, source-priority decisions, failed or absent proof, and contradiction with current architecture guardrails.

**Non-claims.** L6 is not a permanent rejection of the underlying topic. It rejects the assumption as stated. A narrower version may re-enter L1-L5 with evidence.

**Promotion criteria.** Re-entry requires reformulation into a source-agnostic or proof-gated claim, named evidence requirements, and confirmation that it no longer overrides the LegalGraph core.

**Current examples.** RusLawOD as the immediate primary corpus, RuBERT-CRF as a required extractor before evaluation, single-transaction graph+vector behavior without database proof, and BFO/Common Logic as an immediate MVP blocker.

## 4. Initial classification of standards and claims

| Standard or claim | Ladder level | Rationale | Caveats / required proof |
|---|---|---|---|
| Project-local LegalGraph core (`SourceDocument`, `SourceBlock`, `LegalUnit`, `ActEdition`, `EvidenceSpan`) | L0 core contract | Matches current evidence-first architecture direction and preserves source/provenance boundaries. | Still planning/runtime-bounded; product completeness requires implementation proof. |
| Akoma Ntoso | L1 compatibility projection | Useful as a structural normalization/export shape while preserving the current parser records as the internal source of truth. | Needs representative projection tests, documented loss/caveat fields, and proof that source identifiers and evidence spans survive the projection. |
| FRBR | L2 reference identity layer | Clarifies Work/Expression/Manifestation/Item separation for act, edition, source file, and source instance without forcing full conformance. | Needs Russian legal identity edge-case tests and stable ID rules before becoming core semantics. |
| LKIF | L3 candidate semantic layer | Relevant for obligations, permissions, prohibitions, negation, and legal-role semantics around candidate norm statements. | Requires source-span provenance, extraction evaluation, negation tests, ambiguity handling, and legal review gates. |
| RusLegalCore | L3 candidate semantic layer | Useful working name for Russian legal hierarchy, competence, judicial interpretation, and domain-specific legal classes. | Scope must be bounded; must not imply legal correctness, authoritative reasoning, or complete Russian-law coverage. |
| BFO | L4 formal alignment layer | Valuable as a formal category review lens and long-term interoperability target once the evidence-first core is stable. | Must be verified against primary sources; should not block current parser/retrieval proofs or be treated as MVP conformance. |
| GOST R 59798-2021 | L4 formal alignment layer | Potential Russian standards alignment reference for ontology engineering and formal terminology. | Requires primary-source review and scoped conformance claims before it influences architecture gates. |
| OWL 2 | L4 formal alignment layer | Possible formal ontology/interchange layer for a future bounded subset of LegalGraph semantics. | Requires tool/runtime proof, conformance subset definition, and rollback if reasoning conflicts with source-backed legal evidence. |
| Common Logic | L4 formal alignment layer | Possible high-rigor formal logic interchange or review layer for future interoperability. | Requires primary-source verification, executable examples, and proof that it is not an immediate implementation blocker. |
| Legal collision maxims (`lex superior`, `lex specialis`, `lex posterior`) | L3 candidate semantic layer | Extends temporal conflict handling into explainable norm-priority reasoning. | Requires explicit conflict-policy gate and examples; cannot silently decide legal outcomes. |
| Ontology GraphRAG | L5 deferred proof area | Directionally aligned with graph-constrained retrieval, but retrieval quality, inactive-version filtering, and runtime behavior are unproven. | Needs retrieval benchmarks, citation checks, failure diagnostics, and generated-answer non-authority checks. |
| HNSW/vector claims | L5 deferred proof area / L6 as stated for unverified graph-vector guarantees | Depends on actual database capability, index behavior, and runtime proof rather than ontology research text alone. | Must be verified with FalkorDB-specific evidence before claiming graph-vector execution, HNSW behavior, or transaction guarantees. |
| RuBERT-CRF | L6 rejected as-is assumption | Too implementation-specific before extractor evaluation and conflicts with deterministic-first, proof-gated adoption posture. | May re-enter as a candidate extractor after benchmark design, source-span evaluation, and failure-mode diagnostics. |
| RusLawOD | L6 rejected as-is assumption | Conflicts with current Consultant-first source-priority decisions when framed as the immediate primary corpus; Garant remains deferred/supporting, and RusLawOD is reference/future-corpus material only. | Does not supersede Consultant-first evidence and is not primary corpus unless a future explicit human decision changes source priority and a named proof gate proves source compatibility, corpus quality, and downstream evidence preservation. |
| 1000-document pilot | L5 deferred proof area | Useful readiness target beyond current bounded fixtures and tracer proofs. | Requires corpus definition, run logs, SLA metrics, parser anomaly triage, and repeatable success/failure criteria. |

## 5. Promotion workflow

1. **State the candidate layer.** Name the standard, scope, expected value, and current ladder level.
2. **Record allowed evidence.** Identify source artifacts, fixtures, real documents, runtime checks, legal review criteria, or primary standards needed.
3. **Record non-claims.** Explicitly state what the candidate does not prove.
4. **Define a proof gate.** Include success criteria, negative tests, diagnostics, and rollback/failure behavior.
5. **Run bounded proof.** Use representative current project sources before broadening to external corpora or production scale.
6. **Promote narrowly.** Promote only the proven subset. Leave unproven behavior at L3-L5 or reject it as stated at L6.

## 6. Anti-overclaim language rules

Use these phrases for unproven layers:

- "candidate layer"
- "compatibility projection"
- "reference mapping"
- "proof-gated hypothesis"
- "deferred proof area"
- "not adopted as stated"
- "bounded evidence only"

Avoid these phrases unless a future proof gate explicitly supports them:

- "validated architecture"
- "production-ready"
- "complete parser support"
- "legally correct"
- "authoritative legal reasoning"
- "full ontology conformance"
- "guaranteed graph-vector behavior"
- "single-transaction guarantee"

## 7. Slice-level caveat

This ladder records rationale and caveats for each standard so future agents can see why external ontology standards were not adopted directly into the core contract. It intentionally favors staged adoption over broad standards replacement because the current project state is evidence-first planning with bounded proofs, and it does not claim product architecture validation.
