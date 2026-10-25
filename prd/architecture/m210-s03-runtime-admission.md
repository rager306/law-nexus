# M210/S03 conditional bounded semantic runtime admission checkpoint

**admission: granted**
**recorded:** 2026-09-25
**milestone / slice:** M210-3afp79 / S03
**classification:** source-bound conditional bounded semantic runtime admission checkpoint, fail-closed
**scope:** the conditional bounded semantic runtime of M210/S03 only, bounded exactly to the
adopted candidate layer of variant C (abstention_first_candidates_only): the S03 start gate,
the bounded semantics contract, the abstention diagnostic over the 18 source-bound S01 inputs
and the gated activation delta. Out of scope: rule composition, precedence resolution, facet
defaults, case applicability, any edit of prd/temporal-legal-model.md section 3, any Review
Case event, any crate change, any requirement or lifecycle promotion, any declared runtime
surface, F13 operation grammar, ln-applicability NormRule, RuVector and TEI. This record
grants no authorization for any of those and bounds every future grant to the same surface.
**source_revision:** sha256:6fddac12e86c48a3f27aba5a143b94e3b098b0198c0a39366bef0e6c87d107ad
**owner_admission_ref:** subjective-UAT criterion 37181c25-88b0-4896-bffe-d10642970e6f
**admission_basis:** admission_granted is derived from the superseding S02 v2 sources: the adoption checkpoint carries exactly one verdict line reading granted with the bounded variant C scope, the answer record v2 status is owner_decision_recorded with an authenticated interactive source and an accepted disposition on an authenticated channel, the governing-surface check verdict governing_surface_absent is re-read under v2 as a v1-scoped pre-decision finding rather than a blocker, and the superseded v1 checkpoint and v1 answer record stay byte-identical.
**adopted_variant:** C (abstention_first_candidates_only)
**adopted_construct_set:** candidate_emission, source_anchors, family_classification_hypotheses, unknown_verdict, conflict_verdict, provenance_links
**runtime_stop:** lifted for the adopted candidate-layer scope only (variant C, abstention_first_candidates_only); it stays active for composed-rule runtime, applicability runtime and any section 3 promotion.
**runtime_work:** not-started
**runtime_demo:** not-proven
**review_case_events_written:** 0
**requirements_promoted:** 0
**section3_pin:** sha256:a8f7184d38c9a48605c1c91f16fa64a33644a949ff83a8066efb97bd3f3cebd6
**f13_status:** deferred-explicit (the owner kept amendment operations deferred; the owning slice reopens F13 with a fresh rebind before any bounded temporal replay relies on it)
**contract:** scripts/m210_s03_start_gate_contract.test.mjs

## Purpose and boundary

RC28-F18 requires a human-owned legal IR adoption before implementation, and the
milestone vision forbids starting the bounded semantic runtime before the owner
adopts it. S02 first closed with `admission: not-adopted` and was then superseded
by the v2 records that carry the owner's authenticated interactive decision. This
harness cannot enforce a milestone dependency, so S03 carries an explicit,
machine-checked start gate instead of starting by the mere fact that S02 closed.

This document is that checkpoint, re-bound to the live v2 sources. The v1
checkpoint and the v1 answer record stay byte-identical as superseded history:
the v2 checkpoint and the v2 answer record each bind their predecessor by digest,
and the gate refuses to proceed if either superseded byte string moved. Nothing is
rewritten behind them, and every earlier S03 receipt stays in git history.

The verdict is `granted` for the adopted candidate layer of variant C only. The
gate is not a grant, not an approval, not a waiver, not a requirement closure, not
a Review Case disposition, not a legal conclusion, not a lifecycle promotion and
not an adoption of normative semantics. It bounds the grant to the adopted
candidate layer and keeps every surface outside that layer on hold.

The v1 governing-surface check recorded `governing_surface_absent` and
`actor_bound_path_available: false`. Both findings belong to the v1 state, in
which no authenticated interactive answer existed yet, and they concern the
review-case disposition path rather than the subjective-UAT channel. Under v2 the
authenticated direction exists in the tracked, hash-bound answer record v2, so the
gate re-reads the old finding as a v1-scoped pre-decision record instead of a
blocker. No repeat owner decision is required, and none is implied.

