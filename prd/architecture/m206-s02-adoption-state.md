# M206/S02 adoption state: RC28-F09 and RC28-F10

**scope: RC28-F09, RC28-F10**
**classification: design-only**
**runtime_demo: not-proven**
**runtime_stop_active: true**
**human_adoption: pending**
**requirement_status_effect: unchanged**
**review_disposition_effect: unchanged**
**selected_already: G01, G02, G14**
**must_not_select: G06, G07, G12, G13**
**resume: new explicit source-bound owner admission and separate runtime replan**

## Purpose and boundary

This document records a fail-closed, design-only stop for list composition and
arbitration origins. It is not a parser specification, runtime authority,
acceptance, approval, waiver, requirement update, Review Case disposition,
or human adoption record. It does not amend ADR-0028, the M205 pins, the
requirements register, findings, or lifecycle state. No runtime demo is claimed
or implied by this artifact.

The boundary follows D388 and its closeout refinement: G01, G02, and G14 are
the already-selected baseline. G02 is already wired through the existing
`capture_lawrefs` defaults-only path and must not be implemented or connected
a second time. The residual policy is not selected. G06, G07, G12, and G13
must not be selected by this document, and the remaining deferred gates stay
individually deferred. An integrity PASS or completed documentation task is
not admission and cannot clear the runtime stop.

## Source-bound admission state

M205/S02 remains a design-only pre-capture contract with
`human_adoption: pending` and `runtime_stop_active: true`. M205/S04 remains a
non-authoritative reconciliation pin with the same pending adoption and active
stop. M206/S01 records the owner Reject for F06/F10 interaction
`04fd05a2-338f-45af-a1cc-13501717dc53`; that owner Reject is preserved as
provenance for the current stop. It is not a new F09 Reject: no new owner
Reject for F09 was recorded.

The F09 list-composition and origin policies therefore have no separate
source-bound owner admission. The pending state is intentional. No implicit
policy can be inferred from the existing frame implementation, G02 wiring,
source-function order, milestone completion, or integrity/reconciliation
checks. The source-function order is not precedence, and origin loss is
forbidden; unresolved overlap policy remains unresolved rather than being
chosen here.

The complete M205/S02 deferred list is preserved:

`G03,G04,G05,G06,G07,G08,G09,G10,G11,G12,G13,G15,G16`

The already-selected list is only `G01, G02, G14`; it is not an admission
record. In particular, G02 is already-wired and must not be reconnected, and
no residual policy is selected. No S03 alias, ThisRef, context, or IR work is
included. F10 is limited here to the lexical/span dependency described below;
range membership and edition-index membership remain S04/P8 concerns and are
not asserted by this state.

## Future battery backlog: not executed

The following scenarios define a future, source-bound battery. They are
backlog entries only. None is a runtime test PASS, product result, parser
readiness claim, or adoption result in this document.

| ID | Future scenario and required invariant | Status |
| --- | --- | --- |
| `F09-independent-sentences` | Unrelated mixed-act sentences must not be merged. | not executed |
| `F09-incomplete-tail` | A pre-capture token/morphology frame without `date` or `doc_no` preserves its local anchor; inherited fields are never rewritten as source text. | not executed |
| `F09-boundaries` | Sentence, heading, and paragraph boundaries remain distinguishable and are not silently merged. | not executed |
| `F09-refused-token-only` | Token evidence alone, without `captures`, `refused_captures`, `ContextView`, or requisites, is refused as grammar input. | not executed |
| `F09-identical-origins` | Identical same-span evidence preserves both `source_id`, `source_span`, and `source_kind` origins. | not executed |
| `F09-overlap` | Partial or incompatible overlap is a conflict; containment without policy is `ambiguous_both`; unknown policy is a conflict. | not executed |
| `F09-order` | Producer order is not precedence and must not discard any origin. | not executed |
| `F10-original-spans` | Original UTF-8 anchors and dash variants are retained, with morphology explicitly represented as unavailable when it cannot be obtained. | not executed |

The F10 row is only a lexical/span dependency. It does not cover ranges or
membership, which remain separate from local grammar. The scenarios do not
authorize arithmetic expansion, inheritance, identity binding, or any runtime
implementation.

## Stop and resume conditions

Runtime work remains stopped. Resumption requires a new explicit owner
admission that is source-bound and identifies the accepted policies, gates,
source bindings, and owning runtime-test surfaces. It must also confirm the
M204 and M205 prerequisites. A future admission is not created by an
integrity PASS, completion, a documentation reconciliation, or the presence
of this backlog.

Even after such an admission, implementation requires a separately sanctioned
replan. This task does not perform that replan and does not start a runtime
battery. If fresh sources contradict this record, the result is a blocker;
this document does not choose a policy by inference.

## Prohibited changes under this state

- Do not change ADR-0028, M205 pins, requirements, findings, or lifecycle.
- Do not create an approval, waiver, or adoption artifact.
- Do not alter crates, scripts, runtime tests, or product behavior.
- Do not treat the backlog rows as executed tests or runtime evidence.
- Do not perform a corpus walk, use external requests, or handle PII/secrets.
- Do not rewire G02 or select residual arbitration policy.

This artifact is intentionally repository-relative and design-only. Its sole
purpose is to preserve provenance, the active stop, the complete deferred gate
state, the future scenario contract, and the source-bound resume condition.

**battery_status: NOT_RUN** — the future-battery scenarios recorded above have not been executed as runtime tests.
