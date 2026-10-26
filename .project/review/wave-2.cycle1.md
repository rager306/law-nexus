# Review — wave 2, cycle 1

Wave verdict: pass
Cycle: 1
Depth: full
Tasks reviewed: 4

<!-- Review method: each task judged on its isolated product — the recorded
     base plus only the complete patch from `commit^..commit` for its declared
     product files, reconstructed and verified byte-equal to the landing; the
     orchestrator's recorded isolated Verify output in each task Log is the
     Verify evidence. No task Verify or project Verify was re-run. -->

## T004 — Close the M225 validation residual with an honest re-run: pass

- ✅ tested_source_revision in the battery is a full 40-hex SHA — the exact HEAD the re-validation ran at — and the placeholder string is gone; the role text states the 40-hex-HEAD semantics (E3). — battery line 5 in the isolated product reads `"tested_source_revision": "61effa6efe68df1efff2c71f4bd39c4b701e434c"` (regex-verified 40-hex); `pending-fill-by-validate-unit` is absent from the whole file; role text at line 6 states the "Full 40-hex git SHA of the exact HEAD" E3 semantics; the task Log and the record's environment block both pin the re-validation run at that exact HEAD (captured via `git rev-parse HEAD` before validating, branch gsd-path-task/T004).
- ✅ The 15 historical check entries of the battery are byte-identical to their recorded state; only the pin, its role text, and the environment annotation changed. — the battery diff `e776fc5c^..e776fc5c` is a single hunk touching exactly the pin, the role text, and the additive `environment.native_rerun_m001` annotation; structural compare of the `checks` array between base and landing is identical (15 entries), so the historical entries are byte-identical by diff.
- ✅ The rerun record exists at prd/migration/rust-evidence/m225-validation-rerun-m001.json, covers every battery check id with an explicit disposition from the fixed set, and its verdict states the measurement class — a hermetic run is not a byte-parity PASS (N1), and corpus parity evidence remains the pinned 2026-10-18 corpus-present run. — `prd/migration/rust-evidence/m225-validation-rerun-m001.json` exists in the isolated product; 15/15 battery check ids covered exactly once with dispositions 9 re-run-passed-hermetic / 4 skipped-corpus-absent / 2 not-rerun-environment-gated, all inside the fixed set; verdict at lines 133-140: status `hermetic-pass-parity-unproven`, `measurement_class: hermetic-observability-corpus-absent`, statement says the run "is hermetic observability, not a byte-parity PASS (INTENT N1)" and keeps corpus parity with the pinned 2026-10-18 corpus-present run at HEAD e4f6c81a; `non_claims` repeats "No corpus scenario ran".
- ✅ No file under crates/ changes (S02 untouched); the landing diff touches exactly the three declared paths. — landing paths `e776fc5c^..e776fc5c` are the assigned task file plus exactly the three declared paths; no `crates/` path appears anywhere in the landing.
- ✅ tests/test_m225_validation_residual.py pins criteria 1 and 3 mechanically and fails if the residual were reverted to the placeholder. — `tests/test_m225_validation_residual.py` asserts the 40-hex regex and placeholder absence (reverting the pin trips both), same revision across battery and record, exact check-id coverage with fixed-set dispositions, and the measurement-class disclaimers (test lines 26-70); recorded Verify 5 passed, exit 0, at HEAD 61effa6e, plus recorded orchestrator isolate Verify pass, exit 0 (`5 passed in 0.23s`, and again after the formatting-only r2: `5 passed in 0.24s`).

Warnings (non-blocking):
- The two environment-gated dispositions (`operational-governor`, `operational-preflight`: not-rerun-environment-gated) are honest and pre-declared by the task Approach — the governor is branch-locked and fails closed in an isolate by design — but their supporting evidence is the orchestrator's bound-branch governor run at the wave gate; that run must actually be recorded for the discharge to hold.
- "The exact HEAD the re-validation ran at" rests on the worker's recorded capture (Log and record agree on 61effa6e; the record's own edits were written after the runs); per mode rules the recorded output plus the isolated diff is the evidence, so this is a recorded-claim note, not a defect.

Contract violations (blocking):
- none

## T005 — Create the minimal PDD product model: pass

