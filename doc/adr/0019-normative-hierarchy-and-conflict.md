---
id: ADR-0019
title: Normative hierarchy and conflict resolution (ontology layer L4)
status: Accepted
lifecycle: "[proposed]"
date: 2026-08-11
superseds: none
related: [ADR-0018, ADR-0020, ADR-0022]
---

# ADR-0019: Normative hierarchy and conflict resolution

## Status

**Accepted [proposed]** — hierarchy and conflict-resolution model designed.
Not implemented. Moves to `[bounded]` when a ConflictResolver with explainable
maxim selection ships in Rust; to `[validated]` with real conflict corpus.

## Context

Russian law has a strict normative hierarchy (Constitution > Federal
Constitutional Law > Federal Law / Code > Presidential decree > Government
resolution > departmental act > regional > local) and classical conflict maxims
(lex superior derogat inferiori; lex specialis derogat generali; lex posterior
derogat priori). In practice these collide constantly: Budget Code vs Civil Code
vs 44-FZ vs 61-FZ; a Government resolution vs a Federal Law; a later general law
vs an earlier special law.

Prior research (`prd/research/ontology_architecture_requirements/05-03`) selected
the RusLegalCore domain ontology as a compatibility reference for hierarchy and
the conflict maxims, at adoption-ladder level L5 (compatibility, proof-gated per
D046). law-nexus needs its own explainable resolver, not a silent priority pick.

## Decision

1. **NormativeRank enum (Russian-jurisdiction):**

   ```
   Constitution > FKZ > FederalLaw/Code > PresidentialDecree >
   GovernmentResolution > DepartmentalAct > RegionalLaw > LocalAct
   ```

   Industry codes (БК, ГрК, 44-ФЗ, 61-ФЗ, КоАП) sit at the `FederalLaw/Code`
   rank; their industry priority is a profile concern (ADR-0022), not a rank
   elevation.

2. **Conflict resolution maxims — deterministic and explainable.** Given two
   conflicting norms at date `t`, the resolver applies maxims in a defined
   precedence and ALWAYS returns the maxim + evidence that decided priority:

   | Maxim | Rule |
   |-------|------|
   | `lex superior` | higher rank wins (FKZ > FederalLaw) |
   | `lex specialis` | special norm wins over general, at equal rank |
   | `lex posterior` | later norm wins, at equal rank and equal specificity |
   | `industry priority` | profile-specific (БК for budget, ГрК for construction) |

3. **Explainability is mandatory (R035/05-03-07).** A conflict outcome carries
   `decided_by: <maxim>, evidence: <relation+source>`. An agent never states
   "norm X prevails" without provenance.

4. **Fail-closed on underdetermined conflicts.** If maxims do not resolve
   (e.g., equal rank, equal specificity, equal date — a genuine legal conflict),
   the resolver returns `Conflict`, surfacing the collision for human/profile
   judgment, never silently picking one.

5. **Hierarchy is status- and time-aware.** Conflict resolution composes with
   ADR-0018 NormativeState(t): a `Repealed`/`Suspended` norm does not prevail
   regardless of rank. All comparisons happen at the governing clock date
   (ADR-0009).

6. **RusLegalCore = compatibility reference (L5), not canon.** Project-local
   hierarchy lives in the evidence kernel; RusLegalCore mappings are a
   deterministic, reversible projection for interoperability.

### EA-04 clarification — profile priority is not rank elevation

`industry priority` is a versioned profile-supplied input to the explainable
ConflictResolver. It never changes `NormativeRank`, silently reorders the core
maxims, or decides applicability outside ADR-0023. An underdetermined result
remains `Conflict` for human review.

## Consequences

- Adds NormativeRank + ConflictResolver above ADR-0018 NormativeState.
- Enables an agent to reason about which norm governs a situation at date `t`
  with explainable provenance.
- Industry-specific priority (budget vs construction) is deferred to profile
  adapters (ADR-0022), keeping the core hierarchy industry-neutral.

## Non-claims

- No legal correctness of conflict resolution without real conflict corpus.
- Industry priority rules are profile-defined, not core-resolved.
- Constitutional-court annulment effects (ex tunc) modeled via ADR-0018/0020,
  not by rank mutation.

## References

- `prd/research/ontology_architecture_requirements/05-03-ruslegalcore-domain-ontology-collisions.md`
- D046 adoption-ladder (L5 compatibility)
- ADR-0009 (five clocks; conflict resolved at governing date)
- ADR-0018 (status-aware comparison)
- ADR-0020 (practice can surface, not rank-mutate, conflicts)
- ADR-0022 (industry priority profiles)
