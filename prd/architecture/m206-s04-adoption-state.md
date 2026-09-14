# M206/S04 adoption state: RC28-F10, RC28-F11 and RC28-F12

**scope: RC28-F10, RC28-F11, RC28-F12**
**classification: design-only**
**authoritative: false**
**lifecycle: proposed**
**human_adoption: pending**
**runtime_stop_active: true**
**runtime_demo: not-proven**
**requirement_status_effect: unchanged**
**review_disposition_effect: unchanged**
**selected_baseline: G01, G02, G14**
**deferred_gates: G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13, G15, G16**
**must_not_select: G08, G09, G10, G11, G12, G13, G15**
**resume: separate source-bound owner admission, confirmation of M204/M205 prerequisites, and sanctioned runtime replan**

## Purpose and no-start boundary

This is a source-bound, design-only no-start record for the scoped cues,
range distinctions, and future reference vertical assigned to M206/S04. It is
not a parser specification, runtime authority, adoption decision, approval,
waiver, requirement update, Review Case disposition, or product readiness
claim. The scenarios below are future obligations only: none has been
executed, and no initial runtime demo is claimed.

The boundary is grounded in the immutable tool-generated Review 28 and the
existing M205/M206 design records. Documentation integrity, milestone
completion, a marker check, or a future contract PASS cannot admit runtime.
This record does not select a cue policy, normalization policy, endpoint or
membership policy, hop bound, precedence rule, or legal interpretation. Where
the owning source leaves a policy unresolved, the future outcome is
fail-closed and the policy remains unresolved rather than inferred.

## Provenance and ownership

Tracked repository-relative source anchors are:

- `doc/review/review-28-10-09-2026.md`: RC28-F10, RC28-F11 and RC28-F12
  findings remain proposed, open, and require source-bound reproduction;
  review text is not a runtime proof or legal acceptance.
- `prd/architecture/m206-s02-adoption-state.md`: upstream no-start state for
  lexical/span dependencies; ranges and edition-index membership remain
  separate from local grammar.
- `prd/architecture/m206-s03-adoption-state.md`: upstream no-start state for
  self, antecedent, alias, series, and edition-reference separation.
- `prd/architecture/npa-document-context.yaml`: proposed, non-authoritative
  document-context and reference construction boundary.
- `prd/architecture/current-document-requisites.yaml`: proposed requisites
  and source-bound evidence boundary for current-document constructions.
- `prd/architecture/npa-capture-arbitration.yaml`: proposed capture and
  arbitration boundary; no residual policy is selected here.
- `prd/architecture/reference-binding-contract.yaml`: proposed design-only
  Mention/Binding/Semantics separation and typed non-success boundary.
- `prd/architecture/m205-s03-context-fsm.yaml`: proposed context ownership
  and construction guards retained from the preceding context slice.
- `prd/temporal-legal-model.md`: section 3 keeps unresolved temporal and
  normative vocabulary separate; this record does not mint runtime types.
- `prd/architecture/model-crystal.md`: MC-SEPARATION and MC-REF preserve
  mention, binding, semantics, identity, membership, and force as distinct
  planes; the projection is non-canon.
Existing project decisions are navigation/provenance only and are not
amended by this record.

The owner Reject interaction
`04fd05a2-338f-45af-a1cc-13501717dc53` is retained as upstream F06/F10
provenance. It is not a Reject of F11 or F12, and this record creates no new
finding disposition or owner decision. In particular, no Reject is transferred
from F06/F10 to F11/F12.

## Gate selection boundary

The independently pinned baseline is exactly `G01, G02, G14`; it is not an
admission record. G02 remains already wired and is not reconnected here. The
deferred set is preserved exactly as listed in the singleton marker above.
`G08, G09, G10, G11, G12, G13, G15` must not be selected by this record. No
new gate is selected. Numeric hop limits, precedence, normalization choices,
range expansion rules, and cue-policy thresholds remain unresolved. A future
owner admission must pin each accepted policy to its owning gate, source, and
runtime-test surface rather than deriving it from this document.

## Future scenario contract: exactly twelve, all not executed

