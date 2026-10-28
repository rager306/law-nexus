# Review — wave 1, cycle 1

<!-- Reviewer role, wave mode (full). PLAN.md Wave 1 Review depth is `full`, so no
     lens applies.

     SIDECAR HEAD: c036d6b16c6db3904b3ccf7a577c49d3f0e40f95, branch
     gsd-path-verify/wave-1-cycle-1 (gitdir
     /root/law-nexus/.git/worktrees/wave-1-cycle-1), tracked tree clean. Both
     task landings are in it: T001 bb7c5a011803fbfac0a3fb343ebe64d488b2cf2f on
     base eac6fd994565c0a39717a6bed2bfa2bd2dfb122f; T002
     c036d6b16c6db3904b3ccf7a577c49d3f0e40f95 on base
     bb7c5a011803fbfac0a3fb343ebe64d488b2cf2f. The tasks touch disjoint files
     (T001: workflow + pin test; T002: projection + roadmap), so the sidecar tree
     equals base + T001 patch + T002 patch and no task product had to be
     reconstructed separately.

     METHOD. `git diff eac6fd99..c036d6b1` = 6 files, +60/-19:
     `.github/workflows/repository-quality.yml` +2/-0,
     `tests/test_ci_runtime_restore.py` +20/-0,
     `prd/project-state/data/roadmap.json` +1/-1,
     `prd/project-state/roadmap.md` +11/-11, and both task files (frontmatter +
     append-only Log). Recorded orchestrator Verify reused as-is, never re-run:
     T001 Log — sidecar gsd-path-verify/task-t001-verify, exit 0, `1 passed, 16
     deselected`; T002 Log — sidecar gsd-path-verify/task-t002-verify, exit 0,
     `5 passed, 5 skipped`.

     Independent re-runs of my own, only where the recorded output plus the
     isolated diff could not check the criterion (E1, E2, N1, N2/N3, SC1–SC3),
     each inside this sidecar and each followed by `git status --porcelain`
     showing only the staged review directory:
       1. SC3 command on the reviewed tree: `28 passed, 5 skipped`, exit 0.
       2. Held-out E1, mutation A — delete the `tests/test_post_ship_pointers.py`
          line from the suite list: `test_ci_runs_the_post_ship_pointer_suites`
          fails, `AssertionError: tests/test_post_ship_pointers.py must run in
          CI`.
       3. Held-out E1, mutation B — delete the
          `tests/test_project_state_roadmap_freshness.py` line: the same test
          fails naming that suite. The pin is symmetric.
       4. N1 — suite-list diff base vs head: 20 suites -> 22, removed = none,
          added = exactly the two pointer suites, the 20 pre-existing entries
          keep their order.
       5. E2 — `current_milestone.id` set to the stale `ci-fixture-fix`: 2 failed
          (pointer suite + freshness suite); set to `""`: 2 failed; the
          `current_milestone` key deleted: 2 failed, `KeyError:
          'current_milestone'`. Loud on all three shapes.
       6. Landing simulation A — STATE.md at the M007 shipped surface
          (`milestone: ci-proof-inputs`, `phase: shipped`, `status: done`):
          `11 passed, 5 skipped`.
       7. Landing simulation B — same shipped STATE.md plus the pre-fix
          `ci-fixture-fix` projection: the two pointer suites fail. So the
          refreshed projection is exactly what the shipped STATE.md demands and
          the pre-fix projection now fails the CI-listed suites.
       8. Drift replay — restore the real M007 ship surface from `e311f0ed`
          (STATE.md, roadmap.json, roadmap.md) under the new CI suite list: the
          same two tests fail (`test_roadmap_json_current_milestone_tracks_the_latest_archive`,
          `test_native_marker_names_the_operational_milestone`). The exact drift
          that was found by hand after the M007 integration now fails CI.
       9. Regression sweep of the other suites that read the projection and the
          workflow: `tests/test_repository_quality_gate.py` 5 passed; governor +
          preflight 267 passed, 2 skipped; architecture-closure-roadmap +
          branch_context + workflow_state + documentation_navigation + governor
          328 passed, 2 skipped.
      10. Ledger cross-checks: tag `milestone/007-ci-proof-inputs` exists; ship
          `e311f0ed` and integration merge `50386e26` are real and are what the
          M007 MANIFEST records; the superseded `ci-fixture-fix` clause cites the
          real M005 ship `e890831e` and merge `121a2006`. -->

Wave verdict: pass
Cycle: 1
Depth: full
Tasks reviewed: 2

