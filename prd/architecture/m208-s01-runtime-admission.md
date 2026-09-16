# M208/S01 runtime admission: quoted change operands and local change operations

**admission: not-adopted**
**recorded:** 2026-09-16
**milestone / slice:** M208-wrz6fg / S01
**classification:** source-bound runtime admission checkpoint (fail-closed)
**scope:** local quoted change operations of M208/S01 only — quoted operand spans
(old / new / location) and the five local source operations
Replace / NewWording / Insert / Remove / Repeal, realized as
`crates/ln-decode/src/change_operand.rs` and
`crates/ln-decode/src/change_operation.rs`.
**selected_d388_gates:** G01, G02, G14
**requested_not_selected_d388_gates:** G05, G11, G12, G13
**deferred_d388_gates:** G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13, G15, G16
**runtime_stop:** remains active for M208/S01; this record lifts runtime_stop for
no scope.
**runtime_work:** not-started
**admission_basis:** No source-bound owner admission covering RC28-F13
(amendment operands and the Change operation alphabet) for M208/S01 exists in
the tracked repository; every owning pin keeps `human_adoption: pending`, and the
only admitted runtime scope recorded for this area (RC28-F06..F12, M206/S05-S07)
does not include F13.
**owner_admission_ref:** none
**contract:** scripts/m208_s01_admission_contract.test.mjs
**prerequisite M206:** complete (M206-jnbhlz); its adoption-state records are
historical no-start provenance and are not inverted by this document.
**M205 pins:** not edited by this document.

## Purpose and boundary

This document is the mandatory start gate of M208/S01. The milestone criterion
`New vocabulary human-adopted before code` requires a recorded admission before
runtime code is written, and D457 / D458 / D459 forbid minting that adoption out
of YAML design data, out of a design pin, or out of an integrity PASS.

T01 therefore determined the adoption state of the M205 Change-family rows by
reading the live tracked sources listed below, and recorded the result. The
result is **not-adopted**: no re-readable, source-bound owner admission for the
M208/S01 scope was found. Per the slice plan, a not-adopted verdict is a blocker:
the S01 runtime demo stays not-proven and the runtime tasks must not start.

This record is a checkpoint, not a grant. It is not an approval, waiver,
requirement closure, Review Case disposition, legal conclusion, lifecycle
promotion, or runtime authorization.

## Sources checked

Each row is repository-relative and byte-bound: the recorded sha256 is compared
against the live file content by the executable contract. Any later change to a
cited source invalidates this record and requires a fresh checkpoint.