These are twelve independent future scenarios. Each row is a specification of
what a later authorized runtime battery must prove, not a runtime test, result,
admission, adoption, or legal conclusion. `source anchors` list only existing
tracked repository-relative paths.

| ID | Finding | Input condition | Expected future positive or fail-closed outcome | Source anchors | Required future runtime proof | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `F10-CUE-TOKEN` | F10 token/range variants | The word `до` occurs inside a larger token or a temporal-looking substring is not a token-bound cue. | Do not emit a separate temporal cue; preserve the original source span and abstain from substring interpretation. | `doc/review/review-28-10-09-2026.md`; `prd/architecture/npa-capture-arbitration.yaml` | Rust token-bound cue fixture with substring negative, original-anchor preservation, and fail-closed diagnostic. | not executed |
| `F10-CUE-POSITIVE` | F10 standalone cue/span | A standalone source-backed cue or span is captured without a legal conclusion or status inference. | Preserve the cue/span as a candidate evidence item; do not promote it to a rule, force, applicability, or legal conclusion. | `doc/review/review-28-10-09-2026.md`; `prd/architecture/npa-capture-arbitration.yaml`; `prd/architecture/reference-binding-contract.yaml` | Rust positive candidate fixture plus negative assertion that no NormRule, NormativeState, or applicability result is emitted. | not executed |
| `F10-ACTOR-ANCHORED` | F10 participant anchoring | A source-backed Actor participant span is available in the relevant grammatical scope. | Attach Actor only to the proven participant span and retain its source anchor; never widen it to the whole block by default. | `doc/review/review-28-10-09-2026.md`; `prd/architecture/npa-document-context.yaml`; `prd/architecture/npa-capture-arbitration.yaml` | Rust positive scope fixture asserting exact participant span, owner/context binding, and provenance. | not executed |
| `F10-ACTOR-NEGATIVE` | F10 missing participant evidence | No source-backed participant span confirms an Actor, or the candidate is ambiguous/conflicting. | Actor remains absent or typed Unknown; no Actor is guessed from block scope, proximity, or cue presence. | `doc/review/review-28-10-09-2026.md`; `prd/architecture/npa-document-context.yaml`; `prd/architecture/reference-binding-contract.yaml` | Rust negative fixture for absent and conflicting spans with fail-closed typed outcome and diagnostic. | not executed |
| `F11-ENDPOINTS` | F11 range endpoints | A written range supplies two endpoints but no proof for every designation between them. | Preserve endpoint evidence as endpoints only; do not represent endpoints as full StructuralMembership or complete range membership. | `doc/review/review-28-10-09-2026.md`; `prd/architecture/model-crystal.md`; `prd/architecture/m206-s02-adoption-state.md` | Rust range fixture asserting endpoint spans and explicit non-membership/non-completeness result. | not executed |
| `F11-MEMBERSHIP` | F11 full membership | A future selected edition provides separately anchored members for a range. | Full membership may be reported only when the ordered selected-edition structure and every required member are independently proven. | `doc/review/review-28-10-09-2026.md`; `prd/architecture/model-crystal.md`; `prd/architecture/reference-binding-contract.yaml` | Rust edition-index fixture with member anchors and a coverage/completeness proof distinct from endpoint parsing. | not executed |
| `F11-MISSING-MEMBER` | F11 incomplete membership | One or more members between valid endpoints are absent, unknown, or lack a source anchor. | Do not report Complete; return typed incomplete/Unknown evidence with the missing-member diagnostic. | `doc/review/review-28-10-09-2026.md`; `prd/architecture/model-crystal.md`; `prd/architecture/m206-s02-adoption-state.md` | Rust hostile fixture removing one member and asserting fail-closed completeness plus preserved endpoints. | not executed |
| `F11-RANGE-INVALID` | F11 malformed or ambiguous range | Range syntax, endpoint ordering, designation structure, or edition context is malformed or ambiguous. | Refuse arithmetic guessing and implicit normalization; retain evidence and return a typed invalid/ambiguous outcome. | `doc/review/review-28-10-09-2026.md`; `prd/architecture/npa-capture-arbitration.yaml`; `prd/architecture/reference-binding-contract.yaml` | Rust malformed/ambiguous fixtures, including dash variants, with nonzero/fail-closed diagnostics and no invented members. | not executed |
| `F12-VERTICAL-POSITIVE` | F12 source-bound reference vertical | A later authorized path can bind source mention → capture → context → binding candidate → inspection with anchors at every step. | Produce only a source-bound candidate/inspection trace; confidence and any later status remain governed by adopted contracts, not this record. | `doc/review/review-28-10-09-2026.md`; `prd/architecture/npa-document-context.yaml`; `prd/architecture/current-document-requisites.yaml`; `prd/architecture/reference-binding-contract.yaml` | Rust composed vertical fixture proving every hop, anchor retention, deterministic replay, and typed candidate outcome. | not executed |
| `F12-VERTICAL-NEGATIVE` | F12 unresolved or conflicting context | Context is missing, unresolved, crosses an unauthorized boundary, or contains conflicting candidate bindings. | Do not emit a confident binding; preserve candidates/conflict and return typed Unknown/ambiguous outcome with derivation paths. | `doc/review/review-28-10-09-2026.md`; `prd/architecture/m205-s03-context-fsm.yaml`; `prd/architecture/reference-binding-contract.yaml` | Rust negative vertical fixtures for missing, boundary-crossing, and conflicting context; assert no confident binding. | not executed |
| `F12-CONTEXT-SEPARATION` | F12 construction separation | Inputs exercise self, antecedent, scoped alias, coordinating series, or edition relation constructions. | Keep each construction and its authorization evidence separate; no proximity, source-function order, or shared label silently merges them. | `doc/review/review-28-10-09-2026.md`; `prd/architecture/m205-s03-context-fsm.yaml`; `prd/architecture/npa-document-context.yaml`; `prd/architecture/current-document-requisites.yaml` | Rust cross-construction matrix with declare/use/shadow/conflict and boundary cases, preserving independent traces. | not executed |
| `F12-NO-IR` | F12 candidate authority ceiling | A reference candidate or inspection result exists without an independently adopted normative semantics contract. | Candidate is not NormRule and does not create status, applicability, force, or legal IR; deferred semantics stay deferred-undefined. | `doc/review/review-28-10-09-2026.md`; `prd/temporal-legal-model.md`; `prd/architecture/model-crystal.md`; `prd/architecture/reference-binding-contract.yaml` | Rust negative promotion fixture asserting no NormRule/status/applicability fields or runtime path are created from a candidate. | not executed |

