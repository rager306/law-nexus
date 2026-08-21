---
id: ADR-0021
title: Transitional provisions and risk assessment (ontology layer L6)
status: Accepted
lifecycle: "[proposed]"
date: 2026-08-11
supersedes: none
related: [ADR-0017, ADR-0018, ADR-0020]
---

# ADR-0021: Transitional provisions and risk assessment

## Status

**Accepted [proposed]** — transitional-resolver and risk-assessment model
designed. Not implemented. Moves to `[bounded]` when a TransitionalResolver
with fail-closed outcomes and a RiskAssessment derived projection ship with
TDD; to `[validated]` only with a real corpus of transitional cases and
practice precedent-analogs.

## Context

When a law changes, which version applies to an event that occurred during the
transition? Russian acts carry **переходные положения** (transitional
provisions) that answer this, and they are a frequent source of error in
procurement, budget, and construction practice. A separate but related need:
an agent should help a user **assess legal risk** — likelihood a conduct is
qualified as a violation, consequences, and mitigating circumstances — grounded
in precedent-analogs from practice (ADR-0020) at the governing clock date.

Neither transitional resolution nor risk are authoritative legal facts: they
are derived, explainable projections. They must never be smoothed into
authoritative conclusions.

## Decision

1. **TransitionalResolver — which version applies at date `t`.** Given an
   amendment `Act(t0) → amended by → Act(t1)` and an event between them:

   ```
   resolve_transitional(event_t, amendment) ->
       OldVersion      # transitional provision says old applies
     | NewVersion      # transitional provision says new applies
     | Transitional    # a specific transitional article applies
     | Unknown         # no transitional evidence — fail-closed
   ```

   The resolver consumes the transitional provisions as CTV text (ADR-0017)
   anchored to `legal_act_effect`; it MUST NOT infer transitionality by default.

2. **RiskAssessment — derived, non-authoritative projection.** Composed from:

   | Input | Source |
   |-------|--------|
   | normative text + status at `t` | ADR-0017 / ADR-0018 |
   | conflict resolution at `t` | ADR-0019 |
   | effective interpretation at `t` | ADR-0020 |
   | precedent-analogs at `t` | practice corpus (FAS/суд precedent) |
   | consequences (КоАП sanction at `t`) | CTV of the sanction norm |

   Output: a **RiskReport** with provenance — likelihood band, consequence,
   mitigating circumstances — each tied to evidence. It is explicitly marked
   non-authoritative and `[bounded]`.

3. **Risk is never a legal conclusion.** The RiskReport is decision-support,
   not a legal determination. It is consumed by the agent as advisory context,
   with full provenance, never as authoritative fact (D116/D120 authority).

4. **Fail-closed on missing precedent.** If no precedent-analog exists in the
   practice corpus at `t`, risk likelihood is `Unknown`, not "low by default".

5. **Limitation periods (давность, ст. 4.5 КоАП) are modeled as a temporal
   bound** on the risk window, anchored to the `proceeding` / `factual_event`
   clocks (ADR-0009), not to wall-clock.

### EA-04 clarification — transition, risk and applicability stay separate

A RiskReport never selects `OldVersion`, `NewVersion` or `Transitional`, and a
TransitionalResolver outcome never decides case applicability outside the
ADR-0023 protocol. Both remain fail-closed and preserve their existing
non-authoritative boundaries.

## Consequences

- Adds TransitionalResolver + RiskAssessment above the normative and practice
  layers.
- Directly serves the user's requirement that agents "evaluate risks" grounded
  in practice and transitional rules.
- Keeps risk honestly non-authoritative: it is the most an AI can offer without
  overclaiming legal authority (D098 anti-smoothing).

## G0 note (2026-08-20, L0 `doc/review/review-25-08-2026.md`, disposition D216)

Two deltas from the accepted compiler model — design level only:

- **`TransitionConstraint` is a typed effect, and the `Transitional`
  force value migrates here (fork F13-T, ADR-0018 G0(c)).** "Old version
  still applies for relation R until date D" is a version-choice
  constraint over the ADR-0017 G0(c) causal DAG (mode
  `ForRelationsAfter`), not a NormativeState. This ADR owns the migrated
  semantics; the glossary sync lands in P0.
- **`EventRelative` reference binding modes dock here.** A reference whose
  target fixes "as of event E" composes with `TransitionConstraint`
  resolution; both stay non-authoritative overlays over ledger facts.

## Non-claims

- No legal correctness; risk is advisory, not a determination.
- No actuarial probability — likelihood is a band grounded in precedent-analogs,
  not a calibrated probability.
- Depends on a practice corpus (ADR-0020) that does not exist yet.

## References

- ADR-0009 (clocks anchor the risk window and transitionality)
- ADR-0017 (CTV text of transitional provisions)
- ADR-0018 (status feeds risk; Transitional status)
- ADR-0020 (practice precedent-analogs feed risk likelihood)
- D116/D120 (authority — risk is non-authoritative)
