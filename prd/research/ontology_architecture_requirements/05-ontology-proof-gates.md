---
source_gap_analysis: "prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md"
source_adoption_ladder: "prd/research/ontology_architecture_requirements/05-ontology-adoption-ladder.md"
status: "proof-gate contract"
verification_note: "This file defines gate contracts only. No gate listed here is satisfied by this document. Satisfaction requires future named evidence and verification."
---

# Ontology Proof Gates

## 1. Purpose and boundary

This document defines a reusable proof-gate contract for major ontology research areas identified by the architecture gap analysis. It turns broad ontology ambitions into explicit gates with validation criteria, evidence class, owner path, dependencies, and non-claim boundaries.

This file is **not** proof that any gate is satisfied. In plain verification terms: this file is not proof that any gate is satisfied. It is a planning and observability surface for future architecture work. A gate can be promoted only when future work supplies the required evidence and records the result through the project architecture-verification workflow.

Central rule:

> Unproven ontology claims must remain visible as gates, not hidden as architecture assumptions.

Current source-priority and safety boundaries remain in force:

- The project-local LegalGraph core remains the internal contract.
- Consultant-first evidence direction is not superseded by RusLawOD, Garant, Akoma Ntoso, LKIF, BFO, GOST, OWL, or Common Logic research.
- LLM answers remain citation-bound and non-authoritative.
- Parser completeness, legal correctness, retrieval quality, FalkorDB production behavior, graph-vector behavior, generated-Cypher safety, and formal ontology conformance are not claimed by this document.

## 2. Proof gate record contract

Every ontology proof gate must use the following fields.

| Field | Required | Meaning | Allowed / expected values |
|---|---:|---|---|
| `gate_id` | Yes | Stable gate identifier used in research, registry, GSD, and verification notes. | `GATE-*`, globally unique within the architecture gate namespace. |
| `gate_title` | Yes | Short human-readable name. | Imperative or noun phrase. |
| `claim_boundary` | Yes | The exact claim the gate would allow if satisfied. | Narrow, testable claim; no broad architecture slogans. |
| `current_state` | Yes | Whether the gate is satisfied. | `unsatisfied`, `partially-evidenced`, `satisfied`, `rejected-as-stated`, `superseded`. Initial ontology gates in this file are `unsatisfied`. |
| `adoption_level` | Yes | Ontology adoption ladder level for the claim. | `L1` compatibility projection, `L2` reference identity, `L3` candidate semantic layer, `L4` formal alignment, `L5` deferred proof area, or `L6` rejected-as-is assumption. |
| `owner_path` | Yes | Repository area expected to own proof artifacts and verification updates. | Repository-relative path or workflow area such as `prd/architecture/`, `prd/research/...`, `scripts/`, or future milestone/slice paths. |
| `dependencies` | Yes | Gates, requirements, decisions, data contracts, or source evidence that must exist before this gate can be satisfied. | Existing gate IDs, requirement IDs, decision IDs, research docs, fixtures, or runtime proof artifacts. Use `none` only when truly independent. |
| `evidence_required` | Yes | Evidence class needed before promotion. | Source-anchor, fixture proof, real-document proof, runtime smoke, integration proof, benchmark, legal review, primary-standard review, or production observation. |
| `validation_criteria` | Yes | Observable pass criteria. | Concrete checks, fixtures, metrics, negative tests, verifier expectations, review outcomes, or repeatable commands. |
| `failure_behavior` | Yes | What the system or architecture must do if the gate is not satisfied. | Keep feature disabled, keep layer candidate-only, fail closed, require manual review, preserve current core, or avoid registry promotion. |
| `non_claims` | Yes | Explicit statements of what the gate does not prove. | Must include legal-authority, parser-completeness, runtime, retrieval-quality, or formal-conformance caveats where relevant. |
| `relation_to_existing_gates` | Yes | How this gate relates to current known gates or guardrails. | Extends, depends on, narrows, does not replace, or supersedes. |
| `promotion_output` | Yes | What artifact changes if the gate is satisfied. | Registry item/gate update, decision, requirement update, benchmark report, parser contract, schema migration, or milestone summary. |
| `diagnostics_required` | Yes | Observability expected for future verification. | Logs, manifests, anomaly reports, benchmark outputs, query plans, verifier output, source-span trace, or review notes. |

### Status semantics

| Status | Meaning |
|---|---|
| `unsatisfied` | Contract exists, but no sufficient evidence has been attached. This is the default for new gates. |
| `partially-evidenced` | Some bounded evidence exists, but one or more validation criteria remain open. Downstream work must treat the claim as unproven. |
| `satisfied` | All required evidence and validation criteria were met and recorded in durable artifacts. The satisfied subset must remain narrow. |
| `rejected-as-stated` | The claim conflicts with project guardrails, source priority, or capability evidence in its current form. A narrower reformulation may create a new gate. |
| `superseded` | A later gate replaces this gate. The successor must be named. |

