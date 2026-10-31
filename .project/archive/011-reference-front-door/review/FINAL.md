# Final Review — law-nexus

Reviewed HEAD: 86bd8af3f3fcb9cc23917b1f90eaf936587e06e9
Overall verdict: pass

<!-- Warnings (non-blocking):
     1. PLAN.md `## Held-out checks` names `build_same_dir_twice_is_idempotent` and
        `truncated_artifact_is_drift_exit_6`; neither exists at this HEAD. The landed pinning
        tests are `crates/ln-product-cli/tests/reference_package_cli.rs`::`build_measure_ed50_package_is_complete_idempotent_and_input_safe`
        (build twice, same dir — INTENT E1 wording) and `zero_byte_artifact_is_drift_exit_6_not_missing_input_exit_3`
        (zero-byte artifact is drift 6, not missing input 3 — INTENT E2 wording); both recorded
        passing at this HEAD and reproduced green by this review. Refresh the PLAN table in a docs pass.
     2. This sidecar's staged copies of `.project/build/verify-ledger.jsonl` and `.project/review/final-gap-1.md` predate the
        post-patch project-verify re-run; the canonical recorded pass at this HEAD is the ledger
        entry for 86bd8af3f3fcb9cc23917b1f90eaf936587e06e9 (exit 0) with the regenerated `.project/review/final-gap-1.md` (Gap verdict: pass). -->

Project Verify (cited, not re-run): `.project/build/verify-ledger.jsonl` entry 86bd8af3f3fcb9cc23917b1f90eaf936587e06e9 — `cargo fmt --all --check && cargo test --workspace --offline && uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py tests/test_repository_quality_gate.py -q`, result pass, exit 0; gap view `.project/review/final-gap-1.md` verdict pass. Collected gap verdict: gap 1 (Risk: project Verify) = pass.

## Success criteria

### SC1 — `law-nexus-inspect reference-package build --corpus-dir <measure-ed50 fixture> --catalog <catalog> --out-dir <dir>` exits 0 and creates the expected reference artifact set (edition/digest layer, references document, pageindex document, measurement artifacts) on the tracked measure-ed50 fixture; it writes only inside `--out-dir` and leaves the corpus directory and catalog byte-unchanged.

- **Verdict**: met
- **Surface**: terminal CLI
- **Check**: Walkthrough steps 1 and E1 rebuild in the verify sidecar at HEAD: `law-nexus-inspect reference-package build --corpus-dir <measure-ed50 corpus> --catalog <recipe-built catalog> --out-dir <dir>` (`target/debug/law-nexus-inspect`, twice into the same dir), with sha256 snapshots of every corpus file and the catalog taken before and after both builds.
- **Observed**: Exit 0 both runs; all six artifacts written non-empty with `wrote` lines (`m217-reference-timeline.json`, `m217-reference-digests.jsonl`, `m217-reference-named-graphs.json`, `m217-reference-amend-provenance.json`, `m217-reference-references.json`, `m217-reference-pageindex.json`); the out-dir held exactly those six plus a pre-existing unrelated file, left untouched; the corpus+catalog snapshot is byte-identical after both builds (N2: write only inside `--out-dir`, inputs unchanged). E1 evidence: the same-dir rebuild is byte-identical and keeps the unrelated file; the held-out edge E1 pin `crates/ln-product-cli/tests/reference_package_cli.rs`::`build_measure_ed50_package_is_complete_idempotent_and_input_safe` ok — `cargo test -p ln-product-cli --offline --test reference_package_cli` re-run by this review in the verify sidecar at HEAD — 8/8 ok (`test result: ok. 8 passed; 0 failed`), green also in the recorded project-verify workspace run at this HEAD. Note: PLAN.md pins E1 under the name `build_same_dir_twice_is_idempotent`, which does not exist at this HEAD; the landed test pins the INTENT E1 wording ("build twice, same dir") — see warning 1.
- **Reference**: crates/ln-product-cli/tests/reference_package_cli.rs:206; .project/build/verify-ledger.jsonl (86bd8af3f3fcb9cc23917b1f90eaf936587e06e9, pass); README status band at README.md:12-15 names the tracked fixture lineage `measure-ed50` used by this run
- **Finding**: none
- **Fix direction**: none
### SC2 — `law-nexus-inspect reference-package check` with the same arguments on the unmodified built package exits 0 and must never exit 0 when any artifact differs from the derivation — any byte drift, including a truncated or zero-byte artifact, exits 6.