## T001 — Run the pointer suites in CI: pass

- ✅ Both pointer suites run in CI, so a stale projection fails a job (E1: a list that omits either fails the pin). — `.github/workflows/repository-quality.yml:150-154` puts `tests/test_post_ship_pointers.py` and `tests/test_project_state_roadmap_freshness.py` at the head of the `Product and architecture harness tests` run block in `rust-harness-quality`; that job sets no `continue-on-error` and the step has no `continue-on-error`/`if`, so a non-zero pytest exit fails the job. `tests/test_ci_runtime_restore.py:277-294` pins both names inside that exact step's run text. Held-out E1 reproduced twice here: dropping either line makes `test_ci_runs_the_post_ship_pointer_suites` fail naming the missing suite; the unmutated file passes. Recorded orchestrator Verify (exit 0, `1 passed, 16 deselected`) is consistent.
- ✅ No suite is removed from the list to make it pass (N1). — Suite-list diff base `eac6fd99` -> head: 20 suites before, 22 after, `removed: set()`, `added: {tests/test_post_ship_pointers.py, tests/test_project_state_roadmap_freshness.py}`, and the 20 pre-existing entries keep their order. No pin was deleted or loosened: `git diff eac6fd99..bb7c5a01 -- tests/test_ci_runtime_restore.py` is pure addition (+20/-0), and `tests/test_repository_quality_gate.py`'s own `CI_PROCESS_SUITE` expectations still pass (5 passed).

Warnings (non-blocking):
- The two added suites are not registered in `prd/migration/decommission/repository-quality-gate.json` `ci_process_suite`. `tests/test_repository_quality_gate.py` compares that inventory to the workflow in one direction only (inventory -> workflow), so the new CI entries are pinned by `tests/test_ci_runtime_restore.py` but not by the inventory ledger. SC1/N1 do not require it; the two pins can still drift apart.
- The new pin reads the step's run block as text, so a suite named inside a comment of the same `>-` scalar would satisfy it. Weak but harmless for a single-invocation block.

Contract violations (blocking):
- none — the commit touches `.github/workflows/repository-quality.yml` and `tests/test_ci_runtime_restore.py` (both declared in `files`) plus its own task file, where only the orchestrator-owned `status`/`agent`/`base` fields and an append-only `## Log` entry changed; Context, Approach, Interface contract, Intent coverage, Acceptance criteria and Verify are byte-identical.

## T002 — Refresh the roadmap projection to the shipped milestone: pass

- ✅ The projection names the shipped STATE.md milestone in both roadmap.json and the live marker (E2 loud failure on an absent id). — `prd/project-state/data/roadmap.json:615` now reads `"id": "ci-proof-inputs"` (status stays `"active"`) and `prd/project-state/roadmap.md:50` is the live bullet `- **Local GSD workflow marker:** ci-proof-inputs is the current milestone —`. `ci-proof-inputs` is exactly `.project/STATE.md`'s milestone at the M007 ship `e311f0ed` and integration `50386e26`, and the slug of the highest archive `.project/archive/007-ci-proof-inputs`; the bullet's recorded facts (`e311f0ed`, `50386e26`, tag `milestone/007-ci-proof-inputs`, archive path) all check out against git. On the shipped/done landing simulation the pointer suites are `11 passed, 5 skipped`. Held-out E2 reproduced as loud failures on all three absent-id shapes: stale id, empty id, and a missing `current_milestone` key (`KeyError`).
- ✅ No test is edited to accept the stale projection (N2, N3). — `git diff bb7c5a01..c036d6b1 -- tests/` is empty, and the whole wave changes only the one new T001 pin file under `tests/`. No assertion was relaxed: the archive-keyed assertion at `tests/test_post_ship_pointers.py:85-93` still demands `current_milestone == {id: <latest archive slug>, status: "active"}` exactly, which is why the stale id fails. The three-file SC3 command reports 0 failures on the reviewed tree.

Warnings (non-blocking):
- The refresh re-words the live bullet to name the in-flight `pointer-in-ci` milestone and folds the `ci-fixture-fix` record into an inline `Superseded bullet (2026-10-28)` clause instead of a separate dated bullet. That matches the archive-keyed contract the suites enforce and no test pins the M005/M006 bullets, but the `005-ci-fixture-fix` ship/merge/tag/archive line disappears and the `006-red-ci-clear` ship is not recorded at all, so the marker history is no longer uniform with its siblings.
- `prd/project-state/roadmap.md:60` still names `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` as the current-state document, but that file's shipped-milestone table stops at M003 and its CI table stops at the M003 run. Dated context, not a pinned assertion, and SC2 does not own it — worth a refresh so the pointer chain does not go stale again.