## 3. Initial ontology gates

All gates below are initialized as `unsatisfied`. They define what would be required for future promotion; they do not promote the underlying claim now.

| Gate ID | Gate title | Claim boundary | Current state | Adoption level | Owner path | Dependencies | Evidence required | Validation criteria | Failure behavior | Non-claims | Relation to existing gates | Promotion output | Diagnostics required |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GATE-AKOMA-FRBR-NORMALIZATION` | Akoma / FRBR normalization | LegalGraph can project source-backed legal units and act editions into an Akoma Ntoso / LegalDocML-compatible and FRBR-like identity shape while preserving project-local IDs and evidence spans. | `unsatisfied` | `L1` / `L2` | `prd/research/ontology_architecture_requirements/`; future parser proof owner under parser milestone paths | Project-local LegalGraph core; `SourceDocument`, `SourceBlock`, `LegalUnit`, `ActEdition`, `EvidenceSpan`; current Consultant-first parser evidence; temporal status semantics | Representative fixture proof and real-document proof over current supported source types; mapping table; loss/caveat report | Projection preserves stable legal-unit IDs, act/edition/source boundaries, source spans, status/effective-period data, and documented unmapped fields; negative tests cover ambiguous hierarchy and missing metadata | Keep Akoma/FRBR as compatibility/reference only; do not replace internal records | Does not prove Akoma Ntoso, LegalDocML, or FRBR conformance; does not prove parser completeness or source coverage; does not make RusLawOD primary | Extends parser record and temporal identity guardrails; does not replace existing parser proof gates or source-priority decisions | Mapping contract, fixture outputs, verifier notes, and optional future registry items for document identity | Projection manifest, source-span trace, unmapped-field report, verifier output |
| `GATE-DEONTIC-MAPPING-PROOF` | Deontic mapping proof | Candidate legal text spans can be mapped to obligation, permission, prohibition, exception, and negation-aware `NormStatement` records with reviewable provenance. | `unsatisfied` | `L3` | `prd/research/ontology_architecture_requirements/`; future extraction/evaluation milestone paths | Source-backed legal units; evidence-span model; deterministic-first guardrails; non-authoritative answer boundary | Labeled examples, fixture proof, real-document benchmark, legal-domain review criteria, negative tests for negation and ambiguity | Precision/recall or adjudicated acceptance threshold is documented; every assertion has source span, confidence/review status, extractor version, and failure state; tests cover modal verbs, negation inversion, exceptions, and ambiguous statements | Keep deontic extraction candidate-only; require manual review or fail closed before downstream legal reasoning | Does not prove legal correctness, authoritative norm interpretation, LKIF conformance, ML extractor quality, or complete coverage | New gate; depends on evidence-first legal-unit contract and does not override source text or LLM non-authority gates | Evaluation report, extraction schema update, reviewed benchmark, and possible future candidate registry item | Confusion matrix or adjudication table, false-positive/false-negative samples, source-span trace, anomaly report |
| `GATE-RUSLEGALCORE-SCOPE` | RusLegalCore scope boundary | A bounded Russian legal domain ontology scope can model source hierarchy, competence, judicial interpretation links, and legal-domain classes without claiming complete Russian-law coverage. | `unsatisfied` | `L3` | `prd/research/ontology_architecture_requirements/`; future legal-domain modeling paths | LegalGraph core; source hierarchy research; collision-policy gate for priority reasoning | Source-anchor review, curated examples, legal review notes, scope exclusions, class/property glossary | Scope document defines included/excluded classes, relation meanings, evidence requirements, review status, and examples; competency questions are answered only from source-backed data | Keep `RusLegalCore` as working name/candidate layer; prevent registry promotion as adopted domain ontology | Does not prove legal correctness, federal competence completeness, judicial interpretation completeness, or authoritative Russian-law ontology | Complements `DATA-LEGAL-EVIDENCE-CORE`; does not replace current evidence core or source-priority decisions | Scope specification, glossary, competency-question fixtures, and possible future registry gate/item | Review notes, example traceability matrix, unresolved-scope issue list |
| `GATE-BFO-GOST-ALIGNMENT` | BFO / GOST alignment | BFO, GOST R 59798-2021, OWL 2, or Common Logic can be used as a bounded formal alignment or review layer for selected LegalGraph concepts. | `unsatisfied` | `L4` | `prd/research/ontology_architecture_requirements/`; future standards review paths | Stable LegalGraph L0/L1 concepts; primary-source standards access; formal subset definition | Primary-standard review, source-anchor evidence, bounded formal mapping, conformance smoke checks where tooling exists | Primary sources are cited; selected subset is explicitly named; mappings include examples and counterexamples; tooling/runtime checks pass for any executable claim; conflicts with source-backed legal evidence have rollback rules | Keep BFO/GOST/OWL/Common Logic as review lens only; do not block parser or retrieval proof | Does not prove full BFO, GOST, OWL 2, or Common Logic conformance; does not require immediate implementation; does not prove reasoner correctness | New formal-alignment gate; does not replace architecture verifier or evidence-first registry workflow | Standards review report, formal subset document, optional registry non-claim updates | Primary-source citation list, mapping table, conformance smoke output, conflict log |
| `GATE-LEGAL-COLLISION-POLICY` | Legal collision policy | LegalGraph can represent and explain selected priority relationships such as supersession, `lex superior`, `lex specialis`, and `lex posterior` without silently deciding legal outcomes. | `unsatisfied` | `L3` | `prd/research/ontology_architecture_requirements/`; future temporal/legal-reasoning milestone paths | Temporal status semantics; `GATE-G005` temporal same-date / multi-edition conflict policy; source hierarchy scope | Curated collision examples, legal review criteria, source-span evidence, negative tests for conflicting or insufficient facts | Policy records explain applicable maxim, source hierarchy, temporal basis, uncertainty, and citation trace; tests include unresolved conflicts and contradictory evidence | Return unresolved/review-required state; do not rank norms authoritatively when evidence is insufficient | Does not prove legal correctness, court-grade conflict resolution, complete hierarchy coverage, or authoritative advice | Extends `GATE-G005` beyond temporal conflicts; does not replace temporal same-date policy | Conflict policy spec, example fixtures, retrieval/reasoning guardrail updates | Decision trace, unresolved-conflict report, source-span matrix, review notes |
| `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` | Ontology GraphRAG integration | Retrieval can use ontology-aware graph filters, temporal filters, and optional vector search while preserving citation-bound, non-authoritative answers. | `unsatisfied` | `L5` | Future retrieval/GraphRAG milestone paths; research anchor in `prd/research/ontology_architecture_requirements/` | Retrieval output ID validation; temporal filtering requirements; generated-Cypher safety gates; graph-runtime capability evidence | Integration proof, retrieval benchmark, generated-query safety checks, runtime smoke, citation validation, negative tests | Queries exclude inactive versions by default where required; answers cite source IDs/spans; graph filters are logged; generated Cypher is bounded and validated; retrieval quality metrics and failure cases are reported | Keep ontology GraphRAG as deferred proof area; do not claim product retrieval quality or runtime readiness | Does not prove vector quality, hybrid retrieval quality, FalkorDB production behavior, HNSW behavior, single-transaction graph/vector behavior, or LLM authority | Depends on existing retrieval ID validation and generated-Cypher safety gates; does not bypass them | Benchmark report, integration proof, retrieval guardrail update, possible future architecture registry promotion | Query logs, filter traces, citation validation output, benchmark metrics, failed-query diagnostics |
| `GATE-1000-DOC-PILOT` | 1000-document pilot | The parser-to-graph-to-retrieval pipeline can process a defined 1000-document corpus with recorded SLA, anomaly, quality, and failure diagnostics. | `unsatisfied` | `L5` | Future pilot milestone paths; research anchor in `prd/research/ontology_architecture_requirements/` | Source-priority decision; parser contracts; evidence-span model; graph runtime smoke; retrieval validation | Repeatable corpus manifest, run logs, benchmark metrics, anomaly triage, quality sampling, resource profile | Corpus composition is fixed; run is repeatable; success/failure thresholds are stated; parser anomalies are classified; retrieval/citation spot checks are recorded; resource and duration metrics are captured | Do not claim pilot readiness, production scale, parser completeness, or retrieval quality; keep bounded proofs valid but not generalized | Does not prove full production readiness, all-corpus support, legal correctness, or general retrieval quality | New scale-readiness gate; does not invalidate current fixture/tracer proofs | Pilot report, SLA/anomaly summary, possible production-readiness requirement update | Corpus manifest, run logs, anomaly report, metrics report, failed-document samples |

## 4. Existing gate overlap map

The ontology proof gates above are additive planning contracts. They do not supersede current architecture gates `GATE-G005`, `GATE-G008`, `GATE-G011`, or `GATE-G015`; existing gates remain active and unresolved unless a future explicit architecture-registry update names the replaced gate, successor gate, rationale, evidence, and verification result. A satisfied ontology gate may extend or depend on an existing gate, but it must not silently close or weaken the older gate.

| Existing gate | Current boundary from architecture report | Ontology gate overlap | Relationship | Non-replacement rule |
|---|---|---|---|---|
| `GATE-G005` | Temporal same-date / multi-edition conflict policy remains unresolved. | `GATE-LEGAL-COLLISION-POLICY`; partial overlap with `GATE-AKOMA-FRBR-NORMALIZATION` where edition identity affects conflicts. | Extends and depends on temporal status semantics. Legal collision policy broadens conflict reasoning to source hierarchy, `lex superior`, `lex specialis`, and `lex posterior`, while FRBR normalization provides identity vocabulary. | `GATE-G005` is not superseded. Temporal conflict policy must still be proven directly before same-date or multi-edition behavior can be claimed. |
| `GATE-G008` | Product parser/retrieval readiness over real legal sources remains unresolved. | `GATE-AKOMA-FRBR-NORMALIZATION`, `GATE-DEONTIC-MAPPING-PROOF`, `GATE-RUSLEGALCORE-SCOPE`, `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`, and `GATE-1000-DOC-PILOT`. | Mostly depends on and extends parser/retrieval readiness. Ontology gates add projection, semantic extraction, domain scope, integration, and scale criteria above source-backed parser evidence. | `GATE-G008` is not superseded. Ontology fixtures, mappings, or pilot plans cannot replace parser completeness boundaries, citation-safe retrieval proof, or retrieval quality proof. |
| `GATE-G011` | Product retrieval quality under local/open-weight embedding constraints remains unresolved. | `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` and `GATE-1000-DOC-PILOT`. | Depends on retrieval quality and adds ontology-aware filters, temporal filtering, citation validation, benchmark diagnostics, and corpus-scale observations. | `GATE-G011` is not superseded. Ontology-aware retrieval must still pass retrieval-quality evidence before product quality claims are allowed. |
| `GATE-G015` | FalkorDBLite-to-Docker migration/load proof remains unresolved. | `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`, `GATE-1000-DOC-PILOT`, and any future runtime-backed `GATE-BFO-GOST-ALIGNMENT` executable checks. | Depends on runtime migration/load proof when an ontology claim requires production-like graph runtime behavior, query plans, vector/full-text behavior, or scale evidence. | `GATE-G015` is not superseded. Ontology integration or pilot evidence cannot claim FalkorDB production readiness without the runtime migration/load gate being explicitly satisfied. |
| none / indirect | No existing gate directly covers formal ontology standards or bounded Russian legal domain scope. | `GATE-BFO-GOST-ALIGNMENT` and `GATE-RUSLEGALCORE-SCOPE`. | Independent from G005/G008/G011/G015 except where future executable checks require parser, retrieval, temporal, or runtime evidence. | Independence does not remove existing gates; it only means these ontology gates introduce additional proof obligations. |

Operationally, future registry work should encode these relationships as `depends_on`, `extends`, `bounded_by`, or similar explicit edges. It should use `supersedes` only when the registry update intentionally retires a named prior gate and records why the replacement is safe.

## 5. Gate authoring checklist

Future gates should satisfy this checklist before being added:

1. The gate title names a narrow claim, not a broad ambition.
2. `current_state` starts as `unsatisfied` unless durable evidence already exists and is linked.
3. `claim_boundary` states exactly what downstream work may rely on after satisfaction.
4. `evidence_required` names the class of evidence, not just a document title.
5. `validation_criteria` includes observable pass/fail behavior and negative cases.
6. `failure_behavior` says what remains disabled, candidate-only, or review-required.
7. `non_claims` prevents legal-authority, runtime, parser, retrieval, and standards overclaims.
8. `relation_to_existing_gates` makes dependencies and non-replacements explicit.
9. `diagnostics_required` makes future verification inspectable by another agent.
10. The gate does not change source priority or adoption level without an explicit decision and proof trail.

## 6. Minimum promotion workflow

A future task may mark a gate `satisfied` only after all of the following are true:

1. Required evidence artifacts exist in tracked repository paths or approved durable stores.
2. Validation criteria were executed or reviewed, with pass/fail output recorded.
3. Negative tests or counterexamples were considered where the gate affects legal semantics, retrieval, parsing, runtime, or formal conformance.
4. Non-claims were preserved or narrowed explicitly.
5. The architecture verifier or relevant project verifier was run when registry artifacts changed.
6. A summary records the exact satisfied subset and leaves all unproven behavior unsatisfied.

Promotion must be narrow. Satisfying a fixture proof does not automatically satisfy real-document, integration, benchmark, production, legal-review, or formal-conformance claims.

## 7. Anti-overclaim wording

Use these terms for unsatisfied gates:

- "proof gate"
- "candidate layer"
- "compatibility projection"
- "reference identity layer"
- "formal alignment review"
- "deferred proof area"
- "not satisfied yet"

Avoid these terms unless a gate has been explicitly satisfied for that exact claim:

- "validated ontology architecture"
- "complete legal ontology"
- "legally correct reasoning"
- "production-ready GraphRAG"
- "full Akoma Ntoso conformance"
- "full FRBR conformance"
- "BFO/GOST compliant"
- "guaranteed graph-vector behavior"
- "1000-document readiness"
