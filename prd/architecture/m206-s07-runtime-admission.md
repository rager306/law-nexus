# M206/S07 runtime admission overlay: RC28-F06..F12

**admission_source:** `prd/architecture/m206-s05-runtime-admission.md`
**scope:** M206-jnbhlz / S07 Runtime grammar context remediation completion
**status:** admitted completion work for the same source-bound RC28-F06..F12 set
**selected_d388_gates:** G01, G02, G14
**deferred_d388_gates:** G03,G04,G05,G06,G07,G08,G09,G10,G11,G12,G13,G15,G16
**runtime_stop:** lifted for M206/S07 completion of the S05-admitted scope only

## Source-bound decision and boundary

S05 already records the owner's Accept for RC28-F06..F12. S07 is the sanctioned
completion slice named by the S06 remediation assessment; it does not mint a
second owner Accept and does not broaden the admitted scope. The D388 baseline
is limited to selected G01/G02/G14. The remainder stays deferred, including
numeric grammar and hop budgets; G02 remains wired at its existing capture
surface and is not reselected or duplicated here.

S07 owns the following runtime proof surfaces:

- `crates/ln-decode` document context, local grammar, and law-reference
  capture/resolution contracts for F06, F07, F08, F09, and F10;
- `crates/ln-temporal` context, semantic-scope, and binding-candidate
  contracts for F11 and F12;
- provider-isolated port composition and bounded diagnostic evidence only.

## Historical provenance and non-claims

S01, S02, S03, and S04 remain **NOT_RUN** historical adoption-state records.
Their `runtime_stop_active` and no-start markers are not rewritten and their
future scenario rows are not retroactively promoted to runtime PASS. Their
adoption-contract checks remain provenance checks, not S07 implementation
proof.

This overlay is not product readiness, a `[validated]` lifecycle promotion,
a corpus-wide correctness claim, or a disposition of packet
`RC-2026-09-10-001`. It does not close R035, R038, R070, R074, or R081, amend
ADR-0028, select deferred-undefined vocabulary, introduce legal IR, or alter
M205 pins. Candidates remain candidates; missing, conflicting, or unavailable
evidence remains fail-closed and source-bound.

## Completion condition

The S07 implementation may claim green only after the honest reproduction
oracle distinguishes a real executed test from a missing `--exact` match,
then the F06..F12 target suites and composed battery pass with positive and
fail-closed paths. The executable admission contract
`scripts/m206_s07_admission_contract.test.mjs` checks these source-bound
literals and refuses absent or incomplete admission metadata.