The grammar deliberately matches the M208, M209 and M210/S02 admission
checkpoints: exactly one verdict line of the form shown by the shared expression
/^\*\*admission: (granted|not-adopted)\*\*$/m, plus bold header fields and
level-## sections. The fail-closed boundary section enumerates the exact code set
this checkpoint's contract can emit.

## Sources checked

Each row is repository-relative and byte-bound: the recorded digest is compared
against the live file content by scripts/m210_s03_start_gate_contract.test.mjs.
Any later content change to a cited source invalidates this checkpoint and
requires a fresh checkpoint rather than an edit of the verdict here.

Digests are accepted in both spellings, a bare 64-hex value and the canonical
`sha256:`-prefixed value, and are normalized before comparison. This table uses the
prefixed spelling while the v2 checkpoint table uses the bare spelling, so the
contract exercises both forms on live data; a digest-shaped cell in any other
spelling is rejected by name rather than skipped.

| Source | sha256 | What it records |
| --- | --- | --- |
| `prd/architecture/m210-s02-adoption-checkpoint-v2.md` | `sha256:6556bab25ab1c046784087311947d354f6eeb4815de2f879f477006f20813902` | The superseding adoption checkpoint this gate derives its verdict from. Exactly one verdict line: admission granted, scope bounded to variant C, owner_admission_ref = subjective-UAT criterion 37181c25-88b0-4896-bffe-d10642970e6f, runtime_stop lifted for the candidate layer only, f13_status deferred-explicit. |
| `prd/architecture/m210-s02-answer-record-v2.json` | `sha256:b45762e9cb0a67dc7b7eb01501a347200ae652be0381efa7db876ff4c3e4c8cd` | The superseding interactive answer record. Status owner_decision_recorded with answer_source interactive and authenticated subjective-UAT references, selected option C abstention_first_candidates_only, f13_status deferred-explicit. |
| `prd/architecture/m210-s02-governing-surface-check.json` | `sha256:1caaa7d3772085c8f1626c9aee4e67ecd872947c5e5d06c8400e3ca5e8482056` | The v1-scoped governing-surface check, re-read under v2. Its answer_record_ref is the v1 answer record and its verdict governing_surface_absent describes the v1 state; under v2 it is a pre-decision record, not a blocker. |
| `prd/architecture/m210-s02-adoption-checkpoint.md` | `sha256:31ed55b9f5db500a40441ce642b773127b6523b016a2453038fc8648d81f7031` | The superseded v1 checkpoint, preserved byte-identically. Its single verdict line is admission not-adopted and the v2 checkpoint binds this exact digest. |
| `prd/architecture/m210-s02-answer-record.json` | `sha256:efc1b820506dabadde87d1ff8f338b95d6bd85417bce127ca17a07e5b3f9528b` | The superseded v1 answer record, preserved byte-identically. Status pending_human_decision with answer_source none, and the v2 answer record binds this exact digest as the record it supersedes. |
| `prd/architecture/m210-s02-rebind-report.json` | `sha256:e6689b8137534eb7a6d367e78d87e21329d33bc6fa601edb382e49bd5221736b` | The S02 rebind of every tracked S01 input plus the re-derived corpus anchors, carrying the tested source revision the grant names. |
| `prd/architecture/m210-s02-owner-decision-packet-v2.json` | `sha256:e0900eb3480e601126ca499e5b6c77da95c9bb1d0077b3aa7b7f18959240517d` | The corrected machine-readable question set: the IR options including variant C, the separate F13 question, and an advisory recommendation carrying is_consent false. |
| `prd/architecture/m210-s02-owner-decision-presentation-v2.md` | `sha256:0b17919a62b7c1ef27f44e6a761de0c3f781d6920315b2ad89c922ba5789afeb` | The presentation shown to the owner, recording that the recommendation is advisory and that no option is preselected. |
| `prd/architecture/m210-s02-packet-corrections-v2.md` | `sha256:582c28158f7bfdce06f8ab8221714d21e2e131de8addd65f5170ca626ab32355` | The explicit corrections between the v1 and v2 decision packets: what was wrong in v1 and what the owner must read differently. |
| `prd/temporal-legal-model.md` | `sha256:a8f7184d38c9a48605c1c91f16fa64a33644a949ff83a8066efb97bd3f3cebd6` | The living temporal and legal model. Section 3 keeps NormRule, Condition, LegalEffect, Exception, Defeater and ApplicabilitySelector deferred-undefined, and the file is byte-identical to the pin recorded here. |
| `prd/architecture/m210-s01-ir-alternatives.json` | `sha256:74295295efb6a66e9a10a65a22cf1d3615d94ce0ceee719e2d6fddb71789e470` | The three S01 IR variants and, per variant, the required_new_adr_terms a gated dictionary delta would have to define. Variant C is the adopted one. |
| `prd/architecture/m208-s01-runtime-admission.md` | `sha256:aad5f2800dfa7eaec61e79e364e80902af12b83617a22089bd576b3136e9b60e` | The M208/S01 admission checkpoint for RC28-F13. It defines what counts as a grantor reference: an interaction id with a timestamp or an authenticated subjective-UAT criterion id, never a bare name, a role, a milestone closeout or a lock. |
| `prd/architecture/m209-s01-punkt-decision.md` | `sha256:0b59f95a96d54cdcf62a08a026a082102fa46d61e55fa73244ae9f242602f2b0` | The grammar precedent: exactly one verdict line, bold header fields, level-## sections, a named resume condition and not-adopted as a terminal lawful outcome with owner_admission_ref none. |
| `prd/architecture/review-cases/rc28-remediation-program.md` | `sha256:8ae51137a5ead37a761cff59e87d5a8747a348ee9b21ea0855bd60ca6b82232f` | The remediation program: RC28-F18 requires a human-owned legal IR adoption before implementation, and F13 ownership sits with M205/S03 and M208/S01-S04. |
| `doc/adr/README.md` | `sha256:bc103b4f7133c5729971825b5bc8bbe782dfb78c9791e66023978e3e564b991f` | The ADR status surface: status Accepted records design acceptance of an architecture record and is not human adoption of normative semantics. |

