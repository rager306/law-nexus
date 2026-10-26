# Review — wave 2, cycle 2

<!-- Review sidecar checkout HEAD (recorded per brief, confirmed via `git rev-parse`):
     cc57376b948b6b11e9906acdb893f5f4e7f9048d — the recorded review base. Method:
     read-only isolated diffs (`commit^..commit`) and artifact re-reads
     (`git show <commit>:<path>`) inside this sidecar checkout; the recorded dispatch
     base 61effa6e of T010/T004/T005 is the wave-1 review-pass commit and the wave
     base, and those three landings chain on the branch, so the isolated review patch
     per reviewer-wave is `commit^..commit` (exactly the tree delta each landing
     introduced); for T006 base 2a0ead24 == `commit^` and both formulations coincide.
     The recorded orchestrator Verify outputs in the task Logs are the Verify
     evidence; no task Verify or project Verify was re-run. Re-review after cycle 1:
     cycle 1 passed substantively and its task/SC verdicts are re-checked here from
     the same evidence, re-verified directly (battery and rerun record parsed, block
     hash independently recomputed, marker sweep re-run); no criterion had failed.
     The rubric is the corrected INTENT.md (## Corrections 2026-10-26 "(a)"): the
     correction re-scopes SC8 (owned by wave-3 T009) and changes no text of
     SC3/SC4/SC5 owned by this wave. -->

Wave verdict: pass
Cycle: 2
Depth: full
Tasks reviewed: 4

## T004 — Close the M225 validation residual with an honest re-run: pass

- ✅ tested_source_revision in the battery is a full 40-hex SHA — the exact HEAD the re-validation ran at — and the placeholder string is gone; the role text states the 40-hex-HEAD semantics (E3). — re-read at landing commit e776fc5c: `tested_source_revision` is `61effa6efe68df1efff2c71f4bd39c4b701e434c` (40-hex, the recorded base HEAD that both the worker Verify and the orchestrator isolate Verify rows state they ran at), the string `pending-fill-by-validate-unit` is absent from the battery raw text, and the rewritten `tested_source_revision_role` states the E3 exact-40-hex-HEAD semantics with the mismatch-invalidates rule.
- ✅ The 15 historical check entries of the battery are byte-identical to their recorded state; only the pin, its role text, and the environment annotation changed. — parsed both trees: `checks` and `non_claims` compare equal between base 61effa6e and e776fc5c; the isolated patch (`e776fc5c^..e776fc5c`) contains a single battery hunk touching exactly the pin line, the role line, and the `environment` block (gaining `native_rerun_m001` with runner and git_state).
- ✅ The rerun record exists at prd/migration/rust-evidence/m225-validation-rerun-m001.json, covers every battery check id with an explicit disposition from the fixed set, and its verdict states the measurement class — a hermetic run is not a byte-parity PASS (N1), and corpus parity evidence remains the pinned 2026-10-18 corpus-present run. — re-read at e776fc5c: 15/15 battery check ids dispositioned, set-equal with no missing or extra ids, dispositions inside the fixed set (`re-run-passed-hermetic` 9 / `skipped-corpus-absent` 4 / `not-rerun-environment-gated` 2; the summary block agrees), verdict status `hermetic-pass-parity-unproven` with `measurement_class: hermetic-observability-corpus-absent`, a statement disclaiming byte parity and pinning corpus parity evidence to the 2026-10-18 corpus-present run at HEAD e4f6c81a, and `tested_source_revision` equal to the battery pin.
- ✅ No file under crates/ changes (S02 untouched); the landing diff touches exactly the three declared paths. — the commit stat of e776fc5c lists only the battery, the rerun record, `tests/test_m225_validation_residual.py`, and the task file; no `crates/` path appears in the diff.
- ✅ tests/test_m225_validation_residual.py pins criteria 1 and 3 mechanically and fails if the residual were reverted to the placeholder. — the suite (re-read at e776fc5c, 5 tests) asserts a full-40-hex pin, placeholder absence from the battery raw text, role semantics, pin equality across battery and rerun record, set-equal full check-id coverage with fixed-set dispositions, and the measurement-class disclaimers; recorded Verify `5 passed` (worker r2, exit 0, at HEAD 61effa6e on gsd-path-task/T004) and orchestrator isolate Verify `5 passed`, exit 0.

Warnings (non-blocking):
- none

Contract violations (blocking):
- none

## T005 — Create the minimal PDD product model: pass

- ✅ product-model/ exists in the tracked tree with the PDD layout core — README.md, config.yaml, the product file, coverage.md, at least one interface, its capabilities with scenarios, and entities — following the bundled format reference shapes. — `git ls-tree` at ab0286e4 shows 28 tracked files under `product-model/`: README.md, config.yaml (`schema: 11`, `sdd.paths: prd/`), taxonomies.yaml, product.md, coverage.md, interfaces/terminal (interface + 2 screens), 4 capabilities with 9 scenarios, 2 entities, 4 business rules; the recorded bundled pinned lint (pdd-toolkit 0.37.1) returned `ok: true` with zero errors, which is the format-shape conformance evidence.
- ✅ The model records only established observable behavior: StubEmbedding is named as the fail-closed stub it is and the stores are recorded as in-memory; no capability claims live embeddings, persistent storage, or corpus behavior (E4, N5 — review judges the prose, the test pins the markers). — marker sweep over all 28 files re-run at ab0286e4: `StubEmbedding` named a fail-closed stub in product.md, inspect-document, the retrieval business rule, and its scenario; `in-memory` recorded in 6 files including product.md and the capability prose; the only `persist` hit in the whole model is the true negative statement "Nothing persists between runs"; no RuVector, TEI, FalkorDB, live-embedding, persistent-storage, or corpus-ingestion claim anywhere.
- ✅ The PDD statements in AGENTS.md and docs/agent-stack/WORKFLOW.md are true with no edits to those files — the directory and the model now exist. — the landing diff of ab0286e4 touches neither file (paths: `product-model/`, `tests/test_product_model.py`, task file); at that tree AGENTS.md:262 and docs/agent-stack/WORKFLOW.md:14 reference `product-model/`, which exists with a real model.
- ✅ The pdd lint output, or its unavailability on the host, is recorded in the task Log; the tracked test passes with no host-only tooling. — the Log records the bundled pinned runner lint output verbatim (`ok: true`, one assessed-and-kept naming warning on `replay-edition`) plus a cross-check with the host-pinned CLI 0.37.1; recorded Verify `4 passed in 0.27s` runs on tracked files only, and orchestrator isolate Verify `4 passed in 0.30s`, exit 0.
- ✅ tests/test_product_model.py pins criteria 1 and 2 mechanically and fails if the model directory is absent or stripped of the stub markers. — the suite (re-read at ab0286e4, 4 tests) asserts the layout core, an interface with capabilities/scenarios and entities, `StubEmbedding` named with `stub` + `fail-closed` wording, and rejects any capability claiming a live embedding or a persistent store; the Log records the negative-path checks (directory absent, stub mentions stripped) raising the expected assertion errors.

Warnings (non-blocking):
- none

Contract violations (blocking):
- none

## T006 — Re-index GitNexus and regenerate the AGENTS.md tool block: pass

- ✅ The index is rebuilt with the tracked command in the primary worktree on gsd-path/M001, and prd/project-state/data/gitnexus-index.json records the command, a full 40-hex indexed head, the counts, the timestamp, and the sha256 of the AGENTS.md block between the gitnexus markers. — the Log records the tracked `node .gitnexus/run.cjs analyze --force --name law-nexus` run in the primary worktree on gsd-path/M001 (exit 0, 123.0s) after the documented bunx bootstrap created the missing .gitnexus/ runner (audit row 9 condition); the receipt re-read at 55ec0072 carries schema `law-nexus/gitnexus-index-receipt/v1`, the exact command, indexed_head `2a0ead24e812aba07b6e0e72897ae54eed35106e` (full 40-hex, the analyze HEAD), counts 43047/102234/584, a timestamp, and the block sha256.
- ✅ The AGENTS.md tool block between the gitnexus markers matches the receipt — equal hash, counts present, repo name law-nexus — and was produced by the tool, not by hand (E5, N6: on analyze failure the previous block and receipt stay untouched and consistent, and the error is reported, never hand-patched away). — independently recomputed the sha256 of the block text between the markers at 55ec0072 (exact slice the tracked test defines: inclusive of both markers, no trailing newline): `896a95033fdd8b45e8f67f465132cb2b22bd632ddd5d676622c4d5bfa01a328f`, equal to the receipt; all three counts appear in the block text and it names law-nexus; the AGENTS.md hunk touches only the block (count line 23577/50919/568 replaced by 43047/102234/584); the Log states the coder never edited the block region and no analyze failure occurred.
- ✅ The task Log records the preflight gitnexus-index-freshness result at the analyze HEAD showing a match with no metadata-missing warning, and states the expected one-commit drift after landing. — the Log's dedicated preflight record: before, .gitnexus/ absent (the audit-row-9 metadata-missing condition); after, at the analyze HEAD, meta.json present and parses with `lastCommit` equal to `git rev-parse HEAD` = 2a0ead24e812aba07b6e0e72897ae54eed35106e, commit match, no metadata-missing warning and no commit-mismatch warning, and the expected one-commit drift after landing is stated.
- ✅ tests/test_gitnexus_block_receipt.py pins criteria 1 and 2 mechanically and fails if the receipt is absent or the block changed without the tool. — the suite (re-read at 55ec0072, 4 tests) asserts receipt schema/command/40-hex head, block-hash equality against the receipt (a hand-edited block or stale receipt fails), counts-in-block, and the repo name; recorded Verify `4 passed in 0.27s` at HEAD 2a0ead24e812aba07b6e0e72897ae54eed35106e on gsd-path/M001, and orchestrator sidecar Verify `4 passed in 1.20s`, exit 0.

Warnings (non-blocking):
- The stock preflight line at the analyze HEAD read `warn` (dirty tree: the check returns early on a non-empty git status because the task's own in-flight edits were uncommitted); the Log proves freshness through the check's own decision inputs instead. Disclosed and consistent with the check's implementation; a green stock line was unobtainable mid-task by design.

Contract violations (blocking):
- none

## T010 — Reword the corpus-glob-guard claim in law-source/consultant/README.md: pass

- ✅ law-source/consultant/README.md no longer contains the string `law-source-corpus-glob-guard`; the rule-4 claim names only `law-source-fixture-guard` and states that this check covers the README fixture-vault marker, not corpus globbing. — re-read at 64a7d88: the string is absent from the README tree; the isolated patch contains exactly one README hunk replacing the rule-4 sentence with a claim naming `law-source-fixture-guard`, covering only the fixture-vault README marker plus the `.deprecated/` gitignore state, corpus globbing remaining a review-time defect under rule 4 itself.
- ✅ The marker substrings `НЕ КОРПУС`, `consru_export`, and `43 785` remain in the README, so `check_law_source_fixture_guard`'s marker test still passes; no other README line changed. — all three substrings verified present at 64a7d88; the diff contains exactly one README hunk (the rule-4 claim), nothing else.
- ✅ .project/research/DOCS-AUDIT.md User rulings row 16 shows Planned `T010`; the rest of the audit file is unchanged. — row 16 re-read at 64a7d88 reads `| 16 | fix-doc | «продолжаем - двигай проект» (2026-10-26), п.5 — поправить формулировку README | T010 |`; the audit file compares byte-identical between base 61effa6e and the landing.
- ✅ The landing diff touches exactly law-source/consultant/README.md and .project/research/DOCS-AUDIT.md. — the landing diff of 64a7d88 touches law-source/consultant/README.md plus the task file and no other path; the audit needed no edit because row 16 already read `T010` at base (recorded at plan approval ccd15ff5, before dispatch, and disclosed in the Log), so the diff stays inside the declared `files` set. Passed on this satisfied reading; see the warning below.
- ✅ The Verify command passes. — the recorded grep chain exits 0 in the task worktree (Log), and the orchestrator isolate Verify rows record pass, exit 0, twice; the chain is fallible (each grep can fail), so it is real evidence.

Warnings (non-blocking):
- AC4's wording ("touches exactly ... and .project/research/DOCS-AUDIT.md") over-specifies: the queue-row edit was pre-recorded at plan approval (ccd15ff5), so the task landing correctly contains no audit hunk. The AC should say "touches nothing outside the declared files" for future tasks.
- The Log discloses that a first Verify invocation ran in the primary root and exited 1 there (read-only greps against the unedited tree); it was discarded in favor of the worktree run. Honest disclosure, no mutation, but running Verify outside the isolated tree should be avoided.

Contract violations (blocking):
- none

## Intent coverage

### SC3 — SC3 — The M225 validation residual is closed natively: the battery records a filled `tested_source_revision`, the source pin is re-bound to the exact validation HEAD, native validation is re-run and an honest verdict (with its measurement class) is recorded; S02 code is unchanged.: pass
- ✅ Closed natively by T004 at e776fc5c: the battery pin is the full 40-hex `61effa6efe68df1efff2c71f4bd39c4b701e434c` — the exact HEAD the recorded native re-validation ran at (worker and orchestrator Verify rows both state HEAD 61effa6e on gsd-path-task/T004); the rerun record re-ran the hermetic validation surface natively (9 hermetic re-runs recorded with commands and exit codes) and the verdict states its measurement class; no `crates/` path changes in the landing diff, so S02 code is unchanged.
- ✅ E3 (held-out, tests/test_m225_validation_residual.py): recorded output `5 passed` — worker r2 `5 passed in 0.29s`, orchestrator isolate Verify `5 passed in 0.24s`, exit 0; the suite asserts the pin is a full 40-hex SHA bound to the exact re-validation HEAD and fails on any placeholder revert, so a mismatch would invalidate the battery mechanically.
- ✅ N1 (SC3 prohibition): the recorded verdict is `hermetic-pass-parity-unproven` with measurement class `hermetic-observability-corpus-absent`; the corpus-bound battery checks are dispositioned `skipped-corpus-absent` (including the m217 pytest battery, whose corpus-bound test's fail-closed exit 3 without the corpus is recorded as a skip, not a pass), and the statement says green here does not prove corpus scenarios ran. No corpus-absent hermetic green run is recorded as a byte-parity PASS.

### SC4 — SC4 — `product-model/` exists with a minimal PDD model of the already established product behavior (stubs modeled as stubs, nothing aspirational); the PDD statements in AGENTS.md and docs/agent-stack/WORKFLOW.md are true (audit #6/#19).: pass
- ✅ Created by T005 at ab0286e4: 28 tracked model files covering the four law-nexus-inspect subcommands with 9 scenarios, entities, interfaces, and business rules; AGENTS.md:262 and docs/agent-stack/WORKFLOW.md:14 claims are true with no edits to either file.
- ✅ E4/N5 (minimal = existing observable behavior only; stubs stay stubs): prose re-read at ab0286e4 — StubEmbedding modeled as the fail-closed stub it is (named in product.md limitations, inspect-document, the retrieval rule, and a scenario step), stores recorded in-memory and non-persistent, retrieval deterministic non-semantic; no RuVector, live retrieval stack, corpus ingestion, or planned persistence anywhere in the model; the runner belt is excluded as evidence tooling and unmapped crates are disclosed as unmapped.

### SC5 — SC5 — GitNexus is re-indexed and the tool block in AGENTS.md matches the live index (audit #9).: pass
- ✅ Re-indexed by T006 at 55ec0072: the tracked analyze command ran in the primary worktree on gsd-path/M001 (exit 0); the AGENTS.md tool block now states 43047 symbols / 102234 relationships / 584 execution flows, matching the tool-written index metadata that the tracked receipt pins, and the block's sha256 equals the receipt's recorded hash (recomputed independently at 55ec0072). The machine-local .gitnexus/ index is untracked by design; the tracked receipt (schema `law-nexus/gitnexus-index-receipt/v1`) is the sidecar-checkable carrier of the live-index state, so the block-vs-index match is mechanically checkable after landing.
- ✅ E5 (held-out, tests/test_gitnexus_block_receipt.py): recorded output `4 passed` — worker `4 passed in 0.27s` at HEAD 2a0ead24e812aba07b6e0e72897ae54eed35106e on gsd-path/M001, orchestrator sidecar Verify `4 passed in 1.20s`, exit 0; the suite enforces the failure path by construction (a failed analyze leaves the previous block and receipt untouched and hash-consistent, and a hand-edited block breaks the hash equality).
- ✅ N6 (SC5 prohibition): the block was produced by the tool, not hand-edited — the AGENTS.md hunk touches only the gitnexus block, the block hash equals the tool-run receipt, and the Log states the coder never edited the block region; the stale 23577/50919/568 block is replaced by the live-index counts, not presented as live.

## Fixed since last cycle

- No criterion failed in cycle 1 (wave verdict pass, no failed findings); the cycle-2 re-gate exists because the cycle-1 review artifact itself failed the canonical format gate: its Intent-coverage headings repeated the `SCn —` id prefix inside the criterion text (`### SC3 — SC3 — ...`), so the heading's middle text did not equal the INTENT criterion. Confirmed fixed in this file: the three headings re-emitted single-line with the criterion text only, verified character-equal to INTENT.md `## Success criteria` with whitespace collapsed. All task and SC verdicts re-checked from the same landing commits (re-verified directly: battery and rerun record parsed and compared to base, marker sweep over product-model/ re-run, block sha256 independently recomputed, README/audit re-read); no regressions — all wave-2 landed artifacts also spot-checked intact at the review HEAD cc57376b.

## Summary for orchestrator

- blocked findings: none
- repeat offenders: none — no criterion failed in either cycle; the only prior defect was the cycle-1 artifact's Intent-coverage heading format, corrected here.
- warnings worth a human eye:
  - T010 AC4 wording over-specifies the audit hunk (see T010 warnings); tighten the AC template for queue-row ride-alongs.
  - T010 Log records a discarded first Verify run in the primary root (read-only, disclosed); workers should run Verify only inside the isolated tree.
  - T006 AC3 is satisfied via the preflight check's decision inputs (commit match, no metadata-missing warning) rather than a green stock preflight line, which was unobtainable mid-task on a dirty tree; the Log discloses this fully.
  - Landing subjects use the `T###: <task title>` form, not strict Conventional Commits `type(scope): subject`. This is the branch-wide isolation-landing convention since wave 1 (T001-T003 identical, review-passed at 61effa6), and subjects are English; flagging only so the owner can decide whether the landing tool's format is the sanctioned reading of the INTENT constraint.
