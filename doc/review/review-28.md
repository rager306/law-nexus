# Review 28 Addendum: S19 fixed-census closeout

Date: 2026-09-12
Status: supporting-only; additive process and evidence note, not legal or capability acceptance.
Scope: M204-w2ktfw/S19, post-S18 validate-milestone no-artifact abort and sibling supervisor closeout break.

## Fixed evidence

The tracked S19 census is `prd/migration/rust-evidence/m204-s19-post-s18-validate-abort.json` and its predecessor manifest is `prd/migration/rust-evidence/m204-s19-frozen-hashes.json`. The census records one post-S18 no-artifact `validate-milestone` abort and a separate supervisor `closeout-break` exit. `supervisor_exit` is not an additional abort and is not an intercept.

The closed checker (`scripts/m204_s19_loop_note.py`) is invoked by `scripts/m204_s19_t03_verify.sh` in `check` mode only. T03 does not compose, replace, or repair the census, does not invoke `validate-milestone`, and does not inspect the live database, journal, supervisor, or corpus. The verifier requires exactly twelve ordered predecessor pins, checks their frozen hash and byte-size values through the checker, runs the independent adversarial subprocess suite, and compares all input hashes before and after execution. Any drift, malformed schema, unsafe path, timeout, nonzero subprocess, or missing marker fails closed.

## Disposition

This is supporting evidence for the repeated engine deadlock pattern, not a retry substitute. The disposition remains:

- C4: `non-pass`;
- engine fix: `not_fixed`;
- upstream issue: `not_filed`;
- `law_nexus_fixable`: `false`;
- lifecycle/status effect: `unchanged`;
- `s19_called_validate_milestone`: `false`;
- validation projection: absent;
- `retry_substitute`: `false`;
- S12, S16, S17 and S18 stopped-dispatch flags: `false`.

No product runtime, Rust source, historical receipt, predecessor evidence, lifecycle state, or corpus claim is changed by this addendum. RC28 findings in the dated review remain independent and are not promoted by S19.

## Verification contract

Run `bash scripts/m204_s19_t03_verify.sh`. Success requires the existing S19 checker marker, all adversarial and independent consumer checks, exactly twelve immutable predecessor pins, unchanged tracked evidence hashes, and the final marker `S19_T03_VERIFY_OK`.

# Review 28 Addendum: S21 mixed post-S20 validate window

Date: 2026-09-13
Status: supporting-only; additive process and evidence note, not legal or capability acceptance.
Scope: M204-w2ktfw/S21, the fixed mixed census after S20 completion and UAT.

## Fixed evidence

The tracked S21 census is `prd/migration/rust-evidence/m204-s21-post-s20-validate-loop.json` and its predecessor manifest is `prd/migration/rust-evidence/m204-s21-frozen-hashes.json`. The census records four validate dispatches: two no-artifact/finalize-retry aborts and two journal-cancelled interrupts. All four have `unit-start`; the two cancelled rows have `toolCalls=0` in the terminal session context, are not intercepts, and carry no finalize fields. Their measured provider error is recorded as `Provider error: Connection error.` and is not attributed to the historical SQL trigger defect. The sibling supervisor terminal flow is a separate `closeout-break` exit bound to headless PID `1841192`; STOP after four retries is not an additional abort and is not the census abort count.

The closed checker (`scripts/m204_s21_loop_note.py`) is invoked by `scripts/m204_s21_t03_verify.sh` in `check` mode only. T03 does not compose, replace, or repair the census, does not invoke `validate-milestone`, and does not inspect the live database, journal, supervisor, or corpus. It checks the sixteen ordered S09–S20 predecessor pins, runs the independent S21 adversarial suite, verifies the documented anchors, and compares all census, manifest, and predecessor hashes before and after execution. Any drift, malformed schema, unsafe path, contradictory count, nonzero subprocess, or missing marker fails closed.

## Disposition and non-claims

This is supporting evidence for the repeated engine deadlock pattern, not a retry substitute. `engine_fix=not_fixed`, `law_nexus_fixable=false`, and C4 remains `non-pass`; no requirement or finding is closed, no validation projection is created, and `validate-milestone` is not an automatic retry substitute. The historical trigger defect and the measured provider connection errors remain separate claims. No product runtime, Rust source, historical receipt, predecessor evidence, lifecycle state, or corpus claim is changed by this addendum.

## Verification contract

Run `bash scripts/m204_s21_t03_verify.sh`. Success requires the S21 checker marker, all independent adversarial checks, exactly sixteen ordered predecessor pins, unchanged census/manifest/pin bytes, the fixed-window documentation anchors, and the final marker `S21_T03_VERIFY_OK`.

# Review 28 Addendum: S22 source-bound operational control

Date: 2026-09-13
Status: supporting-only; additive operational evidence, not lifecycle or legal acceptance.
Scope: M204-w2ktfw/S22, external GSD recovery blocker plus a bounded C4 `Comparison` control.

The S22 external blocker remains `gsd_recovery_liveness=blocked-external`, `engine_fix=not_fixed`, `law_nexus_fixable=false`, and `retry_substitute=false`. The S10 duplicate `inventory_digest` reason remains non-pass; S22 does not call `validate-milestone`, retry the engine, or claim closure of R035/R070. The Rust control is a separate subprocess receipt: `cargo test -p ln-consultant-parser --offline --locked -j 1 --test contour_diagnostics_contract`. Its result is `c4_control=pass` only when the actual bounded suite exits zero and reports at least one test; this does not promote `c4_operational_acceptance`, which remains `non-pass`.

The recorder binds the exact argv, relative working directory, UTC and monotonic timing, cargo/rustc versions, stdout/stderr hashes, and tracked Cargo/Rust plus S22 evidence/document sources. The check-only host runs T01, the independent S22 subprocess suite, S21 check, and S15 classify, then rechecks every source and output hash without rewriting evidence or reading live/GSD-ignored state. A timeout, nonzero exit, empty test-result summary, missing log, stale source, or forged promotion fails closed.

No S22 battery is a GSD `testedSourceRevision`, validation projection, engine repair authorization, requirement closure, or automatic validate retry. Historical S09-S21 evidence and the S10 non-pass receipt remain byte-immutable.

Verification contract: `bash scripts/m204_s22_t03_verify.sh`.