## Start gate verdict

The gate records `admission: granted` for the adopted candidate layer of variant C.
The grant is bounded exactly to what the owner adopted: candidate emission, source
anchors, family classification hypotheses, Unknown and Conflict verdicts and
provenance links, with their contracts, diagnostics and tests. A no-start
directive remains for everything outside that layer: composed-rule runtime,
precedence resolution, facet defaults, case applicability, any section 3
promotion, any Review Case event and any crate change. Those surfaces stay on
hold and this record lifts nothing for them.

Accepting the adoption is not executing it. Adoption and execution are recorded as
two separate states: `adoption_state` names the established adoption, while
`execution_state` records that nothing was executed, zero candidates were emitted
and zero conflicts were found. Reading adoption as execution, or execution as
adoption, is refused by name.

The owner admission reference is bound to the criterion recorded in the v2 answer
record, `subjective-UAT criterion 37181c25-88b0-4896-bffe-d10642970e6f`, and to the
tested source revision the v2 checkpoint names. A superseded, foreign, borrowed or
replayed reference is refused; a lock, an integrity or battery PASS, a milestone
closeout, an ADR status and any bare name or role title are never grantor
references.

## Owning surfaces (declared, not created)

This checkpoint declares the runtime surfaces a later sanctioned slice would
create, and it asserts that none of them exists today:

| Surface | State |
| --- | --- |
| `crates/ln-temporal/src/normative_candidate.rs` | declared, absent |
| `crates/ln-temporal/src/bounded_semantics.rs` | declared, absent |
| `crates/ln-temporal/tests/normative_candidate_contract.rs` | declared, absent |
| `crates/ln-decode/src/candidate_emission.rs` | declared, absent |
| `scripts/m210_s03_verify.sh` | declared, absent |

No crate module is registered for any of them, `crates_touched` stays empty and no
requirement or lifecycle row is promoted. The adoption permits the candidate layer
in a later, separately sanctioned slice; it does not create it here and it does
not widen any earlier admission scope.