| Source | sha256 | What it records |
| --- | --- | --- |
| `prd/architecture/m205-s01-pullenti-matrix.yaml` | `559b6637139acdf81f8a09cd8683cf28e48f1dd4507e0b9aa6ac67905727a131` | The eight `PC-C-*` Change-family rows; each carries `human_adoption: pending`, `lifecycle: [proposed]`, and per-row requested gates (OWNER/KIND/LOCVALUE/no-auto-reinterpret request G12+G13; CHILD G11+G12; VALUE G05+G12; PARAM/value-kind G12). Only PC-C-OWNER, PC-C-KIND and PC-C-VALUE carry `unblocks: [S03, M208]`. |
| `prd/architecture/m205-s03-context-fsm.yaml` | `1d6fdf0ab295839e81aa301b8db89ada6d6be26d7b200f8604f60ccc0ac02d9d` | The Context FSM projection consumes the same `source_rows` (PC-C-OWNER, PC-C-KIND, PC-C-CHILD, PC-C-VALUE, PC-C-PARAM, PC-C-LOCVALUE, PC-C-value-kind, PC-C-no-auto-reinterpret) with `kind_source: PC-C-KIND`, and keeps `human_adoption: pending`. |
| `prd/architecture/m205-s04-docs-reconciliation.yaml` | `fd254f66fa899596989398a7210d460052e54ae3a687ec74f5ba306aca14de4f` | `human_adoption: pending`, `runtime_stop_active: true`, and the row `T-HUMAN-ADOPTION-PENDING` whose non-claims read "no first-cells or recorded adoption". Its non-claims also state it is "not a human adoption record". |
| `doc/adr/0028-typed-lexer-legal-marker-lexicon.md` | `e40a12ea5f32755425fa7b645c7cc96f37f726037fcf45e3de7332b0bc640d09` | Owning ADR (D380-D388). Its M205/S04 companion states that no `DecreeChange` type, G0 adoption, or identifying-cycle `Change` slot is adopted, and that no human adoption or finding disposition is claimed. |
| `prd/ARCHITECTURE.md` | `8293e68da5319ef2daf5127fcdf272fb0e61e68badfe1bf004f66dc433b4f8f3` | Active Direction Contract. Its M205/S04 reconciliation section states the pin "keeps `human_adoption: pending` and `runtime_stop` active" and that "human adoption and all findings remain pending". |
| `prd/architecture/m206-s05-runtime-admission.md` | `ed7bac704a2184ff3f052f0065af99a76b2366c4f64e9f2892c6ba749f6b5751` | The only tracked source-bound runtime admission in this area. It records M204/M205 completion with human adoption accepted (interaction d1630290, TSR sha256:021dafc7...) and lifts runtime_stop for M206/S05 only. Its admitted finding scope is RC28-F06..F12, whose owning surfaces are ln-decode `document_context.rs` / `local_grammar.rs` / `lawref.rs` and ln-temporal `document_context.rs` / `semantic_scope.rs`; RC28-F13 is not admitted. |
| `prd/architecture/m206-s07-runtime-admission.md` | `75f5a031296d2afe8b808a3e1257a9a579e908157198c9a0be7ee81b70a8c4ab` | Extends the S05 acceptance to the S07 remediation completion, scope RC28-F06..F12 only, and repeats that the D388 deferred gates are not selected and no Pullenti port is admitted. |
| `prd/architecture/m206-s01-adoption-state.md` | `1586c94c21e182f0e4f7cbf0cecb36eaac328473f0da85e9708a90f21fd6125e` | Precedent record: no separate source-bound owner admission was found for that scope, `human_adoption` stayed pending, `runtime_stop.active` stayed true, and the owner selected Reject (interaction 04fd05a2-...). It states that integrity or reconciliation PASS cannot substitute for an admission. |
| `prd/architecture/m206-s02-adoption-state.md` | `66555109130c7eac0ff463c99c55d9898b4946f3da261516a403bbd934722ff8` | Keeps `human_adoption: pending` and `runtime_stop_active: true`; forbids creating an approval, waiver, or adoption artifact. |
| `prd/architecture/m206-s03-adoption-state.md` | `9e0e4ef1a931f799058f954643e9599fd69230bcfaf25097d16d4981c2602efd` | Same no-start pattern; none of its scenarios is runtime PASS, admission, or adoption evidence. |
| `prd/architecture/m206-s04-adoption-state.md` | `d830d14c17268dc4005102ef4b683adad0b9775340a42c25a7e7ce7ca484db9d` | Same no-start pattern; forbids creating an approval, waiver, or adoption artifact or changing review records. |
| `prd/architecture/operation-registry.yaml` | `cee807b9b7cc68c1a23fa44a3d1fb1432349118e85e36dc7ddaffa36c049e8d6` | `lifecycle: [proposed]`, `authoritative: false`; the registry declares it mints no Rust types and is not a runtime component. It is the `law_nexus_surface` owner named by PC-C-KIND. |
| `prd/architecture/review-cases/rc28-remediation-program.md` | `8ae51137a5ead37a761cff59e87d5a8747a348ee9b21ea0855bd60ca6b82232f` | Assigns F13 to M205/S03 and M208/S01-S04, requires each changed policy to be actually adopted before work, and states that no runtime step may cross its required adoption gate. |

Additional live facts that are not file-bound and therefore cited as provenance
only, not as admission evidence:

- M207-b2i96m has no human pilot: its stores and evaluation report are absent and
  the rates are not-measured, so the milestone validation is needs-attention, not
  pass.
- D499 is a GSD milestone lock (`GSD_MILESTONE_LOCK=M208-wrz6fg`). It is a public
  API `deriveStateFromDb` process affordance, not an owner adoption of legal
  vocabulary, and this checkpoint does not treat it as one.

## Adoption state of the Change-family rows

All eight rows requested by T01 are still unadopted in the tracked corpus:

| Row | owning surface | `human_adoption` | requested gates | unblocks |
| --- | --- | --- | --- | --- |
| PC-C-OWNER | `prd/architecture/npa-document-context.yaml` | pending | G12, G13 | S03, M208 |
| PC-C-KIND | `prd/architecture/operation-registry.yaml` | pending | G12, G13 | S03, M208 |
| PC-C-CHILD | `prd/architecture/npa-document-context.yaml` | pending | G11, G12 | S03 |
| PC-C-VALUE | `prd/architecture/npa-document-context.yaml` | pending | G05, G12 | S03, M208 |
| PC-C-PARAM | `prd/architecture/npa-document-context.yaml` | pending | G12 | S03 |
| PC-C-LOCVALUE | `prd/architecture/npa-document-context.yaml` | pending | G12, G13 | S03 |
| PC-C-value-kind | `prd/architecture/npa-document-context.yaml` | pending | G12 | S03 |
| PC-C-no-auto-reinterpret | `prd/architecture/npa-document-context.yaml` | pending | G12, G13 | S03 |

The M205 milestone-level authenticated subjective UAT (criterion d8d3c60d) is
recorded in the GSD registry as an acceptance of the M205 design deliverable and
is cited by the tracked M206/S05 admission as the M204/M205 prerequisite. It is
**not** treated here as the M208/S01 admission, for three source-bound reasons:

1. It is a milestone-close acceptance of the M205 design scope, not a scope
   binding for M208/S01 runtime surfaces; D500 records that this reference does
   not remove the source-bound record requirement for M208/S01.
2. Its recorded admitted runtime scope (the only tracked, source-bound admission
   in this area, M206/S05-S07) is RC28-F06..F12 and excludes RC28-F13 — the
   amendment-operand finding this slice implements.
3. The owning tracked documents still assert the opposite: the M205 pins carry
   `human_adoption: pending`, ADR-0028 states that no identifying-cycle `Change`
   slot is adopted and no human adoption is claimed, and `prd/ARCHITECTURE.md`
   states that human adoption and all findings remain pending. Where a tracked
   owning source contradicts an inference, the checkpoint is fail-closed.

Deriving an admission from the matrix itself, from the FSM pin, from an integrity
or battery PASS, or from the D499 lock is explicitly refused; those are the named
fail-closed cases below.

## Selected, requested and deferred D388 gates

- `selected_d388_gates: G01, G02, G14` — this is the pre-existing baseline
  admitted before M208. A not-adopted checkpoint selects no additional gate.
- `requested_not_selected_d388_gates: G05, G11, G12, G13` — the gates requested by
  the Change-family rows themselves. They stay deferred-undefined; adoption, not
  the pin, is what would select them.
- `deferred_d388_gates: G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13,
  G15, G16` — the complement of the selected set. They remain individually
  deferred-undefined.

Selecting any gate outside the selected set is a contract failure
(`gate_outside_selected_baseline`).

## Owning surfaces

The surfaces this checkpoint governs, none of which may be created or modified
while the verdict is not-adopted:

- `crates/ln-decode/src/change_operand.rs` — quoted operand extraction (T02);
- `crates/ln-decode/src/change_operation.rs` — the five local operations and the
  `IncompleteBecause` contour (T03/T04);
- `crates/ln-decode/src/lib.rs` — module registration;
- `crates/ln-decode/tests/npa_change_operand_contract.rs`,
  `crates/ln-decode/tests/npa_change_operand_hostile_contract.rs`,
  `crates/ln-decode/tests/npa_change_operation_contract.rs`,
  `crates/ln-decode/tests/npa_change_operation_hostile_contract.rs`;
- `scripts/m208_s01_change_battery.test.mjs`,
  `scripts/m208_s01_t05_verify.sh`,
  `prd/migration/rust-evidence/m208-s01-change-battery.json`,
  `crates/ln-decode/tests/m208_frozen_surface_guard.rs`.

Read-only inputs consumed by the checkpoint, never written by it: the M205 pins,
the M206 admission records, ADR-0028, `prd/ARCHITECTURE.md`, and the M200/M201
frozen evidence artifacts.

## Non-claims

- This document is not a grant, not an approval, not a waiver, not requirement
  closure, not a Review Case disposition, and not legal acceptance.
