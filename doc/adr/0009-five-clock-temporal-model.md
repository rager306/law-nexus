---
id: ADR-0009
title: Five-clock event-anchored temporal model (D118)
status: Accepted
lifecycle: "[bounded]"
date: 2026-07-22
superseds: none
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
   | `legal_act_effect` | When a legal act takes effect | HC-09 (`ln-temporal`) |
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

## Consequences

- Product temporal reasoning must name clocks explicitly and reject silent substitution.
- Derived intervals and bitemporal views are projections over immutable evidence, not source truth.
- Ontology layers (ADR-0016..0022) consume these clocks; they do not invent a sixth core clock.

## Non-claims

- Applicable-law or effective-date legal correctness is not claimed.
- No product temporal database or bitemporal storage is selected.
- Clock values are synthetic in proof; real legal dates are not validated.

## References

- D118 in `.gsd/DECISIONS.md`
- HC-09 (`ln-temporal`, `S10-HC-09-RT`)
- `prd/architecture/m111-temporal-contract.md`
