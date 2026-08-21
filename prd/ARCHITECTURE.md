# ARCHITECTURE — law-nexus living truth oracle

> **Read this FIRST**, not memory or history. This is the single-page forced
> truth about law-nexus state. Updated at every milestone closeout (mandatory,
> D098 enforcement #2). Lifecycle tags are mandatory (D098 enforcement #1):
> `[bounded]` / `[smoke]` / `[validated]` / `[proposed]` / `[deferred]`.
> Active ADRs must not depend on missing `prd/research/` or gitignored
> `AGENTS.md` as durable authority (RC12-F18).
>
> Detailed decisions: [`doc/adr/**`](../doc/adr/README.md).
> `.gsd/**` is local workflow state, not a cold-reader authority surface.
> [`PRODUCT.md`](PRODUCT.md) and [`REQUIREMENTS.md`](REQUIREMENTS.md) remain `[proposed]`;
> EA-02 marked them `ready-for-assessment` (`37f82c4`) — not EA-10 acceptance.

## What law-nexus IS

A **citation-safe, evidence-verifiable legal graph for Russian normative acts**.
Current product direction `[bounded]`: turn a normative act into a graph-vector
representation for exact article/semantic search, temporal filtering by
edition/effective-date, and provable answers with legal citations. **LLM is not
legal authority** — all checkable operations remain deterministic and
source-anchored. Rust owns product behavior; formal Legal KnowQL remains a
law-nexus application concern.

**Current status:** 20/20 hostile contracts have `[bounded]` synthetic Rust
runtime PASS. The parser foundation has `[bounded]` independent Consultant and
Garant adapters plus one tracked real document per provider; RuVector integration
remains `[proposed]`, and real-corpus retrieval and citation safety are not
validated. Python is prior art
or repository-control harness only, not the product reference specification.

## Active Direction Contract

```text
runtime=rust-only
python=repository-control-only
graph_vector=ruvector
infrastructure_lifecycle=proposed
embedding=tei-user-bge-m3-1024d
acp_git_lex=archive-only
falkordb=historical-only
```

## Foundation ADR map (active, not archive)

| ADR | Topic | Lifecycle |
|-----|-------|-----------|
| ADR-0004 | Rust product transition | `[bounded]` |
| ADR-0005 | Rust target architecture (crate map superseded by ADR-0011) | `[bounded]` |
| ADR-0007 | Python repository-control harness | `[validated]` |
| ADR-0008 | Promotion / publication authority | `[bounded]` |
| ADR-0009 | Five-clock temporal model (safety contract; not full temporal algebra — RC11-F06) | `[bounded]` |
| ADR-0010 | Evidence kernel gates (C10/C12/C13) | `[bounded]` |
| ADR-0011 | KOF-DA exclusive ownership (`ln-*`) | `[bounded]` |
| ADR-0012 | Consequential evidence protocol | `[bounded]` |
| ADR-0013 | Universal multi-source parser | `[bounded]` |
| ADR-0014 | RuVector primary infrastructure | `[proposed]` |
| ADR-0015 | Hexagonal verification architecture | `[bounded]` |
| ADR-0016..0022 | Temporal legal ontology L1→L7 | `[proposed]` each |
| ADR-0023 | Applicability protocol ownership (core decision/trace + profile inputs; no runtime) | `[proposed]` |; capability inventory (RC12-F05)
| ADR-0024 | Review Case intake and disposition (non-authoritative projection + human promotion gate; no runtime) | `[proposed]` |
| ADR-0025 | Consultant parser — separate crate for provider-specific extraction (hyperlinks, catalog, cross-act edges) | `[bounded]` |
| ADR-0026 | RuVector as agent memory layer for the meta-parser (graph + vectors + SONA + GNN) | `[proposed]` |
| ADR-0027 | Multi-layer manifest classifier for document-specific link classification | `[bounded]` |

Index: `doc/adr/README.md`. Do not treat ACP/git-lex/FalkorDB-era docs as
active ADR substance.

## Knowledge-base ontology draft (O1, `[proposed]`)

Accumulating **materialization** requirements (not production schema):
`prd/architecture/kb-ontology-requirements.md`,
`prd/architecture/kb-ontology-l1-l3-draft.md`,
`prd/architecture/kb-ontology-projection-contract.json`.
L1–L3 only (identity carriers, membership/CTV structure, force status);
L4–L7 and Applicable remain deferred. Structural Governor check only. Offline force↔membership join:
`join_force_with_membership` + FRBR `mint_work`/`compare_work_identities` (O2; number ≠ Work; membership ≠ InForce). Pure write-set crate
`ln-kb-ontology` (no I/O; not O3/O4). Versioned membership fold:
`fold_membership_at` → `StructuralAst` (projection, not CTV text).
CC-in-Expression: `fold_expression_presence` (no silent inherit).
Decode lift: `map_hierarchy_marker` (Unknown if unmapped; not legal fact).
Ontology FSM/vocabulary: `prd/architecture/kb-ontology.yaml` (not hardcoded).
Decode aliases: YAML `decode_level_aliases` via `marker_from_decode_token`.
Write-set kinds: YAML tokens via `try_push_node`/`try_push_edge` (KBO-R027).
Closed vocab coverage: YAML `closed_vocabularies` vs Rust enums (KBO-R028).
Composition lift: product-cli `lift_extracted_hierarchy` (KBO-R029); empty registry is Unknown.
Decode prefixes: YAML `decode_marker_prefixes` via `DecodePrefixCatalog` (KBO-R030).
Calendar ordinal: YAML `calendar` via `legal_act_effect_day_to_ordinal` (KBO-R031).
Review 4 assembly inventory `[proposed]`: `doc/review/review-13-08-2026.md` (L0);
YAML `assembly_fsm` current `S_verify` runs oracle diff: `fold(events, t)`
compared against registry CCs (KBO-R047). Zero drift on 402-ФЗ (37 expected /
37 actual). `edition_ast_at` (KBO-R045) unifies 3 L2 canons. Review 5
(`doc/review/review-14-08-2026.md`) maps remaining gaps.
Readiness FSM stays `O2_calendar_ordinal`. Assembly FSM complete: all 12
states reached (S_ready_bounded). 402-ФЗ passes full pipeline with real
Expression ID, zero drift, resolvable CTVs. C1 corpus acquired (Review 7):
138-ФЗ/333-ФЗ/484-ФЗ amending acts available for real cross-act edges.
M169-yi017n grounds the pipeline on real corpus paths: per-edition identity
from `law_DATE_N-fz/edition-XXXX_rev-DATE` filenames (fail-closed), 44-ФЗ
registry bindings (8 glava + 94 statya), full assembly on edition-0118 with
drift=0, first legislative replay 0080→0081 (476-ФЗ purge: added=24
removed=57, drift=0), CLI `replay` report, and a closed learning loop: the
ranked unknown-form census (fingerprint ids only, never raw text) emits
deterministic YAML patch candidates that a human applies via the public
`apply_patch_candidates` API — applying a full candidate drops the census to
zero (KBO-R057; candidates are never auto-applied). The classifier P/R is
measured on the real catalog golden set — 120 explicit amends positives /
300 non-amending negatives: the singular title-form needle «внесении
изменения» closed the measured gap and both engines (rules and templates)
score recall=1.000, precision=1.000 against floors P>=0.8/R>=0.5 (KBO-R058;
one-catalog bounded evidence, not corpus-wide quality). Governor runs an
advisory corpus-grounding check (KBO-R059): registry needles must match real
export paths when CONSULTANT_EXPORT_DIR is present, so grounding cannot
regress to toy-path-only.
Document-group structural profiles (`kb-ontology.yaml` `document_groups:`)
are `[bounded]` YAML vocabulary — closed roles, per-group ladders with
recursive `max_depth`, granularity as data — and the pure write-set binding
`Work ──(parsed_as)──▶ DocumentGroupRef{group, catalog_version}` carries the
FNV-1a 64 catalog section hash; the governor `document-groups-coverage`
check (advisory, KBO-R062/R066) keeps ladders ⊆ token catalog and roles
closed, so binding/catalog version drift is a visible warning (ADR-0013/0016/0027
amendments; Review 8). Recursive walk is `[bounded]` on the subordinate act
corpus (44-ФЗ registry stays a flat anchor, D192), CC-path identity
(`cc:work:statya-93/punkt-4/punkt-4.2`, D191) and the StructuralNearMiss
census → human-apply loop (D194) are `[bounded]`. `law-nexus-inspect` mints
at the group's YAML granularity (M172 wiring): on the real Garant PP_60
corpus the class-matched punkt text-CTV step shows `ctv_resolved` > 0 with
`membership_committed` = 0 — intra-S3 TSG-017 journal only, no S4 raise
and ADR-0017 stays `[proposed]`.
Consultant parser (ADR-0025/0027): `ln-consultant-parser` has 10 source
modules including `lib.rs`, 64 integration test functions and 4 source-unit
tests. The G1 Consultant protocol/tracer anchor is 119 structural hierarchy
markers on the tracked 435-ФЗ fixture (`EXPECTED_HIERARCHY_COUNT` in
`crates/ln-decode/tests/consultant_real_tracer.rs`); those markers are
one-fixture `[bounded]` decode evidence, not legal hierarchy or corpus
completeness. A non-skipping tracked 435-ФЗ system contract covers hyperlink →
path-aware classification → edge candidate → unknown observation mechanics
and an atomic malformed decode diagnostic. Tracked crate mechanics remain
`[bounded]`: contains+bounded-morph
AND/OR scoring, path-aware profile confidence composition, YAML
sibling-section isolation, edge candidates, observations, edition helpers
and read-only SQLite catalog lookup with typed miss/error separation. Temporary production-like schema and shared adapter
contracts are bounded proof; the local catalog remains smoke. Values
3772/3641/2619/502 and the
118-edition temporal graph (44-ФЗ 6→1025 amends, 171×) come from
gitignored `consru_export`; they are local `[smoke]`, skip-capable when
the export is absent, and not durable promotion evidence. The 118-edition
inventory must not be rewritten as the 119 G1 marker anchor. Not a
`[validated]` parser, not corpus/legal/citation completeness, not G2/G3,
not TSG S6, not Applicable. Parser evidence ceiling stays G1.

## Temporal legal ontology — design spine (all `[proposed]`)

A progressive top-down ontology of what an agent needs to reason legally over
time. Each layer depends on the one below; all are **fail-closed** (missing
provenance → `Unknown`, never smoothed) and follow the D046 adoption ladder
(project-local evidence kernel is canon; LRMoo/AKML/ELI/LKIF are compatibility
references, not canon replacements). Full substance: `doc/adr/0016`..`0022`.

```text
L1 ADR-0016 [proposed]  FRBR/LRMoo structural identity   WEMI: Work/Expression/Manifestation/Item
             date + authority = identity canon (act numbers are non-unique)
   ▼
L2 ADR-0017 [proposed]  Component Temporal Versioning ◄── temporal core; TextChange≠NormativeEffect design taxonomy (RC11-F07); structural CTV ops spine (RC11-F08); structural apply S3
             CC/CTV/CLV (F1/F2); validity DERIVED from events (event-sourcing);
             macro/micro events (P9 consists of); F27∩E64 amendment typing;
             bitemporal valid/transaction time; fail-closed resolver (R070/R068).
             Adapted from de Martim arXiv:2506.07853 v5 (LRMoo, 2026);
             Review 4: Work stays stable (not TV=new Work); three L2 canons;
             AmendmentEvent n-ary; EditionOracle is checksum not canon.
   ▼
L3 ADR-0018 [proposed]  NormativeState(t)                text ≠ status (InForce/Suspended/Repealed/…); dimensional separation design (RC11-F09); force resolver S2–S3
   ▼
L4 ADR-0019 [proposed]  hierarchy + conflict             lex superior/specialis/posterior, explainable
   ▼
L5 ADR-0020 [proposed]  practice overlay                 Суды/ФАС/Контроль (first-class temporality over five clocks; non-authoritative)
   ▼
L6 ADR-0021 [proposed]  transitional + risk              derived, non-authoritative; limitation periods
   ▼
L7 ADR-0022 [proposed]  industry profiles                бюджет/стройка/медицина/общий = adapters
   ▼
   ADR-0023 [proposed]  applicability ownership boundary neutral core protocol + versioned profile inputs; `ln-applicability` v0 is fail-closed abstention-only with NormRule IR + pure predicate algebra spines (no Applicable/NotApplicable product claim)
```

Proposed semantic reconciliation, glossary and graduation gates are tracked in [`temporal-legal-model.md`](temporal-legal-model.md). The Reviews 10–14 model has a tracked projection surface: [`architecture/model-crystal.md`](architecture/model-crystal.md) — Layer 0/1, `[proposed]` non-canon, governor-anchored; cite its INV-/AXIS-/OP- IDs in briefs instead of pasting reviews. For work that changes temporal, parser, evidence, citation, retrieval, applicability, practice, risk or profile vocabulary, maintainers and coding agents must read its §3 glossary plus the owning active ADR before naming a public contract or Rust type; `deferred-undefined` and `runtime deferred` are stop-signs. The tracked update/injection process is [`architecture/glossary-governance.md`](architecture/glossary-governance.md). Governor checks inventory the glossary and warn on narrowly allowlisted presentation drift across vocabulary lifecycle and closed-clock boundaries; they remain advisory process controls. These process/design surfaces do not amend ADRs, generate product types or promote O1–O7.

**Kernel canon, standards compatibility (D046):** the project-local evidence
kernel (D119 C10/C12/C13) owns substance; LRMoo/CIDOC-CRM/AKML/ELI/LKIF are
deterministic reversible projections for interoperability. Budget cycle is a
profile projection over the five clocks (ADR-0009), NOT a sixth clock.

## Where we actually are (truth, not optimism)

```
[HISTORICAL FOOTNOTE — not active product work]
  Python-era M001–M108 (parser/ACP/git-lex/FalkorDB) are prior art:
  prd/archive/ + python_archive/ (R066 archive-only). Meta-drift lesson:
  anti-drift infrastructure must not replace product delivery.
   ▼
M109-M129 Rust baseline + 20 hostile contracts  [bounded]
   root Cargo workspace + repository harness (ADR-0007 [validated]);
   20 PASS / 0 FAIL synthetic hostile cases — not product readiness
   ▼
M131-M140 parser foundation + archival cutover  [bounded]
   ADR-0013 universal parser (Consultant WordML + Garant ODT);
   Python product → python_archive/; historical ACP/git-lex (archive-only)
   disconnected from the active plane
   ▼
M141-M164 hardening + retrieval honesty  [bounded]
   shared port contracts, CI/governor honesty, clippy gates; real cosine
   ranking (InMemory); semantic-stub + historical-test-debt probes;
   deterministic CLI vectors (non-semantic)
   ▼
M165 temporal legal ontology L1–L7  [proposed] design (ADR-0016..0022)
   Foundation LC hygiene + truth-oracle sync, vault untrack, archive relocate
   ▼
M166-M168 parser/assembly execution  [bounded]
   real-corpus grounding, EditionOracle checksum fold, oracle drift verify
   ▼
M169-M172 real-corpus identity + text CTV + document groups  [bounded]
   per-edition identity from filenames; 44-ФЗ edition-0118 assembly drift=0;
   legislative replay 0080→0081 (476-ФЗ purge, drift=0, CLI replay report);
   article text CTV (resolve_ctv 85/94 statya); document_groups profiles
   (federal_law@v1, government_resolution, departmental_order); punkt-CTV on
   PP_60 (M172); unknown-form census→patch loop
   ▼
M173 inspect PP_60 class-matched punkt proof  [bounded]
   ▼
M174 wave-1 debt closure  [bounded]
   heal_missing fail-closed provenance (R9-08 fixed); presence channel
   (edition_ast_at) visible in CLI replay; L0 reviews 9-14 committed
   ▼
DESIGN FRONT (no Rust, L0 reviews)
   Reviews 9-14 (doc/review/review-20..25-08-2026.md): C1-commit model,
   citation tape, bitemporal legislative event compiler formula — [proposed]
   direction; human G0 disposition recorded (D216); G0 ADR amendments/notes
   landed (adr-0013/0016/0017/0018/0019 + temporal-legal-model), crystal v2;
   reviews immutable L0; projection: architecture/model-crystal.md (non-canon)
   ▼
ASSESSMENT FRONT (no Rust)
   EA-10 complete: D150 accepted-with-findings (EA-09 at 120d44b); retained
   process/staleness findings open; L2 CTV and TEI/RuVector remain evidence-gated
```

## Current layer (where work happens now)

**Rust product runtime** — `[bounded]` direction (ADR-0004/0005) with active
hexagonal crates under `crates/` and the observable product CLI
`law-nexus-inspect`. Rust owns decode, storage ports, KnowQL composition and
product behavior. Direction is accepted and the runtime exists; this is not
product readiness (blocked on RuVector/TEI infrastructure + real-corpus proof;
no `[validated]` product capability claim).
One tracked real fixture per provider remains `[bounded]` evidence; no
corpus/legal/citation completeness claims.

**Python repository-control harness** — `[validated]` process boundary
(ADR-0007) under `src/law_nexus_harness/`. Active Python is governor/preflight
orchestration only: Cargo/ADR/document freshness/GSD glue. ADR-0024 `[proposed]`
places Review Case intake, disposition, residual inventory and continuity
bridges in this control plane as a non-authoritative, human-gated, hexagonal
contour. Live packets/ledger/CLI/Governor integrity exist as process machinery;
they do not accept findings or claim product readiness. Continuity keeps three
lifecycles orthogonal — L_review (residual), L_delivery (GSD/work), L_capability
(TSG/ADR proof) — with closure ceilings and B1–B5 bridges
(`prd/architecture/review-cases/continuity-contract.md`; GSD dual-truth bridge: `prd/architecture/review-cases/gsd-review-bridge.md`; L_capability promotion board: `prd/architecture/capability-promotion-board.md`). The harness must not
import product domain packages, forbidden PyO3/FFI bridges, or historical-only
graph-database adapters from retired eras.

**`python_archive/product/`** — archived Python product prior art after M140/M141
cutover and residual dependency closure. Historical onion package surfaces,
legacy proof scripts and residual product-era tests live here only. They are not
the target product specification and do not gate active CI product behavior.

**Historical library boundary (retired ADR-0003, prior art only):** Python-era Pydantic/domain and parser-record decisions are prior-art evidence only, not active ADR substance; Rust equivalents are independently defined serde/schemars types behind current hexagonal boundaries. FalkorDB is historical evidence, not active product infrastructure. ADR-0014 selects RuVector only at `[proposed]`; real TEI→RVF, graph materialization, cross-store recovery and citation gates remain open.

**Consultant XML parser hardening** — `[bounded]` through M086–M105: 81 XML
source files, multi-level hierarchy, FRBR IDs, references, temporal/deontic
markers and staging artifacts; single/corpus modes record hashes and counts
in the canonical baseline manifest and CLI `--check` verifies without writes.
Frozen for Rust parity input; not parser completeness, Consultant/Garant
parity or production graph readiness.

## What is downstream and BLOCKED until parser data ready

| Capability | Status | Why blocked |
|---|---|---|
| Universal parser | `[bounded]` independent Consultant/Garant block adapters, shared hierarchy/sentence/morphology and reference/temporal/deontic lexical candidates with one tracked real document per provider; `prd/parser/representative_golden_corpus_acceptance_protocol.md` defines the fail-closed G0–G3 evidence ladder | current evidence reaches G1 only; needs G2 multi-fixture human-reviewed structural goldens plus human-owned quality/representativeness criteria, then separate legal resolution and citation mapping |
| RuVector graph-vector infrastructure | `[proposed]`; synthetic capability checks only | needs TEI 1024d real corpus, RVF/redb materialization, crash consistency and citation contract |
| Retrieval / citation-safe answers | `[bounded]` real cosine-similarity ranking in the InMemory adapter + RetrievalGate (M161); retrieval scores are real per-result cosine values, not a constant. No live corpus/embedding yet. | needs future-schema `EvidenceSpan`/`SourceBlock` fixtures (both remain `deferred-undefined`), TEI 1024d corpus, quality metrics and exact byte round-trip |
| KnowQL | `[bounded]` hand-coded AST demo only | needs real parser and typed application executor; `ruvector-graph` Cypher execution is not relied upon |
| R035 | `[proposed]` active, not validated | standing graph-vector proof-boundary requirement |
| R038 | `[bounded]` active | standing independent review gate |
| Temporal legal ontology L1-L7 | `[proposed]` (ADR-0016..0022) | design crystallized M165; each layer graduates to `[bounded]` when its TDD Rust domain + fail-closed resolver ships, to `[validated]` only with real-corpus proof. L2 CTV is the first implementation priority once parser data is ready. |

## ACP / git-lex status (historical decommission only)

**Decommission decision accepted; active authority is archive-only (D104/R066).** Historical ACP/git-lex has no place in target architecture, runtime, CI, skills, requirements or source of truth; residual D3–D6 work is `[proposed]` manifest/archive hygiene and cannot reopen the boundary. Project-local history: `python_archive/acp_git_lex/` (archive-only); external `/root/git-lex-kit-acp/` is historical-only and unmodified. M108 disconnected the git-lex hook (no legacy chain; `.lex` byte-identical); general ADR/evidence/consistency checks survive only when rewritten without historical runtime or vocabulary dependencies.

## What law-nexus does NOT have (non-claims)

- production retrieval; legal answers; RuVector product runtime; KnowQL product
- parser completeness; Consultant/Garant parity; real-corpus link, temporal or
  deontic correctness
- cross-store atomicity, recovery, concurrency, scale or citation byte safety
- any `[validated]` product capability — all product work is `[bounded]`/`[smoke]`/`[proposed]`

## Repository truth rules

1. Read THIS first, not memory or archive history.
2. Lifecycle-tag state claims; never smooth bounded/smoke into validated.
3. Architecture/requirement claims need tracked source and executable proof.
4. Generated projections and harness reports are diagnostics, not product truth.
5. Rust owns product behavior; Python harness owns repository orchestration only.
6. ACP/git-lex history is archive-only and cannot gate or mutate active work.

## Maintenance

- Documentation correction and publication gaps are tracked in [`documentation-semantic-control-plan.md`](architecture/documentation-semantic-control-plan.md) and [`assessment/08-known-defects.md`](../assessment/08-known-defects.md); both are process evidence, not architecture authority.
- **Mandatory update** at every milestone closeout (D098 enforcement #2).
- One page. If it grows, split detail into tracked focused PRD sub-docs; do not restore retired pre-Rust filenames as active truth.
- Truth over optimism. If a claim has no cited evidence + proof gate, it is
  `[bounded]` or `[smoke]`, never `[validated]`.
