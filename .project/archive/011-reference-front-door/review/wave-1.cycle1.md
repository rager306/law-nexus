# Review — wave 1, cycle 1

Reviewed HEAD: 32837fe5c7e588058067af235125466602c5faf3
Review scope: final

Wave verdict: pass
Cycle: 1
Depth: full
Tasks reviewed: 2

## T001 — Add reference-package build/check to law-nexus-inspect, fixture-proven: pass

Recorded evidence: orchestrator isolated Verify at base 6c905a4d94d8454408b13f94f71bb032c76d748b, `.git/gsd-path/dispatch/gsd-path-M011/T001/attempt-2/verify.json` — exit 0, verbatim task Verify command, 8/8 tests ok (`test result: ok. 8 passed; 0 failed`), `health` ok. The recorded tree's product blobs are byte-identical to landing commit cb7e3f6a0f38929c5dace055323f7ac7c0b4a318 (Cargo.toml 639b6c0b, main.rs 4d2b372f, reference_package_cli.rs 51f77f7e), so the recorded output proves the landed code. The full commit^..commit product patch reverse-applies cleanly onto this sidecar at the review base. The battery drives the real binary (`CARGO_BIN_EXE_law-nexus-inspect`), so argv parsing, composition and exit codes are proven together; no derivation logic is duplicated (main.rs:624-636 documents the composition over `ln_consultant_parser::reference_layer`).

- ✅ (SC1, E1, N2) `reference-package build` on the measure-ed50 fixture exits 0 and writes the expected artifact set into `--out-dir`; a second build into the same dir succeeds byte-identically and touches nothing outside it; corpus and catalog hashes are unchanged. — recorded Verify: `build_measure_ed50_package_is_complete_idempotent_and_input_safe` ok (tests/reference_package_cli.rs:206) — all six artifacts (`m217-reference-timeline.json`, `m217-reference-digests.jsonl`, `m217-reference-named-graphs.json`, `m217-reference-amend-provenance.json`, `m217-reference-references.json`, `m217-reference-pageindex.json`) exist non-empty after exit 0; rebuild into the same dir is byte-identical; the unrelated out-dir file is kept; the input snapshot (corpus files plus catalog bytes, tests:171) is unchanged before/after both builds (N2).
- ✅ (SC2) `reference-package check` on the unmodified package exits 0; after any artifact byte is modified it exits 6. — recorded Verify: `check_unmodified_package_passes_and_flipped_bytes_all_exit_6` ok (tests:266) — unmodified exit 0 with `check=ok`; the first byte of every artifact flipped exits 6 with all six drift rows named on stderr; restored bytes exit 0 again. Source confirms N1: `run_check` collects every drift row, prints each, then exits (`drift:` loop at reference_layer.rs:2597, `return EXIT_DRIFT` at :2600) — no warn-and-pass path.
- ✅ (SC3) Builds into two different temp dirs are byte-identical. — recorded Verify: `builds_into_different_dirs_are_byte_identical` ok (tests:354) — package-a vs package-b byte-equal across all six artifacts.
- ✅ (SC4, E2) A missing catalog, an absent corpus dir, and an empty corpus directory each exit 3; a zero-byte artifact exits 6. — recorded Verify: `unreadable_inputs_exit_3` ok (tests:375) — absent corpus dir exits 3 on build and on check, missing catalog exits 3, empty corpus directory (zero XML documents) exits 3; `zero_byte_artifact_is_drift_exit_6_not_missing_input_exit_3` ok (tests:316) — the pageindex truncated to zero bytes exits 6, not 3 (E2).
- ✅ (SC5) An unknown flag and a missing required flag each exit 2. — recorded Verify: `invalid_arguments_exit_2` ok (tests:412) — unknown flag, missing required flag, flag value absent, unknown mode, no mode all exit 2 with a non-empty stderr reason; the parser is a closed three-flag enum (main.rs:637-664) with `EXIT_ARGV` on anything else.
- ✅ (SC6) A corpus without edition 50 builds and checks with measurements explicitly marked not applicable, exit 0. — recorded Verify: `measurement_scope_follows_edition_50_presence` ok (tests:457) — the `basic` fixture (no edition 50) builds exit 0 with the explicit marking `measurement not applicable: corpus has no edition 50` (main.rs:713), writes only the four core artifacts, and checks exit 0 keeping the marking; a mixed corpus (`basic` + the edition-0050 file) compares its measurements normally (E4).
- ✅ (SC7) `cargo run -q -p ln-product-cli -- health` exits 0 exactly as the README writes it. — recorded Verify runs that exact command in the same chain: health JSON `{"phase":"Health","status":"ok","binary":"law-nexus-inspect","runtime":"rust",...}` and `VERIFY_EXIT=0`; `default-run = "law-nexus-inspect"` at Cargo.toml:6; README.md:416 writes the command verbatim.

