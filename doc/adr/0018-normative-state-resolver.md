---
id: ADR-0018
title: NormativeState(t) — normative status resolver (ontology layer L3)
status: Accepted
lifecycle: "[proposed]"
date: 2026-08-11
superseds: none
related: [ADR-0009, ADR-0017, ADR-0019, ADR-0021]
---

# ADR-0018: NormativeState(t) — normative status resolver

## Status

**Accepted [proposed]** — normative status model designed. Not implemented.
Moves to `[bounded]` when a NormativeStatus resolver with provenance-backed
transitions and a fail path ships in Rust; to `[validated]` only with real-corpus
status-edge proof.

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

1. **NormativeStatus enum, provenance-backed:**

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
   (ADR-0020) influences *effective interpretation*, not the NormativeStatus
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

## Non-claims

- No legal correctness of status resolution without real corpus + provenance.
- Practice overlay (ADR-0020) is separate and non-authoritative for status.
- Transitional status resolution depends on ADR-0021 `[proposed]`.

## References

- ADR-0009 (five clocks; status anchored to `legal_act_effect`)
- ADR-0010 (evidence kernel; C10 lifecycle gates status transitions)
- ADR-0017 (CTV; NormativeState joins by component identity)
- ADR-0019 (hierarchy; a status only resolves within its rank context)
- ADR-0021 (transitional provisions feed `Transitional` status)
