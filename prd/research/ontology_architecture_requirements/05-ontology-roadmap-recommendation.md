---
source_gap_analysis: "prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md"
source_evidence_intake: "prd/research/ontology_architecture_requirements/05-bounded-evidence-intake.md"
source_adoption_ladder: "prd/research/ontology_architecture_requirements/05-ontology-adoption-ladder.md"
source_proof_gates: "prd/research/ontology_architecture_requirements/05-ontology-proof-gates.md"
source_registry_plan: "prd/research/ontology_architecture_requirements/05-registry-integration-plan.md"
status: "roadmap recommendation; implementation deferred until proof gates are accepted"
verification_note: "This roadmap is an architecture-review artifact. It does not validate parser completeness, legal correctness, ontology conformance, FalkorDB production behavior, graph-vector behavior, retrieval quality, generated-Cypher safety, or LLM authority."
---

# Ontology Roadmap Recommendation

## 1. Recommendation summary

Keep the project-local LegalGraph core as the internal contract and use external ontology standards as reference, compatibility, or proof-gated layers. M017 evidence supports a roadmap for bounded architecture intake, not immediate implementation of Akoma Ntoso, FRBR, LKIF, RusLegalCore, BFO, GOST, OWL, Common Logic, graph-vector storage, HNSW, or pilot-scale readiness claims.

Recommended next posture:

1. **Adopt now:** evidence-first LegalGraph core semantics that are already aligned with current registry guardrails: source-backed legal units, temporal status, provenance, citation-bound retrieval output, and non-authoritative LLM answers.
2. **Use as reference/compatibility:** FRBR and Akoma Ntoso / LegalDocML should shape optional mapping and identity vocabulary without replacing current parser records.
3. **Keep proof-gated:** LKIF/deontic mapping, RusLegalCore, legal collision maxims, and ontology-aware GraphRAG require named gates and evidence before downstream reliance.
4. **Defer heavy/runtime claims:** BFO/GOST/OWL/Common Logic formal conformance, graph-vector/HNSW/FalkorDB execution behavior, and a 1000-document pilot remain future proof areas.
5. **Do not adopt as-is:** RusLawOD as primary corpus, RuBERT-CRF as required extractor, single-transaction graph+vector guarantees, and BFO/Common Logic as immediate blockers are rejected in their current formulation.

## 2. Roadmap classification matrix

Each major R035 ontology area appears once in the table below. The category is the recommended current roadmap bucket; rationale and source links explain why the area belongs there now.

