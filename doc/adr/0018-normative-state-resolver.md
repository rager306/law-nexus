---
id: ADR-0018
title: NormativeState(t) — normative status resolver (ontology layer L3)
status: Accepted
lifecycle: "[proposed]"
date: 2026-08-11
supersedes: none
related: [ADR-0009, ADR-0017, ADR-0019, ADR-0021]
---

# ADR-0018: NormativeState(t) — normative status resolver

## Status

**Accepted [proposed]** — normative status model designed; **force dimension** has a
bounded offline Rust resolver (`resolve_force_status_at` / `ForceStatusTimeline` in
`ln-temporal`, TSG-004 S2–S3). Still not full multi-dimension product runtime.
Moves to `[bounded]` when provenance-backed force + CTV join + fail path are product-
shaped with representative fixtures; to `[validated]` only with real-corpus status-edge proof.

## Context

ADR-0017 answers "what was the text of article X on date Y?" But text is not
status. A norm may have valid text (a CTV exists) yet be **suspended**
(moratorium), **repealed**, **superseded**, or apply only **transitionally**.
An agent reasoning about a violation must know both the *text* and the
*legal status* at the governing clock date. Treating "text present" as "norm in
force" is the exact text≠status gap that produces wrong legal conclusions.

There is currently no domain type for normative status in law-nexus; `ln-temporal`
resolves clocks but not the *normative consequence* of those clocks.

## Decision

1. **NormativeState enum, provenance-backed:**

   | Status | Meaning |
   |-------|---------|
   | `InForce` | active, applies normally |
   | `Suspended` | temporarily inoperative (moratorium / presidential act) |
   | `Repealed` | ceased to have effect |
   | `Superseded` | replaced by a successor norm |
   | `Transitional` | applies only via a transitional provision (ADR-0021) |
   | `Unknown` | fail-closed: status evidence missing or conflicting |

2. **Status ≠ text.** NormativeState(t) is resolved independently of CTV text
   resolution (ADR-0017) and joined by component identity. A component can have
   a CTV but be `Suspended`; or be `Repealed` while its last CTV text is
   retained for historical citation.

3. **Status transitions are evidence-gated (C10 lifecycle, ADR-0010).** Each
   transition `InForce → Suspended → InForce` (or → `Repealed`) is a relation
   in the evidence kernel with its own AmendingAct/suspension/repeal provenance
   and its own `legal_act_effect` anchor (ADR-0009). No status transition is
   inferred from absence of evidence.

4. **Fail-closed default.** If status evidence is missing or conflicting at date
   `t`, the resolver returns `Unknown` — the agent reports "cannot determine
   status of article X on date Y" rather than assuming `InForce`. This is the
   R068 anti-smoothing boundary applied to status.

5. **Practice does not mutate NormativeState directly.** Judicial/FAS practice
   (ADR-0020) influences *effective interpretation*, not the NormativeState
   field itself, except where a constitutional court ruling annuls a norm ex
   tunc — modeled as a typed status event with its own provenance.

### EA-04 clarification — canonical status name

`NormativeState` is the canonical public name of this dimension and its future
Rust domain type. Earlier `NormativeStatus` wording in this ADR is a deprecated
alias for the same dimension, not a second concept. The enum values and
fail-closed rules are unchanged.

## Consequences

- Adds a NormativeState domain model + resolver above ADR-0017 CTV.
- Enables an agent to distinguish "norm exists as text" from "norm is in force",
  closing the text≠status gap.
- Surfaces real gaps honestly: components with no status evidence resolve to
  `Unknown`, never smoothed to `InForce`.

## G0 amendment (2026-08-20, L0 `doc/review/review-25-08-2026.md`, disposition D216)

Human disposition G0 (D216) accepted the Reviews 10–14 compiler model. This
amendment records the three ADR-0018 deltas at `[proposed]` design level;
no lifecycle promotion and no Rust type changes.

### G0(a) `NotYetInForce` added to the status vocabulary

The vacatio case proves a hole in the enum: 44-ФЗ adopted 05.04.2013,
published 08.04.2013, main entry into force **01.01.2014** (art. 114), while
188-ФЗ amended its text in July 2013 — before the base act entered into
force. The status model therefore gains `NotYetInForce` (adopted and/or
published, not yet effective) alongside `Unknown`. The seed rule follows:
a new Work's components default to `NotYetInForce` or `Unknown`, **never**
an automatic `InForce`; entry into force is a separate, evidence-gated
`EntryIntoForceEvent` per component (ADR-0017 G0 seed: Adoption /
OfficialPublication / EntryIntoForce / ApplicabilityConstraint are four
different events).

### G0(b) Force is an event-derived interval **set**

`resolve_force_status_at` returns one status at `t`, but the underlying
model is a set of intervals derived from status events (commence, suspend,
resume, repeal, expire, invalidate, restore — the ADR-0017 G0(g) Force op
family applied through this overlay). Suspension and resumption produce
multiple disjoint `InForce` intervals for the same component; any single
interval is a projection of that set. Static `effective_from`/`effective_to`
fields remain projections (ADR-0017 §2), never source truth.

### G0(c) Fork F13-T: `Transitional` leaves the status enum

Review 14 recommends removing `Transitional` from the force enum: being
applicable only via a transitional provision is a **version-choice relation**
(ADR-0021 `TransitionConstraint`), not a force state. Disposition: **fork
accepted** — `Transitional` migrates to the ADR-0021 overlay as a typed
effect/constraint; the NormativeState enum narrows to force states proper
(`InForce`, `NotYetInForce`, `Suspended`, `Repealed`, `Superseded`, plus
`Expired`/`Invalidated` as P1 design candidates). Until ADR-0021 carries the
moved semantics and the glossary syncs (P0), `Transitional` stays in the
table above as a **deprecated-in-design** value: no new runtime or glossary
row may build on it.

## Non-claims

- Offline `resolve_force_status_at` is **ForceStatus only**: not CTV/version join,
  not applicability, not practice overlay, not legal corpus correctness.
- `Unknown` on missing/conflicting same-day evidence is fail-closed, not a transition
  written into the timeline.

- No legal correctness of status resolution without real corpus + provenance.
- Practice overlay (ADR-0020) is separate and non-authoritative for status.
- Transitional status resolution depends on ADR-0021 `[proposed]`.
- **Dimensional separation (RC11-F09 / TSG-004):** force/status, version/text
  relation, applicability, and epistemic outcome are orthogonal design dimensions
  (`NormativeDimension` inventory in `ln-temporal`). Naming the separation does
  not implement a NormativeState resolver, CTV join, applicability decision, or
  knowledge base. Text presence ≠ `InForce`; `InForce` ≠ Applicable; Unknown is
  not a force or applicability success.
- **G0 amendment is design canon only:** `NotYetInForce`, the interval-set
  model and fork F13-T are `[proposed]` design decisions; the bounded
  `ForceStatusTimeline` runtime on HEAD does not implement them; no Rust
  enum change is minted by this text (P2), and `Transitional` removal
  completes only with the ADR-0021 + glossary sync (P0).

## References

- ADR-0009 (five clocks; status anchored to `legal_act_effect`)
- ADR-0010 (evidence kernel; C10 lifecycle gates status transitions)
- ADR-0017 (CTV; NormativeState joins by component identity)
- ADR-0019 (hierarchy; a status only resolves within its rank context)
- ADR-0021 (transitional provisions feed `Transitional` status)
