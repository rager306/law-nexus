# M208/S04 runtime admission: bounded chain replay, oracle exam and known-as-of preservation

**admission: not-adopted**
**recorded:** 2026-09-16
**milestone / slice:** M208-wrz6fg / S04
**classification:** source-bound runtime admission checkpoint (fail-closed)
**scope:** bounded causal replay of new edition chains, scoped oracle agreement and
known-as-of preservation — the replay leg of RC28-F13 and the transitions /
edition-deltas leg of RC28-F17 (M208/S04), realized — if ever admitted — by
`crates/ln-temporal/src/bounded_chain_replay.rs`,
`crates/ln-temporal/src/oracle_exam.rs` and the surfaces listed under
`Owning surfaces` below.
**selected_d388_gates:** G01, G02, G14
**requested_not_selected_d388_gates:** (empty set)
**deferred_d388_gates:** G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13, G15, G16
**runtime_stop:** remains active for M208/S04; this record lifts runtime_stop for
no scope.
**runtime_work:** not-started
**runtime_demo:** not-proven
**admission_basis:** No source-bound owner admission covering the M208/S04 scope
(bounded causal replay of new edition chains, scoped oracle agreement,
known-as-of preservation) exists in the tracked repository. The M208/S01, M208/S02
and M208/S03 checkpoints all stand at `not-adopted`; every one of the five
`prd/architecture/m205-s01-pullenti-matrix.yaml` rows whose `unblocks` contains
`S04` belongs to the `leave` family with `d388_gates: []` and
`human_adoption: not-required`, so the requested gate union of those rows is empty
by construction of the matrix; the design pin
`prd/architecture/m205-s04-docs-reconciliation.yaml` has already consumed those
leave rows (`pc_x_leave`, `T-PC-X-LEAVE`) and its non-claims state verbatim
`not P9 ledger emission, M206 implementation, or M208 replay`; and the only
tracked granted scope in this area (RC28-F06..F12, M206/S05) includes neither the
replay leg of RC28-F13 nor RC28-F17.
**owner_admission_ref:** none
**contract:** scripts/m208_s04_admission_contract.test.mjs
**prerequisite M208/S01:** closed as a source-bound design-only no-start; its record
`prd/architecture/m208-s01-runtime-admission.md` stands at `not-adopted` and is
consumed here as the basis, not inverted by this document.
**prerequisite M208/S02:** closed as a source-bound design-only no-start; its record
`prd/architecture/m208-s02-nested-target-admission.md` stands at `not-adopted` and
is consumed here as the basis, not inverted by this document.
**prerequisite M208/S03:** closed as a source-bound design-only no-start; its record
`prd/architecture/m208-s03-admission-commencement.md` stands at `not-adopted` and
is consumed here as the basis, not inverted by this document.
**M205 pins / ADR-0028 / prd/ARCHITECTURE.md:** not edited by this document.

## Purpose and boundary

This document is the mandatory start gate of M208/S04. The milestone criterion
`New vocabulary human-adopted before code` requires a recorded admission before
runtime code is written, and D457 / D458 / D459 forbid minting that adoption out of
YAML design data, out of a design pin, out of an integrity PASS, or out of a GSD
milestone lock. D503 (M208/S01), D504 (M208/S02) and D507 (M208/S03) record that
the three preceding slices closed as no-starts for exactly this reason, and D510
records that S04 is planned and closed the same way rather than as a runtime replay.
The S01, S02 and S03 checkpoints are scope-bound to their own slices: none covers
bounded causal replay, oracle exam / discrepancy, or known-as-of preservation, so
S04 must open with its own source-bound checkpoint.

This record is a checkpoint, not a grant. It is not an approval, waiver,
requirement closure, Review Case disposition, legal conclusion, lifecycle
promotion, or runtime authorization. It records that no re-readable, source-bound
owner admission for the M208/S04 scope was found, and it therefore holds the
runtime stop: bounded-replay, oracle-exam and known-as-of runtime work does not
start and the S04 demo stays **not-proven** (`runtime_demo: not-proven`).

**no_start_directive:** while the verdict is `not-adopted`, no runtime work for
M208/S04 may start, no S04 runtime surface may be created, and no design statement
in this document may be read as proof.

## Sources checked

Each row is repository-relative and byte-bound: the recorded sha256 is compared
against the live file content by the executable contract. Any later change to a
cited source invalidates this record and requires a fresh checkpoint. Every path
below is tracked (`git ls-files --error-unmatch`); no ignored (`.agents/**`,
`.gsd/**`, `.lex/**`), absolute, or traversal path is cited anywhere in this
record.

