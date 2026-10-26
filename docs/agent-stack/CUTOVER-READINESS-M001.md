# M001 cutover readiness assessment (SC8)

- Milestone: `001-native-workflow-acceptance`
- Branch: `gsd-path/M001`, assessment written at base `6eb3133e` (task T009, revision r2)
- Date: 2026-10-26
- Author: build_T009 (coder, corrected contract)
- Ruling applied: owner decision «(a)» 2026-10-26 (`INTENT.md ## Corrections`) — publication and
  CI are ship-phase-gated; this assessment records both as **pending-ship**, performs no push and
  no CI watch.

SC8 produces this written readiness assessment only; cutover (C7) is not flipped — `cutover` stays
`false` (N2). Every verdict cites evidence already recorded under `.project/` or in the landing
commits; no task Verify is re-run here except the two cheap read-only re-checks named in place.
The wave reviews read the recorded orchestrator Verify outputs plus the isolated diffs, so a
"recorded" citation below means exactly that evidence chain.

## Readiness summary

| SC | Verdict | Primary evidence |
|----|---------|------------------|
| SC1 | met | T001 landing `9cb5107a`; wave-1 review pass; SC1 suites 0 failures |
| SC2 | met | T002 landing `99abed61`; marker names the slug exactly; governor 0 errors on the bound branch |
| SC3 | met (honest verdict, not a green one) | T004 landing `e776fc5c`; 40-hex pin; verdict `hermetic-pass-parity-unproven` |
| SC4 | met | T005 landing `ab0286e4`; 28-file minimal PDD; stubs modeled as stubs |
| SC5 | met | T006 landing `55ec0072`; GitNexus re-index; receipt-hash-pinned AGENTS.md block |
| SC6 | met on the recorded cycle; wave-3 review verdict pending | T007 landing `105b3d6c`; dispatch receipt, worker, validators, isolated verify sidecar |
| SC7 | met | T008 landing `2ce3b6d7`; `.project/M001-RESUME-PROOF.md` — 4 commands, all exit 0 |
| SC8 | delivered by this document | publication/CI pending-ship (section below) |
| SC9 | met | T003 landing `2e1e3c58`; blocking schema gate with a narrow documented advisory allowlist |
| SC10 | met | T007 landing `105b3d6c`; junk files absent (re-verified at this base) |

## SC1 — the five pre-milestone fixes: met

- Landing commit `9cb5107a` (T001) carries exactly the canonical patch union
  (`dev-profile-strip`, `pre-milestone-phase`, `unclassified-and-brief-contract`, preserved under
  `/root/law-nexus-pre-milestone-fix/`) plus the E1 recovery test; the wave-1 reviewer re-proved
  byte-identity of the landed five-file diff to the verified r2 work patch
  (`.project/review/wave-1.cycle1.md ## T001`).
- The SC1 command `uv run --frozen pytest tests/test_harness_governor.py
  tests/test_phase_dispatch_adapter.py` reports 0 failures on the bound branch: recorded
  orchestrator isolate Verify twice (276 passed, 2 skipped, 0 failed) and the r2 serial run on the
  branch itself (278 passed, 0 failed) at content the review proves byte-identical to the landing
  (task Log `.project/tasks/T001-land-pre-milestone-fixes.md`).
- Held-out edge E1 (concurrency): `tests/test_path_isolation_recovery.py` pins that an interrupted
  task landing recovers only through the isolation helper's `recover` — the helper refuses a
  detached HEAD and reports honest `none`/`resume` verdicts, never a fabricated success; manual git
  repair stays vetoed. The test ran inside both isolate Verify runs.

## SC2 — workflow marker: met