| R035 / roadmap area | Category | Rationale | Source links |
|---|---|---|---|
| Project-local LegalGraph core | Adopt now | This is the safest internal contract because it preserves `SourceDocument`, `SourceBlock`, `LegalUnit`, `ActEdition`, `EvidenceSpan`, candidate `NormStatement`, source, temporal, provenance, citation, and non-authority guardrails while external standards remain under review. | `05-architecture-gap-analysis-against-current-registry.md` §2, §6.3, §8; `05-ontology-adoption-ladder.md` L0 |
| Akoma Ntoso / LegalDocML | Compatibility projection | Use as optional structural export/projection or comparison target only. It should not replace source-specific parser records until projection tests preserve legal-unit IDs, evidence spans, temporal metadata, and unmapped-field diagnostics. | Gap analysis §3.1, §4.2, §6.3; adoption ladder L1; `GATE-AKOMA-FRBR-NORMALIZATION` |
| FRBR legal identity | Reference layer | FRBR is useful vocabulary for separating abstract act/work, edition/expression, source manifestation, and file/item boundaries, but full conformance and Russian legal identity edge cases remain unproven. | Gap analysis §2.2, §3.2; adoption ladder L2; `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` |
| LKIF / deontic mapping | Proof-gated candidate | Obligation, permission, prohibition, exceptions, negation, and modal-verb handling require benchmark evidence, source-span provenance, review status, and failure behavior before semantic assertions can influence retrieval or reasoning. | Gap analysis §3.3; proof gates `GATE-DEONTIC-MAPPING-PROOF`; adoption ladder L3 |
| RusLegalCore domain ontology | Proof-gated candidate | Treat as a working-name candidate for Russian legal hierarchy, competence, judicial interpretation, and legal-domain classes. Scope, exclusions, competency questions, and source evidence must be proven before registry promotion. | Gap analysis §3.4; proof gates `GATE-RUSLEGALCORE-SCOPE`; adoption ladder L3 |
| Legal collision maxims | Proof-gated candidate | Current temporal conflict policy is narrower than full legal collision reasoning over `lex superior`, `lex specialis`, `lex posterior`, and supersession. Any priority explanation must preserve uncertainty, citations, source hierarchy evidence, and review-required outcomes. | Gap analysis §3.6; proof gates `GATE-LEGAL-COLLISION-POLICY`; adoption ladder L3 |
| BFO / GOST R 59798-2021 formal alignment | Defer | Use as a future standards-review and formal-alignment workstream after the LegalGraph core and projection/semantic layers have bounded evidence. Primary-source verification and conformance subset checks are required before adoption. | Gap analysis §3.5, §4.4; proof gates `GATE-BFO-GOST-ALIGNMENT`; adoption ladder L4 |
| OWL 2 / Common Logic formal reasoning | Defer | These may support long-term interoperability or formal reasoning, but they are too heavy for current scope and need executable examples, tool/runtime compatibility, and rollback rules before they can constrain product architecture. | Gap analysis §3.5, §7; proof gates `GATE-BFO-GOST-ALIGNMENT`; adoption ladder L4 |
| Ontology-driven GraphRAG | Proof-gated candidate | Directionally aligned with graph-constrained retrieval, inactive-version filtering, citation-bound answers, and generated-query safety, but retrieval quality and integration behavior remain unproven. | Gap analysis §2.3, §4.5; proof gates `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`; adoption ladder L5 |
| Graph-vector / HNSW / FalkorDB graph-vector behavior | Defer | Runtime behavior, graph/vector index support, HNSW behavior, production-scale FalkorDB behavior, and single-transaction graph+vector guarantees must come from FalkorDB-specific capability/runtime evidence, not ontology research text. | Gap analysis §4.5; bounded evidence intake non-claims; proof gates `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`, `GATE-1000-DOC-PILOT` |
| Pilot-scale / 1000-document readiness | Defer | A 1000-document pilot is a useful readiness gate, but current evidence is bounded to research, registry planning, fixtures, and verifier checks. Corpus definition, run logs, anomaly triage, SLA metrics, and quality sampling are still missing. | Gap analysis Gap F; proof gates `GATE-1000-DOC-PILOT`; adoption ladder L5 |
| RusLawOD as immediate primary corpus | Do-not-adopt-as-is | This conflicts with the current Consultant-first evidence direction. RusLawOD may remain future/reference corpus material only if a later decision and proof gate promote it without overriding current source priority. | Gap analysis §4.1, §7; adoption ladder L6; bounded evidence intake non-claims |
| RuBERT-CRF as required extractor | Do-not-adopt-as-is | This is too implementation-specific before evaluation and conflicts with deterministic-first, fail-closed, proof-gated extraction. It may re-enter only as a candidate extractor with benchmark and provenance evidence. | Gap analysis §4.3, §7; adoption ladder L6; bounded evidence intake non-claims |
| Single-transaction graph+vector guarantee | Do-not-adopt-as-is | This is a database/runtime capability claim and must not be promoted without direct FalkorDB evidence. Keep it rejected as stated until a narrower, tested runtime claim exists. | Gap analysis §4.5, §7; bounded evidence intake non-claims; adoption ladder L6 |
| BFO / Common Logic as immediate MVP blocker | Do-not-adopt-as-is | Formal ontology alignment should not block parser, evidence, or retrieval proof at this stage. A narrower formal-review milestone may be planned later, but immediate blocking adoption would create scope explosion. | Gap analysis §4.4, §7; adoption ladder L6 |