| Source | sha256 | What it records |
| --- | --- | --- |
| `prd/architecture/m208-s01-runtime-admission.md` | `aad5f2800dfa7eaec61e79e364e80902af12b83617a22089bd576b3136e9b60e` | The M208/S01 basis. `**admission: not-adopted**`, `runtime_stop: remains active for M208/S01`, `runtime_work: not-started`, `owner_admission_ref: none`, scope restricted to the S01 quoted operands and local change operations. Scope-bound, so it cannot serve as the S04 admission. |
| `prd/architecture/m208-s02-nested-target-admission.md` | `9ea63ebae3cf3956a38da27f51f6daddfb5f778ae1002fe813d77e13522b964e` | The M208/S02 basis. `**admission: not-adopted**`, `runtime_stop: remains active for M208/S02`, `owner_admission_ref: none`, requested-not-selected gates `G05, G11, G12, G13`. Scope-bound to nested targets and amending-act scope binding, so it cannot serve as the S04 admission. |
| `prd/architecture/m208-s03-admission-commencement.md` | `677c3b7cbff3ecb3431fde75e6842bfb67ed4a9326a2f039cefc5d50a62982a8` | The M208/S03 basis. `**admission: not-adopted**`, `runtime_stop: remains active for M208/S03`, `owner_admission_ref: none`, requested-not-selected gates `G05, G11, G12, G13, G15`. Scope-bound to the parsed-operation admission gate and commencement evidence, so it cannot serve as the S04 admission. |
| `prd/architecture/m205-s01-pullenti-matrix.yaml` | `559b6637139acdf81f8a09cd8683cf28e48f1dd4507e0b9aa6ac67905727a131` | The prior-art matrix. Exactly five rows (`PC-X-SemanticService`, `PC-X-MorphEngine`, `PC-X-global-analyzer-init`, `PC-X-Instrument-tree`, `PC-X-occurrence-span`) carry `family: leave`, `take_or_leave: leave`, `unblocks: [S04]`, `d388_gates: []`, `human_adoption: not-required`, `rc28: [F14]` and `lifecycle: [proposed]`. The file declares `authoritative: false` and states that the inventory is not a license grant, runtime parity, or gold corpus. |
| `prd/architecture/m205-s03-context-fsm.yaml` | `1d6fdf0ab295839e81aa301b8db89ada6d6be26d7b200f8604f60ccc0ac02d9d` | The design-only context FSM and source-operation alphabet pin. Header keeps `human_adoption: pending` and `runtime_stop_active: true`; `context_fsm_contract.d388_control.selected_baseline: [G01, G02, G14]`; `must_not_select: [G08, G09, G10, G11, G12, G13, G15]`. Its non-claims state that proposed labels remain pending, that labels cannot mint `WorkId`, `ComponentId`, `CTV`, `InForce`, `NormRule`, or `LegislativeEffect`, and that `F13 replay is M208`. |
| `prd/architecture/m205-s04-docs-reconciliation.yaml` | `fd254f66fa899596989398a7210d460052e54ae3a687ec74f5ba306aca14de4f` | `human_adoption: pending`, `runtime_stop_active: true`, `hashed_yaml_mutation: forbidden`; `pc_x_leave.ids` is exactly the five `PC-X-*` leave rows and the `T-PC-X-LEAVE` item scopes them as `leave rows and S04 unblocks` with `pending_adoption: true`; `non_claims` includes the verbatim `not P9 ledger emission, M206 implementation, or M208 replay`; `d388_control.deferred_undefined` is the complement of `selected_baseline: [G01, G02, G14]` over G01..G16. |
| `prd/architecture/m206-s05-runtime-admission.md` | `ed7bac704a2184ff3f052f0065af99a76b2366c4f64e9f2892c6ba749f6b5751` | The only tracked source-bound `admission: granted` record in this area. Its scope is explicitly `M206/S05 runtime implementation of RC28-F06..F12`, with `runtime_stop: lifted for M206/S05 scope only` and G05/G11/G12/G13 left deferred and unselected. It admits neither the replay leg of RC28-F13 nor RC28-F17. |
| `prd/architecture/review-cases/rc28-remediation-program.md` | `8ae51137a5ead37a761cff59e87d5a8747a348ee9b21ea0855bd60ca6b82232f` | Assigns `F13: M205/S03, M208/S01-S04` with required proof `adopted operation grammar, old/new operands, nested targets, admission and bounded causal replay`, and `F17: M208/S03-S04, M209/S03-S04` with required proof `operation x provision x commencement x transitions x edition deltas, scoped coverage, frozen M201 untouched`. Gives M208 the start prerequisite `M205 operation adoption and M206` and states that no runtime step may cross its required adoption gate. |
| `doc/adr/0028-typed-lexer-legal-marker-lexicon.md` | `e40a12ea5f32755425fa7b645c7cc96f37f726037fcf45e3de7332b0bc640d09` | Owning ADR (D380-D388). Records that Pullenti's alphabet is an orientation only, that no `DecreeChange` type, G0 adoption, or identifying-cycle `Change` slot is adopted, and that no human adoption or finding disposition is claimed. Its `## M205/S04 reconciliation companion [proposed]` section is the already-executed home of the matrix's `S04 owns ADR` wording; it does not amend the ADR or promote any lifecycle. |
| `doc/adr/0017-component-temporal-versioning.md` | `fd8740985b54d8a45bfc30c617ed1de3eaa63f72eae078394bdaa1bb8c761414` | The control rule `fold(events, t) ≈ snapshot(oracle@t)` and `drift(t) = fold(events, t) Δ snapshot(oracle@t)` with `Non-zero drift is healed by a new event or explicit waiver — never by writing the oracle tree back as canon`; the third hash leg binds the oracle exam; `known_as_of` is a required parameter of every projection and never a view. |
| `doc/adr/0009-five-clock-temporal-model.md` | `26782b641572ea00772f17292ebdfa03260a686b736f19884dd19c31bdc0318a` | Five-clock policy: `known_as_of` binds the `system_observation` role of the snapshot fold (`legal_as_of` and `known_as_of` are independent facts, neither substituting for the other). |
| `prd/temporal-legal-model.md` | `a8f7184d38c9a48605c1c91f16fa64a33644a949ff83a8066efb97bd3f3cebd6` | INV-05: `Assertion correction never rewrites the known_as_of past` (ADR-0017 G0(a), ledger). |
| `prd/architecture/model-crystal.md` | `d3da08d89d94f70d20b44e336628d6ef35ed4d5d8b52271fa85deac8d05e4b95` | Principle 7 `oracle exam scoped discrepancy` with the qualifier `discrepancy = parse gap, not photo erasure`, and the named view `VIEW-Discrepancy` (difference between the reconstructed expression and the edition oracle); `known_as_of is a required parameter of every projection, never a view`. |
| `prd/architecture/fz44-tracked-edition-chain.yaml` | `5f7a7a17cb898f693bcb17f729286fb07d3d720c0726d9ced44caef10ab0a2e8` | The frozen bounded packet `484-FZ -> cc:44-fz:statya-93`: `lifecycle: "[bounded]"`, `authoritative: false`, caller-supplied admission packet for ONE tracked edition chain, `NOT parsed by product code` (D216/D252: no YAML codegen, no runtime authority). |
| `prd/architecture/npa-promotion-gates.json` | `123b94a9c5d5f0fa49402943f9884aa8686e0d9e95342875d72ac5ce7fc361e7` | Records the open requirement debt `R070` `remaining: "118 consolidated editions remain uncovered; commencement and transitional slot-filled evidence is not proven."` and the `non_claims` that promotions do not close `R035`/`R070` and that fixture or diagnostic evidence is not promotion proof. |

