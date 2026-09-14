# M206/S03 adoption state: RC28-F07, RC28-F08 and RC28-F12

**scope: RC28-F07, RC28-F08, RC28-F12**
**classification: design-only**
**authoritative: false**
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

This is a source-bound design-only record for the context and reference
construction scope assigned to M206/S03. It preserves an active stop; it is
not a parser specification, runtime authority, adoption decision, approval,
waiver, requirement update, Review Case disposition, or product readiness
claim. The future scenarios below are obligations for a later authorized
battery, not executed tests or runtime results.

D461 is the governing rationale for this narrowed S03 boundary: S01 and S02
preserved the upstream stop, while M205/S03 remains pending adoption and its
source authority policy remains deferred-undefined. Documentation integrity
cannot be used as runtime admission. S01/S02 completion, an integrity PASS,
M205 pin presence, or milestone progress does not authorize the sketch demo.
If a source contradicts this state, work stops rather than inferring a policy.

## Provenance and ownership

Tracked source anchors are:

- `prd/architecture/m205-s03-context-fsm.yaml`: proposed, non-authoritative;
  `human_adoption: pending`, `runtime_stop_active: true`, deferred-undefined
  source authority, and construction guards for self, antecedent, alias,
  series, and edition relations.
- `prd/architecture/m206-s02-adoption-state.md`: the preceding design-only
  no-start record and its unchanged selected/deferred gate boundary.
- `doc/review/review-28-10-09-2026.md`: RC28-F07/F08/F12 remain open,
  tool-generated, and require source-bound reproduction rather than a
  documentation claim.
- `prd/temporal-legal-model.md` section 3 and
  `prd/architecture/model-crystal.md`: reference, identity, CTV, force, and
  temporal distinctions remain separate; a reference or projection does not
  become legal authority or identity by inference.
- `.gsd/DECISIONS.md`: D461 records the current design-only no-start and the
  requirement for new explicit source-bound admission before runtime replan.

The owner Reject provenance for F06/F10 interaction
`04fd05a2-338f-45af-a1cc-13501717dc53` is retained only as upstream provenance
for the stop. It is not a Reject of RC28-F07, RC28-F08, or RC28-F12, and this
record creates no new disposition. Ownership is not changed by these static
observations.

## Static observations, not reproduction

The current code surfaces explain why runtime evidence is not claimed here:

- `ln-decode` dispatch for current-document requisites uses
  `ThisRefGrammarEvidence::new([])`, so this record does not present that path
  as positive ThisRef authorization.
- The overlay builder selects heads globally and compares block-local offsets;
  this record does not treat those observations as continuation eligibility or
  as a reproduction PASS.
- `ln-temporal` has a separate document-context model; this record does not
  resolve crate ownership or authorize converging the models.

These are static observations for future source-bound work. They do not mint
new temporal or parser types, alter ownership, wire runtime behavior, or prove
completeness.

## Gate selection boundary

The selected baseline is exactly `G01, G02, G14`; it is not an admission
record. G02 is not reconnected. The deferred set is preserved exactly as
listed above. `G08, G09, G10, G11, G12, G13, G15` must not be selected in this
record. No residual gate, numeric bound, precedence policy, or new policy is
chosen. F13 and S04 cues, ranges, and membership are outside this scope.

## Future scenario contract: all not executed

The following table contains twelve unique future scenario IDs. Each is a
source-bound obligation with a required invariant. Every status is explicitly
`not executed`; none is runtime PASS, admission, or adoption evidence.

| ID | Required invariant | Status |
| --- | --- | --- |
| `F08-self-positive` | Explicit `ThisRef` grammar plus a complete, non-conflicting sidecar authorizes current-document self-reference. | not executed |
| `F08-cited-act-negative` | An ordinary citation remains an earlier cited act, not self-reference, even when a sidecar is present. | not executed |
| `F08-self-missing-conflict` | Missing grammar or conflicting required fields fails closed; sidecar-only or guessed self-reference is insufficient. | not executed |
| `F12-antecedent-positive` | A proven cited series head authorizes an antecedent/previous-act relation; proximity alone does not. | not executed |
| `F12-antecedent-unproven` | An unproven head remains incomplete; proximity and sidecar evidence cannot authorize it. | not executed |
| `F12-alias-declare-use` | An explicitly declared alias and its use bind only within the same container. | not executed |
| `F12-alias-shadow-conflict` | Explicit shadowing or conflict is retained as conflict; no precedence is invented. | not executed |
| `F12-alias-boundary` | Cross-container or boundary-crossing names do not become global matches. | not executed |
| `F07-series-positive` | Open coordination, source-block order, owner/boundary compatibility, bounded hops, and an explicit derivation path are all present. | not executed |
| `F07-three-unrelated` | Three unrelated citations create no continuation edges merely because they are nearby or numerous. | not executed |
| `F07-series-invalid` | Missing order, incompatible owner/boundary, exhausted hops, or cross-block local offsets fail to prove eligibility. No numeric hop limit is assigned here. | not executed |
| `F12-edition-relation` | A `в ред.` relation is a source-backed candidate only; it is not substituted with Expression identity, edition date, CTV, or InForce. | not executed |

The scenario names deliberately separate self, previous-act/antecedent, scoped
alias, coordinating series, and edition relation. Their outcomes are future
obligations, not runtime claims. No numeric hop limit is selected by this
record.

## Resume conditions and prohibited promotion

Resume requires a separate source-bound owner admission binding each accepted
policy to its gate, source, and owning runtime test surface; it must confirm
the M204 and M205 prerequisites. That admission must be followed by a
sanctioned runtime replan. Even a future admission would not make this
artifact a runtime implementation or a proof of the demo without those
separate steps.

Until then:

- do not modify Rust, tests, dependencies, ADRs, M205 pins, requirements, or
  findings;
- do not create an approval or waiver, or change review disposition;
- do not run a corpus walk, network request, or runtime battery;
- do not treat static observations, scenario definitions, or integrity PASS as
  reproduction evidence;
- do not select deferred gates, assign numeric precedence/hop policy, or
  reconnect G02;
- do not pull F13 or S04 cues, ranges, or membership into this scope.

This repository-relative document is intentionally limited to preserving the
active stop, provenance, gate boundaries, and twelve unverified future
scenarios for the next authorized owner decision.
