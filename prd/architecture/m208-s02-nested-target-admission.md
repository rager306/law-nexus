# M208/S02 runtime admission: nested amendment targets and amending-act scope binding

**admission: not-adopted**
**recorded:** 2026-09-16
**milestone / slice:** M208-wrz6fg / S02
**classification:** source-bound runtime admission checkpoint (fail-closed)
**scope:** nested targets of the amending act and the scope binding of an amending
act without leakage across siblings or quotes (RC28-F13; M205/S03 and M208/S01-S04
in the Review 28 remediation program), realized — if ever admitted — by
`crates/ln-decode/src/change_target.rs` and the surfaces listed under
`Owning surfaces` below.
**selected_d388_gates:** G01, G02, G14
**requested_not_selected_d388_gates:** G05, G11, G12, G13
**deferred_d388_gates:** G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G13, G15, G16
**runtime_stop:** remains active for M208/S02; this record lifts runtime_stop for
no scope.
**runtime_work:** not-started
**admission_basis:** No source-bound owner admission covering RC28-F13 (nested
amendment targets and their scope binding) for M208/S02 exists in the tracked
repository; the M208/S01 checkpoint stands at `not-adopted`; every owning
Change-family pin keeps `human_adoption: pending`. The only admitted runtime scope
recorded in this area (RC28-F06..F12, M206/S05-S07) does not include F13.
**owner_admission_ref:** none
**contract:** scripts/m208_s02_admission_contract.test.mjs
**prerequisite M208/S01:** closed as a source-bound design-only no-start; its
record `prd/architecture/m208-s01-runtime-admission.md` stands at `not-adopted`
and is consumed here as the basis, not inverted by this document.
**M205 pins:** not edited by this document.

## Purpose and boundary

This document is the mandatory start gate of M208/S02. The milestone criterion
`New vocabulary human-adopted before code` requires a recorded admission before
runtime code is written, and D457 / D458 / D459 forbid minting that adoption out of
YAML design data, out of a design pin, or out of an integrity PASS. D503 records
that M208/S01 closed as a no-start for exactly this reason, and the S01 checkpoint
is scope-bound to M208/S01: it does not cover nested targets or amending-act scope
binding, so S02 must open with its own source-bound checkpoint.

This record is a checkpoint, not a grant. It is not an approval, waiver,
requirement closure, Review Case disposition, legal conclusion, lifecycle
promotion, or runtime authorization. It records that no re-readable, source-bound
owner admission for the M208/S02 scope was found, and it therefore holds the
runtime stop: nested-target and scope-binding runtime work does not start and the
S02 demo stays **not-proven** (`runtime_demo: not-proven`).

**no_start_directive:** while the verdict is `not-adopted`, no runtime work for
M208/S02 may start, no S02 runtime surface may be created, and no design
statement in this document may be read as proof.

## Sources checked

Each row is repository-relative and byte-bound: the recorded sha256 is compared
against the live file content by the executable contract. Any later change to a
cited source invalidates this record and requires a fresh checkpoint.