Warnings (non-blocking):
- PLAN.md's Held-out checks table names `build_same_dir_twice_is_idempotent` and `truncated_artifact_is_drift_exit_6`; the landed pinning tests are named `build_measure_ed50_package_is_complete_idempotent_and_input_safe` and `zero_byte_artifact_is_drift_exit_6_not_missing_input_exit_3`. INTENT.md's Edge coverage rows (the binding wording: "Pinned by a named test") are satisfied and the recorded run is green, but PLAN's test names do not resolve as written — refresh the PLAN table or align the names in a later docs pass.

Contract violations (blocking):
- none

## T002 — Align front-door docs and PDD model with the shipped reference-package surface: pass

Recorded evidence: orchestrator isolated Verify at base cb7e3f6a0f38929c5dace055323f7ac7c0b4a318, `.git/gsd-path/dispatch/gsd-path-M011/T002/attempt-1/verify.json` — exit 0, verbatim task Verify command (grep chain). The recorded tree's product blobs are byte-identical to landing commit 32837fe5c7e588058067af235125466602c5faf3 (all eight files), and the full commit^..commit product patch reverse-applies cleanly onto this sidecar at the review base. Every doc claim below was additionally re-read directly in the sidecar at the review base.

- ✅ (SC8) README names 47 members including the two parser crates; AGENTS.md references `.agents/skills/law-nexus-rust/` and its retired pointer is gone (the Verify grep pins the absence by the slug `implement-rust-slice`); POST-SHIP-STATE marks the M004 chapter superseded and dates the red-CI table; ARCHITECTURE.md ADR-0031 row carries the honest module-code/unproven wording. — recorded Verify exit 0 plus files read at the review base: README.md:12-15 status band counts 47 members naming `ln-kb-ontology` and `ln-consultant-parser` (member table at README.md:217, rows :227-228); AGENTS.md:330 points at `.agents/skills/law-nexus-rust/`, which exists (slice-writing guide present at `.agents/skills/law-nexus-rust/workflows/implement-rust-slice.md`), and the retired slug `implement-rust-slice` no longer appears in AGENTS.md; POST-SHIP-STATE-2026-10-28.md:53 retitles the red-CI section "(dated history)" with the live green pointer (run 40805352394 success, re-confirmed by main run 40822037565, :56-58; runs recorded as verified in `.project/research/DOCS-AUDIT.md`), and :100 marks "## M004 continuation (superseded)" as dated history with the M004 record kept verbatim; prd/ARCHITECTURE.md:68 states module code exists at measurement level (`reference_layer` + `reference-package build|check`, 0/2/3/6, 5 reserved) while corpus-wide D5/D4 execution stays unproven, tag `[proposed]` unchanged — N3 checked: none of the four files carries proven-parity or raised-band language.
- ✅ (SC9) `product-model/capabilities/reference-package/` documents the build/check capability with the fixture, the named test path, and the recorded check result; `product-model/coverage.md` lists it. — read at the review base: capability.md links the tracked measure-ed50 fixture path (capability.md:34), the executable test `crates/ln-product-cli/tests/reference_package_cli.rs` (:15), and the recorded check result citing the T001 Log and the verify.json evidence path (:40); both scenarios name the pinning tests and the recorded 8/8 result; coverage.md lists the capability and corrects the count to five subcommands (:5, :7). N4 (judgment) checked: the new docs state fixture-level proof only, claim no corpus-wide D5/D4 execution, and keep ADR-0031 at `[proposed]` — no lifecycle tag is raised above the recorded bands.

