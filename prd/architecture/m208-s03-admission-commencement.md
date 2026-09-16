# M208/S03 runtime admission: operation admission gate and commencement evidence

**admission: not-adopted**
**recorded:** 2026-09-16
**milestone / slice:** M208-wrz6fg / S03
**classification:** source-bound runtime admission checkpoint (fail-closed)
**scope:** the admission gate of a parsed operation (accepted target + operand match
+ temporal evidence) and commencement evidence — the admission leg of RC28-F13 and
RC28-F17 (M208/S03), realized — if ever admitted — by
`crates/ln-temporal/src/operation_admission.rs`,
`crates/ln-decode/src/change_commencement.rs` and the surfaces listed under
`Owning surfaces` below.
**selected_d388_gates:** G01, G02, G14
**requested_not_selected_d388_gates:** G05, G11, G12, G13, G15
**deferred_d388_gates:** G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13, G15, G16
**runtime_stop:** remains active for M208/S03; this record lifts runtime_stop for
no scope.
**runtime_work:** not-started
**runtime_demo:** not-proven
**admission_basis:** No source-bound owner admission covering the M208/S03 scope
(the admission gate of a parsed operation and commencement evidence) exists in the
tracked repository. The M208/S01 and M208/S02 checkpoints both stand at
`not-adopted`; every one of the ten `prd/architecture/m205-s01-pullenti-matrix.yaml`
rows whose `unblocks` contains `S03` keeps `human_adoption: pending` and
`lifecycle: [proposed]`; the only tracked granted scope in this area (RC28-F06..F12,
M206/S05) includes neither the admission leg of RC28-F13 nor RC28-F17.
**owner_admission_ref:** none
**contract:** scripts/m208_s03_admission_contract.test.mjs
**prerequisite M208/S01:** closed as a source-bound design-only no-start; its record
`prd/architecture/m208-s01-runtime-admission.md` stands at `not-adopted` and is
consumed here as the basis, not inverted by this document.
**prerequisite M208/S02:** closed as a source-bound design-only no-start; its record
`prd/architecture/m208-s02-nested-target-admission.md` stands at `not-adopted` and
is consumed here as the basis, not inverted by this document.
**M205 pins:** not edited by this document.

## Purpose and boundary

This document is the mandatory start gate of M208/S03. The milestone criterion
`New vocabulary human-adopted before code` requires a recorded admission before
runtime code is written, and D457 / D458 / D459 forbid minting that adoption out of
YAML design data, out of a design pin, or out of an integrity PASS. D503 (M208/S01)
and D504 (M208/S02) record that both preceding slices closed as no-starts for
exactly this reason, and D507 records that S03 is planned as a source-bound
design-only no-start as well. The S01 and S02 checkpoints are scope-bound to their
own slices: neither covers the admission gate of a parsed operation nor
commencement evidence, so S03 must open with its own source-bound checkpoint.

This record is a checkpoint, not a grant. It is not an approval, waiver,
requirement closure, Review Case disposition, legal conclusion, lifecycle
promotion, or runtime authorization. It records that no re-readable, source-bound
owner admission for the M208/S03 scope was found, and it therefore holds the
runtime stop: operation-admission and commencement-evidence runtime work does not
start and the S03 demo stays **not-proven** (`runtime_demo: not-proven`).

**no_start_directive:** while the verdict is `not-adopted`, no runtime work for
M208/S03 may start, no S03 runtime surface may be created, and no design statement
in this document may be read as proof.

## Sources checked

Each row is repository-relative and byte-bound: the recorded sha256 is compared
against the live file content by the executable contract. Any later change to a
cited source invalidates this record and requires a fresh checkpoint. Every path
below is tracked (`git ls-files --error-unmatch`); no ignored (`.agents/**`,
`.gsd/**`), absolute, or traversal path is cited anywhere in this record.