- It does not edit the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`, the M206
  records, the operation registry, or any hashed NPA YAML.
- It does not promote any lifecycle: the pins stay `[proposed]` and
  `authoritative: false`.
- It does not admit Pullenti; D380 stands and no vendor code, dictionary,
  threshold or `DecreeChange*` type is ported.
- It does not mint a candidate type: `MicroOperation`, `LegislativeEffect`,
  `NormRule`, `Condition`, `Exception`, `InForce`, `WorkId` and `force` all stay
  deferred-undefined. Extraction never implies force.
- It does not claim that M206's runtime stop was inverted or lifted: the M206
  adoption-state records remain historical no-start provenance with
  `runtime_stop_active: true`.
- It does not claim the S01 demo. With a not-adopted verdict the demo stays
  not-proven.

## Fail-closed boundary

The executable contract `scripts/m208_s01_admission_contract.test.mjs` runs
offline (`node --test`) and refuses the following states:

| Failure case | Code |
| --- | --- |
| No `**admission: ...**` verdict line | `verdict_missing` |
| More than one verdict line (ambiguous) | `verdict_ambiguous` |
| Fewer than six byte-bound source rows | `sources_insufficient` |
| Cited source missing, absolute, or outside version control | `source_unresolved` / `source_not_tracked` |
| Recorded sha256 differs from live file content | `source_hash_mismatch` |
| Adoption minted from pins/YAML alone (`granted` with only `.yaml` sources) | `self_minted_adoption` |
| `granted` without an owner interaction reference | `owner_admission_ref_missing` |
| `granted` citing an integrity/battery PASS instead of an owner decision | `integrity_pass_as_admission` |
| `granted` citing D499 / `GSD_MILESTONE_LOCK` as the admission | `lock_as_admission` |
| A selected gate outside the admitted set | `gate_outside_selected_baseline` |
| Deferred set not equal to the complement of the selected set | `gate_deferred_mismatch` |
| `runtime_stop` lifted while the verdict is not-adopted | `runtime_stop_inverted` |
| No-start directive absent for a not-adopted verdict | `no_start_directive_missing` |
| Required section (`Owning surfaces`, `Non-claims`, `Fail-closed boundary`) absent | `section_missing` |
| Contract reference absent | `contract_reference_missing` |

Missing, conflicting, or unavailable evidence stays fail-closed. No policy is
chosen by inference.

## Marker semantics

- `M208_S01_ADMISSION_OK` — emitted by the contract when the checkpoint record is
  valid: an unambiguous verdict, byte-bound resolvable sources, a valid gate
  partition, and intact M206 runtime-stop invariants. It denotes a valid
  **checkpoint**, not a grant.
- `M208_S01_ADMISSION_NOT_GRANTED` — emitted together with the marker above when
  the verdict is not-adopted, so the marker cannot be read as a grant.
- `M208_S01_GATES_OK` — emitted when the selected / requested / deferred gate
  partition is valid.
- `M208_S01_VERIFY_OK` — emitted only by `scripts/m208_s01_t05_verify.sh`, i.e.
  only on full slice success; it is never emitted from this checkpoint.
- `M208_S01_T05_NO_START_OK` — emitted by the checkpoint contract when the T05
  no-start state holds: the proof battery, the frozen-surface guard and the verify
  runner are absent, the M200/M201 frozen evidence artifacts are unmodified, and no
  checkpoint-contract or D499 lock PASS is re-labelled as runtime proof. Like the
  markers above it denotes a checkpoint state, never a runtime or C4 result.

## T02 no-start note: quoted operand contour

Recorded by M208/S01/T02 on 2026-09-16 under the not-adopted verdict above. This
note adds provenance to the checkpoint; it does not relax it.

- Provenance: T01 attempt `f436a10e` settled failed/blocker-discovered, host
  recovery abort `532e9062`, decision D503. Resume of that recovery would loop
  the same HARD BLOCK, so the slice closes the task by the no-start pattern.
- The quoted-operand runtime contour stays **not-started**. T02 was executed as a
  design-only task: no `crates/ln-decode/src/change_operand.rs` was created, no
  operand candidate type (`ChangeOperand`, `ChangeOperandCandidate` or similar)
  was minted, and `crates/ln-decode/src/lib.rs` was not touched.
- Consequently no runtime surface in this slice state emits exact old / new /
  location byte spans for quoted operands; the S01 demo stays not-proven.
- `crates/ln-decode/src/lawref.rs` keeps its existing private `match_quoted_enum`
  helper for law-reference quoted enumerations. It is **not** reused, lifted,
  exported or generalised for change operands. Any future reuse must be argued
  explicitly in an admitted slice instead of being inherited by proximity.
- Missing-operand behaviour remains a design statement only: a missing operand
  would be `IncompleteBecause` without rewriting KIND. No proof of that contour is
  claimed while the admission is not-adopted.
- No frozen surface was touched: the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`,
  the M206 records and the M200/M201 frozen evidence artifacts are unmodified by
  T02, and no new runtime or test file was created.