No other file is cited as an admission source. Additional live facts that are not
file-bound (for example the GSD milestone lock, journal state, or prior task
summaries) are cited nowhere in this record as admission evidence.

## Adoption state of the rows that unblock S04

Exactly five matrix rows carry `unblocks` containing `S04`. All five are still
unadopted in the tracked corpus, and all five belong to the `leave` family:

| Row | owning surface | `pullenti_behavior` | `human_adoption` | `d388_gates` | `rc28` | `unblocks` |
| --- | --- | --- | --- | --- | --- | --- |
| `PC-X-SemanticService` | `prd/architecture/npa-parsing-program.yaml` | semantic service is not used by NER in real projects | not-required | `[]` | `[F14]` | S04 |
| `PC-X-MorphEngine` | `prd/architecture/npa-parsing-program.yaml` | vendor dictionary and license boundary | not-required | `[]` | `[F14]` | S04 |
| `PC-X-global-analyzer-init` | `prd/architecture/npa-parsing-program.yaml` | global analyzer initialization and vendor dependency | not-required | `[]` | `[F14]` | S04 |
| `PC-X-Instrument-tree` | `prd/architecture/npa-identifying-cycle.yaml` | instrument hierarchy is not LawRef identity | not-required | `[]` | `[F14]` | S04 |
| `PC-X-occurrence-span` | `prd/architecture/npa-identifying-cycle.yaml` | no cross-occurrence span joining | not-required | `[]` | `[F14]` | S04 |

Every row keeps `lifecycle: [proposed]` and `take_or_leave: leave`, so no row is
selectable and no row is selected by this record. The rows are decisions **not to
take** vendor behaviour; they are not admissions of vocabulary, and the matrix
itself states `authoritative: false` and is not a license grant.