| Source | sha256 | What it records |
| --- | --- | --- |
| `prd/architecture/m208-s01-runtime-admission.md` | `aad5f2800dfa7eaec61e79e364e80902af12b83617a22089bd576b3136e9b60e` | The M208/S01 basis. `**admission: not-adopted**` with `runtime_stop: remains active for M208/S01`, `runtime_work: not-started`, `owner_admission_ref: none`, and `scope` restricted to the M208/S01 quoted operands and local change operations. It is scope-bound, so it cannot serve as the S03 admission. |
| `prd/architecture/m208-s02-nested-target-admission.md` | `9ea63ebae3cf3956a38da27f51f6daddfb5f778ae1002fe813d77e13522b964e` | The M208/S02 basis. `**admission: not-adopted**` with `runtime_stop: remains active for M208/S02`, `runtime_work: not-started`, `owner_admission_ref: none`, requested-not-selected gates `G05, G11, G12, G13`. It is scope-bound to nested targets and amending-act scope binding, so it cannot serve as the S03 admission. |
| `prd/architecture/m205-s01-pullenti-matrix.yaml` | `559b6637139acdf81f8a09cd8683cf28e48f1dd4507e0b9aa6ac67905727a131` | The prior-art matrix. Exactly ten rows carry `unblocks` containing `S03` (`PC-D-EDITION`, `PC-D-ThisDecree`, `PC-C-OWNER`, `PC-C-KIND`, `PC-C-CHILD`, `PC-C-VALUE`, `PC-C-PARAM`, `PC-C-LOCVALUE`, `PC-C-value-kind`, `PC-C-no-auto-reinterpret`); all ten keep `human_adoption: pending` and `lifecycle: [proposed]`; their requested gate union is `G05, G11, G12, G13, G15`. The file states `authoritative: false` and `non_claims: prior-art inventory only; not a license grant, runtime parity, or gold corpus`. |
| `prd/architecture/m205-s03-context-fsm.yaml` | `1d6fdf0ab295839e81aa301b8db89ada6d6be26d7b200f8604f60ccc0ac02d9d` | The design-only context FSM and source-operation alphabet pin. Header keeps `human_adoption: pending` and `runtime_stop_active: true`; `must_not_select: [G08, G09, G10, G11, G12, G13, G15]`; `selected_baseline: [G01, G02, G14]`. Its non-claims state that proposed labels remain pending and cannot mint `WorkId`, `ComponentId`, `CTV`, `InForce`, `NormRule`, or `LegislativeEffect`, and that the source authority policy remains deferred-undefined and therefore stop. |
| `prd/architecture/m205-s04-docs-reconciliation.yaml` | `fd254f66fa899596989398a7210d460052e54ae3a687ec74f5ba306aca14de4f` | `human_adoption: pending`, `runtime_stop_active: true`, `hashed_yaml_mutation: forbidden`; `d388_control.deferred_undefined` is the complement of `selected_baseline: [G01, G02, G14]` over G01..G16. Its non-claims state it is not a human adoption record and not `InForce` / force / `MicroOperation` / `LegislativeEffect` mint. |
| `prd/architecture/m206-s05-runtime-admission.md` | `ed7bac704a2184ff3f052f0065af99a76b2366c4f64e9f2892c6ba749f6b5751` | The only tracked source-bound `admission: granted` record in this area. Its scope is explicitly `M206/S05 runtime implementation of RC28-F06..F12`; it records `runtime_stop: lifted for M206/S05 scope only` and leaves G05/G11/G12/G13 deferred and unselected. Neither the admission leg of RC28-F13 nor RC28-F17 is admitted by it. |
| `prd/architecture/review-cases/rc28-remediation-program.md` | `8ae51137a5ead37a761cff59e87d5a8747a348ee9b21ea0855bd60ca6b82232f` | Assigns `F13: M205/S03, M208/S01-S04` with required proof `adopted operation grammar, old/new operands, nested targets, admission and bounded causal replay`, and `F17: M208/S03-S04, M209/S03-S04` with required proof `operation x provision x commencement x transitions x edition deltas, scoped coverage, frozen M201 untouched`. Gives M208 the start prerequisite `M205 operation adoption and M206` and states that no runtime step may cross its required adoption gate. |
| `doc/adr/0028-typed-lexer-legal-marker-lexicon.md` | `e40a12ea5f32755425fa7b645c7cc96f37f726037fcf45e3de7332b0bc640d09` | Owning ADR (D380-D388). It records that Pullenti's alphabet is an orientation only, that no `DecreeChange` type, G0 adoption, or identifying-cycle `Change` slot is adopted, and that no human adoption or finding disposition is claimed. |
| `prd/architecture/pending-effects-contract.yaml` | `87e2a96ae51f9c73c80549518780dfc0c488aec362152d07c1ff550f34d744c2` | Design-only pending-effects contract. `force_status_seed: [NotYetInForce, Unknown]` with the explicit `never automatic InForce` rule and `typed_non_success: [IncompleteSource, UnknownEffect]`; the file forbids reading a seed as an effect and states that an unproven condition yields the fail-closed outcome, never `false`. |
| `prd/architecture/force-interval-set-contract.yaml` | `7a4e28283ecdb50406f83414e30d6529bcc77f19c737c8b59fa9f3e03e201492` | Design-only force interval-set contract. `NotYetInForce` is a written status; the `Commence` trigger carries `seed default NotYetInForce/Unknown` and the comment `seed; never automatic InForce (MC-SEED)`; `Commence` opens `InForce` only as an authorized interval, and the file states `Commence is not ScheduleEffect; entering force is not pending bookkeeping`. |
| `prd/architecture/current-document-requisites.yaml` | `f011db54af7a6c790f046b487ea10e51b395c5f7a6036ef9e7718ba2cf8f60aa` | Declares `rule: authorization selects admissible claims; it never rewrites the literal mention`, and lists `commencement_rules` inside `temporal_separation.not_proven_by_sidecar` — i.e. sidecar material does not prove commencement; it stays explicitly unproven. |
| `prd/architecture/operation-registry.yaml` | `cee807b9b7cc68c1a23fa44a3d1fb1432349118e85e36dc7ddaffa36c049e8d6` | The design-only operation registry. OP-F `Commence` carries the full eight required fields, `evidence_span: span of the instrument wording that authorizes the commencement`, and `runtime_today: none` with `notes: not implemented; applied through the ADR-0018 overlay`. `name_mapping` lists only `Move`, `Renumber`, `Split` (industrial spine) and `Attach` (membership edge) as present today; the file mints no Rust types. |
| `prd/architecture/npa-promotion-gates.json` | `123b94a9c5d5f0fa49402943f9884aa8686e0d9e95342875d72ac5ce7fc361e7` | Records the open requirement debt: `R070` `remaining: "118 consolidated editions remain uncovered; commencement and transitional slot-filled evidence is not proven."`, and `non_claims` that promotions do not close `R035`/`R070`, do not move an ADR lifecycle, and that fixture or diagnostic evidence is not promotion proof. |