## Non-claims

- This gate is a start-gate record: it is not a grant, not an approval, not a
  waiver, not a requirement closure, not a Review Case disposition, not a legal
  conclusion and not a lifecycle promotion.
- admission_granted is derived from the authenticated bounded adoption of
  variant C recorded in the superseding S02 v2 sources: it permits the adopted
  candidate layer only and it is not an execution of that layer.
- The adoption is a bounded construct-layer adoption and not a normative
  semantics adoption: section 3 stays byte-identical to its pin and its deferred
  terms stay deferred-undefined.
- No runtime surface is created by this gate: every declared runtime surface is
  named as declared-and-absent and none of them exists on disk.
- RC28-F18 requires a human-owned legal IR adoption before implementation; a
  milestone lock, an integrity result, a milestone closeout, an ADR status and any
  bare name or role title are never grantor references.
- F13 stays deferred-explicit: it is a separate decision with its own owning
  surfaces and it is never derived from the bounded IR.
- The superseded v1 S02 checkpoint and the superseded v1 S02 answer record stay
  byte-identical and hash-bound as history; nothing is rewritten behind them.
- Out-of-scope surfaces stay untouched: ln-applicability NormRule, RuVector, TEI
  and the F13 operation grammar are not claimed here.
- The bounded semantics contract, the abstention diagnostic and the activation
  delta stay design-only and are not created by this gate.

## Fail-closed boundary

The gate and this checkpoint can emit exactly the following named codes. Each one
is exercised by a mutation in scripts/m210_s03_start_gate_contract.test.mjs.

- Structure: `verdict_missing`, `verdict_ambiguous`, `header_field_missing`,
  `section_missing`, `sources_insufficient`.
- Source binding: `source_unresolved`, `source_hash_mismatch`,
  `source_revision_mismatch`, `source_pin_form_rejected`, `v2_source_not_wired`,
  `superseded_source_selected`, `superseded_hash_accepted`,
  `superseded_ref_accepted`, `receipt_silently_rewritten`.
- Grant provenance: `grant_without_interactive_ref`,
  `grant_without_governing_surface`, `non_owner_surface_as_grantor`,
  `lock_as_admission`, `integrity_pass_as_admission`,
  `milestone_closeout_as_admission`, `owner_decision_read_as_answered`.
- Verdict and scope: `admission_verdict_mismatch`, `scope_overclaim`,
  `f13_hold_misread`, `f13_scope_borrowed`.
- Adoption against execution: `adoption_read_as_execution`,
  `execution_read_as_adoption`, `runtime_stop_blanket_lifted`,
  `runtime_stop_inverted`, `runtime_permitted_without_admission`,
  `no_start_directive_missing`, `runtime_demo_claimed`.
- Product footprint: `s03_surface_present`, `lib_rs_registration_present`,
  `crate_touched`, `requirements_promoted`, `review_case_event_written`,
  `section3_mutated`, `out_of_scope_surface_claimed`.
- Hygiene: `runtime_claim_present`, `check_not_byte_identical`,
  `non_ascii_artifact`, `raw_text_leak`.

## Marker semantics

The contract prints `M210_S03_START_GATE_OK` only when every case passed. The
generator prints `M210_S03_START_GATE_WRITTEN` after a write,
`M210_S03_START_GATE_CHECK_OK` after a byte-identical check,
`M210_S03_START_GATE_PRINTED` after a print and `M210_S03_ADMISSION_MD_ABSENT`
to stderr when this document is missing. No marker is a grant, and none of them
proves the runtime demo.

## Resume condition

The grant is bounded to the adopted candidate layer and to the tested source
revision the v2 checkpoint names. Runtime work outside that layer resumes only
after a separate adopted contract and its own source-bound checkpoint exist for
the surface in question, and only after the inputs are re-bound by live digest and
the regression battery is green. F13 resumes only when its owning slice reopens it
with a fresh rebind. Any drift in a cited source, in the superseded v1 bytes, in
the owner reference or in the section 3 pin fails the gate closed and requires a
fresh checkpoint rather than an edit of the verdict here.