The T02 evidence is the re-run of this checkpoint contract plus the absence
checks it performs over the four runtime operand surfaces
(`crates/ln-decode/src/change_operand.rs`,
`crates/ln-decode/src/change_operation.rs`,
`crates/ln-decode/tests/npa_change_operand_contract.rs`,
`crates/ln-decode/tests/npa_change_operand_hostile_contract.rs`); the contract
asserts both this note and those absences while the verdict is not-adopted.

## T03 no-start note: five local change operations

Recorded by M208/S01/T03 on 2026-09-16 under the not-adopted verdict above. This
note adds provenance to the checkpoint; it does not relax it.

- Provenance: the same T01 blocker-accepted lineage as T02 — T01 attempt
  `f436a10e` settled failed/blocker-discovered, host recovery abort `532e9062`,
  decision D503. Resume of that recovery would loop the same HARD BLOCK, so the
  slice closes this task by the no-start pattern rather than by implementation.
- The five local source change operations — `Replace` (заменить), `NewWording`
  (изложить в новой редакции), `Insert` (дополнить), `Remove` (исключить) and
  `Repeal` (признать утратившим силу) — remain **design-only names** of the S01
  source-operation alphabet, i.e. of the design surface that
  `prd/architecture/m205-s03-context-fsm.yaml` names for itself
  (`# M205/S03 design-only context FSM and source-operation alphabet pin`).
  They are not implemented names: the pin itself carries no runtime contour for
  them, and nothing in this slice mints one. No `ChangeOperationCandidate` was
  minted, no
  `crates/ln-decode/src/change_operation.rs` was created, no
  `crates/ln-decode/tests/npa_change_operation_contract.rs` was created, and
  `crates/ln-decode/src/lib.rs` was not touched.
- The five names are not `MicroOperation`, not `LegislativeEffect`, and they do
  not mint `WorkId`, `InForce`, `force` or `NormRule`. The owning M205 pin
  `prd/architecture/m205-s03-context-fsm.yaml` fixes
  `kind_not_runtime: [MicroOperation, LegislativeEffect, force, NormRule]`, and
  the Change-family matrix rows carry
  `non_claims: [not MicroOperation, not LegislativeEffect, not InForce, not NormRule]`.
  All of those names stay deferred-undefined; extraction never implies force.
- `Remove` is **not** `Expire` (nor `ExpireChanges`, nor `Suspend`): the same pin
  fixes `distinctions: [Remove != Expire, Expire != ExpireChanges, ExpireChanges != Suspend]`.
  A future admitted contour must keep deletion-of-wording distinct from
  expiry-of-force; this note records no runtime merge of the two.
- The extraction surface stays empty while the verdict is not-adopted, so the
  S01 demo (`Replace/new wording/insert/remove/repeal source candidates have
  exact old/new/location spans`) stays not-proven.
- No frozen surface was touched: the M205 pins, ADR-0028,
  `prd/ARCHITECTURE.md`, the M206 records and the M200/M201 frozen evidence
  artifacts are unmodified by T03, and no runtime or test file was created.

The T03 evidence is the re-run of this checkpoint contract plus the absence
checks it performs over the M208 runtime surfaces, including
`crates/ln-decode/src/change_operation.rs` and
`crates/ln-decode/tests/npa_change_operation_contract.rs`; the contract asserts
this note, the five design-only names and those absences while the verdict is
not-adopted.

## T04 no-start note: hostile IncompleteBecause contour

Recorded by M208/S01/T04 on 2026-09-16 under the not-adopted verdict above. This
note adds provenance to the checkpoint; it does not relax it.

- Provenance: the same T01 blocker-accepted lineage as T02 and T03 — T01 attempt
  `f436a10e` settled failed/blocker-discovered, host recovery abort `532e9062`,
  decision D503, and RC28-F13 is not admitted. Resume of that recovery would loop
  the same HARD BLOCK, so the slice closes this task by the no-start pattern
  rather than by implementation.