No other file is cited as an admission source. Additional live facts that are not
file-bound (for example the GSD milestone lock, journal state, or prior task
summaries) are cited nowhere in this record as admission evidence.

## Adoption state of the rows that unblock S03

Exactly ten matrix rows carry `unblocks` containing `S03`. All ten are still
unadopted in the tracked corpus:

| Row | owning surface | `human_adoption` | requested gates | `unblocks` |
| --- | --- | --- | --- | --- |
| `PC-D-EDITION` | `prd/architecture/npa-document-context.yaml` | pending | G15 | S03 |
| `PC-D-ThisDecree` | `prd/architecture/current-document-requisites.yaml` | pending | G15 | S03 |
| `PC-C-OWNER` | `prd/architecture/npa-document-context.yaml` | pending | G12, G13 | S03, M208 |
| `PC-C-KIND` | `prd/architecture/operation-registry.yaml` | pending | G12, G13 | S03, M208 |
| `PC-C-CHILD` | `prd/architecture/npa-document-context.yaml` | pending | G11, G12 | S03 |
| `PC-C-VALUE` | `prd/architecture/npa-document-context.yaml` | pending | G05, G12 | S03, M208 |
| `PC-C-PARAM` | `prd/architecture/npa-document-context.yaml` | pending | G12 | S03 |
| `PC-C-LOCVALUE` | `prd/architecture/npa-document-context.yaml` | pending | G12, G13 | S03 |
| `PC-C-value-kind` | `prd/architecture/npa-document-context.yaml` | pending | G12 | S03 |
| `PC-C-no-auto-reinterpret` | `prd/architecture/npa-document-context.yaml` | pending | G12, G13 | S03 |

Every row keeps `lifecycle: [proposed]`, so no row is selectable and no row is
selected by this record. `PC-C-KIND` is listed again here (as in the S02
checkpoint) because the operation-admission contour must not silently rewrite
KIND: its owning surface `prd/architecture/operation-registry.yaml` keeps
`lifecycle: [proposed]`, `authoritative: false` and `runtime_today: none` for
`Commence`.

**Provenance uncertainty, recorded not resolved.** The two `PC-D-*` rows
(`PC-D-EDITION`, `PC-D-ThisDecree`) carry only `unblocks: [S03]` with no `M208`
member, so their `S03` may address M205/S03 (the context-FSM slice) rather than
M208/S03. That ambiguity concerns M205/S03 alone; it is recorded as unclaimed
scope and is not resolved by guesswork. At any reading, `G15` stays
requested-not-selected, and neither row is claimed as M208/S03 scope.

The M205 milestone-level authenticated subjective UAT (criterion `d8d3c60d`) is
recorded in the GSD registry as an acceptance of the M205 design deliverable and is
cited by the tracked M206/S05 admission as the M204/M205 prerequisite. It is
**not** treated here as the M208/S03 admission, for the same source-bound reasons
recorded by the S01 and S02 checkpoints: it is a milestone-close acceptance of the
M205 design scope, not a scope binding for M208/S03 runtime surfaces; the only
tracked admitted runtime scope in this area is RC28-F06..F12; and the owning tracked
documents assert the opposite — the M205 pins carry `human_adoption: pending`,
ADR-0028 states that no identifying-cycle `Change` slot is adopted and no human
adoption is claimed, and `prd/architecture/npa-promotion-gates.json` states that
`commencement and transitional slot-filled evidence is not proven`. Where a tracked
owning source contradicts an inference, the checkpoint is fail-closed.

Deriving an admission from the matrix itself, from the context-FSM pin, from a
force/pending-effects/requisites design contract, from an integrity or battery PASS,
or from the D499 milestone lock is explicitly refused; those are the named
fail-closed cases below.

## Selected, requested and deferred D388 gates

- `selected_d388_gates: G01, G02, G14` — the pre-existing baseline already wired
  before M208 (it is also the `selected_baseline` of the M205/S03 pin and the gate
  set of the M206/S05 admitted scope). A not-adopted checkpoint selects no
  additional gate.
- `requested_not_selected_d388_gates: G05, G11, G12, G13, G15` — the union of the
  D388 gates requested by the ten rows whose `unblocks` contains `S03` (D508). The
  rows request them; adoption, not the pin, is what would select them. Provenance
  per gate:
  - `G05` — requested by the operand row `PC-C-VALUE` (`d388_gates: [G05, G12]`);
  - `G11` — requested by the nesting row `PC-C-CHILD` (`d388_gates: [G11, G12]`);
  - `G12` — requested by `PC-C-OWNER`, `PC-C-KIND`, `PC-C-CHILD`, `PC-C-VALUE`,
    `PC-C-PARAM`, `PC-C-LOCVALUE`, `PC-C-value-kind`, `PC-C-no-auto-reinterpret`;
  - `G13` — requested by `PC-C-OWNER`, `PC-C-KIND`, `PC-C-LOCVALUE`,
    `PC-C-no-auto-reinterpret`;
  - `G15` — requested by `PC-D-EDITION` and `PC-D-ThisDecree` only; per the
    provenance uncertainty above, those rows may address M205/S03, and at any
    reading `G15` stays unselected.
  The M205/S03 pin independently publishes `must_not_select: [G08, G09, G10, G11,
  G12, G13, G15]`, so `G11`/`G12`/`G13`/`G15` are explicitly barred from selection
  in the design pin as well.
