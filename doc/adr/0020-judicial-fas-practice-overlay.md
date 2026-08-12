---
id: ADR-0020
title: Judicial, FAS and control-organ practice overlay (ontology layer L5)
status: Accepted
lifecycle: "[proposed]"
date: 2026-08-11
supersedes: none
related: [ADR-0009, ADR-0018, ADR-0019, ADR-0021]
---

# ADR-0020: Judicial, FAS and control-organ practice overlay

## Status

**Accepted [proposed]** — practice overlay model designed. Not implemented.
Moves to `[bounded]` when a PracticeEvidence port + EffectiveInterpretation
projection ship with TDD; to `[validated]` only with a real practice corpus.

## Context

A normative text is not its application. In Russian practice, the *effective
meaning* of a norm is shaped by: Plenum of the Supreme Court (толкование),
Constitutional Court (КС РФ), FAS / Presidium of the Supreme Court спорная
практика, and control-organ clarifications (Казначейство, Счётная палата,
Росздравнадзор, etc.). An agent that reasons only from normative text, ignoring
how courts and control organs actually apply it, produces legally naive
conclusions. The user's core requirement is that agents reason with practice.

Practice has its **own temporality**: a Plenum resolution changes interpretation
from its effective date (ex nunc), while a КС РФ annulment can operate ex tunc.
This is a distinct overlay with first-class temporality over the five ADR-0009
clock roles, not a sixth core clock and not a mutation of NormativeState
(ADR-0018).

## Decision

**EA-04 clarification:** practice has first-class temporality over the closed
ADR-0009 clock roles; “own clock” in the Context means its own temporal
behavior/projection, not a sixth core clock.

1. **PracticeEvidence as a separate, temporally-bounded port.** Sources:

   | Source | What it carries | Clock (ADR-0009) |
   |--------|----------------|------------------|
   | Plenum ВС | abstract norm interpretation | `legal_act_effect` (ex nunc) |
   | КС РФ | constitutional interpretation / annulment | `legal_act_effect` (ex nunc or ex tunc, typed) |
   | FAS / Presidium ВС | case precedent-analog | `proceeding` (case date) |
   | Control-organ clarification | departmental reading | `legal_act_effect` |

2. **Practice is NON-AUTHORITATIVE for evidence-kernel mutation.** Practice
   overlays *effective interpretation*; it does NOT rewrite CTV text (ADR-0017)
   or NormativeState (ADR-0018) directly. Exception: a typed КС РФ ex-tunc
   annulment is modeled as a status event with its own provenance, not a
   practice mutation. This honors D116/D120 authority singularity.

3. **EffectiveInterpretation(t) projection.** Given a norm (CTV + status) at
   date `t`, the overlay produces an `EffectiveInterpretation` — how the norm
   is actually applied in that period — composed from the practice evidence
   whose clocks are active at `t`. This is a *derived projection*, lifecycle
   `[bounded]`, never authoritative.

4. **Practice temporality is first-class.** A Plenum from 2020 does not
   retroactively reinterpret a 2018 event unless an explicit ex-tunc event
   exists. Clocks are never substituted (D118).

5. **Deontic / defeasibility overlay is bounded.** Norm-as-obligation/
   prohibition/permission with defeasibility (LKIF-inspired) may be used as a
   *bounded vocabulary* in the practice layer to express that a norm is
   "defeated" by a later interpretation, but it is an evidence overlay, not a
   replacement for the kernel (D119: kernel owns semantics; family modules own
   bounded vocabularies).

6. **LKIF / deontic-reified = compatibility reference (L5/L6 ladder),
   proof-gated**, not canon.

## Consequences

- Adds a PracticeEvidence port + EffectiveInterpretation projection above the
  normative layers (L1-L4) and below risk assessment (ADR-0021).
- Lets an agent distinguish "what the norm says" from "how it is applied at
  date t", directly serving the Суды/ФАС/Контроль requirement.
- Practice gaps resolve to "no active practice overlay", not to fabricated
  interpretation.

## Non-claims

- No claim of legal authority for any practice source; only real courts/organs
  are authoritative within their competence.
- Practice corpus does not exist yet; this layer is `[proposed]` until it does.
- Risk assessment (ADR-0021) consumes EffectiveInterpretation but remains a
  non-authoritative derived projection.

## References

- ADR-0009 (practice temporality projects over the five clocks; no sixth core clock)
- ADR-0010 (kernel authority; practice is non-authoritative for mutation)
- ADR-0018 (practice does not mutate NormativeState except typed ex-tunc)
- ADR-0019 (practice can surface conflicts, not rank-mutate)
- ADR-0021 (risk consumes EffectiveInterpretation)
