---
id: ADR-0008
title: Promotion and publication authority ceiling (D116/D120)
status: Accepted
lifecycle: "[bounded]"
date: 2026-07-22
supersedes: none
related: [ADR-0009, ADR-0010, ADR-0011, D116, D120]
---

# ADR-0008: Promotion and publication authority ceiling

## Status

**Accepted [bounded]** — the authority separation is proven by 20 hostile-case
runtime proofs (HC-04 promotion, HC-15 publication, HC-16 provisional
acceleration). The decision is architectural; no product storage, fencing or
transaction infrastructure is selected.

## Context

law-nexus requires two distinct singular authorities over the legal evidence
lifecycle:

- **Promotion Authority (D116):** decides which curated source material enters
  the authoritative corpus. Owned by the promotion use case (HC-04,
  `ln-promote`).
- **Publication Authority (D120):** decides which complete H1 unit becomes
  authoritative. Owned by the publication use case (HC-15, `ln-publish`).

These are **separate exclusive owners**, not co-owners. Conflating them
allows a promotion path to bypass publication completeness checks, or a
publication path to bypass promotion curation.

## Decision

1. **Sole Promotion Authority** (D116): exactly one application-owned component
   decides curated promotion. No adapter, invoker or contributor can mint
   promoted material independently.

2. **Sole Publication Authority** (D120): exactly one application-owned component
   decides authoritative H1 publication. No adapter, invoker or contributor
   can mint authoritative units independently.

3. **Complete H1-only authority:** only a complete candidate can receive
   publication authority. Partial, missing or incomplete candidates are
   rejected as non-authoritative.

4. **Provisional ceiling:** provisional acceleration (HC-16) remains
   non-authoritative. A provisional record cannot be directly promoted to
   authoritative; direct promotion is rejected.

5. **Dual-writer rejection:** a second writer for the same scope is rejected
   without mutating the first authoritative unit.

6. **Typed non-success outcomes:** `CompetingWriterRejected`, `Incomplete`,
   `Conflict`, `Cancelled`, `Failed`, `Duplicate`, `LabelMutationRejected`,
   `DirectPromotionRejected` — each is a typed outcome with explicit semantics.

## Consequences

- Promotion and publication remain separate singular authorities (D116/D120).
- Incomplete, dual-writer, and direct provisional promotion paths fail closed with typed outcomes.
- Downstream ontology/product layers must not invent a second publication authority.

## Non-claims

- No product storage, fencing or transaction infrastructure is selected.
- No distributed concurrency, network or multi-process authority claim.
- Legal correctness of promoted or published material is not claimed.

## References

- D116, D120 in `.gsd/DECISIONS.md`
- HC-04 (`ln-promote`), HC-15 (`ln-publish`), HC-16 (`ln-accelerate`)
- `prd/architecture/m111-final-architecture-baseline.md`