- `deferred_d388_gates: G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13,
  G15, G16` — the complement of the selected set over G01..G16. Each of the 13
  gates remains individually deferred-undefined, and each requested-not-selected
  gate lies inside this deferred set.

Selecting any gate outside the selected set is a contract failure
(`gate_outside_selected_baseline`). A gate-set partition whose deferred member is
not the complement of the selected set is a contract failure
(`gate_deferred_mismatch`).

## Owning surfaces

The runtime surfaces this checkpoint governs, none of which may be created or
modified while the verdict is `not-adopted`:

- `crates/ln-temporal/src/operation_admission.rs` — the parsed-operation admission
  gate (accepted target + operand match + temporal evidence) (declared, not
  created);
- `crates/ln-decode/src/change_commencement.rs` — commencement-evidence extraction
  for a change operation (declared, not created);
- `crates/ln-temporal/tests/npa_operation_admission_contract.rs` — contract suite
  (declared, not created);
- `crates/ln-temporal/tests/npa_operation_admission_hostile_contract.rs` — hostile
  admission suite (declared, not created);
- `crates/ln-decode/tests/npa_change_commencement_contract.rs` — commencement
  contract suite (declared, not created);
- `crates/ln-temporal/src/lib.rs` — the `mod operation_admission` registration is
  absent and must stay absent;
- `crates/ln-decode/src/lib.rs` — the `mod change_commencement` registration is
  absent and must stay absent;
- `scripts/m208_s03_admission_commencement_battery.test.mjs` — proof battery
  (declared, not created);
- `prd/migration/rust-evidence/m208-s03-admission-commencement-battery.json` —
  durable battery evidence (declared, not created);
- `crates/ln-temporal/tests/m208_s03_frozen_surface_guard.rs` — frozen-surface
  guard (declared, not created);
- `scripts/m208_s03_t05_verify.sh` — the only would-be emitter of
  `M208_S03_VERIFY_OK` (declared, not created).

The declared names are the declared scope of absence, not a decision about the
final API: a future admitted runtime slice may choose different names and must
supersede this record with fresh hashes.

Inherited S01 and S02 runtime surfaces stay absent as well:
`crates/ln-decode/src/change_operand.rs` and `crates/ln-decode/src/change_operation.rs`
(contract code `s01_surface_present`) and `crates/ln-decode/src/change_target.rs`
(contract code `s02_surface_present`). Their absence is not re-scoped by this
document.

Read-only inputs consumed by the checkpoint, never written by it: the M205 pins,
ADR-0028, `prd/ARCHITECTURE.md`, the M206 admission records, the M208/S01 and
M208/S02 records, the operation registry, the design-only force / pending-effects /
requisites contracts, the M201 promotion gates, and the M200/M201 frozen evidence
artifacts.

## Neighbouring admitted contours

Existing admission, commencement and force surfaces belong to their own admitted
scopes (M206/S05-S07 and earlier) and are neighbours, not S03 deliveries:

- `crates/ln-temporal/src/provenance.rs` — `CommencementEvidence`,
  `TransitionalEvidence`, `ProvenanceAdmission`. `ProvenanceAdmission` is a
  caller-supplied provenance packet for one held `edition_delta` target; it is a
  per-target evidence carrier, not a parse-time admission gate for a parsed
  operation.
- `crates/ln-temporal/src/domain.rs` — `NormativeState`, `NotYetInForce`,
  `resolve_force_status_at` (ADR-0018 force overlay).
- `crates/ln-admission/src/lib.rs` — the HC-13 application/capacity policy
  (`DecideAdmission`, `AdmissionDecision { Admitted, Paused, Rejected }` with
  capacity/vendor/completeness reasons). It is an application scheduling policy,
  not an operation-admission gate over legal vocabulary.
- Suites `crates/ln-temporal/tests/provenance_edition_delta.rs`,
  `normative_state_force.rs`, `r070_proof_gate.rs`, `transitional_justification.rs`
  — each proves only its own admitted scope.

No PASS of any neighbouring surface may be quoted as S03 evidence, as the F13/F17
admission, or as C4 evidence (contract code `neighbouring_contour_as_evidence`).
Conversely, this record does not re-scope, edit, or re-interpret those contours.

## Non-claims

- This document is not a grant, not an approval, not a waiver, not requirement
  closure, not a Review Case disposition, and not legal acceptance.