Warnings (non-blocking):
- The authoritative T002 Verify was recorded by orchestrator manual finish (the coder child exited without the machine-readable RESULT line); the recorded rerun in verify.json carries the verbatim command and exit 0, which is the sanctioned orchestrator evidence path — noted for transparency only.

Contract violations (blocking):
- none

## Intent coverage

### SC1 — `law-nexus-inspect reference-package build --corpus-dir <measure-ed50 fixture> --catalog <catalog> --out-dir <dir>` exits 0 and creates the expected reference artifact set (edition/digest layer, references document, pageindex document, measurement artifacts) on the tracked measure-ed50 fixture; it writes only inside `--out-dir` and leaves the corpus directory and catalog byte-unchanged.: pass
- ✅ Recorded Verify 8/8 ok (verify.json T001/attempt-2, exit 0): `build_measure_ed50_package_is_complete_idempotent_and_input_safe` (tests:206) exits 0 and writes all six artifacts non-empty on the tracked measure-ed50 fixture content (scratch copy; the N2 input-snapshot hash stays byte-identical); writes are confined to `--out-dir` (`write_reference_artifact`, main.rs:724-740). Held-out E1 (idempotency, build twice same dir) is pinned by that same named test, recorded ok.
- **Surface**: terminal CLI
- **Check**: `cargo test -p ln-product-cli --offline --test reference_package_cli`
- **Observed**: build exits 0; six artifacts (edition/digest layer: timeline, digests, named graphs, amend provenance; references document; pageindex document) non-empty in the out-dir; second build into the same dir byte-identical; unrelated out-dir file untouched; corpus files and catalog bytes unchanged (input snapshot compared before/after both builds).

### SC2 — `law-nexus-inspect reference-package check` with the same arguments on the unmodified built package exits 0 and must never exit 0 when any artifact differs from the derivation — any byte drift, including a truncated or zero-byte artifact, exits 6.: pass
- ✅ Recorded Verify 8/8 ok: `check_unmodified_package_passes_and_flipped_bytes_all_exit_6` (tests:266) — exit 0 with `check=ok` unmodified; every flipped artifact byte exits 6 naming every row; `zero_byte_artifact_is_drift_exit_6_not_missing_input_exit_3` (tests:316, held-out E2) recorded ok; `deleted_artifact_is_drift_exit_6` (tests:336) recorded ok. N1 checked in source: `run_check` notes every drift row on stderr before `return EXIT_DRIFT` (reference_layer.rs:2593-2600); there is no warn-and-pass path.
- **Surface**: terminal CLI
- **Check**: `cargo test -p ln-product-cli --offline --test reference_package_cli`
- **Observed**: unmodified package checks ok (exit 0); any-byte drift, zero-byte truncation, and deleted artifact each exit 6 with all drift rows named; restored bytes check ok again (exit 0).

### SC3 — Two builds into different temporary output directories produce byte-identical artifacts.: pass
- ✅ Recorded Verify 8/8 ok: `builds_into_different_dirs_are_byte_identical` (tests:354) — package-a vs package-b byte-equal across all six artifacts (E6: every re-derivation path is covered by this statement).
- **Surface**: terminal CLI
- **Check**: `cargo test -p ln-product-cli --offline --test reference_package_cli`
- **Observed**: two builds into different temp dirs produced byte-identical artifacts over the full six-artifact set.

