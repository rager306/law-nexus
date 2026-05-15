---
source_requirements_dir: "prd/research/ontology_architecture_requirements"
source_registry:
  - "prd/architecture/architecture_items.jsonl"
  - "prd/architecture/architecture_edges.jsonl"
  - "prd/architecture/architecture_report.md"
verification_note: "Registry verifier passed, but registry remains derived and non-authoritative; this analysis compares planning artifacts, not working product code."
---

# Architecture Gap Analysis: Research Requirements 05 vs Current Architecture Registry

## Scope and boundary

This analysis compares the extracted `05-*` architecture requirements from the ontology research document against the current `prd/architecture` JSON graph artifacts.

Important boundary: the project does **not** currently have a working product architecture implementation. The current architecture registry is a derived planning/proof graph over PRD, GSD, research, bounded proofs, fixtures, smoke evidence, and guardrails. It is useful for consistency and traceability, but it is not runtime/product proof.

Freshness check performed before analysis:

```text
uv run python scripts/verify-architecture-graph.py
status=ok
items=46
edges=66
failure_count=0
boundary=derived and non-authoritative
```

This means only that the current derived JSON graph is internally consistent under the verifier rules. It does **not** validate parser completeness, legal correctness, retrieval quality, FalkorDB production scale, generated-Cypher safety, or LLM authority.

## 1. Main conclusion

The new `05-*` requirements mostly do **not** directly conflict with the current JSON graph because the current graph barely models the ontology layer described by the new research document.

The current registry is strong around:

- source-of-truth guardrails;
- architecture verification discipline;
- parser bounded evidence;
- Consultant/Garant source evidence boundaries;
- retrieval output ID validation;
- local embedding bounded proofs;
- non-authoritative LLM guardrails;
- generated-Cypher safety gates;
- FalkorDB runtime boundaries;
- general temporal status semantics.

The new document adds a large missing architecture layer:

- Akoma Ntoso / LegalDocML;
- FRBR legal identity;
- LKIF;
- deontic mapping;
- RusLegalCore;
- Russian legal hierarchy and collision maxims;
- BFO / GOST R 59798-2021;
- OWL 2 / Common Logic;
- ontology-driven GraphRAG;
- pilot-scale SLA and validation requirements.

So this is mostly an **extension and refinement of the planning architecture**, not a contradiction with implemented code.

## 2. Strong alignments with the current architecture

### 2.1 Citation, provenance, and evidence-first behavior

New requirements:

- `05-01-05` — assign globally stable identifiers to structural legal units;
- `05-02-06` — preserve extraction provenance for every semantic assertion;
- `05-05-06` — keep generated answers citation-bound and non-authoritative.

Current registry concepts that align:

- `DATA-LEGAL-EVIDENCE-CORE`;
- `REQ-R034`;
- `EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF`;
- `REQ-R028`;
- `RISK-OVERCLAIM-RUNTIME`.

Interpretation: this reinforces the current project direction. Legal answers, retrieval outputs, semantic assertions, and future graph records should remain anchored to source/evidence/legal-unit/edition identifiers.

### 2.2 Temporal-first model

New requirements:

- `05-01-02` — represent legal identity through FRBR;
- `05-01-03` — preserve temporal legal versions;
- `05-05-04` — support temporal version aggregation for amendments;
- `05-05-05` — exclude inactive legal versions during retrieval by default.

Current registry concepts that align:

- `DATA-TEMPORAL-PROPERTY-BUNDLE`;
- `REQ-TEMPORAL-STATUS-SEMANTICS`;
- `GATE-G005` — temporal same-date / multi-edition conflict policy.

Interpretation: FRBR can formalize the current temporal model. The current graph has edition/status/effective-period concepts, but lacks a clear bibliographic identity model separating abstract act, edition/version, manifestation, and file/item.

Possible mapping:

```text
LegalAct       ~= FRBRWork
ActEdition     ~= FRBRExpression
SourceDocument ~= FRBRManifestation / FRBRItem boundary
LegalUnit      ~= structural unit within an Expression
```

This mapping needs careful design because Consultant WordML, Garant ODT, future Akoma Ntoso, and raw source files should not be conflated.