| Source | sha256 | What it records |
| --- | --- | --- |
| `prd/architecture/m205-s01-pullenti-matrix.yaml` | `559b6637139acdf81f8a09cd8683cf28e48f1dd4507e0b9aa6ac67905727a131` | The Change-family rows. `PC-C-OWNER` carries `pullenti_behavior: nested target decree or part`, owning surface `prd/architecture/npa-document-context.yaml`, `d388_gates: [G12, G13]`, `human_adoption: pending`, `unblocks: [S03, M208]`. `PC-C-CHILD` carries `pullenti_behavior: nested change remains nested`, `d388_gates: [G11, G12]`, `human_adoption: pending`, `unblocks: [S03]`. `PC-C-KIND` carries `d388_gates: [G12, G13]`, `human_adoption: pending`, `unblocks: [S03, M208]`. All eight Change-family rows keep `lifecycle: [proposed]`; the file states `authoritative: false` and `non_claims: prior-art inventory only; not a license grant, runtime parity, or gold corpus`. |
| `prd/architecture/m205-s03-context-fsm.yaml` | `1d6fdf0ab295839e81aa301b8db89ada6d6be26d7b200f8604f60ccc0ac02d9d` | The design-only context FSM and source-operation alphabet pin. `amendment_alphabet.operand_roles` fixes `CHILD: keep-nested`; the `alias` construction guard requires `[declare, use, shadow_or_conflict_status, scope_container_id, boundary_check]` with positive case `{scope_container_id: same, boundary: contained}` and negative case `{scope_container_id: different, result: ContextConflict}`; `must_not_select: [G08, G09, G10, G11, G12, G13, G15]`; `selected_baseline: [G01, G02, G14]`; the file header keeps `runtime_stop_active: true`. |
| `prd/architecture/m205-s04-docs-reconciliation.yaml` | `fd254f66fa899596989398a7210d460052e54ae3a687ec74f5ba306aca14de4f` | `human_adoption: pending`, `runtime_stop_active: true`, and the row `T-HUMAN-ADOPTION-PENDING` whose non-claims read `no first-cells or recorded adoption`. The pin states it is not a human adoption record. |
| `prd/architecture/npa-document-context.yaml` | `7e54fcab83da17174d6f85dbbe7705d6c21ce627c7cd750851e7f97aa68e492c` | The owning design surface named by `PC-C-OWNER` / `PC-C-CHILD`. It declares `lifecycle: "[proposed]"`, `authoritative: false`, and `non_claims: not a Work identity or OfficialIdentityClaim; not an authorization to copy nearest text as context`. It defines the `scoped_alias` query (`resolve «далее — ...» only inside its declared structural scope`), `structural_scope` as a context-request field and memo key, the diagnostic `scoped_alias_ambiguous`, and the hostile-contract seed `alias declaration outside structural scope must not bind`. `fsm_contract.invariant` states that a terminal context state never mutates a source block, frame, or literal mention. |
| `doc/adr/0028-typed-lexer-legal-marker-lexicon.md` | `e40a12ea5f32755425fa7b645c7cc96f37f726037fcf45e3de7332b0bc640d09` | Owning ADR (D380-D388). Its M205/S04 companion states that Pullenti's alphabet is an orientation only, so no `DecreeChange` type, G0 adoption, or identifying-cycle `Change` slot is adopted, that the PC-X rows are leave rows, and that no human adoption or finding disposition is claimed. |
| `prd/architecture/m208-s01-runtime-admission.md` | `aad5f2800dfa7eaec61e79e364e80902af12b83617a22089bd576b3136e9b60e` | The M208/S01 basis. `**admission: not-adopted**` with `runtime_stop: remains active for M208/S01`, `runtime_work: not-started`, `owner_admission_ref: none`, and `scope` restricted to the M208/S01 quoted operands and local change operations. It is scope-bound, so it cannot serve as the S02 admission. |
| `prd/architecture/m206-s05-runtime-admission.md` | `ed7bac704a2184ff3f052f0065af99a76b2366c4f64e9f2892c6ba749f6b5751` | The only tracked source-bound `admission: granted` record in this area. Its scope is `M206/S05 runtime implementation of RC28-F06..F12`; RC28-F13 is not admitted. It records `runtime_stop: lifted for M206/S05 scope only` and leaves G11/G12/G13 deferred and unselected. |
| `prd/architecture/review-cases/rc28-remediation-program.md` | `8ae51137a5ead37a761cff59e87d5a8747a348ee9b21ea0855bd60ca6b82232f` | Assigns `F13: M205/S03, M208/S01-S04` with required proof `adopted operation grammar, old/new operands, nested targets, admission and bounded causal replay`; gives M208 the start prerequisite `M205 operation adoption and M206`; states that no runtime step may cross its required adoption gate; and states that the 13 D388 gates remain individually gated and that no aggregate count, packet completion, or milestone completion adopts them implicitly. |

No other file is cited as an admission source. Additional live facts that are not
file-bound are cited below as provenance only, never as admission evidence.

## Adoption state of the Change-family rows

The rows that own the M208/S02 scope are still unadopted in the tracked corpus:

| Row | owning surface | `human_adoption` | requested gates | unblocks |
| --- | --- | --- | --- | --- |
| PC-C-OWNER | `prd/architecture/npa-document-context.yaml` | pending | G12, G13 | S03, M208 |
| PC-C-CHILD | `prd/architecture/npa-document-context.yaml` | pending | G11, G12 | S03 |
| PC-C-KIND | `prd/architecture/operation-registry.yaml` | pending | G12, G13 | S03, M208 |