Endpoint parsing and complete range membership are deliberately separate
proof surfaces. Cue recognition and participant anchoring are evidence
candidates, not normative interpretation. The reference vertical is a future
composition shape only; no resolver, grammar runtime, NormRule, status,
applicability, force, or IR is introduced here.

## Resume conditions and prohibited promotion

Resume requires a separate source-bound owner admission that identifies the
accepted policy, gate ownership, source bindings, and owning runtime-test
surfaces. That admission must confirm the M204 and M205 prerequisites and must
be followed by a sanctioned runtime replan. Complete milestones are not
admission and cannot exit this stop. A future owner admission still does not
turn this document into runtime evidence without the separately sanctioned
implementation and battery.

Until then:

- do not modify Rust, tests, dependencies, ADRs, M205 pins, requirements, or
  findings;
- do not create an approval, waiver, or adoption artifact, or change review
  disposition;
- do not run a corpus walk, network request, parser/runtime battery, or
  external NLP process;
- do not treat the twelve rows, static anchors, or integrity PASS as executed
  evidence or product readiness;
- do not select a new gate, numeric hop/precedence policy, cue threshold,
  range expansion rule, or normalization policy;
- do not transfer the F06/F10 Reject provenance to F11/F12;
- do not introduce F13 amendment syntax or NormRule runtime.

This repository-relative record intentionally preserves the active no-start
state, exact finding scope, upstream provenance, independent gate sets, and
future proof obligations without changing runtime, ADRs, corpus, upstream
records, or requirements.

**battery_status: NOT_RUN** — the future-battery scenarios recorded above have not been executed as runtime tests.
