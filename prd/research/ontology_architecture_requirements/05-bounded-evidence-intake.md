---
source_document: "prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md"
schema_reference: "prd/architecture/architecture.schema.json"
registry_write_status: "candidate-only; do not hand-edit derived JSONL"
proposed_registry_status: "bounded-evidence"
proposed_proof_level: "source-anchor"
---

# Bounded Evidence Intake: Ontology Architecture Research 05

## Purpose

This intake records a bounded architecture evidence candidate for ontology research document 05. It is intended to make the source anchors, proposed proof level, affected architecture areas, and non-claim boundaries durable before any future architecture-registry extraction or mapping work.

This document is not a registry projection and does not update `prd/architecture/architecture_items.jsonl` or `prd/architecture/architecture_edges.jsonl`.

## Candidate item

```yaml
schema_version: legalgraph-architecture-registry/v1
record_kind: item
id: EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO
type: evidence
title: Ontology architecture research gap analysis for Akoma Ntoso, FRBR, LKIF, RusLegalCore, BFO, and GraphRAG
layer: architecture-governance
status: bounded-evidence
proof_level: source-anchor
risk_level: high
owner: architecture-verification
verification: >-
  Treat this as planning/source evidence only. Future registry work must preserve
  source-anchor proof level unless separate runtime, real-document, integration,
  or production evidence is added and verified through the architecture verifier.
generated_draft: false
```

## Source anchors

Primary anchors from `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`:

| Anchor | Lines | Why it matters |
|---|---:|---|
| Scope and boundary | 12-29 | States that the current registry is derived and non-authoritative, and that verifier success does not prove parser completeness, legal correctness, retrieval quality, FalkorDB production scale, generated-Cypher safety, or LLM authority. |
| Main conclusion | 31-55 | Frames document 05 as a planning architecture extension/refinement rather than proof of implemented product behavior. |
| Akoma Ntoso / LegalDocML gap | 131-154 | Identifies Akoma Ntoso as a possible compatibility/reference structural target, with source-fixture proof still required. |
| FRBR legal identity gap | 156-171 | Identifies missing Work/Expression/Manifestation/Item separation and suggests a future FRBR identity architecture item. |
| LKIF and deontic mapping gap | 173-206 | Identifies obligation, permission, prohibition, deontic operators, negation handling, and LKIF as a future semantic layer requiring proof gates. |
| RusLegalCore domain ontology gap | 208-228 | Identifies Russian legal hierarchy, federal competence, and judicial interpretation as proposed domain ontology scope requiring formal boundaries. |
| BFO / GOST / Common Logic gap | 230-254 | Treats BFO/GOST as an architecture review lens and source-verification research item, not an immediate blocker or validated claim. |
| Legal collision maxims gap | 256-280 | Identifies lex superior, lex specialis, lex posterior, supersession, and explainability as a broader future collision policy area. |
| FalkorDB/HNSW/single-transaction boundary | 347-361 | Keeps graph-vector storage, FalkorDB, HNSW, and unified graph/vector behavior as hypotheses until capability/runtime proof exists. |
| Research evidence item recommendation | 423-444 | Proposes `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO` with `bounded-evidence / source-anchor` status and explicit non-claims. |
| Proof-gate recommendations | 446-462 | Lists future gates for Akoma/FRBR normalization, deontic mapping, RusLegalCore scope, BFO/GOST alignment, legal collision policy, ontology GraphRAG integration, and 1000-document pilot. |
| Ontology adoption ladder | 473-487 | Provides staged adoption levels from source-backed legal units to formal OWL/Common Logic reasoning. |
| Requirement interpretation | 489-515 | Distinguishes architecture direction, future proof-gated hypotheses, and items not to adopt as-is. |
| Central architecture choice | 517-529 | Recommends keeping the project-local LegalGraph core as the internal contract and using Akoma Ntoso, FRBR, LKIF, and BFO as compatibility/reference layers and proof-gated mappings. |

Schema anchors from `prd/architecture/architecture.schema.json`:

| Anchor | Selector | Use in candidate |
|---|---|---|
| `source_anchor` definition | `$defs.source_anchor` | Candidate anchors are repository-relative and section/line bounded. |
| `layer` enum | `$defs.layer` | Candidate uses `architecture-governance`; future child items may touch `legal-evidence`, `temporal-model`, `parser-ingestion`, `retrieval-embedding`, `graph-runtime`, and `security-safety`. |
| `item_type` enum | `$defs.item_type` | Candidate is an `evidence` item, not a requirement, decision, component, interface, data entity, or proof gate. |
| `item_status` enum | `$defs.item_status` | Candidate status is `bounded-evidence`. |
| `proof_level` enum | `$defs.proof_level` | Candidate proof level is `source-anchor`. |
| `non_claims` field | `$defs.item.properties.non_claims` | Candidate must carry explicit non-claims if later mapped into the derived registry. |