- ✅ product-model/ exists in the tracked tree with the PDD layout core — README.md, config.yaml, the product file, coverage.md, at least one interface, its capabilities with scenarios, and entities — following the bundled format reference shapes. — the isolated landing carries the layout core under `product-model/`: README.md, config.yaml, product.md, coverage.md, `interfaces/terminal/interface.md` (type cli, plus 2 screens), 4 capabilities (`check-health`, `inspect-document`, `replay-edition`, `resolve-subordinates`) with 9 scenarios, 2 entities, 4 business rules, taxonomies.yaml; the recorded pinned pdd lint (pdd-toolkit 0.37.1) returned `ok: true` with counts interfaces 1 / screens 2 / entities 2 / capabilities 4 / capabilityScenarios 9 / businessRules 4.
- ✅ The model records only established observable behavior: StubEmbedding is named as the fail-closed stub it is and the stores are recorded as in-memory; no capability claims live embeddings, persistent storage, or corpus behavior (E4, N5 — review judges the prose, the test pins the markers). — prose re-read (E4, N5): StubEmbedding is named "the fail-closed stub of the embedding port" in product.md and the inspect-document capability; stores recorded in-memory throughout; a full-text grep over the model finds zero hits for RuVector, TEI, FalkorDB, persistent, persistence, planned, future, roadmap — the only "corpus" hits are explicit non-claims; the test forbids `TEI`/`RuVector`/`FalkorDB`/`SQLite`/`persist`/`semantic embedding` under capabilities/ (tests/test_product_model.py:35).
- ✅ The PDD statements in AGENTS.md and docs/agent-stack/WORKFLOW.md are true with no edits to those files — the directory and the model now exist. — the landing `ab0286e4^..ab0286e4` touches neither AGENTS.md nor docs/agent-stack/WORKFLOW.md; both files' PDD claims ("Product behavior: PDD Kit in `product-model/`"; the WORKFLOW description row naming `product-model/`) are true now that the directory and model exist.
- ✅ The pdd lint output, or its unavailability on the host, is recorded in the task Log; the tracked test passes with no host-only tooling. — the task Log records the lint output in full (`ok: true`, errors empty, one assessed-and-kept noun-phrase warning on `replay-edition`, cross-checked against the host-pinned 0.37.1 CLI); the tracked test reads only repository files and passes with no host-only tooling — recorded Verify 4 passed, exit 0, plus recorded orchestrator isolate Verify pass, exit 0 (`4 passed in 0.30s`).
- ✅ tests/test_product_model.py pins criteria 1 and 2 mechanically and fails if the model directory is absent or stripped of the stub markers. — the test pins the layout core, the interface/capability/scenario/entity structure, and the stub and in-memory markers; the Log records negative-path runs (model dir absent raises "product-model/ must exist in the tracked tree"; StubEmbedding mentions stripped raises "the model must name StubEmbedding"), so stripped markers fail it.

Warnings (non-blocking):
- none

Contract violations (blocking):
- none

## T006 — Re-index GitNexus and regenerate the AGENTS.md tool block: pass