**The empty requested set is a property of the matrix.** `d388_gates: []` on all
five rows means the mechanical union of the gates requested by the rows whose
`unblocks` contains `S04` is empty. That is not an oversight in this record and it
is not a second, quieter selection: a `leave` decision requests no gate because it
takes no vocabulary. D511 records the same reading.

**`not-required` is not an admission.** `human_adoption: not-required` means "there
is no new vocabulary to adopt, because the vendor surface is not taken". It is
neither weaker nor stronger than `pending`: `pending` states that an adoption is
still owed for a surface that would be taken; `not-required` states that no
adoption is owed because nothing is taken. Neither value grants anything, and
neither can be read as an admission of bounded replay, oracle discrepancy, or
known-as-of preservation. The M205/S03 pin's immutability invariants state the same
rule for the process side: `not_required_is_process_only_and_never_proves_evidence`
and `not-required_is_process_side_only: true` in the M205/S04 pin.

**Provenance uncertainty, recorded not resolved.** The five rows' `S04` may address
M205/S04 (the docs-reconciliation slice) rather than M208/S04: the design pin
`prd/architecture/m205-s04-docs-reconciliation.yaml` already consumes them
(`pc_x_leave.ids`, item `T-PC-X-LEAVE` with scope `leave rows and S04 unblocks`),
and that pin's non-claims explicitly exclude `M208 replay`. D512 records this as
unclaimed scope. The ambiguity is **not** resolved by guesswork: no reading of the
five rows is claimed as M208/S04 scope, and at any reading their gate union stays
empty. Guessing either way is the fail-closed case
`pc_x_provenance_resolved_by_guess`; deriving an admission from the rows is
`leave_row_as_admission`.

The M205 milestone-level authenticated subjective UAT is recorded in the GSD
registry as an acceptance of the M205 design deliverable and is cited by the tracked
M206/S05 admission as the M204/M205 prerequisite. It is **not** treated here as the
M208/S04 admission, for the same source-bound reasons recorded by the S01, S02 and
S03 checkpoints: it is a milestone-close acceptance of the M205 design scope, not a
scope binding naming bounded chain replay, oracle discrepancy and known-as-of
preservation; the only tracked admitted runtime scope in this area is RC28-F06..F12;
and the owning tracked documents assert the opposite — the M205 pins carry
`human_adoption: pending`, ADR-0028 states that no identifying-cycle `Change` slot
is adopted and no human adoption is claimed, and
`prd/architecture/npa-promotion-gates.json` states that commencement and
transitional slot-filled evidence is not proven. Where a tracked owning source
contradicts an inference, the checkpoint is fail-closed. D457/D458/D459 refuse the
remaining shortcuts by name.

## Selected, requested and deferred D388 gates

- `selected_d388_gates: G01, G02, G14` — the pre-existing baseline already wired
  before M208. It is also the `selected_baseline` of the M205/S03 and M205/S04 pins
  and the gate set of the M206/S05 admitted scope. A not-adopted checkpoint selects
  no additional gate.
- `requested_not_selected_d388_gates: (empty set)` — the union of the D388 gates
  requested by the rows whose `unblocks` contains `S04` is empty, because all five
  such rows are `leave` rows with `d388_gates: []`. The empty set is a property of
  the matrix, not a decision of this record, and it is recorded as empty rather
  than omitted so that the partition stays auditable. A future granted checkpoint
  inherits nothing from it.
- `deferred_d388_gates: G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13,
  G15, G16` — the complement of the selected set over G01..G16. Each of the 13
  gates remains individually deferred-undefined. The M205/S03 pin independently
  publishes `must_not_select: [G08, G09, G10, G11, G12, G13, G15]`, so those gates
  are explicitly barred from selection in the design pin as well.

Selecting any gate outside the selected set is a contract failure
(`gate_outside_selected_baseline`). A gate-set partition whose deferred member is
not the complement of the selected set is a contract failure
(`gate_deferred_mismatch`). A requested set that is not exactly empty is a contract
failure (`requested_gate_set_mismatch`).

**Derived observation (not an S04 request).** The gates the S04 legs would need if
they were ever admitted are `G05` (quoted-operand / value shape, requested by the
S01 line via `PC-C-VALUE`), `G11` (nesting, requested by the S02 line via
`PC-C-CHILD`), `G12` and `G13` (target / operand / kind binding, requested by the
`PC-C-*` family), and `G15` (source-authority policy, requested by the `PC-D-*`
rows). All five were recorded by S01, S02 and S03 as **requested-not-selected** and
remain unselected; the M205/S03 pin additionally lists them in `must_not_select`.
This is an observation about the missing legs of the M208 chain, recorded so the
gap is visible — it is **not** a request made by S04, it does not widen the
requested set, and a record whose derived-leg observation differs is a contract
failure (`derived_leg_gates_mismatch`). The S04 legs are named here only as absent
dependencies inherited from the three no-start checkpoints.