`PC-C-KIND` is listed because the nested-target contour must not silently rewrite
KIND; its owning surface `prd/architecture/operation-registry.yaml` keeps
`lifecycle: [proposed]`, `authoritative: false`, and declares that it mints no Rust
types and is not a runtime component.

The M205 milestone-level authenticated subjective UAT (criterion d8d3c60d) is
recorded in the GSD registry as an acceptance of the M205 design deliverable and is
cited by the tracked M206/S05 admission as the M204/M205 prerequisite. It is
**not** treated here as the M208/S02 admission, for the same source-bound reasons
recorded by the S01 checkpoint: it is a milestone-close acceptance of the M205
design scope, not a scope binding for M208/S02 runtime surfaces; the only tracked
admitted runtime scope in this area is RC28-F06..F12; and the owning tracked
documents assert the opposite — the M205 pins carry `human_adoption: pending`,
ADR-0028 states that no identifying-cycle `Change` slot is adopted and no human
adoption is claimed, and `prd/ARCHITECTURE.md` states that human adoption and all
findings remain pending. Where a tracked owning source contradicts an inference,
the checkpoint is fail-closed.

Deriving an admission from the matrix itself, from the context-FSM pin, from the
NPA document-context pin, from an integrity or battery PASS, or from the D499
milestone lock is explicitly refused; those are the named fail-closed cases below.

## Selected, requested and deferred D388 gates

- `selected_d388_gates: G01, G02, G14` — the pre-existing baseline already wired
  before M208 (it is also the `selected_baseline` of the M205/S03 pin and the gate
  set of the M206/S05 admitted scope). A not-adopted checkpoint selects no
  additional gate.
- `requested_not_selected_d388_gates: G05, G11, G12, G13` — the Change-family gates
  that are requested by their owning rows and stay deferred-undefined, because
  adoption, not the pin, is what would select them. Provenance per gate:
  `G12`, `G13` are requested by the S02 target-role row `PC-C-OWNER`; `G11`, `G12`
  by the S02 nesting-depth row `PC-C-CHILD`; `G05` is requested by the operand row
  `PC-C-VALUE`, whose runtime scope belongs to M208/S01 and which is *not* claimed
  by the S02 rows — it is listed only so the requested set stays the Change-family
  requested set recorded by the S01 checkpoint, and it remains unselected here.
  The M205/S03 pin independently publishes `must_not_select: [G08, G09, G10, G11,
  G12, G13, G15]`, so G11/G12/G13 are explicitly barred from selection in the
  design pin as well.
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

- `crates/ln-decode/src/change_target.rs` — nested change-target candidate
  extraction (declared, not created);
- `crates/ln-decode/tests/npa_change_target_contract.rs` — contract suite
  (declared, not created);
- `crates/ln-decode/tests/npa_change_target_hostile_contract.rs` — hostile
  sibling/quote leakage suite (declared, not created);
- `crates/ln-decode/src/lib.rs` — the `mod change_target` registration is absent
  and must stay absent;
- `scripts/m208_s02_nested_target_battery.test.mjs` — proof battery (declared, not
  created);
- `prd/migration/rust-evidence/m208-s02-nested-target-battery.json` — durable
  battery evidence (declared, not created);
- `crates/ln-decode/tests/m208_s02_frozen_surface_guard.rs` — frozen-surface guard
  (declared, not created);
- `scripts/m208_s02_t04_verify.sh` — the only would-be emitter of
  `M208_S02_VERIFY_OK` (declared, not created).

The declared names are the declared scope of absence, not a decision about the
final API: a future admitted runtime slice may choose different names and must
supersede this record with fresh hashes.

Inherited S01 runtime surfaces stay absent as well: `crates/ln-decode/src/change_operand.rs`
and `crates/ln-decode/src/change_operation.rs` (contract code `s01_surface_present`).
Their absence is not re-scoped by this document.

Read-only inputs consumed by the checkpoint, never written by it: the M205 pins,
ADR-0028, `prd/ARCHITECTURE.md`, the M208/S01 record, the M206 admission records,
the operation registry, and the M200/M201 frozen evidence artifacts.

## Non-claims

- This document is not a grant, not an approval, not a waiver, not requirement
  closure, not a Review Case disposition, and not legal acceptance.