Contract violations (blocking):
- none — the commit touches `prd/project-state/data/roadmap.json`, `prd/project-state/roadmap.md` (both declared in `files`) and its own task file, whose change is orchestrator-owned frontmatter plus an append-only Log entry with a byte-identical contract body.

## Intent coverage

### SC1 — SC1 — The CI suite list runs both pointer suites, so a projection that disagrees with the shipped STATE.md fails a job instead of reaching main.: pass
- ✅ Both suites are in the CI list at `.github/workflows/repository-quality.yml:153-154` inside the non-optional `Product and architecture harness tests` step of `rust-harness-quality`, and `tests/test_ci_runtime_restore.py:294` fails when either is dropped (verified by two mutations). The consequence is real, not just a listing: replaying the actual M007 ship surface from `e311f0ed` under the new list fails both suites, and the shipped/done landing simulation with the pre-fix id also fails them, so the drift now fails a job instead of being rediscovered by hand. The two drift pins run in CI rather than skip: the archive-keyed pointer test needs only the tracked roadmap, and `test_native_marker_names_the_operational_milestone` needs only the tracked `.project/STATE.md` — in the sidecar run both PASSED while the five `.gsd`-dependent legacy tests skipped, and the gitignored `.gsd` ledger is absent in CI. Held-out E1 — "A CI suite list that omits either pointer suite fails the pin that names them." — held for both omissions. Prohibition N1 — "remove a suite from the CI list to make it pass" — held: 0 suites removed, 2 added, order preserved.

### SC2 — SC2 — The tracked projection names the shipped milestone: `roadmap.json` `current_milestone.id` equals the milestone in `.project/STATE.md`, and the live marker bullet in `roadmap.md` names the same slug.: pass
- ✅ `roadmap.json` `current_milestone.id` = `ci-proof-inputs` (`prd/project-state/data/roadmap.json:615`) and the single live marker bullet at `prd/project-state/roadmap.md:50` names `ci-proof-inputs`; the shipped STATE.md milestone at the M007 ship and integration is `ci-proof-inputs` (`git show e311f0ed:.project/STATE.md`, `git show 50386e26:.project/STATE.md`), and `007-ci-proof-inputs` is the highest archive — the anchor both suites enforce. The shipped/done landing simulation is `11 passed, 5 skipped`. Held-out E2 — "A projection whose `current_milestone.id` is absent or empty fails the freshness test loudly." — held for stale, empty and missing-key shapes (2 failed each; `KeyError` for the missing key). Prohibition N2 — "edit a test to accept the stale projection" — held: T002 changes no test file and the stale id still fails the unchanged assertions.

### SC3 — SC3 — `uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py tests/test_ci_runtime_restore.py -q` reports 0 failures on the bound branch.: pass
- ✅ `uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py tests/test_ci_runtime_restore.py -q` on the reviewed sidecar tree (HEAD `c036d6b1`): `28 passed, 5 skipped`, exit 0. The 5 skips are the legacy-`.gsd`-only freshness guards, consistent with the recorded T002 Verify (`5 passed, 5 skipped`); with a `.gsd` symlink present the same file stays green, so they are skip-consistent and not newly silenced. Prohibition N3 — no skip or xfail added: `git diff eac6fd99..c036d6b1` introduces no `skip`/`xfail` marker into any pointer test.

## Summary for orchestrator

- blocked findings: none
- repeat offenders: none (cycle 1)
- warnings worth a human eye: (a) the two new CI suites are pinned by `tests/test_ci_runtime_restore.py` but absent from `prd/migration/decommission/repository-quality-gate.json` `ci_process_suite`, whose comparison with the workflow is one-directional; (b) the refreshed live marker bullet absorbs the `ci-fixture-fix` record into an inline clause and drops the `005` ship/merge/tag/archive detail, leaving `006-red-ci-clear` unrecorded, so the dated superseded-bullet history is no longer uniform; (c) `prd/project-state/roadmap.md:60` still points at `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md`, whose shipped-milestone table stops at M003; (d) the bundled `review_findings.py collect --wave 1 --cycle 1` exits non-zero on this milestone with `PLAN.md has no ## Config section`, which is a PLAN.md gap rather than a task defect (milestones 003-007 shipped with the same shape).