## Affected architecture areas

This candidate affects planning and future registry coverage for the following areas:

1. **Architecture governance** — source-of-truth hierarchy, proof-level discipline, registry extraction boundaries, and future architecture verifier expectations.
2. **Legal evidence model** — stable legal-unit identity, source provenance, evidence spans, non-authoritative legal-answer boundaries, legal hierarchy, and collision explanation.
3. **Temporal model** — FRBR-like separation of legal act identity, edition/version, manifestation/source document, item/file, status, effective periods, and supersession.
4. **Parser ingestion** — source-specific parser records, Akoma Ntoso / LegalDocML-compatible projection hypotheses, and the boundary between raw sources, `SourceBlock`, `LegalUnit`, and graph entities.
5. **Retrieval and embedding** — ontology-driven GraphRAG, temporal filters, graph filters, and vector nearest-neighbor behavior as future proof-gated hypotheses.
6. **Graph runtime** — FalkorDB graph/vector/HNSW/single-transaction claims remain capability/runtime hypotheses until separately proven.
7. **Security and safety** — non-authoritative LLM behavior, citation-bound answers, generated-Cypher safety boundaries, and claim-safety wording.
8. **Observability and operability** — future gates such as a 1000-document pilot or ontology GraphRAG integration should define observable checks before any readiness claim.

## Proposed proof level and rationale

Proposed proof level: **`source-anchor`**.

Rationale:

- The evidence is a tracked PRD research analysis with bounded line anchors.
- The document compares research requirements against derived architecture artifacts and explicitly says the registry remains derived and non-authoritative.
- No runtime smoke, integration test, real-document proof, production observation, parser benchmark, legal review, FalkorDB capability test, graph-vector query test, or ontology conformance suite is attached to this candidate.
- The schema supports `source-anchor` as the lowest accurate proof level for PRD/GSD/ADR/source evidence without runtime proof.

The candidate should not be upgraded beyond `source-anchor` unless future evidence is added through the project’s authoritative source/evidence workflow and then verified by the canonical architecture verifier.

## Candidate non-claims

If mapped into a future registry item, the candidate must preserve these non-claims:

- Does not prove parser completeness for Consultant, Garant ODT, RusLawOD, Akoma Ntoso, LegalDocML, or any other corpus/source format.
- Does not prove legal correctness, legal authority, legal reasoning correctness, or suitability for legal advice.
- Does not prove FalkorDB production readiness, production-scale graph behavior, HNSW behavior, graph-vector query semantics, or single-transaction graph/vector behavior.
- Does not prove vector search quality, hybrid retrieval quality, ontology-driven GraphRAG quality, or generated-Cypher safety.
- Does not prove LKIF mapping correctness, deontic extraction correctness, negation handling correctness, or obligation/permission/prohibition classification quality.
- Does not prove RusLegalCore scope, Russian legal hierarchy modeling, judicial interpretation modeling, federal competence modeling, or legal collision maxim correctness.
- Does not prove BFO, GOST R 59798-2021, OWL 2, Common Logic, Akoma Ntoso, LegalDocML, or FRBR conformance.
- Does not override the current project-local LegalGraph core, Consultant-first evidence direction, Garant ODT proof boundaries, or deterministic-first guardrails.
- Does not make LLM output authoritative; LLM-generated answers remain citation-bound, non-authoritative, and subordinate to tracked source evidence.
- Does not require immediate implementation of BFO/Common Logic, RuBERT-CRF, RusLawOD as primary corpus, Akoma Ntoso as canonical internal storage, or a 1000-document pilot as an MVP blocker.

## Future registry mapping notes

Potential future item/gate candidates named by the source document include:

- `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR`
- `DATA-LKIF-DEONTIC-MAPPING`
- `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY`
- `DATA-BFO-GOST-ALIGNMENT`
- `DATA-LEGAL-SOURCE-HIERARCHY`
- `GATE-AKOMA-FRBR-NORMALIZATION`
- `GATE-DEONTIC-MAPPING-PROOF`
- `GATE-RUSLEGALCORE-SCOPE`
- `GATE-BFO-GOST-ALIGNMENT`
- `GATE-LEGAL-COLLISION-POLICY`
- `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`
- `GATE-1000-DOC-PILOT`

These are planning candidates only. Future work should add authoritative source evidence first, regenerate derived registry projections through the approved extractor/build workflow, and run:

```bash
uv run python scripts/verify-architecture-graph.py
```

A passing verifier would show static registry health only; it would still not prove runtime behavior, parser completeness, retrieval quality, legal correctness, generated-Cypher safety, FalkorDB production scale, or LLM authority.
