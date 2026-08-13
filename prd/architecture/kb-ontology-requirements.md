# Knowledge-Base Ontology Requirements Register (draft)

**Lifecycle:** `[proposed]` process + design inventory  
**Authority companions:** `prd/ARCHITECTURE.md`, ADR-0014, ADR-0016..0018,
ADR-0010 (evidence kernel), D046 adoption ladder,  
`prd/architecture/capability-promotion-board.md`,  
`prd/architecture/temporal-semantic-gap-register.md`  
**Non-authority:** this register does **not** define production graph schema,
close TSG rows, promote ADR lifecycle, prove RuVector readiness, legal
correctness, retrieval quality, applicability, or ontology conformance to
LRMoo/AKML/ELI/LKIF/BFO.

## 1. Purpose

Accumulate **KB ontology requirements** as law-nexus moves from temporal legal
design spines (L1–L7 ADRs) toward a **materialization / projection contract**
for graph+vector storage (behind ports, ADR-0014).

Two layers must stay distinct:

| Layer | Owner | Role |
|---|---|---|
| Temporal legal ontology L1–L7 | ADR-0016..0022 | Meaning: identity, CTV, status, hierarchy, practice, risk, profiles |
| KB ontology / graph projection | this register + draft L1–L3 | How domain facts may be stored/retrieved without becoming legal truth |

## 2. FSM for ontology readiness (meta-prompt)

```text
O0 inventory_open
  → O1 draft_l1_l3_projection
  → O2 identity_ctv_force_join_offline
  → O3 representative_fixture_edges
  → O4 port_materialization_bounded
  → O5 human_scope_acceptance
  → O6 closed_bounded | closed_validated   (corpus + non-claims)
```

**Current state:** **O1** (this wave).  
**Exit O1:** draft node/edge inventory + requirements IDs + Governor structural
coverage + explicit forbidden kinds.  
**Not exit criteria:** RuVector live, Cypher product surface, Applicable, S6 TSG.

## 3. Requirement classes

| Class | Meaning |
|---|---|
| `core-contract` | Must hold for any L1–L3 projection |
| `fail-closed` | Hostile / missing evidence behavior |
| `non-claim` | Explicit anti-overclaim |
| `dependency` | Blocked on another capability ladder step |
| `deferred` | Named, not current wave |

## 4. Accumulated requirements (append-only IDs)

| ID | Class | Requirement | Source / review link | Status |
|---|---|---|---|---|
| KBO-R001 | core-contract | Project-local evidence kernel owns substance; external standards are compatibility projections only (D046) | ARCHITECTURE; archive ontology ladder L0 | **accepted-draft** |
| KBO-R002 | core-contract | L1–L3 draft may materialize only: FRBR-ish identity carriers, ComponentConcept membership, structural industrial events, ForceStatus events + provenance | ADR-0016/17/18; TSG-003/004/013 | **accepted-draft** |
| KBO-R003 | core-contract | Join keys are `ComponentConceptId`, `AmendingActId`, and governing `effect_day` (synthetic ordinal offline); no silent wall-clock substitution | ADR-0009; D118; force resolver | **accepted-draft** |
| KBO-R004 | fail-closed | Missing force evidence → `Unknown` status projection, never default `InForce` | ADR-0018; TSG-004 S3 | **accepted-draft** |
| KBO-R005 | fail-closed | Same-day conflicting force transitions → `Unknown` + conflict flag | force resolver hostile tests | **accepted-draft** |
| KBO-R006 | fail-closed | Structural membership apply requires matching plan + unique op id | CTV apply S3 | **accepted-draft** |
| KBO-R007 | non-claim | Graph projection is not legal validation, corpus completeness, or product readiness | product_readiness_blockers; D098 | **accepted-draft** |
| KBO-R008 | non-claim | `InForce` projection must not imply Applicable; force edges must not write applicability nodes | RC11-F09; ADR-0023 | **accepted-draft** |
| KBO-R009 | non-claim | CTV text/membership presence must not imply `InForce` | ADR-0017/18; TSG-004 | **accepted-draft** |
| KBO-R010 | non-claim | RuVector / redb / RVF types are infrastructure, not domain law | ADR-0014 | **accepted-draft** |
| KBO-R011 | dependency | Stable FRBR Work/Expression runtime identity (ADR-0016 ≥ S2) before freezing identity node cardinality | TSG identity / DATA-LEGAL-DOCUMENT-IDENTITY-FRBR | **open** |
| KBO-R012 | dependency | Force↔CTV join by component offline before multi-store materialization of status+text | TSG-004 next; board | **open** |
| KBO-R013 | dependency | Representative amendment / membership fixtures (S4 partial) before corpus edge claims | TSG-003/013 | **open** |
| KBO-R014 | deferred | L4 hierarchy/conflict, L5 practice, L6 transitional/risk, L7 profiles as **core store types** | ADR-0019..0022; TSG-007..010 | **deferred** |
| KBO-R015 | deferred | Production graph schema, generated-Cypher safety, GraphRAG ontology quality | GATE-GENERATED-CYPHER-SAFETY; TSG-016 | **deferred** |
| KBO-R016 | deferred | RusLegalCore / AKML / LKIF / BFO as canon or completeness claim | DATA-RUSLEGALCORE-*; EVID-RESEARCH-ONTOLOGY-* quarantined | **deferred** |
| KBO-R017 | core-contract | Draft inventory must list **forbidden node kinds** (Applicability decision, practice-as-authority, risk-as-status, profile-as-clock) | continuity contract; D153 | **accepted-draft** |
| KBO-R018 | fail-closed | Identity collision (divergent authority/date) must project Conflict/Unknown, not silent pick | ADR-0016 | **accepted-draft** |
| KBO-R019 | core-contract | Parser emits structural carriers only; does not mint NormativeState or Applicable | ADR-0013; ADR-0016 §5 | **accepted-draft** |
| KBO-R020 | non-claim | KB ontology docs + Governor check are structural inventory only; not TSG S6 | D156 pattern | **accepted-draft** |

## 5. Functional preparation backlog (not implemented this wave)

Ordered for debt-first product depth **toward** O2–O4:

1. Offline **force↔CTV join** by `ComponentConceptId` (KBO-R012).  
2. **FRBR identity spine S2** in product domain (KBO-R011) — distinct from C12 digest identity.  
3. Projection pure functions: domain event → typed write-set (no store I/O).  
4. Hostile projection suite: forbidden edge, missing provenance, InForce≠Applicable.  
5. Bounded port adapter write behind graph-store port (still synthetic).  
6. Only then representative fixture edges (O3).

## 6. Review / residual alignment

| Surface | How this register uses it |
|---|---|
| RC11-F08/F09 non-closure | S3 spines feed L2/L3 node kinds; rows stay active |
| RC12-F04/F05 | NormRule/Applicable **out of L1–L3 core** |
| product_open residual empty | Does **not** authorize O6 or production schema |
| Quarantined ontology research evidence | Historical intake only; retarget anchors before claims |

## 7. Related artifacts

- Draft model: `prd/architecture/kb-ontology-l1-l3-draft.md`  
- Machine inventory: `prd/architecture/kb-ontology-projection-contract.json`  
- Capability board: `prd/architecture/capability-promotion-board.md`  
- Archive prior art (non-authority):  
  `prd/archive/research-era/ontology_architecture_requirements/`