## Owning surfaces

The runtime surfaces this checkpoint governs, none of which may be created or
modified while the verdict is `not-adopted`:

- `crates/ln-temporal/src/bounded_chain_replay.rs` — bounded causal replay over a
  caller-supplied admitted edition-chain packet (declared, not created);
- `crates/ln-temporal/src/oracle_exam.rs` — scoped oracle exam and drift
  classification (declared, not created);
- `crates/ln-temporal/tests/npa_bounded_chain_replay_contract.rs` — replay contract
  suite (declared, not created);
- `crates/ln-temporal/tests/npa_oracle_discrepancy_contract.rs` — oracle-discrepancy
  contract suite (declared, not created);
- `crates/ln-temporal/tests/npa_known_as_of_preservation_contract.rs` —
  known-as-of preservation contract suite (declared, not created);
- `scripts/m208_s04_bounded_replay_battery.test.mjs` — proof battery (declared, not
  created);
- `prd/migration/rust-evidence/m208-s04-bounded-replay-battery.json` — durable
  battery evidence (declared, not created);
- `crates/ln-temporal/tests/m208_s04_frozen_surface_guard.rs` — frozen-surface
  guard (declared, not created);
- `scripts/m208_s04_t05_verify.sh` — the only would-be emitter of
  `M208_S04_VERIFY_OK` (declared, not created);
- `crates/ln-temporal/src/lib.rs` — the `mod bounded_chain_replay` and
  `mod oracle_exam` registrations are absent and must stay absent.

The declared names are the declared scope of absence, not a decision about the
final API: a future admitted runtime slice may choose different names and must
supersede this record with fresh hashes.

The existing `EditionOracle`, `ThreeCanonRecord`, `ThreeCanonEventLog`,
`fold_three_canon_at` and `HypothesizedFromOracleDiff` in
`crates/ln-temporal/src/domain.rs` are a **neighbouring admitted contour**, not an
S04 surface: their admission belongs to M190/M201 and earlier, and neither their
existence nor any PASS of them may be read as the S04 oracle-exam surface or as the
S04 admission. Claiming otherwise is the fail-closed case
`neighbouring_contour_as_evidence`.

Inherited S01, S02 and S03 runtime surfaces stay absent as well:
`crates/ln-decode/src/change_operand.rs`, `crates/ln-decode/src/change_operation.rs`
(`s01_surface_present`), `crates/ln-decode/src/change_target.rs`
(`s02_surface_present`), and `crates/ln-temporal/src/operation_admission.rs`,
`crates/ln-decode/src/change_commencement.rs` and the other declared S03 surfaces
(`s03_surface_present`). Their absence is not re-scoped by this document.

Read-only inputs consumed by the checkpoint, never written by it: the M205 pins,
ADR-0028, `prd/ARCHITECTURE.md`, the M206 admission records, the M208/S01, M208/S02
and M208/S03 records, the operation registry, and the M200/M201 frozen evidence
artifacts.

## Neighbouring admitted contours

Existing replay, provenance and oracle surfaces belong to their own admitted scopes
(M190/M201/M206 and earlier) and are neighbours, not S04 deliveries:

- `crates/ln-temporal/src/domain.rs` — `EditionOracle`, `ThreeCanonRecord`,
  `ThreeCanonEventLog`, `fold_three_canon_at`, `HypothesizedFromOracleDiff`. The
  precedence `Legislative > HypothesizedFromOracleDiff > EditorialHint` exists in
  that admitted scope and does **not** upgrade a hypothesized commencement;
  extraction never implies force. `CHECKOUT_NON_CLAIMS` states verbatim that the
  present fold is a `Point per-target fold of the recorded three-canon log; not
  bitemporal checkout (no legal_as_of / known_as_of / VIEW)` — i.e. the S04
  known-as-of surface does not exist there.
- Suites `crates/ln-temporal/tests/fz44_tracked_provenance.rs`,
  `fz44_edition_delta.rs`, `fz44_edition_walk.rs`, `fz44_checkout_projection.rs` —
  each proves only its own admitted scope over the frozen bounded packet.
- Design pins `prd/architecture/fz44-tracked-edition-chain.yaml` and
  `prd/architecture/m203-s07-staged-edition-manifest.yaml` — `[bounded]`,
  `authoritative: false`, not parsed by product code; and
  `prd/migration/rust-evidence/m201-s03-tracked-chain.json` — frozen M201 evidence
  (RC28-F17).
