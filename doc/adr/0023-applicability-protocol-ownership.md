---
id: ADR-0023
title: Applicability protocol ownership and profile inputs
status: Accepted
lifecycle: "[proposed]"
date: 2026-08-11
supersedes: [ADR-0017#applicability-ownership] # §5 sentence only
related: [ADR-0009, ADR-0017, ADR-0018, ADR-0019, ADR-0020, ADR-0021, ADR-0022]
---

# ADR-0023: Applicability protocol ownership and profile inputs

## Status

**Accepted [proposed]** — ownership and fail-closed protocol boundaries are decided. A minimal fail-closed abstention kernel exists in `ln-applicability` v0 (prerequisite gates + mandatory trace only). A structural NormRule IR (conditions, exceptions, defeaters, temporal scope) exists as a **design-only** fail-closed spine for RC11-F04a; IR presence never mints Applicable/NotApplicable. No Applicable/NotApplicable product result, predicate evaluation algebra, procurement profile pipeline, or case-level legal claim exists. The decision may move to `[bounded]` only after Rust domain/port contracts and hostile abstention paths ship; any stronger product claim additionally requires representative real-case evidence and human acceptance under ADR-0015.

This ADR narrowly supersedes only the ADR-0017 §5 sentence that assigns applicability as a profile concern. ADR-0017 remains authoritative for CTV, event-sourced validity, bitemporal awareness and the distinction between enters-legal-order and applicability.

## Context

ADR-0017 separates `legal_act_effect` (enters-legal-order) from case applicability and describes applicability as profile-sensitive. ADR-0021 owns transitional version choice. ADR-0022 owns versioned industry inputs, special norms, practice weighting and risk factors while prohibiting profiles from mutating the neutral kernel.

The Product Contract records the missing typed chain:

```text
NormRule
→ ApplicabilityPredicate
→ CaseFacts
→ ApplicabilityDecision
→ ExplainableTrace
```

Without one ownership decision, an implementation could either collapse `InForce` into `Applicable`, duplicate incompatible decision engines per profile, or let a procurement adapter become a second ontology core. D148 selected a neutral core evaluator with versioned profile inputs.

## Decision

1. **The neutral Rust core owns the applicability protocol.** It owns:

   - the closed evaluation algebra for `ApplicabilityPredicate`;
   - `ApplicabilityDecision` outcomes;
   - fail-closed abstention kinds and prerequisite gates;
   - deterministic composition of predicate results;
   - the structure and completeness rules of `ExplainableTrace`.

2. **The protocol is typed and fail-closed.** Its conceptual outcome set is:

   ```text
   Applicable
   | NotApplicable
   | Abstain(AbstentionKind)
   ```

   `AbstentionKind` must cover at least missing/ambiguous facts, unknown profile or predicate revision, missing CTV, missing or conflicting NormativeState, unresolved transitional version, missing provenance and unsupported predicate kind. The exact Rust enum is deferred to implementation TDD and may be narrower only if every omitted condition maps to an equally explicit typed non-success.

3. **Profiles supply versioned read-only inputs, not final decisions.** A profile may supply:

   - versioned `CaseFacts` schema identifiers and fact instances with provenance;
   - versioned special-predicate declarations and parameters;
   - classifiers, registers and industry lists with source/revision metadata;
   - industry-priority inputs consumed without elevating `NormativeRank`;
   - procurement or other profile fixtures and hostile cases.

   A profile may not emit a final applicability result outside the core protocol, add a clock, mutate CC/CTV/CLV, mutate NormativeState, elevate kernel ranks, rewrite transitional outcomes, or treat LLM prose as a predicate result.

4. **Applicability consumes prerequisite snapshots without owning them.** The protocol may read:

   - CC/CTV identity and text resolution from ADR-0016/0017;
   - NormativeState from ADR-0018;
   - hierarchy/conflict outputs from ADR-0019;
   - practice coverage from ADR-0020 as non-authoritative evidence;
   - transitional version choice from ADR-0021;
   - versioned profile inputs from ADR-0022.

   It cannot repair or silently replace a prerequisite. Any prerequisite `Unknown`, `Conflict`, `MissingAnchor` or equivalent non-success propagates to abstention unless the governing predicate explicitly does not depend on that prerequisite and the trace proves the independence.

5. **Determinism is revision-bound.** Identical `NormRule`, predicate-registry revision, `CaseFacts`, prerequisite snapshot and profile-input revision must produce the same decision and trace. Different profile revisions are different input identities, not different kernels.

6. **`ExplainableTrace` is mandatory for every non-error outcome.** It records:

   - the rule and predicate identities/revisions;
   - fact and profile-input provenance;
   - prerequisite snapshots consumed;
   - each predicate evaluation and abstention reason;
   - the composed decision;
   - explicit non-claims and unresolved evidence.

   A trace is evidence of deterministic execution, not proof that supplied facts or legal interpretation are correct.

7. **Procurement is the first proving profile, not the core ontology.** 44-ФЗ/223-ФЗ facts, classifiers, registers and special predicates exercise the neutral protocol. They do not define the protocol's universal outcomes, clocks, CTV model, NormativeState or rank algebra.

8. **No positive applicability claim exists until implementation proof.** While this ADR is `[proposed]`, every product request for case applicability must return the existing product abstention/non-success boundary. Documentation, derived NormRule graphs, temporal phrases, CTV presence, `InForce`, roadmap completion, LLM output or assessment PASS cannot create `Applicable` or `NotApplicable`.

## Consequences

Positive:

- one deterministic, profile-neutral decision and trace surface;
- shared hostile abstention contracts across profiles;
- procurement can prove depth without contaminating the core;
- ADR-0017 CTV and ADR-0021 transition responsibilities remain distinct;
- profile evolution is visible through input revisions rather than kernel forks.

Negative:

- the core must eventually define a bounded predicate vocabulary and registry contract;
- profiles cannot use arbitrary hidden evaluation code to bypass the protocol;
- versioned facts and predicate declarations add provenance and migration cost;
- early implementation may expose missing predicates and abstain frequently;
- this decision does not solve legal fact acquisition or prove predicate completeness.

## Rejected alternatives

1. **Core decision algebra with profile-owned predicate evaluation.** Rejected because profile-local evaluators weaken product-wide determinism, fragment hostile verification and can hide legal conclusions behind adapter boundaries.
2. **Profile-owned full applicability pipelines.** Rejected because procurement would become a de facto second ontology core and PC-009/PC-010 boundaries would diverge.
3. **Continue deferral without ownership.** Rejected as the architecture decision because it blocks all safe applicability planning; implementation itself remains deferred until proof-gated tasks exist.

## Revisit triggers

Revisit only with a superseding ADR when at least one is true:

- real procurement and a second independent profile demonstrate that the core predicate algebra cannot represent required semantics without profile-owned code;
- hostile tests show the shared decision/trace algebra cannot preserve fail-closed behavior;
- representative real-case evidence demonstrates that the ownership split causes systematic non-explainable or non-deterministic outcomes;
- a profile needs to mutate clocks, CTV, NormativeState or ranks — which should normally reject the profile design rather than relax this ADR.

## Non-claims

- `[deferred]` No predicate evaluation algebra, product `CaseFacts` pipeline, or Applicable/NotApplicable decision is implemented by this ADR. A minimal fail-closed abstention kernel (`ln-applicability` v0) gates prerequisites and emits a mandatory trace. Structural NormRule IR types are design-only (RC11-F04a) and do not evaluate applicability or legal correctness.
- No applicability result, legal correctness or authoritative legal interpretation is validated.
- No procurement profile, classifier, register or legal rule set is complete.
- No derived NormRule graph, LLM output, semantic similarity or profile adapter is source truth.
- No lifecycle in ADR-0016–0022 is promoted.
- This decision does not replace human legal judgment.
- `ln-applicability` is not a KOF-DA exclusive capability owner under ADR-0011 and does not expand the 20 HC owner table.

## References

- D148 — human decision selecting neutral core evaluator with versioned profile inputs
- `prd/PRODUCT.md` — PC-009, PC-010, PC-013
- `prd/REQUIREMENTS.md` — RQ-009, RQ-010, RQ-013
- `prd/temporal-legal-model.md` — TQ-01, TL-G06, TL-G12, TL-GC14–16
- ADR-0009 — five-clock temporal roles
- ADR-0017 — CTV and enters-legal-order/applicability distinction
- ADR-0018 — NormativeState
- ADR-0021 — transitional version choice
- ADR-0022 — industry profiles as neutral-core adapters
- ADR-0015 — verification and lifecycle proof boundaries
