# RC28 disposition inventory — what exists per finding, and what only a human can record

**Status:** `[bounded]` read-only inventory. Written 2026-09-23 during M209-2yg6ix closeout.
**Subject:** review packet `RC-2026-09-10-001` (source `doc/review/review-28-10-09-2026.md`,
reviewed revision `6f1a27537a659f291e0147e0fbd8be6ca199261c`), 19 findings `RC28-F01..F19`.

## Non-claims

This document is an inventory, not a disposition. It records no human authority, writes no ledger
event, changes no finding's `disposition_status`, `execution_status` or `verification_status`, and
promotes no requirement, ADR, roadmap entry or lifecycle state. Reading it is not acceptance of
any finding, and the absence of a verdict below is not a verdict of "closed". Every disposition
must be recorded by a human owner through the sanctioned review-case application APIs, exactly as
`prd/architecture/review-cases/rc28-remediation-program.md` requires.

## Verified packet state (2026-09-23)

`uv run python -m law_nexus_harness review-case validate` reports
`ok: true, finding_count: 35, closed_count: 10, open_count: 21, blocked_count: 0, partial_count: 0,
stale_count: 0`. Read at that level the CLI integrity check passes.

`review-case inventory --packet-id RC-2026-09-10-001` reports for all 19 findings, without
exception:

- `residual_class: awaiting_disposition`
- `operator_stage: S1_normalized`
- `missing_for_next: ["human disposition_recorded with rationale and source_revision"]`
- `next_admissible_events: ["disposition_recorded", "normalization_reviewed"]`
- `open_blockers: []`, `active_blockers: []`, `blocked_by: []`, `open_children: []`
- `normalization_status: draft_extracted`, `last_event: null`
- `non_claims: ["Tool-generated finding; not human disposition or legal acceptance."]`

There is no `events/` directory for this packet: on disk only
`prd/architecture/review-cases/packets/RC-2026-09-10-001.json` exists. Its embedded `events` array
carries exactly one entry, the tool-actor `packet_registered`. By contrast
`RC-2026-08-11-001/events/` holds 29 human envelopes and `RC-2026-08-12-001/events/` holds 10.

The sibling packets are dispositioned, and their vocabulary is worth reusing as a precedent:
`RC-2026-08-11-001` resolves to `accepted_as_gap` (6), `accepted_as_process_defect` (1),
`accepted_as_decision_candidate` (1), `already_satisfied` (1), `deferred` (1);
`RC-2026-08-12-001` to `already_satisfied` (2), `accepted_as_gap` (1),
`accepted_as_process_defect` (1), `duplicate` (1), `deferred` (1). Events carry
`actor_class: "human"`, `actor_id`, a rationale, a `source_revision`, and an envelope sha chain.

Conclusion: the single missing input for every RC28 finding is a human `disposition_recorded`
event with a rationale and a source revision. No normalization step, no technical blocker and no
upstream dependency stands in the way.

## Ownership

Milestone-level assignment, verbatim from `rc28-remediation-program.md`:

| Milestone | Findings |
|---|---|
| M204-w2ktfw | F01-F05, F19 |
| M205-p7xc54 | F06-F14, F18-F19 |
| M206-jnbhlz | F06-F12 |
| M207-b2i96m | F01-F03, F14-F15 |
| M208-wrz6fg (parked) | F13-F14, F17 |
| M209-2yg6ix | F16-F17 |
| M210-3afp79 | F18-F19, final F01-F19 check |

Seventeen of the nineteen findings are therefore owned by milestones that are already complete or
parked. Completing a milestone in this project does not require recording its RC28 dispositions,
which is how this debt accumulated rather than being closed milestone by milestone.

## Per-finding inventory

"Documentation verified" means the path was located by grep in this pass. "Verdict read" means the
recorded verdict was read directly. Anything marked `not re-verified` must be read and classified
by the owning slice before a disposition is written.