- `prd/annotation/m207-s03-eval-protocol.md` and
  `prd/annotation/m207-s04-c4-protocol.md` — M207 delivers protocols, not accepted
  annotations; the human pilot was not run, rates are `not-measured`, and C4 is
  `operational_acceptance=non-pass`.

No PASS of any neighbouring surface may be quoted as S04 evidence, as the F13/F17
admission, as an accepted annotation, or as C4 evidence (contract code
`neighbouring_contour_as_evidence`; `m207_pilot_as_annotation_evidence`). This
record is also not the S04 known-as-of surface: claiming that the existing
three-canon fold already provides bitemporal checkout is the fail-closed case
`known_as_of_checkout_claimed`. Conversely, this record does not re-scope, edit, or
re-interpret those contours.

## Non-claims

- This document is not a grant, not an approval, not a waiver, not requirement
  closure, not a Review Case disposition, and not legal acceptance.
- It does not edit the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`, the M206
  records, the M208/S01, M208/S02 and M208/S03 records, the operation registry, or
  any hashed NPA YAML.
- It does not mint a new edition chain beyond the frozen `484-FZ ->
  cc:44-fz:statya-93` packet, and it does not modify the frozen M201 evidence
  artifact `prd/migration/rust-evidence/m201-s03-tracked-chain.json`
  (`new_chain_minted_beyond_frozen_packet`, `frozen_m201_artifact_modified`).
- It does not promote any lifecycle: the pins stay `[proposed]` /
  `[bounded]` and `authoritative: false`.
- It does not admit Pullenti (D380); no vendor code, dictionary, threshold or
  `DecreeChange*` type is ported.
- It does not mint `ChangeTarget`, `ChangeScope`, `MicroOperation`,
  `LegislativeEffect`, `NormRule`, `InForce`, `WorkId` or `force`, and it does not
  mint an "oracle discrepancy" glossary first-cell in
  `prd/temporal-legal-model.md` §3 (`oracle_discrepancy_glossary_cell_minted`).
- It does not claim the S04 demo (`New chains replay deterministically with scoped
  oracle agreement and known-as-of preservation`). With a `not-adopted` verdict the
  demo stays **not-proven** (`runtime_demo: not-proven`).
- It does not claim that the M206 runtime stop was inverted or lifted, nor that the
  M208/S01, M208/S02 or M208/S03 stops were lifted: all remain active for their own
  scopes.
- It does not treat the D499 GSD milestone lock (`GSD_MILESTONE_LOCK=M208-wrz6fg`),
  an integrity PASS, a battery PASS, a milestone completion, or a PASS of its own
  contract as an admission, as runtime proof, or as C4 evidence
  (`lock_as_admission`, `lock_as_runtime_proof`, `integrity_pass_as_admission`,
  `contract_pass_as_runtime_proof`, `runtime_proof_claimed`).
- It does not reopen ADR-0028. The matrix's `S04 owns ADR` wording addresses
  M205/S04 and is already executed by the `## M205/S04 reconciliation companion
  [proposed]` section of `doc/adr/0028-typed-lexer-legal-marker-lexicon.md`; M208/S04
  does not amend that ADR (`adr0028_reopened`, `s04_owns_adr_claim`).
- It does not read the five `PC-X-*` leave rows as an admission and does not
  resolve their M205/S04-versus-M208/S04 provenance by guesswork
  (`leave_row_as_admission`, `pc_x_provenance_resolved_by_guess`).
- It does not create the S04 hostile contour, battery, frozen-surface guard or
  verify runner: they are deferred, not simulated.
- It does not claim that a gitignored local verification-matrix overlay is a
  tracked durable proof anchor.

## Fail-closed boundary

The executable contract `scripts/m208_s04_admission_contract.test.mjs` runs offline
(`node --test`; subprocesses limited to `git ls-files` and `git status --porcelain`)
and refuses the following states. Its code set is synchronized with the T03 task
plan; the contract's own suite asserts each code below.

| Failure case | Code |
| --- | --- |
| No `**admission: ...**` verdict line | `verdict_missing` |
| More than one verdict line (ambiguous) | `verdict_ambiguous` |
| Fewer than twelve byte-bound source rows | `sources_insufficient` |
| Cited source missing, absolute, or otherwise unresolvable | `source_unresolved` |
| Cited source outside version control | `source_not_tracked` |
| Recorded sha256 differs from live file content | `source_hash_mismatch` |
| An ignored path (`.agents/**`, `.gsd/**`, `.lex/**`) offered as a source | `ignored_path_as_source` |
| Adoption minted from pins/YAML alone (`granted` with only `.yaml` sources) | `self_minted_adoption` |
| `granted` without an owner interaction reference | `owner_admission_ref_missing` |
| `granted` citing an integrity/battery PASS instead of an owner decision | `integrity_pass_as_admission` |
| `granted` citing D499 / `GSD_MILESTONE_LOCK` as the admission | `lock_as_admission` |
| The S01 basis does not read `not-adopted` | `s01_basis_not_adopted` |
| The S02 basis does not read `not-adopted` | `s02_basis_not_adopted` |
| The S03 basis does not read `not-adopted` | `s03_basis_not_adopted` |
| A selected gate outside the admitted set | `gate_outside_selected_baseline` |
| Deferred set not equal to the complement of the selected set | `gate_deferred_mismatch` |
| Requested set not exactly the empty set | `requested_gate_set_mismatch` |
| Derived-leg observation not exactly G05/G11/G12/G13/G15 | `derived_leg_gates_mismatch` |
| `runtime_stop` lifted while the verdict is not-adopted | `runtime_stop_inverted` |
| No-start directive absent for a not-adopted verdict | `no_start_directive_missing` |
| Required section (`Sources checked`, `Owning surfaces`, `Non-claims`, `Fail-closed boundary`, `Marker semantics`, `Resume condition`, `Prohibited changes`, `Neighbouring admitted contours`) absent | `section_missing` |
| Contract reference absent | `contract_reference_missing` |
| Any declared S04 runtime surface exists (one code per surface) | `s04_surface_present` |
| An inherited S01 runtime surface exists | `s01_surface_present` |
| An inherited S02 runtime surface exists | `s02_surface_present` |
| An inherited S03 runtime surface exists | `s03_surface_present` |
| `mod bounded_chain_replay` or `mod oracle_exam` registered in `crates/ln-temporal/src/lib.rs` | `lib_rs_registration_present` |
| A `leave` row of the matrix read as an admission | `leave_row_as_admission` |
| The M205/S04 versus M208/S04 provenance resolved by guesswork | `pc_x_provenance_resolved_by_guess` |
| ADR-0028 reopened by M208/S04 | `adr0028_reopened` |
| The `S04 owns ADR` wording claimed for M208/S04 | `s04_owns_adr_claim` |
| A new edition chain minted beyond the frozen packet | `new_chain_minted_beyond_frozen_packet` |
| The frozen M201 evidence artifact modified | `frozen_m201_artifact_modified` |
| An "oracle discrepancy" glossary first-cell minted | `oracle_discrepancy_glossary_cell_minted` |
| Bitemporal checkout claimed from the existing three-canon fold | `known_as_of_checkout_claimed` |
| An M207 protocol re-labelled as an accepted annotation | `m207_pilot_as_annotation_evidence` |
| A PASS of a neighbouring admitted contour re-labelled as S04 evidence | `neighbouring_contour_as_evidence` |
| Runtime proof claimed while the verdict is not-adopted | `runtime_proof_claimed` |
| `M208_S04_VERIFY_OK` claimed reachable | `verify_marker_reachable_claim` |
| A checkpoint-contract PASS re-labelled as runtime proof | `contract_pass_as_runtime_proof` |
| The D499 lock re-labelled as runtime proof | `lock_as_runtime_proof` |
| The inherited S01 contract is absent | `s01_contract_missing` |
| The inherited S02 contract is absent | `s02_contract_missing` |
| The inherited S03 contract is absent | `s03_contract_missing` |
| The T02 no-start notes are absent | `t02_note_missing` |

Missing, conflicting, or unavailable evidence stays fail-closed. No policy is
chosen by inference, no default admission exists, and a contract PASS denotes only
that the no-start state is intact — never a runtime result.

## Marker semantics

- `M208_S04_ADMISSION_OK` — emitted by the contract when the checkpoint record is
  valid: an unambiguous verdict, at least twelve byte-bound resolvable sources, a
  valid gate partition (including the empty requested set), and intact
  runtime-stop invariants. It denotes a valid **checkpoint**, not a grant.
- `M208_S04_ADMISSION_NOT_GRANTED` — emitted together with the marker above when
  the verdict is `not-adopted`, so the marker cannot be read as a grant.
- `M208_S04_GATES_OK` — emitted when the selected / requested / deferred gate
  partition is valid and the derived-leg observation is exactly
  G05/G11/G12/G13/G15.
- `M208_S04_ADMISSION_NO_START_OK` — emitted when the no-start state holds: no
  declared S04 runtime surface exists, no inherited S01 / S02 / S03 runtime surface
  exists, `mod bounded_chain_replay` and `mod oracle_exam` are unregistered, and no
  checkpoint-contract or D499 lock PASS is re-labelled as runtime proof. The
  contract prints `admission_verdict=not-adopted` and `runtime_surfaces_present=0`.
- `M208_S04_VERIFY_OK` — `verify_marker: unreachable` by construction while the
  verdict is `not-adopted`: its only would-be emitter `scripts/m208_s04_t05_verify.sh`
  is deliberately absent, and the contract asserts that it never emits this marker.

## Verification matrix overlay (not a proof anchor)

`.agents/skills/law-nexus-rust/references/verification-matrix.md` is a gitignored
local overlay (`.gitignore` rule `.agents/skills/`), not a tracked durable proof
anchor. It is therefore cited neither as a source above nor as evidence anywhere in
this record, and it is not hashed. No new M208 change-class row is added to it, and
its content cannot stand in for a tracked change-class row, for runtime proof, or
for an admission.

## Prohibited changes under this state

- Do not start bounded-replay, oracle-exam or known-as-of runtime work; do not
  create `crates/ln-temporal/src/bounded_chain_replay.rs` or
  `crates/ln-temporal/src/oracle_exam.rs`, and do not register
  `mod bounded_chain_replay` or `mod oracle_exam`.
- Do not create the S04 proof surfaces
  (`crates/ln-temporal/tests/npa_bounded_chain_replay_contract.rs`,
  `crates/ln-temporal/tests/npa_oracle_discrepancy_contract.rs`,
  `crates/ln-temporal/tests/npa_known_as_of_preservation_contract.rs`,
  `scripts/m208_s04_bounded_replay_battery.test.mjs`,
  `prd/migration/rust-evidence/m208-s04-bounded-replay-battery.json`,
  `crates/ln-temporal/tests/m208_s04_frozen_surface_guard.rs`,
  `scripts/m208_s04_t05_verify.sh`).
- Do not create an approval, waiver, or adoption artifact from this record.
- Do not change the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`, the M206 records,
  the M208/S01, M208/S02 or M208/S03 records, the operation registry, or any hashed
  NPA YAML to manufacture adoption.
- Do not mint a new edition chain beyond the frozen `484-FZ ->
  cc:44-fz:statya-93` packet, and do not touch
  `prd/migration/rust-evidence/m201-s03-tracked-chain.json` or the other frozen
  M200/M201 evidence artifacts.
- Do not mint a glossary first-cell for "oracle discrepancy" in
  `prd/temporal-legal-model.md` §3.
- Do not promote any gate, lifecycle, requirement or Review Case finding, and do
  not add a change-class row that would claim runtime proof from S04 surfaces.
- Do not mint `ChangeTarget`, `ChangeScope`, `MicroOperation`, `LegislativeEffect`,
  `NormRule`, `InForce`, `WorkId` or `force` under cover of this record.
- Do not invert or delete the M208/S01, M208/S02 or M208/S03 stops, or re-read any
  of those checkpoints as the S04 admission.
- Do not read the five `PC-X-*` leave rows as an admission, and do not resolve
  their M205/S04-versus-M208/S04 provenance by guesswork.
- Do not reopen ADR-0028 or claim the matrix's `S04 owns ADR` wording for M208/S04.
- Do not treat an integrity PASS, a battery PASS, a milestone lock, a milestone
  completion, an M207 protocol, a subagent narrative, or a PASS of this checkpoint
  contract as the missing admission, as runtime proof, or as C4 evidence.
- Do not read the existing `EditionOracle` / `fold_three_canon_at` /
  `HypothesizedFromOracleDiff` contour as the S04 oracle-exam surface or as
  bitemporal checkout.

## Resume condition

M208/S04 runtime work may start only after a separate, explicit, source-bound owner
admission for the M208/S04 scope (bounded causal replay of new edition chains,
scoped oracle agreement, and known-as-of preservation — the replay leg of RC28-F13
and the transitions / edition-deltas leg of RC28-F17) is recorded through the
applicable acceptance path — an owner grant recorded in a tracked document, or an
authenticated subjective UAT naming bounded chain replay and oracle discrepancy
together with its owning runtime surfaces. That admission must be a new decision,
must cite its own sources with hashes, and must state which of the expected gates
(G05, G11, G12, G13, G15) it selects, including its own pinned canon bytes and
sha256 for any new chain it admits.

Until then this checkpoint stands: `runtime_work` stays `not-started`, the runtime
demo stays `not-proven`, and the design-only material of S04 carries no runtime
claim. Once such an admission exists, this document is superseded: its verdict line
changes, the requested set may become non-empty, and the Markdown is re-bound to the
fresh source hashes.