### 2.3 Graph-constrained retrieval

New requirements:

- `05-05-01` — implement ontology-driven GraphRAG;
- `05-05-03` — combine graph filters with vector nearest-neighbor search;
- `05-05-05` — filter inactive versions by default.

Current registry concepts that align:

- `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS`;
- `EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING`;
- `GATE-G011`;
- `GATE-G008`;
- `REQ-R034`.

Interpretation: the direction is consistent, but remains proof-gated. The current registry correctly avoids claiming product retrieval quality or production graph runtime behavior.

## 3. New architecture areas missing from the current registry

### 3.1 Akoma Ntoso / LegalDocML structural target

New requirements:

- `05-01-01`;
- `05-01-04`;
- `05-01-06`.

Current close concepts:

- `EVID-PARSER-RECORD-CONTRACT`;
- `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF`;
- `S05-PARSER-ODT-BOUNDARY`;
- `GATE-G008`.

Gap: the current registry has parser records and bounded source evidence, but does not state Akoma Ntoso / LegalDocML as a target structural representation.

Risk: adopting Akoma Ntoso as a hard target may alter parser roadmap and compete with the current Consultant-first evidence direction.

Safer interpretation:

```text
Akoma Ntoso should be treated as a compatibility/reference structural target or export/projection layer until proven against current source fixtures.
```

### 3.2 FRBR legal identity model

New requirements:

- `05-01-02`;
- `05-01-03`.

Gap: current registry has `ActEdition`, `edition_date`, status, validity/effective periods, and source documents, but no explicit Work / Expression / Manifestation / Item separation.

Potential improvement: add a dedicated architecture item such as:

```text
DATA-LEGAL-DOCUMENT-IDENTITY-FRBR
```

This item should be source-anchored, active or hypothesis, and bounded by future temporal/legal-identity proof.

### 3.3 LKIF and deontic mapping

New requirements:

- `05-02-03`;
- `05-02-04`;
- `05-02-05`;
- `05-03-01`.

Gap: the current registry has almost no representation of:

- obligation;
- permission;
- prohibition;
- deontic operators;
- LKIF;
- negation handling.

This is a major new semantic layer.

Recommended status: future proof-gated hypothesis, not near-term validated architecture.

Candidate gate:

```text
GATE-DEONTIC-MAPPING-PROOF
```

Potential verification requirements:

- precision/recall for obligation, permission, prohibition;
- negation inversion correctness;
- ambiguous modal verb handling;
- source span provenance for every deontic assertion.

### 3.4 RusLegalCore domain ontology

New requirements:

- `05-03-01`;
- `05-03-02`;
- `05-03-03`;
- `05-03-04`.

Gap: the current registry has `DATA-LEGAL-EVIDENCE-CORE`, but not a Russian domain ontology layer covering legal force hierarchy, federal competence, or judicial interpretation.

Recommended interpretation: `RusLegalCore` should remain a working name/proposed domain ontology layer until its scope is formally bounded.

Candidate items:

```text
DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY
DATA-LEGAL-SOURCE-HIERARCHY
DATA-JUDICIAL-INTERPRETATION-LAYER
GATE-RUSLEGALCORE-SCOPE
```

### 3.5 BFO / GOST R 59798-2021 / Common Logic

New requirements:

- `05-04-01` through `05-04-07`.

Gap: current registry does not model BFO, GOST R 59798-2021, OWL 2, or Common Logic.

Risk: this is architecturally heavy and could create scope explosion if treated as immediate implementation requirement.

Recommended interpretation:

```text
BFO/GOST should first be an architecture review lens and source-verification research item, not a blocker for parser/retrieval proof.
```

Candidate items/gates:

```text
EVID-RESEARCH-BFO-GOST-ONTOLOGY-ALIGNMENT
GATE-BFO-GOST-SOURCE-VERIFICATION
GATE-BFO-CATEGORY-CHECKS
```

Important: claims like “GOST requires Common Logic” should be independently verified against primary source or tracked external reference before being promoted.

### 3.6 Legal collision maxims

New requirements:

- `05-03-05`;
- `05-03-06`;
- `05-03-07`.

Current close concept:

- `GATE-G005` — temporal same-date / multi-edition conflict policy.

Gap: `GATE-G005` is narrower than the new legal collision model. It focuses on temporal conflict, while the new requirements add:

- `SUPERSEDES`-style relationships;
- `lex superior`;
- `lex specialis`;
- `lex posterior`;
- explainable norm priority decisions.

Recommended improvement: broaden conflict modeling through a new gate/item:

```text
GATE-LEGAL-COLLISION-POLICY
REQ-LEX-MAXIMS-EXPLAINABILITY
DATA-LEGAL-SOURCE-HIERARCHY
```

## 4. Potential conflicts and tensions

### 4.1 RusLawOD-first vs Consultant-first

The research document presents RusLawOD as the optimal source corpus. The current project direction is closer to Consultant-first parser evidence, with Garant support bounded and lower priority.

This is a planning tension, not a code conflict.

Recommendation: do not adopt RusLawOD as the primary corpus requirement. Rephrase source assumptions as source-agnostic:

```text
The structural normalization layer should support Akoma Ntoso-compatible output for supported legal source corpora, starting from the project’s current Consultant evidence path.
```

RusLawOD can remain a future/reference corpus.

### 4.2 Akoma Ntoso target vs existing parser record contract

The current parser path uses project-specific records such as:

- `DocumentRecord`;
- `SourceBlockRecord`;
- `RelationCandidateRecord`;
- Consultant hierarchy records;
- staging graph records.

Akoma Ntoso introduces a different legal document structure model.

This is manageable if Akoma Ntoso becomes a projection/compatibility target rather than a forced replacement for all current parser artifacts.

Suggested layering:

```text
Raw source parser records
  -> SourceBlock / LegalUnit records
  -> optional Akoma Ntoso-compatible projection
  -> graph entities
  -> retrieval / reasoning
```

### 4.3 RuBERT-CRF / NER vs deterministic-first guardrails

The research proposes RuBERT-CRF and legal-domain NER. The current project has a deterministic-first, fail-closed, proof-gated posture.

NER should not become an authoritative legal layer without evaluation.

Recommendation:

- treat NER/deontic extraction as candidate extraction;
- preserve confidence, provenance, and review/proof status;
- use deterministic lexical/deontic tables before or alongside ML;
- require real-document benchmark proof before accepting semantic assertions.

### 4.4 BFO/Common Logic may overload MVP scope

BFO, GOST, OWL 2, and Common Logic may be valuable for long-term interoperability, but making them immediate blockers would likely overcomplicate the current stage.

Recommendation:

- use BFO/GOST as a review framework first;
- later add conformance gates;
- do not block parser/retrieval bounded proof on full formal ontology alignment.

### 4.5 FalkorDB/HNSW/single-transaction claims

The research mentions graph-vector storage, FalkorDB, HNSW, and unified graph/vector query behavior.

The current registry correctly avoids claiming:

- production-scale FalkorDB behavior;
- product retrieval quality;
- production graph schema readiness;
- vector/full-text runtime guarantees beyond bounded proof.

Recommendation: keep these as hypotheses until capability/runtime proof exists.

## 5. Current registry shortcomings revealed by the new requirements

### Gap A — No formal legal document identity model

Current concepts exist, but FRBR separation is not explicit.

Suggested addition:

```text
DATA-LEGAL-DOCUMENT-IDENTITY-FRBR
```

### Gap B — No explicit ontology/domain layer

Suggested additions:

```text
DATA-LKIF-DEONTIC-MAPPING
DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY
DATA-BFO-GOST-ALIGNMENT
```

### Gap C — Legal collision policy is too narrow

Current `GATE-G005` covers temporal same-date/multi-edition conflict. It does not cover full legal collision logic.

Suggested addition:

```text
GATE-LEGAL-COLLISION-POLICY
```

### Gap D — No deontic extraction proof gate

Suggested addition:

```text
GATE-DEONTIC-MAPPING-PROOF
```

### Gap E — No BFO/GOST proof boundary

Suggested additions:

```text
EVID-RESEARCH-BFO-GOST-ONTOLOGY-ALIGNMENT
GATE-BFO-GOST-SOURCE-VERIFICATION
```

### Gap F — No 1000-document pilot requirement

The new document requires a pilot on at least 1,000 documents. Current evidence is bounded to fixtures/tracers and representative manifests, not 1,000-document end-to-end pipeline validation.

Suggested addition:

```text
GATE-1000-DOC-PILOT
```

This should not invalidate current bounded proofs; it should become a future readiness gate.

## 6. Recommended improvements to the architecture plan

### 6.1 Add a research evidence item for this document

Candidate item:

```text
EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO
```

Recommended status:

```text
bounded-evidence / source-anchor
```

Recommended non-claims:

- does not prove parser completeness;
- does not validate GOST/BFO source claims;
- does not prove LKIF mapping correctness;
- does not prove FalkorDB vector/runtime capability;
- does not override Consultant-first source priority;
- does not make LLM output legal authority.

### 6.2 Add proof gates rather than immediate implementation claims

Candidate gates:

1. `GATE-AKOMA-FRBR-NORMALIZATION`
2. `GATE-DEONTIC-MAPPING-PROOF`
3. `GATE-RUSLEGALCORE-SCOPE`
4. `GATE-BFO-GOST-ALIGNMENT`
5. `GATE-LEGAL-COLLISION-POLICY`
6. `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`
7. `GATE-1000-DOC-PILOT`

### 6.3 Separate source format from canonical legal unit model

Recommended architecture layering:

```text
Source-specific parser
  -> SourceBlockRecord
  -> Canonical LegalUnit / ActEdition / EvidenceSpan
  -> Optional Akoma Ntoso / FRBR projection
  -> Ontology / graph schema
  -> Retrieval / reasoning
```

This avoids forcing a premature choice between Consultant, Garant, RusLawOD, and Akoma Ntoso.

### 6.4 Introduce an ontology adoption ladder

Suggested staged adoption:

| Level | Meaning |
|---|---|
| L0 | Source-backed legal units and provenance |
| L1 | Temporal identity / FRBR-like mapping |
| L2 | Legal source hierarchy and supersession |
| L3 | Deontic mapping |
| L4 | RusLegalCore domain ontology |
| L5 | BFO/GOST alignment |
| L6 | OWL/CL formal reasoning |

This prevents the architecture from jumping directly into BFO/Common Logic before the parser and evidence layers are stable.

## 7. Recommended interpretation by requirement class

### Adopt now as architecture direction

- stable legal-unit identity;
- FRBR-like distinction for act/version/source file;
- provenance for extracted assertions;
- inactive/superseded version filtering;
- citation-bound non-authoritative answers;
- explainable conflict resolution as a future architectural requirement.

### Adopt as future proof-gated hypotheses

- Akoma Ntoso as canonical normalization target;
- LKIF deontic classes;
- RusLegalCore;
- BFO/GOST;
- OWL 2 / Common Logic;
- HNSW/FalkorDB graph-vector execution;
- 1000-document pilot.

### Do not adopt as-is

- RusLawOD as primary corpus, because it conflicts with current Consultant-first direction;
- RuBERT-CRF as required extractor, because this is too specific before evaluation;
- “single transaction” graph+vector behavior, because this depends on actual database capability proof;
- BFO/Common Logic as an immediate blocker, because this is too heavy for the current project stage.

## 8. Central discussion question

The key architecture choice is:

> Should Akoma Ntoso / FRBR / BFO / LKIF become the core architecture, or should they be used as reference standards around a pragmatic project-local LegalGraph core?

Recommended answer for current stage:

> Keep the project-local LegalGraph core as the main internal contract: `SourceDocument`, `SourceBlock`, `LegalUnit`, `ActEdition`, `EvidenceSpan`, `NormStatement`. Use Akoma Ntoso, FRBR, LKIF, and BFO as compatibility/reference layers and proof-gated mappings, not as immediate replacements for current parser/retrieval contracts.

This better matches the project’s current state: hypotheses, bounded proofs, and evidence-first architecture planning rather than working product code.
