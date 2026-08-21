---
id: ADR-0009
title: Five-clock event-anchored temporal model (D118)
status: Accepted
lifecycle: "[bounded]"
date: 2026-07-22
supersedes: none
related: [ADR-0008, ADR-0010, D118]
---

# ADR-0009: Five-clock event-anchored temporal model

## Status

**Accepted [bounded]** — the five-clock model is proven by HC-09 runtime proof
(`ln-temporal`, `S10-HC-09-RT`). Clock substitution is hostile-rejected.
No legal-act-effect correctness is claimed.

## Context

Russian legal acts have multiple overlapping temporal dimensions: when a fact
occurred, when a proceeding started, when a legal act takes effect, when the
source was published, and when the system observed it. Collapsing any two
into a single "timestamp" causes evidence corruption.

## Decision

1. **Five exact clocks** — each is a distinct, named temporal dimension:

   | Clock | What it anchors | Owner |
   |-------|----------------|-------|
   | `factual_event` | When a real-world fact occurred | HC-10 (`ln-work`) |
   | `proceeding` | When a legal proceeding started | HC-10 (`ln-work`) |
   | `legal_act_effect` | When a proven act/status event enters the legal order; not publication, an `InForce` determination, or case applicability | HC-09 (`ln-temporal`) |
   | `source_publication` | When the source document was published | HC-01 (`ln-observe`) |
   | `system_observation` | When the system observed/ingested the data | HC-02 (`ln-inventory`) |

2. **Immutable typed evidence assertions** — evidence assertions are immutable
   typed events. Observation history is authoritative. Derived interval or
   bitemporal views are projections, not source truth.

3. **No silent substitution** — replacing one clock with another (e.g., using
   `source_publication` when `legal_act_effect` is unknown) is a hostile
   attack. HC-09 proves clock substitution is rejected.

4. **Typed unknown/conflict outcomes** — when a clock value is unknown, the
   system returns a typed `Unknown` or `Conflict` outcome, not a default or
   approximate value.

5. **Civil-day ordinal is a projection of `legal_act_effect`, not a sixth
   clock (Review 4 / KBO-R031).** YAML `calendar` bounds map an ISO day to a
   synthetic ordinal for fold/join. Impossible civil days (`2014-02-30`)
   fail closed. Provider title phrases such as «ред. от …» and «вступ. в
   силу с …» name different clocks and must not be collapsed. The ordinal
   is not a legal calendar, not vacatio legis, not CTV text, and not
   `InForce`.

### EA-04 clarification — closed role-bound anchors

The five clocks are a closed set of role-bound evidence anchors. Generic terms
such as transaction or recording time are qualified views, not additional
clocks: they must state whether they refer to `source_publication`,
`system_observation`, or both as independent facts. Neither may substitute for
`legal_act_effect`.

## Consequences

- Product temporal reasoning must name clocks explicitly and reject silent substitution.
- Derived intervals and bitemporal views are projections over immutable evidence, not source truth.
- Ontology layers (ADR-0016..0022) consume these clocks; they do not invent a sixth core clock.

## G0 note (2026-08-20, L0 `doc/review/review-25-08-2026.md`, disposition D216)

The five clocks are unchanged and remain closed. Two design projections
from the accepted compiler model are documented so they are not mistaken
for new clock roles:

- **`EffectSelector` is a projection of clock roles, not a sixth clock.**
  The ADR-0017 G0(c) selectors (`At`, `AfterPublication`, `OnEvent`,
  `OnCondition`, `ForRelationsAfter`, `RetroactiveTo`, `Unknown`)
  project `legal_act_effect` anchors plus explicit conditions; they add
  no temporal dimension and never substitute a clock role.
- **`known_as_of` binds `system_observation`.** In the deterministic
  checkout contract (ADR-0017 G0(d)), `known_as_of` is the
  `system_observation` role bound of the snapshot fold; `legal_as_of`
  ranges over effect selectors. Neither collapses into the other, and
  neither substitutes `source_publication` or `legal_act_effect`.

## Non-claims

- Applicable-law or effective-date legal correctness is not claimed.
- No product temporal database or bitemporal storage is selected.
- Clock values are synthetic in proof; real legal dates are not validated.
- Civil-day ordinal arithmetic is not a legal calendar, not a sixth clock,
  and does not decide force/applicability (Review 4 R4-05).
- The five-clock model is a **safety contract** (role-bound anchors, no silent
  substitution), **not** a complete temporal algebra. Interval overlap/merge,
  bitemporal correction ledgers, treating derived `effective_from/to` as source
  truth, legal-date validation, and applicable-law selection remain deferred
  algebra capabilities (RC11-F06 / `TemporalAlgebraCapability` inventory in
  `ln-temporal`). Inventory of deferred capabilities is not an implementation.

## References

- D118 in `.gsd/DECISIONS.md`
- HC-09 (`ln-temporal`, `S10-HC-09-RT`)
- `prd/architecture/m111-temporal-contract.md`