## 3. Near-term architecture roadmap

### Phase A — Preserve current core and non-claims

- Keep `SourceDocument`, `SourceBlock`, `LegalUnit`, `ActEdition`, `EvidenceSpan`, and candidate `NormStatement` vocabulary as the internal planning core.
- Preserve Consultant-first evidence direction and do not promote RusLawOD, Garant, Akoma Ntoso, LKIF, BFO, GOST, OWL, or Common Logic above existing source-priority decisions.
- Keep LLM output citation-bound and non-authoritative.
- Keep current architecture registry artifacts derived and non-authoritative; update source anchors/extractor mappings before regenerating registry outputs.

### Phase B — Add source-mapped registry candidates, not hand-edited JSONL

- Use `05-registry-integration-plan.md` as the candidate mapping plan.
- Implement registry extraction changes only in a follow-up task/milestone that updates `scripts/extract-prd-architecture-items.py`, regenerates derived JSONL, rebuilds graph reports, and runs the architecture verifier.
- Preserve `source-anchor` proof ceilings and `hypothesis` / `bounded-evidence` statuses for M017 ontology records unless separate proof evidence is added.

### Phase C — Select proof milestones by risk and dependency order

Recommended proof order:

1. Akoma/FRBR projection proof, because it clarifies identity and source-preserving projection before semantic enrichment.
2. Deontic mapping benchmark, because LKIF/RusLegalCore semantics depend on reliable source-span assertions.
3. Legal collision policy proof, because hierarchy and maxims require curated examples and review-required failure states.
4. BFO/GOST/OWL/Common Logic source verification, because formal claims must be bounded before influencing architecture.
5. Ontology GraphRAG integration proof, because retrieval needs proven graph filters, generated-query safety, citation checks, and runtime diagnostics.
6. 1000-document pilot readiness, because scale evidence should come after parser, ontology, retrieval, and runtime gates have observable checks.

## 4. Final risk posture

- **Overall risk:** high if ontology standards are promoted directly; moderate if they remain source-anchored, proof-gated, and optional around the LegalGraph core.
- **Primary risk:** overclaiming research or static registry consistency as product implementation, legal correctness, ontology conformance, or FalkorDB runtime capability.
- **Mitigation:** keep proof levels explicit, use the adoption ladder, require gate evidence before promotion, and preserve non-claims in every registry/source mapping.
- **Decision posture:** no implementation adoption yet; plan follow-up proof milestones and registry extractor work.

## 5. Non-claims to preserve

This roadmap does not prove:

- parser completeness for Consultant, Garant ODT, RusLawOD, Akoma Ntoso, LegalDocML, or any other corpus/source format;
- legal correctness, authoritative legal reasoning, legal advice, or court-grade conflict resolution;
- LKIF/deontic extraction correctness, negation handling, modal-verb classification, or ML/NER quality;
- RusLegalCore scope, Russian legal hierarchy completeness, judicial interpretation correctness, or federal competence coverage;
- BFO, GOST R 59798-2021, OWL 2, Common Logic, Akoma Ntoso, LegalDocML, or FRBR conformance;
- FalkorDB production readiness, graph-vector behavior, HNSW behavior, single-transaction graph/vector behavior, or production-scale graph runtime;
- ontology GraphRAG retrieval quality, vector quality, generated-Cypher safety beyond existing bounded gates, or pilot-scale readiness;
- LLM answer authority.

## 6. Open work for later S05 tasks

T02 should extend this file with next milestone candidates including entry criteria, dependency gates, expected evidence classes, and non-goals. T03 should then assess whether R035 can be validated or should remain active pending registry extraction/regeneration and proof-gate acceptance.