- **Verdict**: met
- **Surface**: terminal CLI
- **Check**: Walkthrough step 3 in the verify sidecar at HEAD: `reference-package check` on the unmodified package; first byte of `m217-reference-pageindex.json` flipped; bytes restored; plus the zero-byte and deleted-artifact held-out cases via the named tests.
- **Observed**: Unmodified check exit 0 with `check=ok artifacts byte-identical`; one flipped artifact byte → exit 6 with the `drift: <artifact path>` row on stderr; restored → exit 0. E2 evidence: the held-out edge E2 pin `crates/ln-product-cli/tests/reference_package_cli.rs`::`zero_byte_artifact_is_drift_exit_6_not_missing_input_exit_3` ok — a zero-byte artifact exits 6, never 3 — `cargo test -p ln-product-cli --offline --test reference_package_cli` re-run by this review in the verify sidecar at HEAD — 8/8 ok (`test result: ok. 8 passed; 0 failed`), green also in the recorded project-verify workspace run at this HEAD; `deleted_artifact_is_drift_exit_6` ok (a deleted artifact is also 6). N1: `check_unmodified_package_passes_and_flipped_bytes_all_exit_6` ok — every drift row named on stderr, no warn-and-pass path. Note: PLAN.md pins E2 under the name `truncated_artifact_is_drift_exit_6`, which does not exist at this HEAD; the landed test pins the INTENT E2 wording — see warning 1.
- **Reference**: crates/ln-product-cli/tests/reference_package_cli.rs:266,:316,:336; .project/build/verify-ledger.jsonl (86bd8af3f3fcb9cc23917b1f90eaf936587e06e9, pass); sidecar walkthrough run
- **Finding**: none
- **Fix direction**: none
### SC3 — Two builds into different temporary output directories produce byte-identical artifacts.

- **Verdict**: met
- **Surface**: terminal CLI
- **Check**: Walkthrough extension in the verify sidecar at HEAD: two `reference-package build` runs into two different temporary output directories, then byte comparison of all six artifacts.
- **Observed**: Both builds exit 0; all six artifacts are byte-identical across the two directories. Pinning test `crates/ln-product-cli/tests/reference_package_cli.rs`::`builds_into_different_dirs_are_byte_identical` ok — `cargo test -p ln-product-cli --offline --test reference_package_cli` re-run by this review in the verify sidecar at HEAD — 8/8 ok (`test result: ok. 8 passed; 0 failed`), green also in the recorded project-verify workspace run at this HEAD.
- **Reference**: crates/ln-product-cli/tests/reference_package_cli.rs:354; sidecar walkthrough run
- **Finding**: none
- **Fix direction**: none
### SC4 — A missing or unreadable input (corpus dir absent, catalog unreadable, empty corpus directory with zero XML documents) exits 3.

- **Verdict**: met
- **Surface**: terminal CLI
- **Check**: Walkthrough step 4 in the verify sidecar at HEAD: catalog removed, `reference-package build` re-run; absent-corpus-dir and empty-corpus-directory cases via the named test.
- **Observed**: Missing catalog → exit 3 (`unreadable inputs: unreadable catalog: …`). Pinning test `crates/ln-product-cli/tests/reference_package_cli.rs`::`unreadable_inputs_exit_3` ok — `cargo test -p ln-product-cli --offline --test reference_package_cli` re-run by this review in the verify sidecar at HEAD — 8/8 ok (`test result: ok. 8 passed; 0 failed`), green also in the recorded project-verify workspace run at this HEAD: absent corpus dir exits 3 on build and on check; empty corpus directory (zero XML documents) exits 3 (edge E3).
- **Reference**: crates/ln-product-cli/tests/reference_package_cli.rs:375; sidecar walkthrough run
- **Finding**: none
- **Fix direction**: none
### SC5 — Invalid arguments (unknown flag, missing required flag) exit 2.

- **Verdict**: met
- **Surface**: terminal CLI
- **Check**: Walkthrough step 4 in the verify sidecar at HEAD: `reference-package build` with an unknown flag; remaining argv cases via the named test.
- **Observed**: Unknown flag → exit 2 with `unexpected argument: --bogus`. Pinning test `crates/ln-product-cli/tests/reference_package_cli.rs`::`invalid_arguments_exit_2` ok — `cargo test -p ln-product-cli --offline --test reference_package_cli` re-run by this review in the verify sidecar at HEAD — 8/8 ok (`test result: ok. 8 passed; 0 failed`), green also in the recorded project-verify workspace run at this HEAD: missing required flag, missing flag value, unknown mode and no mode all exit 2 with a non-empty reason; the flag set is a closed enum (edge E5 dismissed by INTENT).
- **Reference**: crates/ln-product-cli/tests/reference_package_cli.rs:412; sidecar walkthrough run
- **Finding**: none
- **Fix direction**: none
### SC6 — A corpus that carries no edition 50 builds and checks with the measurements explicitly reported not applicable (no drift counted, exit 0); a corpus that carries edition 50 has its measurements compared normally.

- **Verdict**: met
- **Surface**: terminal CLI
- **Check**: Walkthrough step 5 in the verify sidecar at HEAD: `reference-package build` and `check` on the tracked `basic` fixture corpus (no edition 50); mixed corpus (`basic` + the edition-0050 edition file) for edge E4; named test.
- **Observed**: No-edition-50 build exits 0 with the explicit marking `measurement not applicable: corpus has no edition 50` and writes only the four core artifacts (measurements never written, never drift); check exits 0 keeping the marking and `check=ok`. Mixed corpus: build exits 0 without the marking, both measurement artifacts written and compared normally, check exits 0 (E4). Pinning test `crates/ln-product-cli/tests/reference_package_cli.rs`::`measurement_scope_follows_edition_50_presence` ok — `cargo test -p ln-product-cli --offline --test reference_package_cli` re-run by this review in the verify sidecar at HEAD — 8/8 ok (`test result: ok. 8 passed; 0 failed`), green also in the recorded project-verify workspace run at this HEAD.
- **Reference**: crates/ln-product-cli/tests/reference_package_cli.rs:457; sidecar walkthrough run
- **Finding**: none
- **Fix direction**: none
### SC7 — `cargo run -q -p ln-product-cli -- health` (README quick-start, as written) exits 0 after `default-run` is set.

