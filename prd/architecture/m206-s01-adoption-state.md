# M206/S01 adoption state: F06 and F10

**Status:** `blocker-accepted` — design-only state record, not an approval.
**Recorded:** 2026-09-14
**Milestone / slice:** M206-jnbhlz / S01
**Scope:** RC28-F06 structural parenting and annex-root policy; RC28-F10 lexical variants, original source spans, and explicit unavailable morphology.

## Purpose and boundary

This document records the source-bound admission state after T01 and the
owner's subjective UAT decision. It is not a parser specification, runtime
change, lifecycle promotion, legal acceptance, Review Case disposition, or
human adoption approval. It does not amend ADR-0028, change any M205 pin, or
move product logic into the harness.

## Sources checked by T01

T01 checked the following repository sources for a separate source-bound
admission of the F06/F10 policies:

1. `doc/adr/0028-typed-lexer-legal-marker-lexicon.md` (ADR-0028), whose
   lifecycle remains `[proposed]` and whose morphology and grammar/context
   bounds remain deferred.
2. `prd/architecture/m205-s02-pre-capture-grammar.yaml` (M205/S02
   structural profiles and range layers), which declares
   `human_adoption: pending`, `runtime_stop_active: true`,
   `ambiguous_profile: diagnostic_and_fail_closed`, explicit structural
   profile ownership, required original anchors, and missing membership.
3. `prd/architecture/m205-s04-docs-reconciliation.yaml` (M205/S04
   reconciliation), which remains `authoritative: false`, `[proposed]`,
   `human_adoption: pending`, and `runtime_stop_active: true`; its non-claims
   include that it is not a human adoption record and does not mutate S01-S03
   pins.
4. `prd/architecture/review-cases/rc28-remediation-program.md` (Review 28
   remediation program), which assigns F06 to M205/S02 and M206/S01 and
   requires each changed policy to be actually adopted before M206 work.

## Admission result

No separate source-bound owner admission for F06/F10 was found. The M205
pins are design-only and `[proposed]`; integrity or reconciliation PASS does
not constitute human adoption. `human_adoption` remains pending and
`runtime_stop.active` remains true. The F06/F10 implementation work in T02
through T04 must therefore not start, and the S01 demo must not be claimed.

The state is explicitly fail-closed for sibling/annex parentage, lexical
normalization and original-span guarantees, endpoint-versus-membership
interpretation, and unavailable morphology. No inferred policy or implicit
approval is permitted.

## Owner decision

On 2026-09-14 the owner selected **Reject** in the subjective UAT
interaction:

- **Decision:** `Reject`
- **Actor:** user session
- **Interaction:** `04fd05a2-338f-45af-a1cc-13501717dc53`
- **Recorded outcome:** the proposed F06/F10 adoption is not accepted.

This decision records the current admission outcome only. It does not create
an approval, waiver, requirement closure, Review Case disposition, or runtime
authorization.

## Resume condition

T02-T04 may be resumed only after a separate, explicit, source-bound owner
admission for the F06/F10 structural and lexical policies is recorded through
the applicable acceptance path. That admission must be a new decision and
must identify the accepted policy/source binding; it is not implied by a
future integrity PASS, milestone completion, or this document.

Once that condition exists, T02-T04 may be re-scoped or dispatched. This is a
descope/stop condition, not cancellation of the planned work and not an
excuse to alter M205 pins. Until then, runtime work remains stopped.

## Prohibited changes under this state

- Do not create an approval or adoption artifact from this record.
- Do not change M205 structural-profile, range-layer, or reconciliation pins.
- Do not begin runtime or product implementation for T02-T04.
- Do not edit ADR-0028 to manufacture adoption or readiness.
- Do not add product logic to `law_nexus_harness` (R064 boundary).

## F10 lexical blocker provenance (T03, design-only)

The lexical portion of F10 remains blocked and is not an implementation
claim. The intended scope covers one canonical treatment of dash and
inflection variants, preservation of each variant's original source spans,
and typed morphology, including an explicit unavailable-morphology outcome.
Those guarantees cannot be implemented or accepted without a separate
source-bound runtime admission; under the current `Reject` decision and
active stop, runtime work remains stopped.

Five prior attempts are preserved as blocker provenance rather than treated
as missing implementation evidence:

1. **Attempt #1 — no artifact:** no source-bound admission artifact was
   available.
2. **Attempt #2 — blocker-discovered:** the exact owning crate and test suite
   were unavailable, and runtime adoption was rejected.
3. **Attempt #3 — no artifact:** no source-bound admission artifact was
   available.
4. **Attempt #4 — no artifact:** no source-bound admission artifact was
   available.
5. **Attempt #5 — blocker-discovered:** the exact owning crate and test suite
   were unavailable, and runtime adoption was rejected.

This provenance does not authorize lexical normalization, span binding,
parenting, morphology, or tests in the runtime. Resumption requires a new,
explicit source-bound owner admission identifying the accepted F10 policy and
its owning runtime/test surface; integrity or reconciliation PASS cannot
substitute for it. Until then, runtime work remains stopped.
