# M210-3afp79 S04: RC28 final check checkpoint

**packet_id:** RC-2026-09-10-001
**source_path:** doc/review/review-28-10-09-2026.md
**source_content_sha256:** sha256:baad2d036a629be39fa049c7aab7d1383ffc77524db38e7ce2767252533b15a1
**packet_file_path:** prd/architecture/review-cases/packets/RC-2026-09-10-001.json
**packet_file_sha256:** sha256:b75c0c228b10811399e5bad1b0649b7d33591597d433fca13dadb425c76eea64
**packet_declared_content_sha256:** sha256:baad2d036a629be39fa049c7aab7d1383ffc77524db38e7ce2767252533b15a1
**reviewed_git_revision:** 6f1a27537a659f291e0147e0fbd8be6ca199261c
**findings_total:** 19
**rereverified_rows:** 4
**class_match_compatibility_rows:** 13
**class_mismatch_rows:** 6
**exact_class_matched_verdict_rows:** 2
**dispositions_recorded:** 0
**review_case_events_written:** 0
**human_session_run:** false
**submission_path:** actor_bound_path_available false
**hold_basis:** valid per-finding dispositions absent
**adoption_basis:** variant C established (v2, authenticated)
**f01_f15:** residual_d519_not_proof
**f13_prior_owner_decision:** explicit owner defer deferred-explicit (established in the S02 answer record v2)
**f13_current_rc28_disposition:** none recorded (the RC28 ledger slot is null)
**f18:** bounded_adoption_evidence_present plus independent_evaluation pending
**f19:** machine_class_match_done human_sufficiency_pending
**resume_condition:** a real authenticated actor-bound session must record valid per-finding dispositions through record_human_disposition with a verified read-back per answer; without that session RC28 stays on hold
**contract:** scripts/m210_s04_slice_battery_contract.test.mjs

**rc28: hold**

This checkpoint records the final machine state of the RC28 review for milestone
M210-3afp79. The hold is a sanctioned fail-closed outcome: the machine
re-verification is complete, the source-bound checks are done and the 19
source-bound cards are ready, but no valid per-finding human disposition exists
yet through the authenticated actor-bound `record_human_disposition` path. The
established bounded adoption of variant C (v2, authenticated) is a separate,
already-recorded fact: it does not close RC28 and it is not the reason for the
hold. The hold rests on the absence of valid per-finding dispositions, never on
an absence of variant C adoption.

## Findings machine verdicts

Each row is the machine verdict carried by the T02 evidence matrix for the
finding. A verdict names what the machine proved, not a human disposition.

| Finding | Proof class | Machine verdict |
| --- | --- | --- |
| RC28-F01 | evidence | evidence_absent_residual_named |
| RC28-F02 | evidence | evidence_present_residual_named |
| RC28-F03 | evidence | evidence_present_residual_named |
| RC28-F04 | process | evidence_present_class_matched |
| RC28-F05 | process | evidence_present_residual_named |
| RC28-F06 | implementation | evidence_class_mismatch |
| RC28-F07 | implementation | evidence_class_mismatch |
| RC28-F08 | implementation | evidence_class_mismatch |
| RC28-F09 | implementation | evidence_class_mismatch |
| RC28-F10 | implementation | evidence_class_mismatch |
| RC28-F11 | implementation | evidence_class_mismatch |
| RC28-F12 | design | evidence_present_residual_named |
| RC28-F13 | design | awaiting_owner_decision |
| RC28-F14 | design | evidence_present_class_matched |
| RC28-F15 | evidence | evidence_absent_residual_named |
| RC28-F16 | evidence | gate_hold |
| RC28-F17 | evidence | evidence_present_residual_named |
| RC28-F18 | design | evidence_present_residual_named |
| RC28-F19 | docs | evidence_present_residual_named |

## Count semantics

Four independent count kinds are recorded in the header, and they must never be
collapsed into one class-matched number:

- `rereverified_rows: 4` - RC28-F02, RC28-F04, RC28-F05 and RC28-F14, the rows
  re-checked against live sources by the T02 matrix.
- `class_match_compatibility_rows: 13` - the rows whose `class_match` field is
  true. The flag is a compatibility statement: the available evidence is of the
  required proof class. It is neither a sufficiency claim nor evidence presence
  and it is not an `evidence_present_class_matched` verdict; a row can carry a
  true flag and still be `evidence_absent_residual_named` (RC28-F01, RC28-F15).
- `class_mismatch_rows: 6` - the rows whose `class_match` field is false, each
  with a named `mismatch_reason_code`.
- `exact_class_matched_verdict_rows: 2` - the rows whose machine verdict is the
  exact `evidence_present_class_matched` (RC28-F04 and RC28-F14). This is the
  only count that names a class match as a positive check outcome.

Every count above is derived from the live T02 rows
(`prd/architecture/m210-s04-finding-evidence-matrix.json`) and every value is
re-derived by the contract. A drift between the header and the live rows is
refused with `counts_drift`, a collapsed count kind is refused with
`count_conflation`, and a T02 summary that disagrees with the rows it summarises
is refused with `matrix_summary_drift`.

## Digest namespaces

Three digests live in three namespaces and must never be relabelled into one:

- `source_content_sha256` - the review source document
  (`doc/review/review-28-10-09-2026.md`) as it exists on disk.
- `packet_file_sha256` - the packet JSON file
  (`prd/architecture/review-cases/packets/RC-2026-09-10-001.json`) as it exists
  on disk. It is a different value from the source digest.
- `packet_declared_content_sha256` - the content digest the packet declares in
  its own `source.content_sha256`; it binds the packet to the source document
  and therefore equals `source_content_sha256`.

The contract re-hashes both files live and refuses a swap of the two namespaces
with `digest_namespace_confused`; a source digest placed in the packet field is a
namespace confusion, not a cosmetic slip.

## Prior owner decision and current RC28 ledger

RC28-F13 has two separate records in two separate namespaces:

- The prior owner decision, recorded in S02: an explicit owner defer
  (`deferred-explicit`). That decision is established and it still stands.
- The current RC28 ledger slot: none recorded. The RC28 answer slot for F13
  stays null because no authenticated actor-bound disposition exists yet.

`none recorded` describes the current RC28 ledger only. It must never be read as
the prior owner defer being absent; that reading is a namespace confusion and is
refused with `prior_owner_defer_denied`. Reading the prior defer as if it were
the current RC28 disposition is refused with `prior_decision_ledger_confused`.

## Human sufficiency

The T02 matrix re-verified 4 rows against live sources and named a class
mismatch with a reason code on 6 rows. The `class_match` compatibility flag is
true on 13 rows, but a true compatibility flag only says the evidence is of the
required proof class; it is neither a sufficiency claim nor evidence presence.
Only 2 rows carry the exact `evidence_present_class_matched` verdict. Human
sufficiency is bounded by what the machine could prove:

- RC28-F01 and RC28-F15: residual named under D519; sufficient for a
  deferred/explicit residual disposition, insufficient for already_satisfied.
  D519 is a scope deferral, not proof.
- RC28-F02, RC28-F03, RC28-F05, RC28-F12, RC28-F17, RC28-F18 and RC28-F19:
  evidence present with a named residual; each is sufficient for a bounded
  disposition of its own class and none is sufficient for a requirement
  promotion.
- RC28-F18 specifically: the bounded adoption evidence is present (v2
  checkpoint and v2 answer record, authenticated criterion), while the
  independent evaluation and the ledger disposition remain pending.
- RC28-F13: the current RC28 ledger slot is still null while the prior S02 owner
  defer stands. No live adoption owner is recorded in the RC28 ledger; no agent
  may record this decision and no agent may impersonate the owner.
- RC28-F16: gate hold from the M209/S01 adjudication.
- RC28-F06 through RC28-F11: class mismatch in the implementation proof class;
  insufficient until a class-matched implementation proof exists.
- RC28-F04, RC28-F14: exact class-matched verdict; the machine class check is
  done, while the human sufficiency decision stays pending.

## Non-claims

- No Review Case event was written, and no `record_human_disposition` call was
  made.
- No disposition was recorded, no option was selected and no requirement was
  promoted; every requirement status stays unchanged.
- The recommendation on each card is advisory and is not consent.
- The established bounded adoption of variant C is not a per-finding
  disposition and is not submission authority for the Review Case ledger.
- The `class_match` compatibility flag on a row is not a class-matched verdict,
  not evidence presence and not sufficiency; only the machine verdict names the
  check outcome.
- No product runtime was touched: `crates/` is untouched and section 3 of
  `prd/temporal-legal-model.md` is byte-identical to its pin.
- This checkpoint is not a session transcript and it contains no answer.

## Fail-closed boundary

The submission path stays closed. The submission gate is `applied=false` and the
actor-bound path is unavailable, so the review records nothing. The named
refusal codes that keep this boundary fail-closed include:
`submission_without_actor_bound_path`, `actor_bound_scope_confused`,
`self_asserted_identity`, `authority_binding_missing`, `forbidden_actor_source`,
`agent_may_not_submit`, `readback_missing`, `event_id_mismatch`,
`drift_invalidates_proposal`, `revision_namespace_confused`, `unconfirmed_answer_recorded`,
`blanket_confirmation_forbidden`, `preselect_forbidden`,
`recommendation_as_consent`, `review_case_event_written`, `crate_touched`,
`non_ascii_artifact` and `raw_text_leak`. The checkpoint itself is refused when
its own semantics drift: `counts_drift`, `count_conflation`,
`matrix_summary_drift`, `digest_namespace_confused`, `prior_owner_defer_denied`,
`prior_decision_ledger_confused`, `hold_basis_invalid` and `checkpoint_failed`. A
checkpoint may not soften the hold into a pass, and `rc28: closed` is refused
until 19 valid human dispositions are recorded through the authenticated
actor-bound path with a per-answer read-back.

## Resume condition

RC28 leaves hold only when a real authenticated actor-bound review session
records a valid per-finding disposition for each of the 19 findings through
`record_human_disposition`, with the deterministic `event_id` and the confirmed
fields echoed back and verified after each answer, while the four fingerprints
(source document digest, packet file digest, card-set digest, tested matrix
revision) still match. Until then the 19 answer slots stay null, the confirmed
count stays 0 and the outcome stays hold.