- **Verdict**: met
- **Surface**: terminal CLI
- **Check**: Walkthrough step 6 in the verify sidecar at HEAD: `cargo run -q -p ln-product-cli -- health` exactly as README.md:416 writes it.
- **Observed**: Exit 0 with the health report `{"phase":"Health","status":"ok","binary":"law-nexus-inspect","runtime":"rust","duration_ms":0}`; `default-run = "law-nexus-inspect"` at crates/ln-product-cli/Cargo.toml:6; the same command also passed inside the recorded project-verify chain.
- **Reference**: README.md:416; crates/ln-product-cli/Cargo.toml:6; .project/build/verify-ledger.jsonl (86bd8af3f3fcb9cc23917b1f90eaf936587e06e9, pass)
- **Finding**: none
- **Fix direction**: none
### SC8 — README status band enumerates 47 workspace members naming `ln-consultant-parser` and `ln-kb-ontology`; AGENTS.md names an existing slice-writing guide (`.agents/skills/law-nexus-rust/`); POST-SHIP-STATE-2026-10-28.md separates current state from dated history (M004 chapter superseded, red-CI table dated); the ARCHITECTURE.md ADR-0031 row states the measurement-level module code exists while corpus-wide D5/D4 execution is unproven — each verifiable by reading the file at HEAD or by the tracked doc suites.

- **Verdict**: met
- **Check**: none — all four files read at HEAD in the verify sidecar
- **Observed**: README.md:12-15 status band enumerates 47 workspace members naming `ln-consultant-parser` and `ln-kb-ontology` (cross-checked: workspace `members` in Cargo.toml = 47, both crates present). AGENTS.md:330 names the slice-writing guide `.agents/skills/law-nexus-rust/`, which exists with `workflows/implement-rust-slice.md` at HEAD. POST-SHIP-STATE-2026-10-28.md separates current state from dated history: the pre-M005 red-CI table sits under "CI state on integrated main through M003 (dated history)" (:53) with the live green pointer (run 40805352394, re-confirmed by 40822037565, :207), and "## M004 continuation (superseded)" (:100) is marked dated history. prd/ARCHITECTURE.md:68 ADR-0031 row states "**Module code exists at measurement level**" (`reference_layer` + `law-nexus-inspect reference-package build|check`, 0/2/3/6, 5 reserved, proven on the tracked measure-ed50 fixture) and "**Corpus-wide D5/D4 execution unproven**", tag `[proposed]` unchanged. N3: none of the four files carries proven-corpus-parity or raised-band language.
- **Reference**: README.md:12-15; AGENTS.md:326-331; docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:53,:100,:207; prd/ARCHITECTURE.md:68
- **Finding**: none
- **Fix direction**: none
### SC9 — `product-model/` gains reference-package capability documentation linked to the measure-ed50 fixture, the executable test, and a recorded check result.

- **Verdict**: met
- **Check**: none — new product-model documents read at HEAD in the verify sidecar; N4 judged against its Detail
- **Observed**: `product-model/capabilities/reference-package/capability.md` documents build|check and links all three required anchors: the tracked measure-ed50 fixture (`crates/ln-consultant-parser/tests/fixtures/reference-layer/measure-ed50/` with the `scripts/test_m217_reference_parity.py` catalog recipe), the executable test (`{}`), and the recorded check result (T001 Log 2026-10-31 + authoritative orchestrator rerun `.git/gsd-path/dispatch/gsd-path-M011/T001/attempt-2/verify.json`, Verify exit 0, 8/8 ok). Scenarios `build-check-ok.md` and `check-detects-drift.md` name the pinning tests and the recorded 8/8 result; `product-model/coverage.md` lists the capability (five subcommands). N4 (judgment): the new docs state "Fixture-level proof only … No corpus-wide D5/D4 execution is claimed or performed; ADR-0031 stays `[proposed]`" — no lifecycle tag is raised above the recorded `[proposed]`/`[bounded]` bands (the only lifecycle tag appearing in the new docs is `[proposed]`; product-model README/product.md carry none), and fixture-level results are never presented as corpus parity.
- **Reference**: product-model/capabilities/reference-package/capability.md; product-model/capabilities/reference-package/scenarios/build-check-ok.md; product-model/capabilities/reference-package/scenarios/check-detects-drift.md; product-model/coverage.md; crates/ln-product-cli/tests/reference_package_cli.rs
- **Finding**: none
- **Fix direction**: none