- The hostile KIND-rewrite contour stays **not-started**: no
  `crates/ln-decode/tests/npa_change_operation_hostile_contract.rs` was created,
  no hostile fixture was added, and no host-side generator, adapter or CLI hook
  was added. The absence of that suite is the expected state — a hostile contour
  may not precede the admission it would test against.
- The design statement it would prove is recorded here, not proven: a missing
  operand stays `IncompleteBecause` and never rewrites KIND. The owning design pin
  `prd/architecture/m205-s03-context-fsm.yaml` fixes that in two places — the
  semantic-process immutability invariant
  `missing_operand_is_IncompleteBecause_without_KIND_rewrite` and the alphabet
  field `missing_operands: IncompleteBecause` — and its construction guard `self`
  records the negative case `{ThisRef: absent, result: IncompleteBecause}`. The
  Change-family row `PC-C-no-auto-reinterpret` names the surface
  `IncompleteBecause diagnostic` while keeping `human_adoption: pending`, so the
  diagnostic is still a proposed design label, not a runtime type.
- Therefore `hostile_proof: deferred`: the proof is deferred until a source-bound
  owner admission of RC28-F13 (amendment operands and the Change operation
  alphabet) exists. `prd/architecture/review-cases/rc28-remediation-program.md`
  assigns F13 to M205/S03 and M208/S01-S04 and requires an adopted operation
  grammar together with the operand and admission evidence before any runtime step
  may run; the milestone-level M205 UAT acceptance cited above is not that
  adoption.
- Missing operands are **not** a false or empty result, and no diagnostic name is
  promoted by this note: `IncompleteBecause` is a coverage verdict value, not an
  entity key or a glossary first-cell, and it stays deferred-undefined alongside
  `MicroOperation`, `LegislativeEffect`, `NormRule`, `InForce`, `WorkId` and
  `force`. Extraction never implies force, and no KIND is rewritten, invented or
  substituted.
- No frozen surface was touched: the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`,
  the M206 records, the M200/M201 frozen evidence artifacts and the operation
  registry are unmodified by T04, and no runtime or test file was created.

The T04 evidence is the re-run of this checkpoint contract plus the absence
checks it performs over
`crates/ln-decode/tests/npa_change_operation_hostile_contract.rs` and the
remaining M208 runtime surfaces; the contract asserts this note, the KIND-rewrite
invariant and those absences while the verdict is not-adopted. The T01 fail-closed
negatives — self-minted adoption from pins alone (`self_minted_adoption`),
an integrity PASS (`integrity_pass_as_admission`) and the D499 lock
(`lock_as_admission`) — are re-run unchanged and still refuse a self-minted
admission.

## T05 no-start note: no battery, no frozen-surface guard, no runtime proof

Recorded by M208/S01/T05 on 2026-09-16 under the not-adopted verdict above. This
note adds provenance to the checkpoint; it does not relax it.

- Provenance: the same T01 blocker-accepted lineage as T02-T04 — T01 attempt
  `f436a10e` settled failed/blocker-discovered, host recovery abort `532e9062`,
  decision D503, and RC28-F13 is not admitted. Resume of that recovery would loop
  the same HARD BLOCK, so the slice closes this task by the no-start pattern
  rather than by implementation.
- The slice proof battery stays **not-started**: `battery_proof: deferred`. No
  `scripts/m208_s01_change_battery.test.mjs` was created, no
  `prd/migration/rust-evidence/m208-s01-change-battery.json` was written, and no
  `scripts/m208_s01_t05_verify.sh` runner exists. A battery would have to assert
  exact old / new / location byte spans emitted by a runtime surface that is
  itself not-started, so it cannot precede the admission it would measure.
- The frozen-surface guard stays **not-started**: `frozen_surface_proof: deferred`.
  No `crates/ln-decode/tests/m208_frozen_surface_guard.rs` was created. The
  M200/M201 frozen evidence artifacts in `prd/migration/rust-evidence/` were
  neither edited nor regenerated: all eight tracked artifacts are untouched, the
  worktree reports no change for them, and their last commits stay `b6c9d79` /
  `e6eaa19` / `1160844` from 2026-09-05/06, i.e. from before M208. The read-only
  frozen-surface check that this task can honestly run lives in the checkpoint
  contract (`M200_M201_FROZEN_ARTIFACTS`), not in a Rust test.
- No change-class row is added and none claims runtime proof: the tracked matrix
  `.agents/skills/law-nexus-rust/references/verification-matrix.md` was not edited
  by T05, and no M208 row asking for `cargo fmt --all --check` / targeted
  `cargo test` / `cargo check --workspace --offline` runtime evidence was added,
  because that runtime change does not exist. When an admission lands, the row
  must cite the real battery instead of this note.
- No runtime proof is claimed anywhere in this record: `runtime_proof: not-claimed`.
  The marker `M208_S01_VERIFY_OK` stays `verify_marker: unreachable` while the
  verdict is not-adopted, because the runner that alone would emit it is
  deliberately absent — its `Marker semantics` entry above names
  `scripts/m208_s01_t05_verify.sh` as the only emitter.
- A **checkpoint contract PASS is not runtime proof**:
  `contract_pass_is_not_runtime_proof: true`. A green
  `node --test scripts/m208_s01_admission_contract.test.mjs` proves only that the
  no-start state is intact; it is not the missing admission, not C4 evidence and
  not the S01 demo. The same holds for the D499 GSD milestone lock:
  `lock_is_not_runtime_proof: true`. Neither a lock nor a contract PASS may be
  cited as a runtime or C4 result.
- The T05 guard codes are `t05_note_missing`, `t05_provenance_missing`,
  `t05_battery_proof_not_deferred`, `t05_frozen_surface_proof_not_deferred`,
  `t05_runtime_proof_claimed`, `t05_marker_reachable_claim`,
  `t05_contract_pass_as_runtime_proof`, `t05_lock_as_runtime_proof`,
  `t05_surface_citation_missing` and `t05_runtime_surface_present`.
- No frozen surface was touched: the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`,
  the M206 records, the M200/M201 frozen evidence artifacts, the operation
  registry and the tracked verification matrix are unmodified by T05, and no
  runtime or test file was created.

