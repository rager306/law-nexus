---
id: ADR-0017
title: Component temporal versioning (CTV) — ontology layer L2
status: Accepted
lifecycle: "[proposed]"
date: 2026-08-11
supersedes: none
superseded_by: [ADR-0023#applicability-ownership] # §5 sentence only; CTV remains current
related: [ADR-0009, ADR-0010, ADR-0016, ADR-0018, ADR-0023]
---

# ADR-0017: Component temporal versioning (CTV)

## Status

**Accepted [proposed]** — component-level temporal versioning model designed.
The text-canon path is implemented as a `[bounded]` real-corpus prototype (M170
S01/S02: `collect_article_texts`, `build_text_log_from_articles`, `resolve_ctv`),
but the full event-sourced CTV resolver is not. Moves to `[bounded]` when a
fail-closed event-sourced CTV resolver ships in Rust with TDD (Unknown/Conflict/
MissingAnchor outcomes proven); to `[validated]` only when provenance closes
across the representative corpus.

## Context

ADR-0016 gives structural identity at the act/edition level. But an agent must
answer "**what was the text of article X on date Y?**" Russian acts are amended
component-by-component: ФЗ-188 amends paragraph 4 of part 1 of article 93 of
44-ФЗ, effective 2014-01-01. Tracking editions at whole-act granularity is
insufficient — the **component** (article/part/point) is the unit that changes,
and each amendment creates a new temporally-bounded version of that component.

Prior research identified ~118 editions of 44-ФЗ alone with no `valid_from`
anchor, and the absence of component-level provenance is the primary blocker for
R070 ("provenance of each edition up to the amending act"). Smoothing a lexical
candidate into a legal fact (R068 anti-pattern) is exactly the failure mode this
layer must prevent.

This layer adapts the **LRMoo-based, component-level, event-centric** model of
de Martim (arXiv:2506.07853 **v5**, 2026) to the Russian jurisdiction, aligned to
the five clocks (ADR-0009) and the evidence kernel (ADR-0010). The v5 model is
chosen over ELI/AKN/LexML precisely because it **reifies each legislative event
as a single first-class node** with global identity, making amendment correlation
*deterministic* rather than heuristic — the property our fail-closed resolver
requires. Review 4 keeps that event-centric pattern and **rejects** de Martim's
identity rule that each Temporal Version is a new F1 Work (see ADR-0016 §6).

## Decision

### 1. Component-level entities — three LRMoo levels, all F1/F2

| Entity | LRMoo type | Meaning | Key relations |
|--------|-----------|---------|---------------|
| **Component Concept (CC)** | F1 Work | abstract identity of a structural component (e.g. "статья 93") | R67 has part (component hierarchy); persists through time |
| **Component Temporal Version (CTV)** | F1 Work | semantic content of the component at a point in time | R10 is member of CC; R2 is derivative of (prior CTV) |
| **Component Language Version (CLV)** | F2 Expression | monolingual realization of a CTV | R3i realises CTV; P72 has language (ru); P190 has symbolic content |

Russian jurisdiction is monolingual (ru), so each CTV typically has one CLV;
the CC/CTV/CLV distinction is retained for semantic integrity (R10 conceptual
membership ≠ R67 work composition ≠ R3 realization ≠ R5 textual incorporation).

### 1a. Three L2 canons, not one “CTV” blob (Review 4 R4-02)

Keep these event logs distinct. Projections may join them; they must not
collapse into a `NormativeBlob` store type.

| Canon | Event log | Projection | Not |
|-------|-----------|------------|-----|
| Structural membership | attach/detach | `StructuralAst` / `fold_membership_at` | text, force |
| Expression presence | include/exclude | `fold_expression_presence` | inheritance across Expressions |
| Text CTV | text-change micro-events | `resolve_CTV(cc, t)` | **shipped** (bounded: real-corpus `resolve_ctv`, M170 S01) |

Industrial ops (`renumber`/`move`/`split`/`merge`) feed the membership log.
Force is ADR-0018 overlay, never a tree field.

### 1b. AmendmentEvent is the n-ary causal node (Review 4 R4-03)

A legislative change binds author, target CC, resulting text/structure, clocks
and legal-effect facet. Collapsing it to binary `eli:amends` discards that
structure. One `AmendmentEvent` may carry several **facets** without merging
them into one field:

- `structural` — attach/detach, include/exclude;
- `industrial` — renumber / move / split / merge;
- `text` — CTV wording (bounded: text-facet drafts via `changed_article_texts`, KBO-R061);
- `force` — NormativeEffect, never inferred from TextChange.

Evidence class is mandatory: `legislative` (from an amending act) >
`hypothesized_from_oracle_diff` (from two consolidated editions) >
`editorial_hint` (Consultant «обзор изменений»). A later legislative event
supersedes a hypothesized one. An overview file never upgrades to
`legislative`.

### 1c. EditionOracle is a checksum, not canon (Review 4 R4-04)

A Consultant/Garant consolidated edition (`ред. от …`) is an
`EditionOracle`: observed composition + text at a title date. It is a
**Manifestation** of an Expression, not the parent of the next edition and
not the event log. Control rule: `fold(events, t) ≈ snapshot(oracle@t)`.
Drift is healed by a new event or an explicit waiver, never by writing the
oracle tree back as canon. Current 44-ФЗ disk corpus is one late C2 oracle
plus a C2hint overview; C0 (2013 seed) and C1 (amending ФЗ files) are
absent — Coverage into the past is Unknown, not reconstructed from 2025.

### 2. Validity is event-sourced, NOT stored as a static attribute

A CTV does **not** store its validity interval as a field. Following
event-sourcing, the interval `[t_start, t_end)` is **derived** from the events
bounding the CTV's life cycle: `t_start` from the event that R16 created it,
`t_end` from the event that P93 took it out of existence (open-ended while no
terminating event exists). This prevents the M161-style fake cascade
(truncate-by-key / infer-validity-by-order) by construction.

### 3. Macro/micro event hierarchy (P9 consists of)

A **macro-event** ("Enactment of Amending Act X") is formally composed of
multiple concurrent **micro-events** via **P9 consists of**. Each micro-event
is a single granular modification to one component's version:

| Operation | Event typing | Asserts |
|-----------|-------------|---------|
| insertion | F27 Work Creation only | R16 created |
| repeal | E64 End of Existence only | P93 took out of existence |
| wording amendment | **F27 ∩ E64** (joint) | P16 used + P93 + R16 |

The joint F27∩E64 typing is deliberate: a constitutive legal change
simultaneously **terminates** one normative entity and **inaugurates** another
(CIDOC CRM state-transition precedent, e.g. death = E64∩E7). We deliberately
avoid E11 Modification because P31 has modified ranges over physical things
(E24/E18), whereas a CTV is a conceptual F1 Work (E28).

A wording-amendment micro-event documents that it:
- **P16 used specific object** — the source provision of the amending instrument
  (authoritative provenance);
- **P93 took out of existence** — the preceding CTV(n-1) of the amended component;
- **R16 created** — the new CTV(n) incorporating the change.

### 4. Deterministic Compilation resolver — fail-closed

Given `(component_concept_id, date t)`:

```
resolve_CTV(CC, t) -> CTV with derived interval covering t AND a proven micro-event edge
  | Unknown          # no CTV covers t OR provenance gap
  | Conflict         # two CTVs claim validity at t (double-termination etc.)
  | MissingAnchor    # creation/termination event evidence missing
```

Whole-act text at date `t` = deterministic union of each component's CTV(t).
If **any** component resolves to Unknown/Conflict/MissingAnchor, the compilation
is fail-closed (R068 anti-smoothing), never partially assembled.

### 5. Bitemporal awareness (transaction time vs valid time)

Legal time is bitemporal. Following Palmirani & Brighi and ELI:
- **transaction time** — when the norm was recorded (publication/recording),
  captured via **P4 has time-span** on the event;
- **valid time** — when the norm produces legal effect, the derived interval
  `[t_start, t_end)`. This decomposes further into **enters-legal-order** vs
  **applicability**, which diverge under vacatio legis (deferred onset),
  retroactive (ex tunc) effect, and lex mitior.

law-nexus models valid-time decomposition through the five clocks (ADR-0009):
`legal_act_effect` = enters-legal-order. The original sentence assigning applicability
as a profile concern is narrowly superseded by ADR-0023: profiles supply versioned
facts/predicate declarations, while the neutral core owns decision/abstention/trace.
Transaction time is recorded independently. Under the ADR-0009 role model,
transaction/recording evidence must identify `source_publication`,
`system_observation`, or both as independent anchors; it is not one composite
clock and cannot substitute for `legal_act_effect`. No applicability runtime is
implied. This is **not a full bitemporal database**; observation/correction
history is a projection (ADR-0009 decision 2), but the valid/transaction
distinction is explicit.

### 6. URI form — LexML-compatible (project-local)

```
urn:lex:ru:federal:zakon:2013-04-05;44-fz@2014-01-01!art93_ch1_p4       # CTV
urn:lex:ru:federal:zakon:2013-04-05;44-fz@2014-01-01~texto;ru!art93     # CLV
```

LexML URN `norm@version~language!part` is an **addressing scheme**, not the
model — our CTVs are first-class F1 Works with explicit derivative lineage,
which LexML/ELI/AKN do not provide (they identify a provision within a
document snapshot; they do not reify the event as a queryable causal entity).

## Consequences

- Adds a CC/CTV/CLV domain model + event-sourced fail-closed resolver above
  ADR-0016 structural identity and below ADR-0018 normative state.
- Closes the R070 edition-provenance gap and hardens the R068 anti-smoothing
  boundary at the component granularity via reified events.
- Demands real amendment micro-event provenance from the corpus — missing
  edges surface as `Unknown`, which is honest, not a blocker to ship the
  resolver.
- LRMoo terminology (F1/F2, R2/R10/R67/R3, P9/P16/P93/R16) is the
  *compatibility/interoperability reference* (D046 L6 ladder); the project-local
  evidence kernel (D119 C10/C12/C13) owns the substance. LRMoo does not replace
  the kernel.

## Review 5 amendments (2026-08-14, L0 `doc/review/review-14-08-2026.md`)

### R5-02: `resolve_CTV` is the main gap vs de Martim v5

de Martim v5 ships CTV/CLV with P190 symbolic content for deterministic
point-in-time text reconstruction. law-nexus has the **event-sourced spine**
(`VersionedMembershipLog`, `fold_membership_at` → `StructuralAst`) and now
ships a **bounded prototype** `resolve_ctv` (KBO-R046): `TextVersionLog` +
`TextVersionEvent` + `resolve_ctv(log, cc, day)` returning `Resolved { text }`,
`Unknown`, or `Conflict`. 6 TDD tests green. Text is a runtime value, not
persisted legal text. Full integration shipped in M170 S01: `collect_article_texts`
(ln-decode) extracts article bodies from real XML, the CLI `inspect`/`replay`
wire `build_text_log_from_articles`, and `resolve_ctv` returns the real article
body on the corpus (see Real-Corpus Evidence below). Bounded: one export layout;
not legal correctness, not corpus coverage, not an Applicable claim.

### R5-03: `edition_ast_at(t)` unifies the three L2 canons

The three canons (§1a: membership / presence / text) each have a separate
fold. `edition_ast_at(t)` should combine them:
`CompositionAst(t) = fold(membership ≤ t)`;
`EditionAst(t) = filter(CompositionAst, fold_presence ≤ t)`;
`TextAst(t) = resolve_CTV(cc, t)` [shipped as bounded `resolve_ctv`, M170 S01;
full `edition_ast_at(t)` unifier still open]. This function closes the S_fold
exit criterion (still partial: membership and presence folds landed, text canon
bounded via `resolve_ctv`).

### R5-05: macro/micro event P9 consists of

de Martim v5 models macro-event ("Enactment of Amending Act X") composed
of micro-events via P9 consists of. law-nexus has `AmendmentEvent` as
n-ary with facets (§1b) but no explicit macro→micro composition hierarchy.
A macro-event = one AmendingAct (e.g. ФЗ-504); micro-events = per-CC
operations (attach art. 93 п. 4, renumber art. 112). Formalizing this
hierarchy makes provenance traceable from act-level to component-level.

### R5-04: Oracle diff and heal

`drift(t) = fold(events, t) Δ snapshot(oracle@t)`. Non-zero drift is healed
by a new event or explicit waiver — never by writing the oracle tree back
as canon (§1c above). On 402-ФЗ, `assemble_membership_ast` gives 4 roots /
37 nodes; oracle diff against the WordML snapshot is the S_verify entry point.

### R5-11: language versioning decision

LV (Language Version) is not needed for monolingual Russian Federation.
Defer until ЕАЭС/СНГ multilingual support is explicitly required.

## Real-Corpus Text CTV Evidence (2026-08-15, M170-2gh5r6)

`resolve_ctv` now carries real article text, not marker titles:

- `collect_article_texts` (ln-decode) stores the statya marker title
  separately — the marker line never enters `ArticleText::text`; accumulation
  starts after the marker and stops at the next Statya|Glava|Razdel|Paragraph(§)
  boundary; nested chast/punkt/podpunkt lines belong to the owning article;
  ProviderComment never contributes.
- `build_text_log_from_articles` (ln-kb-ontology) mints TextVersionEvents
  from plain tuples — no ln-decode dependency, empty body falls back to
  the title.
- Measured on the real corpus: edition-0118 — 86/94 articles carry full
  text, `resolve_ctv(cc:44-fz:statya-1)` returns 6231 chars of real text,
  85 bound statya resolve (residual: no-prose articles plus one same-day
  duplicate-number Conflict — honest count).
- Text facet between editions: 0001→0002 (rev 2013-07-02) is structurally
  empty at marker level yet `changed_article_texts` drafts 3 text-facet
  events; `resolve_ctv` on the merged two-day timeline returns different
  real texts at the two days with no future leakage at the seed day.
  The CLI `replay` command reports `text: {facet_drafts: N}`.

Bounded: extraction/resolution mechanics on one export layout; not legal
correctness, not corpus coverage, not an Applicable claim.

## Punkt/subunit text-CTV contract (KBO-R067, 2026-08-20, M172-tsa1j7)

Design freeze of which layer any punkt/subunit text-CTV claim lives in; the
binding three-layer table and contract clauses are tracked in
`prd/architecture/kb-ontology-requirements.md` (KBO-R067). This section
records the boundary and adds no promotion: the ADR lifecycle stays
`[proposed]`.

- **Three text-CTV layers, never merged into one «punkt CTV» claim:**
  article unit-body CTV at `statya` level (KBO-R060, M170) `[bounded]`;
  punkt-as-unit CTV on `government_resolution`/`departmental_order` — a
  separate `ArticleText` per punkt at the group's YAML
  `granularity: punkt`, executed surface being the `subordinates` CLI
  report on the real Garant PP_60 corpus (M171 S03) `[bounded]`; and
  punkt-as-subunit on `federal_law@v1`, which folds into the owning statya
  body and never mints its own `ArticleText` or CC (D190/D192).
- **Mint level is profile data, not a hardcoded `"statya"`:** the level is
  the document group's YAML granularity; a wrong-level mint fails closed
  (0 Resolved with Unknown — never a silent article-CTV). Locked by
  `crates/ln-decode/tests/punkt_subunit_ctv_contract.rs` and
  `crates/ln-kb-ontology/tests/punkt_subunit_ctv_contract.rs` `[bounded]`.
- **Counting rule (D187):** `ctv_resolved` = unique Resolved CCs on the
  path's mint level (Conflict/Unknown excluded); an empty unit body falls
  back to the title; an unbound number emits no event.
- **Non-claims:** not S4, not Applicable, no nested 44-ФЗ punkt CC (the
  registry stays 8 glava + 94 statya), no inspect wiring (inspect's
  hardcoded statya mint yields an honest 0 on a ПП; wiring is M172 S02),
  no raw legal text in CLI JSON or tracked artifacts, and no lifecycle
  promotion of ADR-0016..0022 (R074 stays active/bounded; TSG-017 ceiling
  S3).

## Non-claims

- `HierarchyMarker` / `map_hierarchy_marker` is a **fail-closed candidate lift**:
  unmapped markers are `Unknown`; number+level does not mint ComponentConcept,
  force, Expression presence, or legal fact. Parser output remains a candidate.

- `component_in_expression` / `fold_expression_presence` is **presence only**:
  not CTV text, not force, not decode HierarchyNode→CC, not calendar legal_act_effect.
  Later Expression does not silently inherit earlier presence.

- `fold_membership_at` / `StructuralAst` (TSG-013) is a **projection** of versioned
  membership events at a synthetic effect day. It is not CTV text resolution, not
  Expression binding, not calendar `legal_act_effect`, and not whole-act text compile.

- Bounded-runtime `apply_industrial_op` / `StructuralEventLog` in `ln-temporal`
  (TSG-003/013 ladder S3) mutates synthetic membership only; it is not event-sourced
  CTV product runtime, not legal amendment correctness, and not corpus compilation.


- No corpus completeness; provenance gaps are expected and reported, not hidden.
- No claim that lexical component extraction (current `ln-decode` candidates) is
  a proven legal fact — candidates feed the CTV model only with anchored
  micro-event evidence.
- Not a full bitemporal database; the valid/transaction distinction is explicit
  but correction-history is a projection.
- LRMoo/CIDOC-CRM typing is a compatibility projection; the Rust domain types
  need not carry CRM class identifiers at runtime.
- **TextChangeEvent vs NormativeEffectEvent** (RC11-F07 / TSG-002): the kinds are
  named and separated as a **design-only** taxonomy in `ln-temporal`
  (`LegislativeEventKind`). Lexical or amendment text does not prove legal
  effect. Design taxonomy inventory is not an executable CTV event runtime,
  amendment micro-event engine, or legal-effect determination.
- **Structural membership + industrial ops (RC11-F08 / TSG-003/013):** `ln-temporal`
  hosts a fail-closed structural membership graph and industrial op planner
  (`renumber`/`move`/`split`/`merge`) with whole-act compile fail-closed on
  incomplete membership. This is a **structural implementation spine**, not a
  full event-sourced CTV resolver, not legal amendment correctness, and not
  representative-corpus compilation product readiness.
- Review 4 assembly vocabulary (`AmendmentEvent`, `EditionOracle`, corpus
  roles C0–C3, evidence classes, assembly FSM) is **design inventory** in
  YAML/KBO. It is not a store node kind, not `resolve_CTV`, and not a 44-ФЗ
  history reconstructed from one 2025 XML.

## References

- de Martim, H. (2026). *Modeling the Diachronic Evolution of Legal Norms: An
  LRMoo-Based, Component-Level, Event-Centric Approach to Legal Knowledge
  Graphs.* arXiv:2506.07853 **v5**. (LRMoo + CIDOC CRM; F27∩E64 event typing;
  macro/micro events via P9; event-sourced validity; bitemporal valid/transaction
  time. Case study: Brazilian Constitution.)
- Palmirani, M. & Brighi, R. — legal time model (enters-legal-order vs
  applicability; vacatio legis; ex tunc; lex mitior).
- D046 adoption-ladder (L6 compatibility for LRMoo/AKML/ELI)
- R068 (five clocks), R070 (edition provenance)
- ADR-0009 (five clocks; `legal_act_effect` = enters-legal-order)
- ADR-0023 (narrow supersession of §5 applicability ownership; core protocol + profile inputs)
- ADR-0010 (evidence kernel; C13 relation registry is revisioned here)
- ADR-0016 (structural identity; CTV lives under Component Concept)
