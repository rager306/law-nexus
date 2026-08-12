# EA-04 ADR amendment and applicability decision assessment

**Assessment class:** frozen ADR corpus review
**Status:** `[bounded]` process evidence; `PASS`; EA-04 complete
**Tested revision:** `93ce8a79cabd61a150a048a38b8a6072662ab6de`
**Review date:** 2026-08-11
**Human decision:** D148 — neutral core evaluator with versioned profile inputs

## 1. Scope

This record assesses:

- ADR-0023 applicability protocol ownership;
- the narrow reciprocal supersession of ADR-0017 §5 applicability ownership;
- EA-04 clarification notes in ADR-0009, 0017, 0018, 0019, 0020, 0021 and 0022;
- synchronization of ADR index, ARCHITECTURE, README, Product Contract, requirements projection, temporal crosswalk and cross-matrix.

It does not assess applicability implementation, legal correctness, case outcomes, procurement completeness, release readiness or EA-09/EA-10 acceptance.

## 2. Frozen checks

| ID | Result | Evidence at tested revision |
|----|--------|-----------------------------|
| EA04-01 single residual ADR | PASS | exactly one `doc/adr/0023-*.md`; no ADR-0024..0032 package |
| EA04-02 D148 fidelity | PASS | ADR-0023 assigns evaluation/decision/abstention/trace to neutral core and versioned facts/predicate declarations/lists to profiles |
| EA04-03 narrow supersession | PASS | ADR-0023 supersedes only ADR-0017 §5 ownership sentence; ADR-0017 reciprocally names ADR-0023 and keeps CTV substance current |
| EA04-04 lifecycle honesty | PASS | ownership `[proposed]`; applicability runtime/product capability `[deferred]`; O1–O7 unchanged |
| EA04-05 TQ-02 | PASS | transaction/recording time maps to independent publication/observation anchors, never a composite clock or legal-effect substitute |
| EA04-06 TQ-03 | PASS | `NormativeState` canonical; `NormativeStatus` deprecated alias |
| EA04-07 TQ-06 | PASS | practice has first-class temporality over the five clocks, not a sixth clock |
| EA04-08 TQ-07 | PASS | industry priority is a versioned profile input and never elevates `NormativeRank` |
| EA04-09 deferred gaps | PASS | TQ-04 correction protocol and TQ-05 temporal reference algorithm remain deferred with triggers |
| EA04-10 surface sync | PASS | ADR index, oracle, entrypoint, Product/RQ, crosswalk and matrix cite ADR-0023 with runtime-absent wording |
| EA04-11 non-claims | PASS | no `Applicable`/`NotApplicable` runtime or legal/product readiness is claimed |

## 3. Decision meaning

D148 and ADR-0023 decide architecture ownership only:

```text
Neutral Rust core
  owns predicate evaluation,
       decision outcomes,
       fail-closed abstention/prerequisite gates,
       ExplainableTrace.

Versioned profiles
  supply CaseFacts schemas and instances,
         special-predicate declarations,
         classifiers/registers/industry lists.
```

Profiles cannot add clocks, mutate CC/CTV/CLV or NormativeState, elevate kernel ranks, rewrite transitional outcomes, emit final applicability decisions outside the core protocol, or use LLM/derived graph output as predicate truth.

## 4. Retained advisories

- ADR-0018 historical body still contains `NormativeStatus`; the EA-04 note explicitly marks it a deprecated alias rather than deleting history.
- ADR-0020 historical Context still says “own clock”; the EA-04 Decision note and oracle clarify that this means first-class temporality over five clocks.
- At tested revision `93ce8a79`, the project-wide `superseds` front-matter spelling was retained for compatibility and required a separate migration rather than a one-file cleanup. That active-plane migration was completed later in `28a51fc`: active ADRs now use canonical `supersedes` / `superseded_by`, while legacy-key parsing remains historical-input compatibility only.
- TQ-04 and TQ-05 remain future decisions only if their implementation triggers become load-bearing.

## 5. Result

EA-04 is complete for the documentation-only architecture package at the tested revision. D5/D6 roadmap/readiness alignment may consume this decision. Product implementation must remain blocked until a later planned Rust slice provides domain/port contracts, hostile abstention tests and representative evidence.

## 6. Non-claims

- No applicability runtime, Rust type/port, procurement profile or case decision is implemented.
- No legal correctness or authoritative legal interpretation is validated.
- No ontology layer is promoted above `[proposed]`.
- No full supersession of ADR-0017 or package ADR-0023..0032 exists.
- EA-04 completion is not EA-09 external assessment or EA-10 final process disposition.
