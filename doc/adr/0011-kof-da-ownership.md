---
id: ADR-0011
title: KOF-DA ownership — twenty exclusive capability owners (D123)
status: Accepted
lifecycle: "[bounded]"
date: 2026-07-22
superseds: [ADR-0005#crate-map-only]
related: [ADR-0005, ADR-0008, ADR-0009, ADR-0010, D123]
---

# ADR-0011: KOF-DA ownership — twenty exclusive capability owners

## Status

**Accepted [bounded]** — the exact owner table is proven by 20 hostile-case
runtime proofs (HC-01 through HC-20). Each capability has exactly one primary
owner. Invoker/contributor/adapter are not co-owners.

## Context

law-nexus has 20 hostile-case capabilities (HC-01 through HC-20). Without
exact ownership assignment, two components could claim authority over the same
capability, leading to composite ownership drift — exactly the anti-pattern
D098 warns against.

KOF-DA (Kernel Ownership Family — Domain Authority) fixes each capability to
exactly one primary owner. O1/O2/O3 ceilings constrain what an owner can
claim.

## Decision

### Exact 20 capability-to-primary-owner bindings

| HC | Capability | Primary owner (crate) |
|----|-----------|----------------------|
| HC-01 | Observe Source | `ln-observe` |
| HC-02 | Inventory Immutable Intake | `ln-inventory` |
| HC-03 | Dispose Review | `ln-dispose` |
| HC-04 | Commit Curated Promotion | `ln-promote` |
| HC-05 | Decode and Anchor | `ln-decode` |
| HC-06 | Gate Lifecycle | `ln-gate` |
| HC-07 | Assert Identity | `ln-identity` |
| HC-08 | Validate Relation | `ln-relation` |
| HC-09 | Resolve Five-Clock State | `ln-temporal` |
| HC-10 | Transition Work State | `ln-work` |
| HC-11 | Compute Dependency Closure | `ln-closure` |
| HC-12 | Rebuild Disposable Projection | `ln-projection` |
| HC-13 | Decide Admission | `ln-admission` |
| HC-14 | Coordinate Checkpoint and Replay | `ln-replay` |
| HC-15 | Publish Authoritative H1 Unit | `ln-publish` |
| HC-16 | Publish Provisional Acceleration | `ln-accelerate` |
| HC-17 | Query Evidence-Bounded State | `ln-query` |
| HC-18 | Resolve Citation | `ln-citation` |
| HC-19 | Emit Safe Diagnostics | `ln-diagnostic` |
| HC-20 | Evaluate Conformance | `ln-conformance` |

### O1/O2/O3 ceilings

- **O1:** The primary owner is the sole authority for the capability's
  lifecycle outcomes. No other component can mint authoritative outcomes for
  this capability.
- **O2:** Invokers and contributors are not co-owners. They call the primary
  owner's API; they do not share authority.
- **O3:** Adapters provide infrastructure but cannot claim ownership over
  capability semantics. A hostile adapter that attempts to override the
  primary owner is rejected.

### Non-co-ownership

No two capabilities share a primary owner. Each crate owns exactly one
capability. Cross-capability composition happens through ports, not through
shared mutable state.

## Consequences

- Product capabilities map to exclusive `ln-*` owners; shared ownership is rejected.
- This ADR reciprocally supersedes only ADR-0005's crate-map sketch; ADR-0005 remains `[bounded]` authority for Rust layering. Conflicting historical crate sketches are non-prescriptive.
- Ownership map is not product readiness proof.

## Non-claims

- Ownership is proven in bounded synthetic hostile-case tests only.
- No product runtime ownership enforcement (e.g., distributed locks) is
  selected.
- Real corpus or production-scale ownership is not validated.

## References

- D123 in `.gsd/DECISIONS.md`
- HC-01 through HC-20 (all hostile-case runtime proofs)
- `prd/architecture/m111-system-skeleton-contract.md`
- `prd/research/m111/whole-system-adversarial-closure.md`