- ✅ The index is rebuilt with the tracked command in the primary worktree on gsd-path/M001, and prd/project-state/data/gitnexus-index.json records the command, a full 40-hex indexed head, the counts, the timestamp, and the sha256 of the AGENTS.md block between the gitnexus markers. — `prd/project-state/data/gitnexus-index.json` in the isolated product records the exact tracked command `node .gitnexus/run.cjs analyze --force --name law-nexus`, indexed_head `2a0ead24e812aba07b6e0e72897ae54eed35106e` (regex-verified 40-hex, equal to the analyze HEAD and the recorded base), counts symbols 43047 / relationships 102234 / execution_flows 584, generated_at 2026-10-26T10:53:09.705Z, and the block sha256; the Log records the documented bunx bootstrap (index tree was absent) followed by the tracked `--force` run, exit 0, in the primary worktree on the bound branch.
- ✅ The AGENTS.md tool block between the gitnexus markers matches the receipt — equal hash, counts present, repo name law-nexus — and was produced by the tool, not by hand (E5, N6: on analyze failure the previous block and receipt stay untouched and consistent, and the error is reported, never hand-patched away). — I recomputed the sha256 of the block between `<!-- gitnexus:start -->` and `<!-- gitnexus:end -->` (markers included) from the isolated AGENTS.md: `896a95033fdd8b45e8f67f465132cb2b22bd632ddd5d676622c4d5bfa01a328f` — equal to the receipt (receipt line 11); the counts 43047/102234/584 and `**law-nexus**` appear in the block (AGENTS.md lines 341-344); the AGENTS.md diff is a single hunk entirely inside the block region, i.e. the tool's own rewrite, never hand-edited (E5, N6).
- ✅ The task Log records the preflight gitnexus-index-freshness result at the analyze HEAD showing a match with no metadata-missing warning, and states the expected one-commit drift after landing. — the task Log entry "preflight gitnexus-index-freshness record (AC3)" records the stock preflight entry at the analyze HEAD (warn via the early return on a non-empty `git status` from this task's own in-flight edits), then verifies the check's decision inputs on the identical fields: `.gitnexus/meta.json` present and parsing, `lastCommit` == `git rev-parse HEAD` == 2a0ead24 — commit match, no metadata-missing warning, no commit-mismatch warning — and states the expected one-commit post-landing drift with the receipt pinning the analyzed revision.
- ✅ tests/test_gitnexus_block_receipt.py pins criteria 1 and 2 mechanically and fails if the receipt is absent or the block changed without the tool. — `tests/test_gitnexus_block_receipt.py` pins the receipt schema/command/40-hex head/timestamp, the block-hash equality (a hand-edited block or stale receipt fails it), counts-in-block, and the repo name (test lines 30-68); recorded Verify 4 passed, exit 0, plus recorded orchestrator sidecar Verify pass, exit 0 (`4 passed in 1.20s`).

Warnings (non-blocking):
- Preflight will legitimately print `gitnexus-index-freshness warn` after this landing (one commit behind by construction, anticipated by AC3) until the documented re-index runs again; a later warn line is expected machine-local drift, not a regression.

Contract violations (blocking):
- none

## T010 — Reword the corpus-glob-guard claim in law-source/consultant/README.md: pass

- ✅ law-source/consultant/README.md no longer contains the string `law-source-corpus-glob-guard`; the rule-4 claim names only `law-source-fixture-guard` and states that this check covers the README fixture-vault marker, not corpus globbing. — the isolated README no longer contains `law-source-corpus-glob-guard` (grep); the rule-4 claim (README lines 34-38) names `law-source-fixture-guard` and states it covers only the fixture-vault README marker plus the `.deprecated/` gitignore state, that corpus globbing is not detected, and that treating the directory as a corpus source remains a review-time defect under rule 4 itself; a re-read of `check_law_source_fixture_guard` at the landing commit confirms exactly that coverage (marker substrings plus `.deprecated/` state, no glob detection).
- ✅ The marker substrings `НЕ КОРПУС`, `consru_export`, and `43 785` remain in the README, so `check_law_source_fixture_guard`'s marker test still passes; no other README line changed. — the README diff is a single hunk (4 insertions, 1 deletion) at the rule-4 claim; `НЕ КОРПУС`, `consru_export`, and `43 785` are all present in the isolated README, and the guard's `marker_ok` requires exactly those three substrings, so its marker test inputs are unchanged.
- ✅ .project/research/DOCS-AUDIT.md User rulings row 16 shows Planned `T010`; the rest of the audit file is unchanged. — audit row 16 in the isolated product reads `| 16 | fix-doc | ... | T010 |` (Planned cell `T010`); the landing contains zero hunks for `.project/research/DOCS-AUDIT.md`, so the rest of the audit is unchanged.
- ✅ The landing diff touches exactly law-source/consultant/README.md and .project/research/DOCS-AUDIT.md. — landing paths `64a7d88f^..64a7d88f` are law-source/consultant/README.md plus the assigned task file only; DOCS-AUDIT.md required no edit because the orchestrator recorded row 16 Planned=`T010` pre-dispatch and it already read `T010` at the recorded base 61effa6e — the required AC3 end state holds in the isolated product and nothing outside the declared pair changed; no code, no new probe, no test harness changes.
- ✅ The Verify command passes. — recorded orchestrator Verify (isolate gsd-path-task/T010): pass, exit 0, twice; every clause of the Verify chain re-verified by hand in the isolate (forbidden string absent, `law-source-fixture-guard` present, `НЕ КОРПУС` present, row-16 regex matches).

Warnings (non-blocking):
- AC4's letter says the landing "touches exactly" README.md and DOCS-AUDIT.md; the landing deliberately touches only README.md plus the task file because the audit row was recorded pre-dispatch at base. The satisfied reading — no change outside the declared pair, required end state reached — passes; the criterion needs tightening for any successor task.

Contract violations (blocking):
- none

## Intent coverage

### SC3 — The M225 validation residual is closed natively: the battery records a filled `tested_source_revision`, the source pin is re-bound to the exact validation HEAD, native validation is re-run and an honest verdict (with its measurement class) is recorded; S02 code is unchanged.: pass
- ✅ battery pin filled with `61effa6efe68df1efff2c71f4bd39c4b701e434c` (40-hex, battery line 5) and the role text re-bound to the exact-HEAD semantics; native validation re-run with real captured outputs and per-check dispositions in the new rerun record; honest verdict recorded with `measurement_class: hermetic-observability-corpus-absent` and status `hermetic-pass-parity-unproven` (rerun JSON lines 133-140); S02 code unchanged (no `crates/` path in the landing).
- ✅ E3 held-out: `tests/test_m225_validation_residual.py` — recorded orchestrator isolate output `5 passed`, exit 0 (pins the 40-hex pin, placeholder absence, and same-revision across battery and record); the pin equals the recorded re-validation HEAD, so no mismatch invalidates the battery.
- ✅ N1 judgment: no corpus-absent hermetic green is recorded as a byte-parity PASS — the verdict's own statement says "This re-run is hermetic observability, not a byte-parity PASS (INTENT N1)", the 4 corpus-bound checks are recorded `skipped-corpus-absent`, and `non_claims` bars the green results from strengthening the 2026-10-18 parity claims.

### SC4 — `product-model/` exists with a minimal PDD model of the already established product behavior (stubs modeled as stubs, nothing aspirational); the PDD statements in AGENTS.md and docs/agent-stack/WORKFLOW.md are true (audit #6/#19).: pass
- ✅ `product-model/` exists in the tracked tree at the landing with the PDD layout core; the model maps only established observable behavior of `law-nexus-inspect` (four subcommands, in-memory stores, fail-closed StubEmbedding, explicit non-claims); recorded pinned lint `ok: true`; aspirational-term grep over the whole model is clean.
- ✅ E4 judgment (minimal = existing observable behavior only): coverage.md scopes the model to `crates/ln-product-cli/` and `crates/ln-storage/`, excludes the hc01-hc20 runner belt as evidence tooling and `src/`+`scripts/` as control plane, and honestly lists unmapped crates and registry-backed-path limitations instead of asserting them.
- ✅ N5 judgment: no desired or future behavior anywhere in the model (zero hits for RuVector, TEI, persistence, planned, future, roadmap); AGENTS.md and docs/agent-stack/WORKFLOW.md are untouched by the landing and their PDD claims are now true (audit #6/#19).

### SC5 — GitNexus is re-indexed and the tool block in AGENTS.md matches the live index (audit #9).: pass
- ✅ the index was rebuilt with the tracked command in the primary worktree on the bound branch (Log, exit 0), and the receipt records the command, a full 40-hex indexed head equal to the analyze HEAD, the counts, the timestamp, and the block sha256; the regenerated block names 43047 symbols / 102234 relationships / 584 execution flows, matching the receipt and replacing the stale 23577/50919/568 line.
- ✅ recomputed block hash equals the receipt hash (N6: the block is tool-produced and hand edits are detectable by the hash pin); the AGENTS.md diff is confined to the block between the gitnexus markers.
- ✅ E5 held-out: `tests/test_gitnexus_block_receipt.py` — recorded orchestrator sidecar output `4 passed`, exit 0 (receipt presence, schema, 40-hex head, block-hash equality, counts-in-block, repo name); on a failed analyze the previous block and receipt stay untouched and hash-consistent by construction.

## Summary for orchestrator

- blocked findings: none
- repeat offenders: none (first review cycle for this wave)
- warnings worth a human eye:
  - T004: the two `not-rerun-environment-gated` battery checks (governor, preflight) are discharged only by the orchestrator's bound-branch governor run at the wave gate — record that run.
  - T006: post-landing preflight `gitnexus-index-freshness warn` (one-commit drift) is expected by construction until the next documented re-index; do not read it as a regression.
  - T010: AC4's wording ("touches exactly ... and DOCS-AUDIT.md") did not anticipate the pre-dispatch orchestrator row recording; tighten the criterion if a successor task ever re-uses this pattern.