- It does not edit the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`, the M206
  records, the M208/S01 record, the operation registry, or any hashed NPA YAML.
- It does not promote any lifecycle: the pins stay `[proposed]` and
  `authoritative: false`, and the operation registry stays a non-runtime
  declaration.
- It does not admit Pullenti (D380); no vendor code, dictionary, threshold or
  `DecreeChange*` type is ported.
- It does not mint a candidate type: `ChangeTarget`, `ChangeScope`,
  `MicroOperation`, `LegislativeEffect`, `NormRule`, `InForce`, `WorkId` and
  `force` all stay deferred-undefined. Extraction never implies force.
- It does not claim the S02 demo. With a `not-adopted` verdict the demo
  (`В статье→в части→заменить binds targets without leakage across siblings/quotes`)
  stays **not-proven** (`runtime_demo: not-proven`).
- It does not claim that the M206 runtime stop was inverted or lifted, nor that
  the M208/S01 stop was lifted: both remain active for their own scopes.
- It does not treat the D499 GSD milestone lock (`GSD_MILESTONE_LOCK=M208-wrz6fg`)
  as an admission. The lock is a process affordance, not an owner adoption of
  legal vocabulary.
- It does not treat a PASS of its own contract — or of any integrity, battery or
  milestone-completion check — as runtime proof or as C4 evidence.

## Fail-closed boundary

The executable contract `scripts/m208_s02_admission_contract.test.mjs` runs
offline (`node --test`; subprocesses limited to `git ls-files` and
`git status --porcelain`) and refuses the following states. Its code set is
synchronized with the T03 task plan; the contract's own suite asserts each code
below.

| Failure case | Code |
| --- | --- |
| No `**admission: ...**` verdict line | `verdict_missing` |
| More than one verdict line (ambiguous) | `verdict_ambiguous` |
| Fewer than eight byte-bound source rows | `sources_insufficient` |
| Cited source missing, absolute, or outside version control | `source_unresolved` / `source_not_tracked` |
| Recorded sha256 differs from live file content | `source_hash_mismatch` |
| An ignored path (`.agents/**`, `.gsd/**`) offered as a source | `ignored_path_as_source` |
| Adoption minted from pins/YAML alone (`granted` with only `.yaml` sources) | `self_minted_adoption` |
| `granted` without an owner interaction reference | `owner_admission_ref_missing` |
| `granted` citing an integrity/battery PASS instead of an owner decision | `integrity_pass_as_admission` |
| `granted` citing D499 / `GSD_MILESTONE_LOCK` as the admission | `lock_as_admission` |
| The S01 basis does not read `not-adopted` | `s01_basis_not_adopted` |
| A selected gate outside the admitted set | `gate_outside_selected_baseline` |
| Deferred set not equal to the complement of the selected set | `gate_deferred_mismatch` |
| `runtime_stop` lifted while the verdict is not-adopted | `runtime_stop_inverted` |
| No-start directive absent for a not-adopted verdict | `no_start_directive_missing` |
| Required section (`Sources checked`, `Owning surfaces`, `Non-claims`, `Fail-closed boundary`, `Marker semantics`, `Resume condition`) absent | `section_missing` |
| Contract reference absent | `contract_reference_missing` |
| Any declared S02 runtime surface exists (one code per surface) | `s02_surface_present` |
| An inherited S01 runtime surface exists | `s01_surface_present` |
| `mod change_target` registered in `crates/ln-decode/src/lib.rs` | `lib_rs_registration_present` |
| Runtime proof claimed while the verdict is not-adopted | `runtime_proof_claimed` |
| `M208_S02_VERIFY_OK` claimed reachable | `verify_marker_reachable_claim` |
| A checkpoint-contract PASS re-labelled as runtime proof | `contract_pass_as_runtime_proof` |
| The D499 lock re-labelled as runtime proof | `lock_as_runtime_proof` |
| The inherited S01 contract is absent | `s01_contract_missing` |
| The T02 no-start notes are absent | `t02_note_missing` |

Missing, conflicting, or unavailable evidence stays fail-closed. No policy is
chosen by inference, and a contract PASS denotes only that the no-start state is
intact — never a runtime result.

## Marker semantics

- `M208_S02_ADMISSION_OK` — emitted by the contract when the checkpoint record is
  valid: an unambiguous verdict, at least eight byte-bound resolvable sources, a
  valid gate partition, and intact runtime-stop invariants. It denotes a valid
  **checkpoint**, not a grant.
- `M208_S02_ADMISSION_NOT_GRANTED` — emitted together with the marker above when
  the verdict is `not-adopted`, so the marker cannot be read as a grant.
- `M208_S02_GATES_OK` — emitted when the selected / requested / deferred gate
  partition is valid.
- `M208_S02_NESTED_NO_START_OK` — emitted when the nested-target no-start state
  holds: no declared S02 runtime surface exists, no inherited S01 runtime surface
  exists, `mod change_target` is unregistered, and no checkpoint-contract or D499
  lock PASS is re-labelled as runtime proof.
- `M208_S02_VERIFY_OK` — `verify_marker: unreachable` by construction while the
  verdict is `not-adopted`: its only would-be emitter
  `scripts/m208_s02_t04_verify.sh` is deliberately absent, and the contract
  asserts that it never emits this marker.

## T02 no-start note: nested change target and nesting depth

Recorded by M208/S02/T02 on 2026-09-16 under the `not-adopted` verdict above
(`verdict=not-adopted`). This note adds provenance to the checkpoint; it does not
relax it, and no statement in it is a proof.

- Provenance: the S01 no-start lineage is consumed here as the S02 admission
  basis — T01 attempt `f436a10e` settled failed/blocker-discovered, host recovery
  abort `532e9062`, decision D503 — while the S02 slice shape itself is D504
  (plan S02 directly as a design-only no-start instead of replaying the S01
  recovery cycle). Every owning Change-family row still carries
  `human_adoption: pending`, RC28-F13 is **not** admitted, and the only tracked
  admitted runtime scope in this area (RC28-F06..F12, M206/S05) does not include
  F13. This note therefore records no runtime work: `runtime_work: not-started`.
- The chain «В статье → в части → заменить» is the **target role** of the amending
  act, not a flat top-level reference. Its owning matrix row is `PC-C-OWNER`
  (`vendor_anchor: Pullenti/Ner/Decree/DecreeChangeReferent.cs:OWNER`,
  `pullenti_behavior: nested target decree or part`, `law_nexus_surface:
  amendment-owner candidate`, `owner_crate_or_yaml:
  prd/architecture/npa-document-context.yaml`, `d388_gates: [G12, G13]`,
  `unblocks: [S03, M208]`), and its nesting depth is a **separate** row
  `PC-C-CHILD` (`vendor_anchor: Pullenti/Ner/Decree/DecreeChangeReferent.cs:CHILD`,
  `pullenti_behavior: nested change remains nested`, `d388_gates: [G11, G12]`,
  `unblocks: [S03]`). Both rows keep `lifecycle: [proposed]` and
  `human_adoption: pending` in `prd/architecture/m205-s01-pullenti-matrix.yaml`.
- The nesting obligation is therefore recorded as a design-only statement, not as
  implemented behaviour: nesting is **preserved** — a nested target is not
  flattened, not collapsed into its parent and not merged into one span. The pin
  `prd/architecture/m205-s03-context-fsm.yaml` fixes that in
  `amendment_alphabet.operand_roles` as `CHILD: keep-nested` (`keep-nested` is a
  declared design value, not a runtime flag), while the `leave` row
  `PC-X-occurrence-span` in the matrix (`pullenti_behavior: no cross-occurrence
  span joining`, `take_or_leave: leave`, `law_nexus_surface: none`) forbids
  joining spans across occurrences: a nested target may not glue the spans of
  different occurrences together, and no cross-occurrence span is produced. That
  row is a leave row and stays a leave row — it is not promotion, not a runtime
  contract, and not an authorization to mint an occurrence-span type.
- Nothing is minted by this note: `ChangeTarget`, `ChangeScope`, `MicroOperation`,
  `LegislativeEffect`, `NormRule`, `InForce`, `WorkId` and `force` all stay
  deferred-undefined; no `crates/ln-decode/src/change_target.rs` is created,
  `mod change_target` is not registered in `crates/ln-decode/src/lib.rs`, and no
  candidate type, observation or diagnostic is added to the operation registry.
  Extraction never implies force, and no KIND is rewritten, invented or
  substituted.
- No frozen surface was touched: the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`,
  the M206 records, the M208/S01 record, the operation registry and the M200/M201
  frozen evidence artifacts are unmodified by T02, and no runtime or test file
  was created.

The T02 evidence for this note is the note-presence state asserted by
`scripts/m208_s02_admission_contract.test.mjs` (contract code `t02_note_missing`)
together with the absence checks it performs over the declared S02 runtime
surfaces; the contract asserts this note while the verdict is `not-adopted`. A
PASS of that contract is **not** runtime proof and not C4 evidence.

## T02 no-start note: amending-act scope binding and sibling / quote anti-leakage

Recorded by M208/S02/T02 on 2026-09-16 under the `not-adopted` verdict above
(`verdict=not-adopted`). This note adds provenance to the checkpoint; it does not
relax it, and no statement in it is a proof.

- Provenance: the same S01 no-start lineage as the note above — T01 attempt
  `f436a10e` settled failed/blocker-discovered, host recovery abort `532e9062`,
  decision D503, with the S02 slice shape recorded by D504. Every owning
  Change-family row still carries `human_adoption: pending`, RC28-F13 is **not**
  admitted, and the M206/S05 admitted scope (RC28-F06..F12) excludes it. No scope
  binder is implemented here: `runtime_work: not-started`.
- Design anchors for the binding contour, cited as design pins and never as
  runtime evidence. `prd/architecture/m205-s03-context-fsm.yaml` fixes the
  alias-guard evidence set
  `required_evidence: [declare, use, shadow_or_conflict_status, scope_container_id, boundary_check]`
  with the positive case `{scope_container_id: same, boundary: contained}` and the
  negative case `{scope_container_id: different, result: ContextConflict}`.
  `prd/architecture/npa-document-context.yaml` fixes `scoped_alias`
  (`purpose: resolve «далее — ...» only inside its declared structural scope`),
  `structural_scope` as a context-request field and memo key, the diagnostic
  `scoped_alias_ambiguous`, the hostile seed `alias declaration outside structural
  scope must not bind`, and the contract invariant `terminal context state never
  mutates a source block, frame, or literal mention`.
- Three anti-leakage statements are recorded as design-only obligations, not as
  proof that they hold:
  1. **sibling leakage** — a target declared in a different scope container must
     not bind here; a `scope_container_id` that differs is not resolved by
     proximity but closed as `ContextConflict`, exactly as the pin's negative
     alias-guard case states. No "nearest sibling" fallback is admissible.
  2. **quote leakage** — a mention of a target inside a quoted operand (the S01
     operand scope: ёлочки-кавычки, German-style quotes and ASCII `"`) must not
     become a nested target and must not be promoted into a change-target span.
     The same pin carries the immutability anchors `source_mentions_are_immutable`,
     `no_inherited_text_rewrites_source_span` and
     `context_results_are_derived_not_authoritative`, so a context result is
     derived, never authoritative over the quoted source span.
  3. **missing or ambiguous boundary** — an absent or ambiguous structural
     boundary must not produce a "nearest" scope. It closes fail-closed as
     `ContextIncomplete` (missing evidence) or `ContextConflict` (incompatible
     evidence) and never rewrites KIND; ambiguity inside the scope-binding contour
     surfaces as `ContextConflict` / `scoped_alias_ambiguous`, not as a silent
     binding.
- A neighbouring admitted contour must not be read as S02 delivery:
  `crates/ln-decode/src/document_context.rs` and its hostile suite exist under
  the admitted M206/S05 scope (RC28-F06 sibling/parent closure, RC28-F07
  continuation eligibility). They do not bind nested change targets, they are not
  within this slice's declared scope, and none of their PASSes may be cited as
  S02 evidence, as F13 admission or as C4 evidence.
- Nothing is minted by this note: `ChangeTarget`, `ChangeScope`, `MicroOperation`,
  `LegislativeEffect`, `NormRule`, `InForce`, `WorkId` and `force` stay
  deferred-undefined, and no `crates/ln-decode/src/change_target.rs`,
  `crates/ln-decode/tests/npa_change_target_contract.rs` or
  `crates/ln-decode/tests/npa_change_target_hostile_contract.rs` is created.
- No frozen surface was touched: the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`,
  the M206 records, the M208/S01 record, the operation registry and the M200/M201
  frozen evidence artifacts are unmodified by T02, and no runtime or test file was
  created.

## T02 no-start note: no hostile contour, no battery, no runtime proof

Recorded by M208/S02/T02 on 2026-09-16 under the `not-adopted` verdict above
(`verdict=not-adopted`). This note adds provenance to the checkpoint; it does not
relax it.

- Provenance: the same S01 no-start lineage as the two notes above — T01 attempt
  `f436a10e` settled failed/blocker-discovered, host recovery abort `532e9062`,
  decision D503, S02 slice shape D504; every owning pin keeps
  `human_adoption: pending`, and RC28-F13 is not admitted; `runtime_work: not-started`.
- The hostile contour stays not-started: `hostile_proof: deferred`. No
  `crates/ln-decode/tests/npa_change_target_hostile_contract.rs` is created, no
  sibling/quote leakage fixture is added, and no host-side generator, adapter or
  CLI hook is added. The absence of that suite is the expected state — a hostile
  contour may not precede the admission it would verify against, so its proof is
  deferred until a source-bound owner admission of RC28-F13 exists.
- The proof battery and the frozen-surface guard stay not-started:
  `battery_proof: deferred` and `frozen_surface_proof: deferred`. No
  `scripts/m208_s02_nested_target_battery.test.mjs`, no
  `prd/migration/rust-evidence/m208-s02-nested-target-battery.json` and no
  `crates/ln-decode/tests/m208_s02_frozen_surface_guard.rs` is created. A battery
  would have to measure byte spans emitted by a runtime surface that is itself
  not-started, so it cannot precede the admission it would measure.
- No runtime proof is claimed anywhere in this record, here or elsewhere:
  `runtime_proof: not-claimed`. `M208_S02_VERIFY_OK` stays
  `verify_marker: unreachable` while the verdict is `not-adopted`, because its
  only would-be emitter `scripts/m208_s02_t04_verify.sh` is deliberately absent,
  and the contract asserts that the marker is never emitted.
- A **checkpoint-contract PASS is not runtime proof**
  (`contract_pass_is_not_runtime_proof: true`), and the D499 GSD milestone lock is
  not an admission or C4 evidence (`lock_is_not_runtime_proof: true`). The same
  holds for any inherited PASS of the M206/S05 admitted scope, for an integrity
  PASS, for a battery PASS, for a milestone completion or for a subagent
  narrative: none of them may be re-labelled as the missing S02 admission, as
  runtime proof, or as the S02 demo (`runtime_demo: not-proven`).
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

- Do not start nested-target or scope-binding runtime work; do not create
  `crates/ln-decode/src/change_target.rs` or register `mod change_target`.
- Do not create the S02 proof surfaces
  (`crates/ln-decode/tests/npa_change_target_contract.rs`,
  `crates/ln-decode/tests/npa_change_target_hostile_contract.rs`,
  `scripts/m208_s02_nested_target_battery.test.mjs`,
  `prd/migration/rust-evidence/m208-s02-nested-target-battery.json`,
  `crates/ln-decode/tests/m208_s02_frozen_surface_guard.rs`,
  `scripts/m208_s02_t04_verify.sh`).
- Do not create an approval, waiver, or adoption artifact from this record.
- Do not change the M205 pins, ADR-0028, `prd/ARCHITECTURE.md`, the M206 records,
  the M208/S01 record, or the operation registry to manufacture adoption.
- Do not promote any gate, lifecycle, requirement or Review Case finding, and do
  not add a change-class row that would claim runtime proof from S02 surfaces.
- Do not invert or delete the M208/S01 stop, or re-read the S01 checkpoint as an
  S02 admission.
- Do not treat an integrity PASS, a battery PASS, a milestone lock, a milestone
  completion, a subagent narrative, or a PASS of this checkpoint contract as the
  missing admission, as runtime proof, or as C4 evidence.

## Resume condition

M208/S02 runtime work may start only after a separate, explicit, source-bound owner
admission for the M208/S02 scope (nested amendment targets and the scope binding of
an amending act without leakage across siblings or quotes, RC28-F13) is recorded
through the applicable acceptance path — an owner grant recorded in a tracked
document, or an authenticated subjective UAT naming the nested-target vocabulary,
the scope-binding contour and its owning runtime surfaces. That admission must be a
new decision, must cite its own sources with hashes, and must state which of the
requested gates (G05, G11, G12, G13) it selects.

Until then this checkpoint stands: `runtime_work` stays `not-started`, the runtime
demo stays `not-proven`, and the design-only material of S02 carries no runtime
claim. Once such an admission exists, this document is superseded: its verdict line
changes, the selected gate set may grow to include the requested gates, and the
Markdown is re-bound to the fresh source hashes.