- Landing commit `99abed61` (T002): the live marker bullet at `prd/project-state/roadmap.md:50`
  names `001-native-workflow-acceptance` exactly (full slug, no variant), and the three-way
  identity STATE.md ↔ `roadmap.json` `current_milestone.id` ↔ marker bullet is pinned by
  `tests/test_project_state_roadmap_freshness.py::test_native_marker_names_the_operational_milestone`
  (recorded `1 passed`; re-run at this assessment's base `6eb3133e`: `1 passed, 5 skipped`).
- Governor on `gsd-path/M001` with the milestone set: exit 0, 0 errors, `roadmap-current-tracks-path`
  passing by identity, operational native mode, no pre-milestone exception (recorded in the T002
  Log; the T008 resume run re-recorded 0 errors, 75 checks pass, 0 warns).
- Edge E2 is fail-closed by construction: the native marker test rejects a slug mismatch, a missing
  live bullet, prefix/suffix variants and duplicate live bullets, and the governor's mismatch is a
  blocking error (the baseline run before the sync recorded exactly one such error).
- Judgment N4 observed: the roadmap diff touches only the live marker bullet — a single hunk; no
  M-number, completed milestone row, requirements line, or recorded hash moved (verified by the
  wave-1 review; `roadmap.json` changed only `current_milestone` identity fields).

## SC3 — M225 validation residual: met (honest verdict, not a green one)

- Landing commit `e776fc5c` (T004): the battery's `tested_source_revision` is the full 40-hex SHA
  `61effa6efe68df1efff2c71f4bd39c4b701e434c` — the exact HEAD the native re-validation ran at; the
  `pending-fill-by-validate-unit` placeholder is gone (held-out edge E3; the role text states the
  exact-HEAD semantics).
- Rerun record `prd/migration/rust-evidence/m225-validation-rerun-m001.json`: 15/15 battery check
  ids dispositioned from the fixed set (9 `re-run-passed-hermetic`, 4 `skipped-corpus-absent`,
  2 `not-rerun-environment-gated`); verdict `hermetic-pass-parity-unproven` with
  `measurement_class: hermetic-observability-corpus-absent`.
- Prohibition N1 respected: no corpus-absent hermetic green run is recorded as a byte-parity PASS;
  corpus parity evidence remains the pinned 2026-10-18 corpus-present run. This measurement class
  carries into the CI-policy honesty section below.
- S02 is unchanged: no `crates/` path appears in the landing diff. Pin suite
  `tests/test_m225_validation_residual.py` recorded `5 passed` (worker r2 and orchestrator isolate).

## SC4 — minimal PDD model: met

- Landing commit `ab0286e4` (T005): 28 tracked files under `product-model/` — README, config,
  product, coverage, one interface, 4 capabilities with 9 scenarios, 2 entities, 4 business rules;
  the bundled pinned `pdd-toolkit` 0.37.1 lint recorded `ok: true` (one assessed-and-kept naming
  warning), in the task Log.
- Edges E4/N5 (minimal = existing observable behavior only): StubEmbedding is named the fail-closed
  stub it is; the stores are recorded in-memory and non-persistent; a marker sweep over all 28 files
  found no RuVector/TEI/FalkorDB/live-embedding/persistence/corpus-ingestion claim; unmapped crates
  are disclosed as unmapped.
- The PDD statements in `AGENTS.md` and `docs/agent-stack/WORKFLOW.md` became true with zero edits
  to either file. `tests/test_product_model.py` recorded `4 passed`.

## SC5 — GitNexus re-index: met

- Landing commit `55ec0072` (T006): the tracked command `node .gitnexus/run.cjs analyze --force
  --name law-nexus` ran in the primary worktree on `gsd-path/M001` (exit 0, 123.0s) after the
  documented bunx bootstrap created the missing `.gitnexus/` runner.
- Receipt `prd/project-state/data/gitnexus-index.json` (schema
  `law-nexus/gitnexus-index-receipt/v1`): `indexed_head`
  `2a0ead24e812aba07b6e0e72897ae54eed35106e`, counts 43047 / 102234 / 584, and the AGENTS.md block
  sha256 — independently recomputed by the wave-2 reviewer and equal to the tool-written block.
- Held-out edge E5 and prohibition N6: the block was produced by the tool, never hand-edited; on an
  analyze failure the previous block and receipt stay untouched and consistent (failure path
  enforced by construction in `tests/test_gitnexus_block_receipt.py`, recorded `4 passed`).

## SC6 — full native cycle: met on the recorded cycle; review verdict pending at assessment time

- Landing commit `105b3d6c` (T007, the deliberately trivial SC10 carrier): the recorded cycle is
  the dispatch receipt (`.project/research/dispatch-record-build-T007-2026-10-26.json`), the worker
  (session `01a177f4-38f0-7654-b320-293a746d9f24`), the native validators (governor + preflight on
  `gsd-path/M001`, plus the Verify ledger line), and the orchestrator's authoritative Verify rerun
  in the isolated verify sidecar `gsd-path-verify/task-t007-verify` — five recorded pass/exit-0
  ledger lines (task Log `.project/tasks/T007-native-cycle-junk-deletion.md`).
- Review independence (E6): the isolated sidecar rerun is a different evidence path from the
  worker's own report — the branch SC6 accepts; no same-family re-run is counted anywhere.
- Prohibition N7 (no self-acceptance): the worker does not accept its own task. Its Log names the
  wave-3 independent reviewer, whose separate read-only diff inspection lands its verdict in the
  wave-3 review after this assessment task. Until that verdict is recorded, SC6's review-verdict
  component stays open — the review phase's own gate, listed in the conclusion, not a build defect.

## SC7 — session close/resume: met

- Landing commit `2ce3b6d7` (T008): a fresh session with no chat history resumed from
  `.project/HANDOFF-M001-resume.md` (handoff commit `7791ca6c125005a2d03c1a46b8ffdb8eb9814028`).
  The proof is disk-only (N8): the new session's own recorded verification output, not chat
  history. STATE.md remains the single journaled source and resume is read-only validation, so a
  repeated resume is harmless (E7, dismissed).
- Proof `.project/M001-RESUME-PROOF.md`, four commands, all exit 0: `python3 scripts/ai/path-run.py
  status` (branch `gsd-path/M001`, milestone `001-native-workflow-acceptance`);
  `uv run --frozen python -m law_nexus_harness.governor` (`error_count: 0`, 75 checks pass);
  `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q` (1 passed, 5 skipped);
  `test -z "$(git ls-files a.txt b.txt c.txt)"` (empty).

## SC8 — this assessment; publication and CI are pending-ship

Delivered by this document under the corrected contract. The publication step is intentionally
absent, and the enforcing contract is the repository's own guard, not a convention:

- `.git/hooks/pre-push` executes `.gsd-path/git_guard.py`; the installed runtime guard's
  `pre_push_violations` states the rule: "A bound-named ref moves only to, or away from, its strict
  ship commit." A non-ship push of `gsd-path/M001` is refused with "moves gsd-path/M001 off its
  ship commit; unshipped milestone work reaches a remote only as its ship commit (STATE
  shipped/done) through archive_milestone.py integrate". Verified live: the r1 attempt's recorded
  refusal of `git push origin gsd-path/M001` (task Log, 2026-10-26) — the guard worked exactly as
  designed, and no workaround was attempted.
- `gsd-path/M001` therefore reaches origin only as its ship commit, through ship integration
  (`archive_milestone.py integrate`); STATE.md completion status is `not-shipped` at this base.
- Repository-quality CI triggers on push to `main` and on `pull_request` only
  (`.github/workflows/repository-quality.yml`, `on:` block) — a branch push produces no run. The
  CI acceptance surface is the integrated `main` per the documented M207 policy; CI evidence
  executes at ship integration and is recorded here as pending-ship.
- Held-out edge E8 governs the future ship-phase run: exactly one rerun is allowed for a red CI
  run; persistently red means SC8 is unmet — fix it or document the failure as advisory. The
  machine block pins the pending-ship form: `reruns: 0`, the budget not consumed before ship.

## SC9 — CI policy and payload type-check package: met

- Landing commit `2e1e3c58` (T003): the unconditional `|| true` around the m207 schema check is
  deleted. The replacement step asserts the exit code, keeps output visible via `tee`, and
  tolerates exactly the two documented advisory signatures — `FAIL CORPUS_COUNT_DRIFT: `
  (gitignored corpus absence) and `FAIL S03_RATE_IMPORTED: ` (frozen-token D466/D487) — plus the
  gate's own summary line; any unknown finding, an empty failure log, or an unaccounted failure
  fails the job. Prohibition N3: the diff introduces no unconditional truth fallback and no new
  `continue-on-error`.
- The corpus-integration job comment states the actual setup (hosted `ubuntu-latest` label, corpus
  absent, job skipped unless `vars.LAW_NEXUS_CORPUS_AVAILABLE == '1'`, and nothing in the workflow
  sets the variable); `runs-on`/`if` are byte-identical context lines.
- Held-out edge E9 (boundary): `workflow_state.py` rejects a present optional identity field of the
  wrong type with a typed fail-closed error at all four sites (state.milestone, state.phase,
  route.milestone, route.phase) while accepting missing and null values — regression tests recorded
  `40 passed` three times (r1, r2, finish isolate); the known documented conflicts stay advisory.

## SC10 — junk files: met

- Landing commit `105b3d6c` (T007) deleted `a.txt`, `b.txt`, `c.txt` via `git rm` (staging named by
  the dispatch contract; the landing commit is the orchestrator's); the landing diff touches
  exactly those three files plus the task's `.project/` artifacts. Edge E10 was dismissed by
  intent: the mapper found zero references in scripts, CI, or tests, and deletion is reversible
  through git history.
- Task Verify `test -z "$(git ls-files a.txt b.txt c.txt)" && test ! -e a.txt && test ! -e b.txt
  && test ! -e c.txt` exit 0; independently re-proven by the resume proof's command 4 and re-checked
  at this assessment's base: `git ls-files a.txt b.txt c.txt` is empty and the worktree paths are
  absent.

## CI-policy honesty (N1)

Green CI never proves corpus scenarios ran:

- The M207 batteries are report-only by documented policy — for example the frozen corpus battery
  step runs with `continue-on-error: true` (`.github/workflows/repository-quality.yml`).
- The strict corpus-integration job stays skipped: its guard
  `vars.LAW_NEXUS_CORPUS_AVAILABLE == '1'` is never satisfied, and setting it on a hosted runner
  would fail the strict environment hard instead of proving anything — the workflow comment states
  exactly this.
- Consequently SC3's honest verdict stands as the milestone's corpus statement: measurement class
  `hermetic-observability-corpus-absent`; corpus parity evidence remains the pinned 2026-10-18
  corpus-present run. A green repository-quality run at the future ship integration proves the
  portable surface only.

## Corpus delivery — settled direction, recorded not built

Settled by `.project/research/SYNTHESIS.md` (decisions "Strict corpus job in M001 — SC9 fix shape"
and "Corpus delivery artifact shape") and the owner's exposure ruling 2026-10-26 (verbatim:
«1: runner-only»). For a future milestone; nothing below is built in M001:

1. Restricted self-hosted runner surface: an explicit runner label, never `ubuntu-latest`;
   protected branches only; ephemeral, secret-free runner.
2. Single pinned zstd tarball of `consru_export/consru_export/exports/` (measured 0.30 GiB
   compressed, 3.53 GiB uncompressed, 43,785 XML files, 11.9x compression) with a recorded sha256
   that the consuming job verifies before strict tests run, including after any cache restore.
   Workflow artifacts are never the delivery channel.
3. On-runner layout contract: strict tests resolve `consru_export/consru_export/exports/` under
   the repo root (or `CONSULTANT_EXPORT_DIR`) and hard-fail under `LAW_NEXUS_REQUIRE_CORPUS=1` —
   whichever delivery channel is chosen must materialize exactly that path and let the tests' own
   hard-fail prove delivery.

## Conclusion — cutover remains false

`cutover` stays `false` (prohibition N2; INTENT.md SC8). The milestone proves the native workflow
mechanics end to end; readiness is not cutover:

1. Publication and CI evidence are pending-ship: the bound branch publishes only as its ship
   commit and CI runs on the integrated `main` surface; neither has executed (E8's rerun budget
   untouched at 0).
2. The strict corpus surface has no runner and no delivery channel yet; the settled runner-only
   direction above is recorded, not built, and every corpus claim stays honest to its measurement
   class (N1).
3. SC6's independent-review verdict (the wave-3 review) is scheduled after this assessment task
   and is recorded here as pending at assessment time.
4. Cutover (C7) is an owner decision; this milestone deliberately assesses readiness and does not
   flip it.

```law-nexus/cutover-readiness/v1
{
  "schema": "law-nexus/cutover-readiness/v1",
  "milestone": "001-native-workflow-acceptance",
  "assessment_date": "2026-10-26",
  "assessment_base": "6eb3133e0302317afdf49d7133110d219f15fe07",
  "cutover": false,
  "publication": {
    "status": "pending-ship",
    "enforcing_contract": ".git/hooks/pre-push -> .gsd-path/git_guard.py: the bound branch moves to origin only as its ship commit",
    "path": "ship integration (archive_milestone.py integrate) lands gsd-path/M001 on origin as its ship commit"
  },
  "ci_runs": [
    {
      "surface": "integrated main (repository-quality on push to main and pull_request; M207 policy acceptance surface)",
      "status": "pending-ship",
      "final": null,
      "reruns": 0,
      "advisory_documented": true
    }
  ],
  "corpus_honesty": true
}
```
