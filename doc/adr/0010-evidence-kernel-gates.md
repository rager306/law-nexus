---
id: ADR-0010
title: Evidence kernel gates (D119 C10/C12/C13)
status: Accepted
lifecycle: "[bounded]"
date: 2026-07-22
superseds: none
related: [ADR-0008, ADR-0009, ADR-0011, D119]
---

# ADR-0010: Evidence kernel gates

## Status

**Accepted [bounded]** — the C10/C12/C13 gates are proven by hostile-case
runtime proofs across HC-05 through HC-14. The compositional evidence kernel
is bounded synthetic proof only.

## Context

The evidence kernel is the compositional core that determines what enters the
authoritative evidence graph. Three gates control this:

- **C10:** lifecycle outcomes are immutable once committed.
- **C12:** identity cannot be merged across families.
- **C13:** relation types come from a closed registry; unregistered relations
  are rejected.

Without these gates, adapters could mutate committed evidence, merge
identities across domain boundaries, or introduce ad-hoc relation types.

## Decision

### C10: Immutable lifecycle outcomes

Once a lifecycle outcome is committed (promoted, published, admitted, etc.),
it cannot be overwritten. The application-owned component enforces this;
adapters cannot mutate committed state.

Proven by: HC-04 (promotion), HC-10 (work state), HC-14 (replay).

### C12: No-merge identity

Identity assertion (`ln-identity`, HC-07) is a single exclusive owner. Families
contribute evidence but cannot merge identities. A hostile adapter that
attempts identity erasure or cross-family merge is rejected.

Proven by: HC-07 (`S10-HC-07-RT`).

### C13: Closed relation registries

Relation types come from a closed registry (`ln-relation`, HC-08). Unregistered
or ad-hoc relation types are rejected. An adapter cannot introduce new relation
types at runtime.

Proven by: HC-08 (`S10-HC-08-RT`).

### Compositional evidence kernel

The kernel is compositional: each family module contributes evidence through
its ports, but no family module can assert authority over another family's
evidence. The composition root wires families together; families do not
import each other directly.

## Non-claims

- No product evidence storage or graph database is selected.
- Evidence kernel is synthetic in proof; real legal evidence is not validated.
- Family composition in production runtime is not proven.

## References

- D119 in `.gsd/DECISIONS.md`
- HC-04, HC-05, HC-07, HC-08, HC-10, HC-14
- `prd/architecture/m111-system-skeleton-contract.md`
