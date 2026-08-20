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
| KBO-R013 | dependency | Representative amendment / membership fixtures (S4 partial) before corpus edge claims | TSG-003/013; KBO-R042 435-FZ forest + 402-FZ chapter tree drafts; **C1 corpus acquired**: consru_export has 121 amending laws + 118 editions of 44-ФЗ | **partial** (advanced: C1 available, integration pending) |
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
| KBO-R038 | non-claim | Current 44-ФЗ disk set is C2 + C2hint + C3; C0 absent. C1 amending acts acquired since Review 7 (138/333/484-ФЗ files on disk) but not yet parsed into the event canon; Coverage into the past is Unknown until the C1 walk lands | Review 4 R4-08; Review 7 acquisition; M174 wording sync | **accepted-draft** |
| KBO-R039 | fail-closed | Provider title «ред. от» and «вступ. в силу с» name different clocks; collapsing them is hostile | Review 4; ADR-0009 §5 | **accepted-draft** |
| KBO-R040 | non-claim | Coverage / Unknown / Conflict are first-class assembly outcomes, not bugs to smooth | Review 4 §4 | **accepted-draft** |
| KBO-R041 | core-contract | Document-order markers propose attach drafts via YAML hierarchy ranks; Unknown skips the stack and does not mint CC; proposals do not append the membership log | Review 4 P6; assembly S_propose | **accepted-draft** |
| KBO-R042 | core-contract | Marker→CC bindings live in YAML (`kb-hierarchy-registry.yaml`); a path matches by needle; unmatched paths stay empty; same-level articles are a forest (0 attach); a glava+statya fixture drafts attach > 0 | Review 4 R3-02; 402-FZ tree; KBO-R013 partial | **accepted-draft** |
| KBO-R043 | core-contract | `admit_membership_proposals` quarantines two-parent conflicts, cycles, and self-parent before commit; first parent wins; exact duplicates are deduplicated; admitted drafts do not append the membership log | Review 4 R3-03; assembly S_admit | **accepted-draft** |
| KBO-R044 | core-contract | `commit_admitted_to_log` + `assemble_membership_ast` close the pipeline: admit → commit (Attach events with synthetic provenance + edition effect_day) → fold (`fold_membership_at`) → StructuralAst; provenance is synthetic for C2 editions until S_identify | Review 4 R3-04; assembly S_commit/S_fold | **accepted-draft** |
| KBO-R045 | core-contract | `edition_ast_at(t)` unifies three L2 canons: CompositionAst = fold(membership ≤ t); EditionAst = filter(CompositionAst, fold_presence ≤ t); TextAst = resolve_CTV(cc, t) [bounded: resolve_ctv live on real corpus, M170 S01]. Closes S_fold exit criterion | Review 5 R5-03; ADR-0017 §1a | **accepted-draft** (implemented: 3 tests green) |
| KBO-R046 | gap | `resolve_ctv(cc, t)` deterministic point-in-time text reconstruction; TextVersionLog + TextVersionEvent; Resolved/Unknown/Conflict; main gap vs de Martim v5 closed at prototype | Review 5 R5-02; TSG-003; ADR-0017 §1c | **accepted-draft** (prototype: 6 tests green) |
| KBO-R047 | core-contract | Oracle diff: `drift(t) = fold(events, t) Δ snapshot(oracle@t)`; non-zero drift heals by new event or waiver, never by writing oracle tree as canon | Review 5 R5-04; ADR-0017 §1c; TSG-017 | **accepted-draft** |
| KBO-R048 | core-contract | Macro/micro event P9 consists of: a macro-event (EnactingAct) composes micro-events (per-CC attach/detach/renumber) via explicit parent→child hierarchy | Review 5 R5-05; ADR-0017 §3; de Martim v5 P9 | **accepted-draft** |
| KBO-R049 | core-contract | Cross-act edges S0→S1 transition requires: typed `CrossActEdgePort` + hostile tests + at least one real C1 edge | Review 5 R5-06; ADR-0019; TSG-007 | **accepted-draft** (S1: port + tests + **real C1 edges**: 138-ФЗ→ст.31/43, 333-ФЗ→ст.95) |
| KBO-R050 | non-claim | ELI/AKN URI mapping is a D046 L6 compatibility projection, not a runtime requirement; internal ID canon (`cc:402fz:statya-1`) is not replaced by `eli/ru/...` | Review 5 R5-07; ADR-0016; D046 | **accepted-draft** |
| KBO-R051 | core-contract | Text extraction: decode article text from ParsedBlock (not just marker) → TextVersionEvent; wires `resolve_ctv` into real corpus | Review 6 R6-01/R6-06; ADR-0013 | **accepted-draft** (implemented: build_text_log_from_markers, 4 tests, CLI wired) |
| KBO-R052 | core-contract | S_heal: when `oracle_diff` drift ≠ 0, create a new event or explicit waiver; never write oracle tree back as canon | Review 6 R6-03; ADR-0017 §1c; assembly S_heal | **accepted-draft** (implemented: heal_missing + waive_drift, 4 tests green) |
| KBO-R053 | core-contract | S_identify: mint FrbrWork + FrbrExpression from XML (type/number/date/authority); replaces synthetic provenance with real Expression ID | Review 6 R6-02/R6-07; ADR-0016; assembly S_identify | **accepted-draft** (partial: YAML works section → mint_work + mint_expression; CLI uses expression_id as provenance) |
| KBO-R054 | core-contract | `diff_marker_sets(before, after) -> MarkerDiff` compares hierarchy markers of two consecutive editions; added/removed markers are candidates for AmendmentEvents; foundation for legislative replay | Review 7 R7-02; ADR-0017; C1 corpus | **accepted-draft** (5 tests green) |
| KBO-R055 | core-contract | Replay bridge: `drafts_from_marker_diff` turns a marker diff between editions into attach/detach `AmendmentEventDraft`s with evidence_class `hypothesized_from_oracle_diff` and facet `structural`; fail-closed on empty provenance; drafts never write the membership log directly | M169 S03; KBO-R054; ADR-0017 | **accepted-draft** (4 tests green; consecutive text-only editions yield zero drafts — honest bounded result) |
| KBO-R056 | core-contract | Legislative replay chain: seed edition commit at seed day + drafts_from_marker_diff applied at target day must reproduce the target snapshot assembly with oracle drift=0; historical layers re-bind removed CCs locally as a fixture decision, never mutating the snapshot registry | M169 S03 T02; KBO-R054/R055; ADR-0017 | **accepted-draft** (real 0080→0081 44-ФЗ: added=24 removed=57, drift=0) |
| KBO-R057 | core-contract | Learning loop: rank_unknown_forms sorts unsupported-form lexemes by frequency (lexeme-only, ProviderComment excluded) and render_yaml_patch_candidates emits a deterministic human-review patch block; applying a candidate is a tracked PR action, never runtime mutation | M169 S04 T01; ADR-0013 golden pipeline boundary | **accepted-draft** (20 tests green: fingerprint identity, ranked text-free report, apply API census-to-zero, patch parser fail-closed) |
| KBO-R058 | core-contract | Classifier quality is measured against the real catalog golden set: legal_relation_items amends-explicit rows (positives) and non-amending normative titles (negatives); title-form needles added only after measured recall gap; floors recall 0.8 precision 0.7 | M169 S04 T02; KBO-R034; ADR-0025 | **accepted-draft** (measured: recall 1.000 precision 1.000 both engines, 120 positives / 300 negatives; singular title-form needle «внесении изменения» closed the gap) |
| KBO-R059 | process | Governor corpus-grounding check (advisory): registry needles (works/bindings) must match at least one real corpus path when CONSULTANT_EXPORT_DIR is present; prevents toy-path-only grounding regressions; ungrounded fixture-only needles are reported, not blocked | M169 S04 T03; governor.py; MEM793 | **accepted-draft** (implemented in governor.py as `corpus-grounding` check; live corpus grounded via law_2013-04-05_44-fz; n-402-fz/n-435-fz/n-44-fz/n-138-fz fixture-only stay ungrounded) |
| KBO-R060 | core-contract | Full article text CTV: `collect_article_texts` stores the statya marker title separately (the marker line never enters the article text); direct prose and nested sub-marker lines accumulate up to the next statya/glava boundary; `build_text_log_from_articles` mints TextVersionEvents from tuples (empty body falls back to title); `resolve_ctv` returns the real article body, not the title | M170 S01; R6-01/R6-06; ADR-0013/0017 | **accepted-draft** (14+11+2 tests green; real corpus: 85/94 statya resolve, statya-1 = 6231 chars) |
| KBO-R061 | core-contract | Text-facet replay: `changed_article_texts` compares full article texts of two editions and drafts `facet: "text"` AmendmentEvents (changed/added/removed) with evidence_class hypothesized_from_oracle_diff, fail-closed provenance; resolve_ctv on a merged multi-day timeline returns edition-correct real text without future leakage | M170 S02; KBO-R055/R060; ADR-0017 §1c | **accepted-draft** (4 TDD tests + real corpus 0001→0002: 3 text drafts, drift=0) |
| KBO-R062 | core-contract | Document-group vocabulary: `document_groups` per-group structural profiles in kb-ontology.yaml with closed role layer (container/unit/subunit/subunit-text/text-only), per-group ladders over the decode-token catalog, granularity/text_boundary as profile data; court_practice is text-only (practice ≠ AST); governor coverage check validates ladders ⊆ token catalog, roles closed, mandatory federal_law@v1, catalog version detectable | Review 8 §1a/1b; R8-01..R8-09; M171 S04 T01/T02 | **accepted-draft** (implemented: kb-ontology.yaml document_groups; governor check_document_groups_coverage advisory) |
| KBO-R063 | core-contract | Recursive ladder tokens: `recursive: true` with per-level per-group `max_depth` (law punkt=2, resolution punkt=3, order punkt=4, corpus-grounded R8-03); depth is policy, not syntax; exceeding max_depth or a non-catalog token → quarantine → census, never a heuristic; recursive walk and `(role_order, depth)` rank pair remain future | Review 8 R8-03/§1d/R8-13 | **accepted-draft** (partial: max_depth YAML data landed; recursive walk `[proposed]`) |
| KBO-R064 | core-contract | parsed_as binding: pure write-set Work→DocumentGroupRef{group, catalog_version} carries the FNV-1a 64 section hash; binding at Work level (act type is a Work property); hostile: never writes ForceStatusEvent/ApplicableDecision, forbidden kinds DocumentProfileAsAuthority/ProfileBindingAsForce/DocumentProfileAsClock; unknown group → fail-closed error | Review 8 R8-10/§1c; M171 S04 T01 | **accepted-draft** (implemented: project_document_group_binding, ref-id docgroupref:{group}:{catalog_version}) |
| KBO-R065 | dependency | StructuralNearMiss census class: near-miss structural candidates (depth exceed, non-catalog token) feed offline profile refinement via the existing census→patch→human-apply loop; ONLINE deterministic walk + OFFLINE self-tuning; never auto-apply (D185). The unsupported-form census exists (`ln-decode/src/unknown_forms.rs`, KBO-R057 loop live); the deferred remainder is the depth-exceed/non-catalog-token StructuralNearMiss class | Review 8 R8-12/§4.2; M174 wording sync | **deferred** (narrow remainder: StructuralNearMiss class only) |
| KBO-R066 | process | Governor coverage-rule generalization: from "Rust enum ⊆ YAML" to "group ladder ⊆ token catalog; roles closed; group references catalog version"; advisory warn, not TSG, not production schema; catalog version in parsed_as binding — drift is a visible warning, not a silent skip | Review 8 §4.8; M171 S04 T02 | **accepted-draft** (implemented: check_document_groups_coverage advisory; Python mirror byte-identical to Rust) |
| KBO-R067 | core-contract | Punkt/subunit text-CTV contract vs article-only M170 (three layers, table below): article unit-body CTV (KBO-R060) stays `statya`; punkt-as-unit CTV on `government_resolution`/`departmental_order` mints at YAML `granularity: punkt` via a separate `ArticleText` per punkt (anchor: already-executed PP_60); punkt-as-subunit on `federal_law@v1` folds into the owning statya body and never mints its own `ArticleText` or CC. Mint level = the group's YAML granularity, never a hardcoded `"statya"`; `ctv_resolved` counts unique Resolved CCs on the path's mint level (Conflict/Unknown excluded, D187); empty body → title fallback; unbound → no event. inspect минтит YAML granularity (this file's wording), so on a ПП with a bound `government_resolution` it mints `punkt` and `ctv_resolved` counts the unique Resolved CCs at that level (detection_unknown=0, membership_committed stays 0). Non-claims: not S4, not Applicable, not nested 44-ФЗ punkt-CC (registry stays 8 glava + 94 statya, D192), not MissingAnchor runtime, PP fixture-CC is a local fixture-CC (not registry identity, not a membership entry); ADR-0017 stays `[proposed]`; KBO-R060 is not rewritten to punkt | M172 S01; D186/D187/D190/D191/D192; KBO-R060/R062/R063 | **accepted-draft** (M172 S01 T02 wired the PP_60 inspect surface; locking tests `punkt_subunit_ctv_contract` in S01 T02) |

### KBO-R067 contract table: three text-CTV layers (M172 S01)

Freeze of which layer any punkt/subunit text-CTV claim lives in; the three
layers must not merge into one «punkt CTV» claim:

| Layer | What it is | Mint level / CC | Current surface | Explicitly not |
|---|---|---|---|---|
| **1. Article unit-body text-CTV** (KBO-R060, M170) | one `ArticleText` per `statya` unit (`federal_law@v1`, `code`); nested chast/punkt/podpunkt lines live inside the owning statya body | `statya` (YAML granularity); registry CC `cc:44-fz:statya-N` | `inspect` / `replay` on `law_*` editions | not punkt granularity; not a subunit CC |
| **2. punkt-as-unit text-CTV** (M171; anchor PP_60) | one `ArticleText` per `punkt` unit (`government_resolution`, `departmental_order`); heading excluded; podpunkt folds into the owning punkt body; primechanie excluded (`departmental_order`) | `punkt` (YAML granularity); PP fixture-CC `cc:<act>:punkt-N`; day from filename ISO ordinal with provenance `fixture:subordinate:…` (edition-day registry parses `law_*` only) | `inspect` (PP_60 wired) + `subordinates` CLI | not registry identity (PP fixture-CC is a local fixture-CC, not a membership entry); not a Work mint |
| **3. punkt-as-subunit** (`federal_law@v1`) | punkt is a subunit: marker line + prose fold into the owning unit body (D190); no separate `ArticleText` | none — 44-ФЗ registry stays 8 glava + 94 statya (D192) | decode accumulator | not «subunit Resolved»; not nested `cc:44-fz:statya-N/punkt-M` (separate bounded wave; D191 path syntax only) |

**punkt/subunit Resolved** = a unique bound CC for which
`resolve_ctv(log, cc, t) == CtvResolution::Resolved { text }`, where `text` is
the unit body (empty body → title fallback). The count is unique Resolved CCs
on the path's mint level (D187) — never `events().len()`; Conflict/Unknown are
excluded, not deduplicated away; unbound tuples emit no event.

Contract clauses:

- **Two senses of «punkt»**: punkt-as-subunit (federal-law ladder) vs
  punkt-as-unit (resolution/order ladder). S02 wiring must not «fix» 44-ФЗ
  by a second collector or nested CC.
- **podpunkt/chast are folded-into-unit** on current anchors; an independent
  subunit CC is future work (D191 path syntax exists, no runtime mint).
- **S02 wiring anchor = PP_60** (already-executed punkt-unit resolution on the
  real Garant ODT corpus via `subordinates`) plus the tracked
  departmental-order inline fixture (exactly 2 Resolved).
- `collect_marker_bodies` is not a CTV source (title-sized fragments at every
  marker).
- Non-claims: not S4, not Applicable, no lifecycle promotion (ADR-0017 stays
  `[proposed]`; R074 stays active/bounded; TSG-017 ceiling S3); no raw legal
  text in CLI JSON or tracked artifacts.

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