| Finding | Required proof (verbatim) | Documentation verified | Verdict read | What the human disposition must decide |
|---|---|---|---|---|
| F01 | real coder-bound measurement and producer-to-promotion negative tests | `m207-s03-eval-protocol.md`, `m207-s04-c4-operational-receipt.json`, `prd/annotation/m207-s02-coder-protocol.md` | human measurement is absent by design | Human annotation is absent and was descoped by owner decision D519. A disposition claiming the measurement exists would be false; the honest options are a residual naming D519, or reopening the human contour. |
| F02 | seeded selection, validated metadata, provider and Work-family leakage checks | `m207-s03-eval-protocol.md` (`[bounded]` evaluation/evidence contract) | not re-verified | Whether the automatic evaluation satisfies the required strata, or is a residual. |
| F03 | true input/semantic digests, complete argv and actual operational outcome | `m207-s04-c4-operational-receipt.json` | receipt self-declares `operational_acceptance: non-pass`, `non_claims` include "not gold" and "not a promotion" | The receipt records an attempt and self-declares non-pass; a disposition must state whether that satisfies F03 or is a residual. |
| F04 | versioned acceptance and equivalent receipt reuse; no silent criterion substitution | `m204-s06-governor-sanctioned-outcome.json`, `m204-s07-governor-repeat.json` (`sanctioned-outcome/v1`) | not re-verified | Whether the recorded sanctioned outcome and its repeat satisfy the versioned-acceptance requirement. |
| F05 | identify four pending tasks, reproduce claim/dispatch defect, sanctioned idempotent recovery; upstream actions need separate confirmation | `m204-s06`, `m204-s07` | not re-verified | Whether the reproduction and sanctioned recovery are recorded; note the upstream defect report `open-gsd/gsd-pi#2412` was filed on owner authorization, which is the "separate confirmation" this line requires. |
| F06-F12 | siblings/annexes, profile hierarchy and downstream owner assertions; authorized derivations, positive and negative ThisRef, no unrelated continuation graph; pre-capture incomplete members, sentence boundaries, preserved origins and bounded arbitration; normalization spans, morphology unavailable outcome, endpoint versus edition-index membership distinction; token-bound cues, negation differences, participant anchors; alias declaration/use/scope, antecedent versus self and non-authoritative edition relation | `m206-s01-adoption-state.md`, `m206-s02-adoption-state.md`, `m206-s03-adoption-state.md`, `m206-s04-adoption-state.md`, `m206-s05-runtime-admission.md`, `m206-s07-runtime-admission.md`, `m205-s03-context-fsm.yaml` | `m206-s07-runtime-admission.md` records a source-bound admission bound to the S05 admission, with `runtime_stop` lifted for that remediation only by owner decision, plus an executable `scripts/m206_s07_admission_contract.test.mjs`; `m206-s03-adoption-state.md` states F07/F08/F12 "remain open" | Whether the M206 admission closes these findings or whether the terms M206 itself recorded as still open are residuals. |
| F13 | adopted operation grammar, old/new operands, nested targets, admission and bounded causal replay | `m205-s03-context-fsm.yaml` (`runtime_stop_active: true`), `m208-s01-runtime-admission.md`, `m208-s03-admission-commencement.md`, `m208-s04-admission-bounded-replay.md`, `m209-s01-punkt-decision.md` | all three M208 checkpoints record `not-adopted` with `owner_admission_ref: none`, `runtime_work: not-started`, `runtime_stop: not-started`; `prd/architecture/operation-registry.yaml` is `lifecycle: "[proposed]"` | **Structural.** F13 has no live adoption owner: M205 handed the replay to M208, M208 recorded not-adopted three times and is parked, and the operation grammar it requires is not adopted. The disposition must be `hold-requires-owner-decision` or an explicit residual, and it must name which of the three lawful outcomes applies. |
| F14 | functional prior-art matrix; no license or runtime-parity claim | `m207-unit-diagnosis.md` (`[bounded]` overlay), `m207-reassessment-2026-09-21.md` (`[bounded]` source audit) | not re-verified | Whether the prior-art matrix satisfies the line, noting M208's optional component is not adopted. |
| F15 | real independent annotation and source-bound human acceptance; no automatic seed enlargement | `prd/annotation/m207-s01-codebook.md`, `prd/annotation/m207-s02-coder-protocol.md`, `prd/migration/rust-evidence/m207-s02-coder-kit-pass1.json` and `pass2.json` | the human contour is absent (`HUMAN_PILOT_ABSENT` exit 3, no published rates) | Same shape as F01: the required human evidence is deliberately absent under D519, so this cannot be closed as satisfied. The machinery that exists is a codebook and a coder kit, not coder-bound measurement. |
| F16 | each R035 gate plus extractor/admission/regeneration; punkt decision before admission | `m209-s01-punkt-decision.md`, `m209-s01-r035-gate-register.json`, `m209-s01-r035-gate-reconciliation.json` | delivered: seven named gates with per-gate quantifiers, `GATE-G015` conflicted, punkt `not-adopted` with `owner_admission_ref: none` and zero punkt rows, contracts 28/28, 21/21, 35/35 | Whether the delivered gate register satisfies F16, given that no requirement was promoted. |
| F17 | operation x provision x commencement x transitions x edition deltas, scoped coverage, frozen M201 untouched | `m209-s03-*` evidence, `m209-s03-r070-scope-ledger.json`, `m208-s03-admission-commencement.md`, `m208-s04-admission-bounded-replay.md` | delivered by M209/S03: 120 amends edges (40 resolved / 80 named codes), 122 commencement slots, 118 editions with a chain digest matching the T01 pin, frozen pins unchanged; M208's components recorded `not-adopted` | Whether M209's evidence closes F17 on its own, with M208's not-adopted checkpoints recorded as the historical admission attempt. |
| F18 | human-owned legal IR adoption before implementation and independent evaluation | M210 plan (`M210-3afp79`) | not applicable yet — M210/S01-S04 is the owning work | This is M210's own obligation, closed at Gates 1 and 2. |
| F19 | class-matched docs/matrix consistency without lifecycle smoothing | `m209-s01-r035-gate-register.json`, `m209-s01-r035-gate-reconciliation.json`, `m204-s05-*`, `m205-s04-*` | M209 referenced F19 in the gate register and its reconciliation | Whether the documentation and matrix are class-matched without lifecycle smoothing, closed by M210/S04 together with the owning slices. |

## What this changes

- No technical work is required to make the 19 findings dispositionable. `blocked_count: 0` and
  `open_blockers: []`; the only missing input is the human event.
- Two findings cannot honestly be accepted as satisfied and must be residuals: **F01 and F15**,
  whose required proof is real human annotation that owner decision D519 deliberately removed.
- One finding is structurally unowned: **F13**, whose adoption chain ends at the parked M208 and
  whose required adopted operation grammar does not exist. Its disposition must name one of the
  three lawful outcomes rather than closing it.
- Deterministic work is not blocked by this debt. The program itself states that unrelated human
  annotation must not block deterministic syntax research, and that no runtime step may cross its
  required adoption gate. M210/S01/S03 may proceed; M210/S03 onward remains behind the S02 human
  adoption gate.

## How a disposition is recorded

Only through the sanctioned application APIs, by a human owner, with a rationale and a source
revision, appending to `prd/architecture/review-cases/packets/RC-2026-09-10-001/events/`. An agent
must never write one. The packet's own non-claim states the rule plainly: a finding is
"Tool-generated; not human disposition or legal acceptance" until a human records otherwise.
