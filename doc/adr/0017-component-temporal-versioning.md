---
id: ADR-0017
title: Component temporal versioning (CTV) — ontology layer L2
status: Accepted
lifecycle: "[proposed]"
date: 2026-08-11
superseds: none
related: [ADR-0009, ADR-0010, ADR-0016, ADR-0018]
---

# ADR-0017: Component temporal versioning (CTV)

## Status

**Accepted [proposed]** — component-level temporal versioning model designed.
Not implemented. Moves to `[bounded]` when a fail-closed event-sourced CTV
resolver ships in Rust with TDD (Unknown/Conflict/MissingAnchor outcomes
proven); to `[validated]` only when provenance closes across the representative
corpus.

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
requires.

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
`legal_act_effect` = enters-legal-order; applicability is a profile concern
(ADR-0022, e.g. tax-anteriority). Transaction time is recorded independently.
This is **not a full bitemporal database**; observation/correction history is a
projection (ADR-0009 §3), but the valid/transaction distinction is explicit.

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

## Non-claims

- No corpus completeness; provenance gaps are expected and reported, not hidden.
- No claim that lexical component extraction (current `ln-decode` candidates) is
  a proven legal fact — candidates feed the CTV model only with anchored
  micro-event evidence.
- Not a full bitemporal database; the valid/transaction distinction is explicit
  but correction-history is a projection.
- LRMoo/CIDOC-CRM typing is a compatibility projection; the Rust domain types
  need not carry CRM class identifiers at runtime.

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
- ADR-0009 (five clocks; `legal_act_effect` = enters-legal-order; applicability
  is profile-scoped)
- ADR-0010 (evidence kernel; C13 relation registry is revisioned here)
- ADR-0016 (structural identity; CTV lives under Component Concept)