### SC4 — A missing or unreadable input (corpus dir absent, catalog unreadable, empty corpus directory with zero XML documents) exits 3.: pass
- ✅ Recorded Verify 8/8 ok: `unreadable_inputs_exit_3` (tests:375) — absent corpus dir exits 3 on build and on check, missing catalog exits 3, empty corpus directory exits 3 (E3); error path maps every `RefError` to `EXIT_INPUT` (reference_layer.rs:89, main.rs:683,707).
- **Surface**: terminal CLI
- **Check**: `cargo test -p ln-product-cli --offline --test reference_package_cli`
- **Observed**: all three unreadable-input shapes exited 3 with a stderr reason; the absent-corpus case also exits 3 on `check`.

### SC5 — Invalid arguments (unknown flag, missing required flag) exit 2.: pass
- ✅ Recorded Verify 8/8 ok: `invalid_arguments_exit_2` (tests:412) — five argv shapes (unknown flag, missing required flag, flag value absent, unknown mode, no mode) all exit 2 with a non-empty reason; the flag set is closed (E5) with no defaults and no fallback to repo paths (main.rs:637-664).
- **Surface**: terminal CLI
- **Check**: `cargo test -p ln-product-cli --offline --test reference_package_cli`
- **Observed**: every invalid-argv shape exited 2 and printed why; exit 5 is never emitted by the Rust side (no `exit(5)` anywhere in main.rs; 0/2/3/6 only).

### SC6 — A corpus that carries no edition 50 builds and checks with the measurements explicitly reported not applicable (no drift counted, exit 0); a corpus that carries edition 50 has its measurements compared normally.: pass
- ✅ Recorded Verify 8/8 ok: `measurement_scope_follows_edition_50_presence` (tests:457) — the `basic` fixture (no edition 50) builds and checks exit 0 with the explicit not-applicable marking and no measurement artifacts written (E4, no-edition-50 side); the mixed corpus (basic + edition-0050 file) writes and compares both measurement artifacts normally. Scope decided by `measurement_applicable` (reference_layer.rs:1913) on build and check alike.
- **Surface**: terminal CLI
- **Check**: `cargo test -p ln-product-cli --offline --test reference_package_cli`
- **Observed**: no-edition-50 build/check exit 0 with `measurement not applicable: corpus has no edition 50` and only four core artifacts on disk; edition-50 corpus compares measurements and checks exit 0.

### SC7 — `cargo run -q -p ln-product-cli -- health` (README quick-start, as written) exits 0 after `default-run` is set.: pass
- ✅ Recorded Verify (verify.json T001/attempt-2, exit 0) runs that exact command: health status ok JSON printed, `VERIFY_EXIT=0`; `default-run = "law-nexus-inspect"` at crates/ln-product-cli/Cargo.toml:6 disambiguates the two binaries; README.md:416 carries the command verbatim.
- **Surface**: terminal CLI
- **Check**: `cargo run -q -p ln-product-cli -- health`
- **Observed**: exit 0 with `{"phase":"Health","status":"ok","binary":"law-nexus-inspect","runtime":"rust","duration_ms":0}`.