- It does not edit the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`, the M206
  records, the M208/S01 and M208/S02 records, the operation registry, or any hashed
  NPA YAML.
- It does not promote any lifecycle: the pins stay `[proposed]` and
  `authoritative: false`, and the operation registry stays a non-runtime
  declaration with `runtime_today: none` for `Commence`.
- It does not admit Pullenti (D380); no vendor code, dictionary, threshold or
  `DecreeChange*` type is ported.
- It does not mint a candidate type: `ChangeTarget`, `ChangeScope`,
  `MicroOperation`, `LegislativeEffect`, `NormRule`, `InForce`, `WorkId` and
  `force` all stay deferred-undefined. Extraction never implies force.
- It does not claim the S03 demo (`Parsed operation becomes executable only with
  accepted target, operand match and temporal evidence`). With a `not-adopted`
  verdict the demo stays **not-proven** (`runtime_demo: not-proven`).
- It does not claim that the M206 runtime stop was inverted or lifted, nor that
  the M208/S01 or M208/S02 stops were lifted: all remain active for their own
  scopes.
- It explicitly records that `crates/ln-admission/src/lib.rs` (the HC-13
  application/capacity policy) and `ProvenanceAdmission`
  (`crates/ln-temporal/src/provenance.rs`) are **not** the S03 operation-admission
  gate, and that claiming so is the fail-closed case
  `operation_admission_gate_claimed`.
- It explicitly refuses the inference that text presence in a consolidated edition
  implies `InForce` (contract code `text_presence_implies_inforce_claimed`);
  `TL-GC19` vacatio is the opposite: the amended text may already be present while
  force stays `NotYetInForce` pending per-component commence.
- It does not treat the D499 GSD milestone lock (`GSD_MILESTONE_LOCK=M208-wrz6fg`)
  as an admission. The lock is a process affordance, not an owner adoption of legal
  vocabulary.
- It does not treat a PASS of its own contract — or of any integrity, battery or
  milestone-completion check — as runtime proof or as C4 evidence.
- It does not create the S03 hostile contour, battery, frozen-surface guard or
  verify runner: they are deferred, not simulated.

## Fail-closed boundary

The executable contract `scripts/m208_s03_admission_contract.test.mjs` runs
offline (`node --test`; subprocesses limited to `git ls-files` and
`git status --porcelain`) and refuses the following states. Its code set is
synchronized with the T03 task plan; the contract's own suite asserts each code
below.

| Failure case | Code |
| --- | --- |
| No `**admission: ...**` verdict line | `verdict_missing` |
| More than one verdict line (ambiguous) | `verdict_ambiguous` |
| Fewer than twelve byte-bound source rows | `sources_insufficient` |
| Cited source missing, absolute, or otherwise unresolvable | `source_unresolved` |
| Cited source outside version control | `source_not_tracked` |
| Recorded sha256 differs from live file content | `source_hash_mismatch` |
| An ignored path (`.agents/**`, `.gsd/**`) offered as a source | `ignored_path_as_source` |
| Adoption minted from pins/YAML alone (`granted` with only `.yaml` sources) | `self_minted_adoption` |
| `granted` without an owner interaction reference | `owner_admission_ref_missing` |
| `granted` citing an integrity/battery PASS instead of an owner decision | `integrity_pass_as_admission` |
| `granted` citing D499 / `GSD_MILESTONE_LOCK` as the admission | `lock_as_admission` |
| The S01 basis does not read `not-adopted` | `s01_basis_not_adopted` |
| The S02 basis does not read `not-adopted` | `s02_basis_not_adopted` |
| A selected gate outside the admitted set | `gate_outside_selected_baseline` |
| Deferred set not equal to the complement of the selected set | `gate_deferred_mismatch` |
| `runtime_stop` lifted while the verdict is not-adopted | `runtime_stop_inverted` |
| No-start directive absent for a not-adopted verdict | `no_start_directive_missing` |
| Required section (`Sources checked`, `Owning surfaces`, `Non-claims`, `Fail-closed boundary`, `Marker semantics`, `Resume condition`) absent | `section_missing` |
| Contract reference absent | `contract_reference_missing` |
| Any declared S03 runtime surface exists (one code per surface) | `s03_surface_present` |
| An inherited S01 runtime surface exists | `s01_surface_present` |
| An inherited S02 runtime surface exists | `s02_surface_present` |
| `mod change_commencement` registered in `crates/ln-decode/src/lib.rs` | `lib_rs_registration_present` |
| `mod operation_admission` registered in `crates/ln-temporal/src/lib.rs` | `temporal_lib_rs_registration_present` |
| The existing HC-13 capacity policy or `ProvenanceAdmission` claimed as the operation-admission gate | `operation_admission_gate_claimed` |
| Text presence in a consolidated edition claimed to imply `InForce` | `text_presence_implies_inforce_claimed` |
| A PASS of a neighbouring admitted contour re-labelled as S03 evidence | `neighbouring_contour_as_evidence` |
| Runtime proof claimed while the verdict is not-adopted | `runtime_proof_claimed` |
| `M208_S03_VERIFY_OK` claimed reachable | `verify_marker_reachable_claim` |
| A checkpoint-contract PASS re-labelled as runtime proof | `contract_pass_as_runtime_proof` |
| The D499 lock re-labelled as runtime proof | `lock_as_runtime_proof` |
| The inherited S01 contract is absent | `s01_contract_missing` |
| The inherited S02 contract is absent | `s02_contract_missing` |
| The T02 no-start notes are absent | `t02_note_missing` |

Missing, conflicting, or unavailable evidence stays fail-closed. No policy is
chosen by inference, no default admission exists, and a contract PASS denotes only
that the no-start state is intact — never a runtime result.

## Marker semantics

- `M208_S03_ADMISSION_OK` — emitted by the contract when the checkpoint record is
  valid: an unambiguous verdict, at least twelve byte-bound resolvable sources, a
  valid gate partition, and intact runtime-stop invariants. It denotes a valid
  **checkpoint**, not a grant.
- `M208_S03_ADMISSION_NOT_GRANTED` — emitted together with the marker above when
  the verdict is `not-adopted`, so the marker cannot be read as a grant.
- `M208_S03_GATES_OK` — emitted when the selected / requested / deferred gate
  partition is valid.
- `M208_S03_ADMISSION_NO_START_OK` — emitted when the admission/commencement
  no-start state holds: no declared S03 runtime surface exists, no inherited S01 or
  S02 runtime surface exists, `mod operation_admission` and `mod change_commencement`
  are unregistered, and no checkpoint-contract or D499 lock PASS is re-labelled as
  runtime proof.
- `M208_S03_VERIFY_OK` — `verify_marker: unreachable` by construction while the
  verdict is `not-adopted`: its only would-be emitter `scripts/m208_s03_t05_verify.sh`
  is deliberately absent, and the contract asserts that it never emits this marker.

## T02 no-start note: operation admission gate (accepted target, operand match, temporal evidence)

Recorded by M208/S03/T02 on 2026-09-16 under the `not-adopted` verdict above
(`verdict=not-adopted`). This note adds provenance to the checkpoint; it does not
relax it, and no statement in it is a proof.

- Provenance: the S01 no-start lineage is consumed here as the S03 admission basis —
  T01 attempt `f436a10e` settled failed/blocker-discovered, host recovery abort
  `532e9062`, decision D503 — the S02 slice shape is D504, and the S03 form itself is
  D507 (design-only no-start instead of a third recovery cycle), with D508 recording
  the requested gate union `G05, G11, G12, G13, G15`. All ten
  `prd/architecture/m205-s01-pullenti-matrix.yaml` rows whose `unblocks` contains
  `S03` (`PC-D-EDITION`, `PC-D-ThisDecree`, `PC-C-OWNER`, `PC-C-KIND`, `PC-C-CHILD`,
  `PC-C-VALUE`, `PC-C-PARAM`, `PC-C-LOCVALUE`, `PC-C-value-kind`,
  `PC-C-no-auto-reinterpret`) still carry `human_adoption: pending` and
  `lifecycle: [proposed]`; neither the admission leg of RC28-F13 nor RC28-F17 is
  admitted, and the only tracked admitted runtime scope in this area
  (RC28-F06..F12, M206/S05) excludes both. This note therefore records no runtime
  work: `runtime_work: not-started`.
- The gate statement `Parsed operation becomes executable only with accepted target,
  operand match and temporal evidence` is recorded here as a **design-only
  obligation** (the S03 demo stays `runtime_demo: not-proven`). No such operation
  admission gate exists today, and this note must not be read as if it did.
  Concretely: `crates/ln-admission/src/lib.rs` is the HC-13 application/capacity
  policy (`DecideAdmission`, `AdmissionDecision { Admitted, Paused, Rejected }` with
  capacity/vendor/completeness reasons) and is **not** an operation admission;
  `ProvenanceAdmission` in `crates/ln-temporal/src/provenance.rs` is a
  caller-supplied provenance packet for one held `edition_delta` target and is
  **not** a parse-time admission for a parsed operation; OP-F `Commence` in
  `prd/architecture/operation-registry.yaml` carries `runtime_today: none`. Claiming
  either neighbour as this gate is the fail-closed case
  `operation_admission_gate_claimed`.
- The three legs of the gate are recorded as design statements only; none of them is
  implemented:
  1. **accepted target** — the S02 contour (nested change target, amending-act scope
     binding), itself `not-adopted`; without an accepted, scope-bound target the
     operation is not admissible.
  2. **operand match** — the S01 contour (quoted operands and the five local change
     operations), itself `not-adopted`; a parsed operand must match its declared
     role before the operation is admissible.
  3. **temporal evidence** — the commencement contour of the note below; an
     operation whose commencement evidence is missing or ambiguous is not
     admissible.
  No leg delegates to another, no leg is satisfied by inference from the same source
  that produced the operation, and no leg may be promoted from a neighbouring
  admitted contour.
- Fail-closed: a missing or incompatible leg closes as **not admitted**. There is no
  "nearest" decision, no default-admission, and no KIND substitution; the operation
  is not executed silently and no `MicroOperation` is derived from the raw mention.
- Nothing is minted by this note: `ChangeTarget`, `ChangeScope`, `MicroOperation`,
  `LegislativeEffect`, `NormRule`, `InForce`, `WorkId` and `force` all stay
  deferred-undefined; `crates/ln-temporal/src/operation_admission.rs` is not
  created, and `mod operation_admission` is not registered in
  `crates/ln-temporal/src/lib.rs`. Extraction never implies force, and no KIND is
  rewritten, invented or substituted.
- No frozen surface was touched: the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`, the
  M206 records, the M208/S01 and M208/S02 records, the operation registry and the
  M200/M201 frozen evidence artifacts are unmodified by T02, and no runtime or test
  file was created.

The T02 evidence for this note is the note-presence state asserted by
`scripts/m208_s03_admission_contract.test.mjs` (contract code `t02_note_missing`)
together with the absence checks it performs over the declared S03 runtime surfaces;
the contract asserts this note while the verdict is `not-adopted`. A PASS of that
contract is **not** runtime proof and not C4 evidence.

## T02 no-start note: commencement evidence and the three anti-leakage statements

Recorded by M208/S03/T02 on 2026-09-16 under the `not-adopted` verdict above
(`verdict=not-adopted`). This note adds provenance to the checkpoint; it does not
relax it, and no statement in it is a proof.

- Provenance: the same S01 no-start lineage as the note above — T01 attempt
  `f436a10e` settled failed/blocker-discovered, host recovery abort `532e9062`,
  decision D503 — with the S02 slice shape D504 and the S03 form D507. Every owning
  matrix row whose `unblocks` contains `S03` keeps `human_adoption: pending`, the
  admission leg of RC28-F13 and RC28-F17 is **not** admitted, and the M206/S05
  admitted scope (RC28-F06..F12) excludes both. No commencement extractor is
  implemented here: `runtime_work: not-started`.
- Design anchors for the commencement contour, cited as design pins and never as
  runtime evidence: `prd/architecture/force-interval-set-contract.yaml` keeps
  `NotYetInForce` in `written_statuses` and gives the `Commence` trigger
  `seed default NotYetInForce/Unknown` with the explicit `never automatic InForce`
  rule; `prd/architecture/pending-effects-contract.yaml` fixes
  `force_status_seed: [NotYetInForce, Unknown]`; `prd/architecture/operation-registry.yaml`
  gives `Commence` an `evidence_span` and `runtime_today: none`;
  `prd/architecture/current-document-requisites.yaml` places `commencement_rules`
  inside `temporal_separation.not_proven_by_sidecar` and states that `authorization
  selects admissible claims; it never rewrites the literal mention`;
  `prd/architecture/npa-promotion-gates.json` records R070 `remaining: "118
  consolidated editions remain uncovered; commencement and transitional
  slot-filled evidence is not proven."`; and `prd/temporal-legal-model.md` TL-GC19
  (vacatio) states that the amended text may already be present while force stays
  `NotYetInForce` pending per-component commence.
- Three anti-leakage statements are recorded as design-only obligations, not as
  proof that they hold:
  1. **text presence is not force** — the presence of text in a consolidated edition
     does **not** give `InForce`; force stays `NotYetInForce` until a per-component
     commence is authorized (TL-GC19). Claiming the opposite is the fail-closed case
     `text_presence_implies_inforce_claimed`.
  2. **editorial or hypothesized commencement is not upgraded** — an editorial hint,
     a hypothesis or a sidecar suggestion about commencement is stored as
     unresolved and is never upgraded into a proven `InForce`; the literal mention
     is never rewritten by an authorization.
  3. **missing or ambiguous temporal evidence closes fail-closed** — no default to
     the publication date, the decision date, the ingestion date, or a "nearest"
     date, and no default admission from the seed status. The outcome is the
     fail-closed non-success, never a silent `InForce` and never `false`.
- A neighbouring admitted contour must not be read as S03 delivery:
  `crates/ln-temporal/src/provenance.rs` (`CommencementEvidence`,
  `TransitionalEvidence`, `ProvenanceAdmission`), `crates/ln-temporal/src/domain.rs`
  (`NormativeState`, `NotYetInForce`, `resolve_force_status_at`) and the suites
  `crates/ln-temporal/tests/provenance_edition_delta.rs`, `normative_state_force.rs`,
  `r070_proof_gate.rs`, `transitional_justification.rs` each prove only their own
  admitted scope (M206/S05-S07 and earlier). None of their PASSes may be cited as S03
  evidence, as the F13/F17 admission or as C4 evidence (fail-closed case
  `neighbouring_contour_as_evidence`).
- Nothing is minted by this note: `ChangeTarget`, `ChangeScope`, `MicroOperation`,
  `LegislativeEffect`, `NormRule`, `InForce`, `WorkId` and `force` stay
  deferred-undefined; `crates/ln-decode/src/change_commencement.rs` is not created,
  and `mod change_commencement` is not registered in `crates/ln-decode/src/lib.rs`.
  Extraction never implies force.
- No frozen surface was touched: the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`, the
  M206 records, the M208/S01 and M208/S02 records, the operation registry and the
  M200/M201 frozen evidence artifacts are unmodified by T02, and no runtime or test
  file was created.

The T02 evidence for this note is the note-presence state asserted by
`scripts/m208_s03_admission_contract.test.mjs` (contract code `t02_note_missing`) and
the anchor-token checks it performs over this section; the contract asserts this note
while the verdict is `not-adopted`. A PASS of that contract is **not** runtime proof
and not C4 evidence.

## T02 no-start note: no hostile contour, no battery, no runtime proof

Recorded by M208/S03/T02 on 2026-09-16 under the `not-adopted` verdict above
(`verdict=not-adopted`). This note adds provenance to the checkpoint; it does not
relax it.

- Provenance: the same S01 no-start lineage as the two notes above — T01 attempt
  `f436a10e` settled failed/blocker-discovered, host recovery abort `532e9062`,
  decision D503, S02 slice shape D504, S03 form D507; every owning row whose
  `unblocks` contains `S03` keeps `human_adoption: pending`, and the admission leg of
  RC28-F13/F17 is not admitted; `runtime_work: not-started`.
- The hostile contour stays not-started: `hostile_proof: deferred`. No
  `crates/ln-temporal/tests/npa_operation_admission_hostile_contract.rs` is created,
  no hostile commencement fixture (missing commencement evidence, text-presence
  `InForce` claim, default-date fallback) is added, and no host-side generator,
  adapter or CLI hook is added. The absence of that suite is the expected state — a
  hostile contour may not precede the admission it would verify against, so its
  proof is deferred until a source-bound owner admission of the M208/S03 scope
  exists.
- The proof battery and the frozen-surface guard stay not-started:
  `battery_proof: deferred` and `frozen_surface_proof: deferred`. No
  `scripts/m208_s03_admission_commencement_battery.test.mjs`, no
  `prd/migration/rust-evidence/m208-s03-admission-commencement-battery.json` and no
  `crates/ln-temporal/tests/m208_s03_frozen_surface_guard.rs` is created. A battery
  would have to measure the admission decisions and commencement evidence of a
  runtime surface that is itself not-started, so it cannot precede the admission it
  would measure.
- No runtime proof is claimed anywhere in this record, here or elsewhere:
  `runtime_proof: not-claimed`. `M208_S03_VERIFY_OK` stays
  `verify_marker: unreachable` while the verdict is `not-adopted`, because its only
  would-be emitter `scripts/m208_s03_t05_verify.sh` is deliberately absent, and the
  contract asserts that the marker is never emitted.
- A **checkpoint-contract PASS is not runtime proof**
  (`contract_pass_is_not_runtime_proof: true`), and the D499 GSD milestone lock is
  not an admission or C4 evidence (`lock_is_not_runtime_proof: true`). The same holds
  for any PASS of the M206/S05-S07 admitted scope, for an integrity PASS, for a
  battery PASS, for a milestone completion or for a subagent narrative: none of them
  may be re-labelled as the missing S03 admission, as runtime proof, or as the S03
  demo (`runtime_demo: not-proven`).
- Neighbouring admitted contours are neighbours only, as recorded in the
  `Neighbouring admitted contours` section above: the HC-13 capacity policy, the
  `ProvenanceAdmission` carrier, the force overlay and their suites prove their own
  admitted scopes and cannot be re-read as this slice's admission.
- Gate rule: every no-start statement in all three T02 notes is explicitly
  conditioned on `verdict=not-adopted`. A future granted admission must produce a
  fresh checkpoint with re-bound source hashes instead of inheriting this text; no
  sentence above may survive as a current claim once the verdict changes.

## Verification matrix overlay (not a proof anchor)

`.agents/skills/law-nexus-rust/references/verification-matrix.md` is a gitignored
local overlay (`.gitignore` rule `.agents/skills/`), not a tracked durable proof
anchor. It is therefore cited neither as a source above nor as evidence anywhere in
this record, and it is not hashed. No new M208 change-class row is added to it, and
its content cannot stand in for a tracked change-class row, for runtime proof, or
for an admission.

## Prohibited changes under this state

- Do not start operation-admission or commencement-evidence runtime work; do not
  create `crates/ln-temporal/src/operation_admission.rs` or
  `crates/ln-decode/src/change_commencement.rs`, and do not register
  `mod operation_admission` or `mod change_commencement`.
- Do not create the S03 proof surfaces
  (`crates/ln-temporal/tests/npa_operation_admission_contract.rs`,
  `crates/ln-temporal/tests/npa_operation_admission_hostile_contract.rs`,
  `crates/ln-decode/tests/npa_change_commencement_contract.rs`,
  `scripts/m208_s03_admission_commencement_battery.test.mjs`,
  `prd/migration/rust-evidence/m208-s03-admission-commencement-battery.json`,
  `crates/ln-temporal/tests/m208_s03_frozen_surface_guard.rs`,
  `scripts/m208_s03_t05_verify.sh`).
- Do not create an approval, waiver, or adoption artifact from this record.
- Do not change the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`, the M206 records,
  the M208/S01 or M208/S02 records, the operation registry, or any design-only
  force / pending-effects / requisites contract to manufacture adoption.
- Do not promote any gate, lifecycle, requirement or Review Case finding, and do
  not add a change-class row that would claim runtime proof from S03 surfaces.
- Do not mint `ChangeTarget`, `ChangeScope`, `MicroOperation`, `LegislativeEffect`,
  `NormRule`, `InForce`, `WorkId` or `force` under cover of this record.
- Do not invert or delete the M208/S01 or M208/S02 stops, or re-read either
  checkpoint as an S03 admission.
- Do not treat an integrity PASS, a battery PASS, a milestone lock, a milestone
  completion, a subagent narrative, or a PASS of this checkpoint contract as the
  missing admission, as runtime proof, or as C4 evidence.
- Do not read the existing M206/S05-S07 commencement or force surfaces, the HC-13
  capacity policy, or `ProvenanceAdmission` as the S03 operation-admission gate.

## Resume condition

M208/S03 runtime work may start only after a separate, explicit, source-bound owner
admission for the M208/S03 scope (the admission gate of a parsed operation —
accepted target + operand match + temporal evidence — and commencement evidence,
the admission leg of RC28-F13 and RC28-F17) is recorded through the applicable
acceptance path — an owner grant recorded in a tracked document, or an
authenticated subjective UAT naming the operation-admission vocabulary, the
commencement-evidence contour and its owning runtime surfaces. That admission must
be a new decision, must cite its own sources with hashes, and must state which of
the requested gates (G05, G11, G12, G13, G15) it selects.

Until then this checkpoint stands: `runtime_work` stays `not-started`, the runtime
demo stays `not-proven`, and the design-only material of S03 carries no runtime
claim. Once such an admission exists, this document is superseded: its verdict line
changes, the selected gate set may grow to include the requested gates, and the
Markdown is re-bound to the fresh source hashes.
