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

**Current state:** **O2_calendar_ordinal** (declared in `kb-ontology.yaml` FSM).
Vocabulary and transitions are YAML-sourced; Rust only validates/executes.
HierarchyMarker→CC: unmapped → Unknown. Not CTV text, not O3/O4.  
Review 4 added assembly vocabulary (`assembly_fsm`, corpus roles, evidence
classes) without moving readiness `fsm.current`. Assembly current is `S_propose`
(draft attach from YAML ranks; empty registry quarantines).  
S4 fixtures (KBO-R013), Manifestation/Item, and port materialization remain open.  
**Exit O1 / O2 spine:** done. **Write-set (toward O4):** landed, I/O-free.  
**Not O3/O4:** no representative fixture edges, no graph-store adapter writes.  
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
| KBO-R011 | dependency | Stable FRBR Work/Expression runtime identity (ADR-0016 ≥ S2) before freezing identity node cardinality | `mint_work`/`compare_work_identities` S2; number≠Work | **partial** |
| KBO-R012 | dependency | Force↔CTV join by component offline before multi-store materialization of status+text | `join_force_with_membership` offline; membership≠InForce | **partial** |
| KBO-R013 | dependency | Representative amendment / membership fixtures (S4 partial) before corpus edge claims | TSG-003/013; KBO-R042 435-FZ forest + 402-FZ chapter tree drafts | **partial** |
| KBO-R014 | deferred | L4 hierarchy/conflict, L5 practice, L6 transitional/risk, L7 profiles as **core store types** | ADR-0019..0022; TSG-007..010 | **deferred** |
| KBO-R015 | deferred | Production graph schema, generated-Cypher safety, GraphRAG ontology quality | GATE-GENERATED-CYPHER-SAFETY; TSG-016 | **deferred** |
| KBO-R016 | deferred | RusLegalCore / AKML / LKIF / BFO as canon or completeness claim | DATA-RUSLEGALCORE-*; EVID-RESEARCH-ONTOLOGY-* quarantined | **deferred** |
| KBO-R017 | core-contract | Draft inventory must list **forbidden node kinds** (Applicability decision, practice-as-authority, risk-as-status, profile-as-clock) | continuity contract; D153 | **accepted-draft** |
| KBO-R018 | fail-closed | Identity collision (divergent authority/date) must project Conflict/Unknown, not silent pick | ADR-0016 | **accepted-draft** |
| KBO-R019 | core-contract | Parser emits structural carriers only; does not mint NormativeState or Applicable | ADR-0013; ADR-0016 §5 | **accepted-draft** |
| KBO-R020 | non-claim | KB ontology docs + Governor check are structural inventory only; not TSG S6 | D156 pattern | **accepted-draft** |
| KBO-R021 | core-contract | Pure write-set projection (domain → typed graph ops) performs no I/O and rejects forbidden L4–L7 kinds | `ln-kb-ontology`; this wave | **accepted-draft** |
| KBO-R022 | core-contract | StructuralAst is a fold projection of versioned membership events at effect_day t; not stored document AST, not CTV text | `fold_membership_at`; TSG-013 | **accepted-draft** |
| KBO-R023 | core-contract | ComponentConcept presence in a dated Expression is event-sourced (include/exclude); later Expression does not inherit silently | `fold_expression_presence`; ADR-0016/17 | **accepted-draft** |
| KBO-R024 | fail-closed | HierarchyMarker (decode candidate) maps to CC only via explicit registry; missing → Unknown; same key + different CC → Conflict | `map_hierarchy_marker`; R3-02 | **accepted-draft** |
| KBO-R025 | core-contract | Ontology vocabulary and readiness FSM live in YAML (`kb-ontology.yaml`); Rust/Governor load the catalog and must not invent kinds, levels, or transitions | meta-prompt FSM | **accepted-draft** |
| KBO-R026 | core-contract | Decode hierarchy tokens map to catalog levels only via YAML `decode_level_aliases`; unknown tokens fail closed | `marker_from_decode_token` | **accepted-draft** |
| KBO-R027 | core-contract | Graph node/edge/presence kinds are YAML catalog tokens; Rust/Governor must not invent kinds or keep a second hardcoded required-kinds list | `try_push_node` / Governor YAML subset | **accepted-draft** |
| KBO-R028 | core-contract | Closed Rust vocabularies (HierarchyLevel, NormativeState, industrial/membership kinds) are subsets of YAML tables; Governor coverage is data-driven via `closed_vocabularies` | Governor + `HierarchyLevel::as_str` | **accepted-draft** |
| KBO-R029 | core-contract | Composition (product-cli) lifts decode HierarchyNode through YAML aliases; empty registry is Unknown and does not mint CC | `lift_extracted_hierarchy` | **accepted-draft** |
| KBO-R030 | core-contract | Decode marker prefixes and number styles are YAML data; ln-decode loads them without depending on ln-kb-ontology | `DecodePrefixCatalog` | **accepted-draft** |
| KBO-R031 | core-contract | ISO `legal_act_effect_day` maps to a YAML-bounded civil-day ordinal; invalid civil days fail closed; not a legal calendar or CTV text | `legal_act_effect_day_to_ordinal` | **accepted-draft** |
| KBO-R032 | core-contract | AmendmentEvent is an n-ary causal node with distinct facets (structural / industrial / text / force); facets must not collapse into NormativeBlob | Review 4 R4-03; ADR-0017 §1b | **accepted-draft** |
| KBO-R033 | core-contract | EditionOracle (consolidated `ред. от`) is a checksum of fold(events, t), never the parent of the next edition and never the event canon | Review 4 R4-04; ADR-0017 §1c | **accepted-draft** |
| KBO-R034 | core-contract | XML files classify into YAML `corpus_roles` (C0/C1/C2/C2hint/C3); unclassified files do not enter a Work log | Review 4 §5 | **accepted-draft** |
| KBO-R035 | fail-closed | Evidence class is closed: legislative > hypothesized_from_oracle_diff > editorial_hint; C2hint never upgrades to legislative | Review 4 R4-11 | **accepted-draft** |
| KBO-R036 | core-contract | Assembly process states live in YAML `assembly_fsm`, separate from readiness `fsm.current`; Rust must not invent assembly states | Review 4 R4-09 | **accepted-draft** |
| KBO-R037 | core-contract | Cross-act edges (amends/implements/specifies/conflicts_with/cites) link ASTs; they are not children of the source tree | Review 4 R4-07; ADR-0019 | **accepted-draft** |
| KBO-R038 | non-claim | Current 44-ФЗ disk set is C2 + C2hint + C3; C0/C1 absent; Coverage into the past is Unknown | Review 4 R4-08 | **accepted-draft** |
| KBO-R039 | fail-closed | Provider title «ред. от» and «вступ. в силу с» name different clocks; collapsing them is hostile | Review 4; ADR-0009 §5 | **accepted-draft** |
| KBO-R040 | non-claim | Coverage / Unknown / Conflict are first-class assembly outcomes, not bugs to smooth | Review 4 §4 | **accepted-draft** |
| KBO-R041 | core-contract | Document-order markers propose attach drafts via YAML hierarchy ranks; Unknown skips the stack and does not mint CC; proposals do not append the membership log | Review 4 P6; assembly S_propose | **accepted-draft** |
| KBO-R042 | core-contract | Marker→CC bindings live in YAML (`kb-hierarchy-registry.yaml`); a path matches by needle; unmatched paths stay empty; same-level articles are a forest (0 attach); a glava+statya fixture drafts attach > 0 | Review 4 R3-02; 402-FZ tree; KBO-R013 partial | **accepted-draft** |
| KBO-R043 | core-contract | `admit_membership_proposals` quarantines two-parent conflicts, cycles, and self-parent before commit; first parent wins; exact duplicates are deduplicated; admitted drafts do not append the membership log | Review 4 R3-03; assembly S_admit | **accepted-draft** |
| KBO-R044 | core-contract | `commit_admitted_to_log` + `assemble_membership_ast` close the pipeline: admit → commit (Attach events with synthetic provenance + edition effect_day) → fold (`fold_membership_at`) → StructuralAst; provenance is synthetic for C2 editions until S_identify | Review 4 R3-04; assembly S_commit/S_fold | **accepted-draft** |

## 5. Functional preparation backlog (not implemented this wave)

Ordered for debt-first product depth **toward** O2–O4:

1. Offline **force↔membership join** by `ComponentConceptId` (KBO-R012) — **partial** via
   `join_force_with_membership` (not full CTV text edition join).  
2. **FRBR identity spine S2** — **partial**: `ln-identity` Work/Expression mint+compare
   (distinct from C12). Manifestation/Item + corpus stability still open.  
3. Projection pure functions: domain event → typed write-set (no store I/O) — **landed**
   in `ln-kb-ontology` (`project_*`).  
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