### SC8 — README status band enumerates 47 workspace members naming `ln-consultant-parser` and `ln-kb-ontology`; AGENTS.md names an existing slice-writing guide (`.agents/skills/law-nexus-rust/`); POST-SHIP-STATE-2026-10-28.md separates current state from dated history (M004 chapter superseded, red-CI table dated); the ARCHITECTURE.md ADR-0031 row states the measurement-level module code exists while corpus-wide D5/D4 execution is unproven — each verifiable by reading the file at HEAD or by the tracked doc suites.: pass
- ✅ Recorded Verify exit 0 (verify.json T002/attempt-1, verbatim grep chain) plus each file read at the review base: README.md:12-15 (band, 47 members, both parser crates named) and :217/:227-228 (member table); AGENTS.md:330 names the existing `.agents/skills/law-nexus-rust/` (its `workflows/implement-rust-slice.md` guide exists) and the retired slug is absent; POST-SHIP-STATE-2026-10-28.md:53 dates the red-CI table "(dated history)" with the live green pointer at :56-58 (runs recorded as verified in the tracked DOCS-AUDIT.md) and :100 marks M004 "(superseded)" with the historical record kept verbatim; prd/ARCHITECTURE.md:68 carries the module-code-exists / D5-D4-unproven wording with `[proposed]` unchanged (N3: no proven-parity or raised-band language in any of the four files).

### SC9 — `product-model/` gains reference-package capability documentation linked to the measure-ed50 fixture, the executable test, and a recorded check result.: pass
- ✅ Read at the review base: `product-model/capabilities/reference-package/capability.md` links the measure-ed50 fixture path (:34), the executable test `crates/ln-product-cli/tests/reference_package_cli.rs` (:15), and the recorded check result with the T001 Log / verify.json evidence (:40); `build-check-ok.md` and `check-detects-drift.md` pin the named tests and the recorded 8/8 result; `coverage.md` lists the capability (:5, :7). N4 (judgment) checked: fixture-level proof only, no corpus-wide D5/D4 execution claimed or implied, ADR-0031 kept at `[proposed]`, no lifecycle tag raised above the recorded bands.

## Summary for orchestrator

- blocked findings: none
- repeat offenders: none (cycle 1)
- warnings worth a human eye: (1) PLAN.md's Held-out checks table test names do not match the landed test names for E1/E2 — INTENT's "pinned by a named test" rule is satisfied and the recorded run is green, but refresh the PLAN table in a later docs pass; (2) T002's authoritative Verify was recorded by orchestrator manual finish after the coder child omitted its RESULT line — the recorded rerun (verbatim command, exit 0) is valid evidence, kept here for transparency; (3) staged-name vs PLAN-depth conflict: this review is staged as briefed at `.project/review/wave-1.cycle1.contract.md` (logical task `review_wave_1_cycle_1_contract`, lens contract), but the bundled `scripts/check_handoffs.py wave` gate rejects a lens-suffixed review name unless PLAN.md's Wave 1 `Review depth:` is `deep`, and PLAN.md says `full` (which expects `wave-1.cycle1.md`). PLAN.md and the review staging are outside this reviewer's writable scope, so the conflict is surfaced unresolved: the orchestrator owns both and must either re-stage this file under the lens-free name or correct PLAN.md's depth before the canonical transfer.


## Adversarial lens — independent second reviewer (pass)

<!-- Provider fallback: the driver-dispatched reviewer child failed on a provider
     transport error four times; the owner-approved native path dispatched two
     independent reviewer agents (contract above, adversarial here), each in its
     own verify sidecar at the same review base. -->

Lens verdict: pass. Hostile probes re-run in the sidecar all failed closed with the ruled 0/2/3/6 codes and no panics: byte flips, zero-byte and non-UTF-8 artifacts, deleted artifacts, absent/corrupt/zero-byte catalogs, file-as-corpus, file-as-out-dir, empty corpora, duplicate/non-numeric/wrong-namespace editions, closed-argv attacks, input-immutability hashes (N2), determinism (SC3), edition-50 applicability (SC7), README health command verbatim (SC7). Recorded Verify trees match the landing commits minus task-log lines. All SC1-SC9 carry the adversarial reviewer's own run/read evidence.
Warnings (non-blocking, recorded for the orchestrator):
- PLAN.md held-out test names drifted from the landed (stronger) test names.
- Measurement artifacts embed the corpus dir basename.
- No argv guard for --out-dir inside --corpus-dir.
- Non-UTF-8 drift row is labeled `missing artifact` (exit 6 either way).