The T05 evidence is the re-run of this checkpoint contract plus the absence
checks it performs over the four T05 surfaces
(`scripts/m208_s01_change_battery.test.mjs`,
`prd/migration/rust-evidence/m208-s01-change-battery.json`,
`crates/ln-decode/tests/m208_frozen_surface_guard.rs` and
`scripts/m208_s01_t05_verify.sh`); the contract asserts this note, the deferred
sentinel pair, the no-runtime-proof claims and those absences while the verdict is
not-adopted.

## Prohibited changes under this state

- Do not start T02, T03, T04 or T05 runtime work; `change_operand.rs` and
  `change_operation.rs` must not be created.
- Do not create the T05 proof surfaces
  (`scripts/m208_s01_change_battery.test.mjs`,
  `prd/migration/rust-evidence/m208-s01-change-battery.json`,
  `crates/ln-decode/tests/m208_frozen_surface_guard.rs`,
  `scripts/m208_s01_t05_verify.sh`) or add a change-class row that would claim
  runtime proof from them before the admission is granted.
- Do not create `crates/ln-decode/tests/npa_change_operation_hostile_contract.rs`
  to prove the missing-operand `IncompleteBecause` contour before RC28-F13 is
  admitted.
- Do not create an approval, waiver, or adoption artifact from this record.
- Do not change the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`, the M206 records,
  or the operation registry to manufacture adoption.
- Do not promote any gate, lifecycle, requirement or Review Case finding.
- Do not treat an integrity PASS, a battery PASS, a milestone lock, a milestone
  completion, a subagent narrative, or a PASS of this checkpoint contract as the
  missing admission, as runtime proof, or as C4 evidence.

## Resume condition

S01 runtime work may start only after a separate, explicit, source-bound owner
admission for the M208/S01 scope (quoted operand spans and the five local change
operations, RC28-F13) is recorded through the applicable acceptance path — an
owner grant recorded in a tracked document, or an authenticated subjective UAT
naming the Change-family vocabulary and its owning runtime surfaces. That
admission must be a new decision, must cite its own sources with hashes, and must
state which of the requested gates (G05, G11, G12, G13) it selects. Until then,
this checkpoint stands and the runtime demo stays not-proven.

Once such an admission exists, this document is superseded: its verdict line
changes, the selected gate set may grow to include the requested gates, and the
Markdown is re-bound to the fresh source hashes.
