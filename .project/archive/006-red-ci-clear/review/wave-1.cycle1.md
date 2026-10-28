# Review — wave 1, cycle 1

<!-- Reviewer role, wave mode (full). Sidecar checkout HEAD recorded per brief:
     f60bef3f97740f2402219bdd3626546818b0ac15 (branch gsd-path-verify/wave-1-cycle-1,
     gitdir /root/law-nexus/.git/worktrees/wave-1-cycle-1).

     METHOD. Both task landings are direct descendants of the recorded bases
     (d276fb3d^ = df819312, f60bef3f^ = d276fb3d), so this sidecar at
     f60bef3f carries base df819312 plus T001's complete patch plus T002's
     complete patch. Diff inspected: `git diff df819312..f60bef3f` = 6 files
     (workflow, pin test, roadmap.json, roadmap.md, both task files).
     Recorded orchestrator Verify reused as-is, never re-run:
       T001 Log — sidecar gsd-path-verify/task-t001-verify, exit 0, `15 passed in 2.74s`.
       T002 Log — sidecar gsd-path-verify/task-t002-verify, exit 0, `5 passed, 5 skipped in 5.17s`.

     Independent re-runs of my own (allowed: the recorded output plus the diff
     could not check the criteria — E1/E2/E3 and the real main-branch behaviour):
       1. SC3 command on a clean clone of the bound branch at f60bef3f, no .gsd:
          `293 passed, 7 skipped`, 0 failed.
       2. Same command at base df819312 on the same kind of clone: `4 failed,
          291 passed, 5 skipped` — the 2 roadmap failures this wave fixes plus
          the pre-existing no-pi-journal pair.
       3. Fresh clone of integrated main (121a2006, origin/main identical, tag
          milestone/005-ci-fixture-fix present, no .gsd): governor exit 0,
          pass_count 72, workflow-state-surface observed
          `kind=shipped-integrated; ... archive .project/archive/005-ci-fixture-fix`.
       4. The landed step body run against that real report with
          GITHUB_REF=refs/heads/main: exit 0. The base (df819312) step body
          against the same report: exit 1, missing
          `.project/archive/001-001-native-workflow-acceptance`.
       5. Same main clone with .project/archive/005-ci-fixture-fix removed:
          governor exit 1, workflow-state-surface fail/error
          (conflicting-ownership), so the step fails — the lying surface still fails. -->

Wave verdict: pass
Cycle: 1
Depth: full
Tasks reviewed: 2

## T001 — Pin the shipped-surface shape in the governor honesty step: pass

- ✅ The step fails when the surface reports shipped-integrated without any archive path, and passes for a later milestone's archive (E1). — Diff `df819312..d276fb3d` on `.github/workflows/repository-quality.yml:264-273` replaces the two-fact loop with two separate fatal assertions: `if "kind=shipped-integrated;" not in observed:` and `if ".project/archive/" not in observed:`, each `sys.exit(...)`. Re-run of the landed heredoc body against a real governor report from a fresh clone of integrated main (`pass_count` 72, archive `.project/archive/005-ci-fixture-fix`): exit 0. Against a report whose observed fact ends `archive absent.`: exit 1 with "governor on main must name the shipped milestone archive". Against `archive .project/archive/006-red-ci-clear` (a later milestone): exit 0. The adapter path was exercised too: `law_nexus_harness.governor.check_workflow_state_surface` driven through `read_workflow_state` with a stub native-status payload for `state_archive` = `.project/archive/005-ci-fixture-fix` and `= .project/archive/006-red-ci-clear` produced `kind=shipped-integrated` findings whose observed fact carries `.project/archive/`, and the step body exited 0 for both. Load-bearing: the base step body against the same real report exits 1.
- ✅ The step still fails when the shipped-integrated shape is missing (N2). — Re-run of the landed heredoc body against a report whose workflow-state-surface finding is `GSD Path workflow state is valid; native status validated STATE.md and routes run-phase.` (operational, no shipped shape): exit 1, "governor on main must report the shipped integrated state". The archive check is not reached, and the shape assertion is a separate `sys.exit` at `.github/workflows/repository-quality.yml:264-268`, so neither assertion can satisfy the other. The same body exits 0 on that operational surface when `GITHUB_REF` is `refs/heads/gsd-path/M006`, so the two assertions are still gated on main as before.
- ✅ No milestone literal remains in the step or its pin test (N1). — Scan of the landed step (`.github/workflows/repository-quality.yml:242-274`) for `[0-9]{3}-[a-z0-9-]+` returns nothing; `native-workflow-acceptance` does not appear. `tests/test_ci_runtime_restore.py:248-256` now asserts `'".project/archive/"' in text` and `"001-001-native-workflow-acceptance" not in text`; the only literal in the pin is inside that negative guard, which forbids the M001 dependency rather than pinning a milestone — the reading N1's "must not reintroduce a milestone literal" requires, so it is not a reintroduction.

Warnings (non-blocking):
- The pin is presence-based, so it cannot see fatality: with the archive `sys.exit(` replaced by `print(` (every pinned string still present) `test_push_to_main_requires_the_shipped_integrated_governor_report` still passes, verified by mutation. `test_no_suppression_around_restore_and_governor_exits` catches only an appended `|| true` / `continue-on-error` (verified: it fails on `|| true`). N2's fatality therefore rests on the step text at this commit, not on a guard. Fix direction for a later milestone: assert the step contains `sys.exit(` inside the `GITHUB_REF` block, or drive the heredoc body against two fixture reports (shape-present archive-absent must exit non-zero).
- The "no milestone literal" half of the pin checks one string only: adding `.project/archive/005-ci-fixture-fix` beside the shape check keeps the pin green (verified by mutation). A general scan of the step for a `[0-9]{3}-[a-z0-9-]+` pattern would enforce N1 for every future milestone instead of the M001 case.
- The step body's only report-level gate is `tool_error_count`; it never reads `report["status"]` or `error_count`. A governor report with `status: failure` whose workflow-state-surface finding is still pass/ok exits 0 from the heredoc. Not reachable today through the CLI (a non-ok report exits non-zero, and `set -o pipefail` ends the step — verified with a pipefail probe: exit 1, heredoc never reached), and unchanged from base; noted because the step's job is honesty about the report.

Contract violations (blocking):
- none — `git diff --name-only df819312..d276fb3d` is `.github/workflows/repository-quality.yml`, `tests/test_ci_runtime_restore.py` (both in the task `files`) and `.project/tasks/T001-ci-governor-shape.md`, whose diff is the orchestrator-owned `status`/`agent`/`base` fields plus one append-only Log entry.

## T002 — Refresh the roadmap projection to the shipped milestone: pass

- ✅ The roadmap projection names the shipped STATE.md milestone (N4). — `prd/project-state/data/roadmap.json:614-616` sets `"current_milestone": {"id": "ci-fixture-fix", "status": "active"}`; `prd/project-state/roadmap.md:50-58` opens the single live marker bullet `ci-fixture-fix is the current milestone — shipped/archived/integrated (2026-10-28)` and records ship commit `e890831e`, integration merge `121a2006`, tag `milestone/005-ci-fixture-fix`, archive `.project/archive/005-ci-fixture-fix`. Every one of those facts re-checked against the repository: `git log -1 e890831e` = "ship: M005 — ci-fixture-fix", `git log -1 121a2006` = "integrate: M005 — merge gsd-path/M005 into main", tag resolves to `121a2006`, archive directory exists. The shipped STATE.md milestone is `ci-fixture-fix` (integrated main 121a2006: `milestone: ci-fixture-fix`, `phase: shipped`, `status: done`), so the projection names the shipped milestone; the in-flight `red-ci-clear` named by the bound-branch STATE.md is what N4 forbids the projection to name, and the bullet says so explicitly at `roadmap.md:54`. Verified by re-running both pins against the shipped/done STATE.md from the main clone and against the bound-branch STATE.md: three-way identity passes in both phases.
- ✅ A roadmap with an absent/empty `current_milestone.id` fails the freshness test loudly (E2). — Held-out test `tests/test_project_state_roadmap_freshness.py`; recorded output from the T002 Log orchestrator Verify (sidecar gsd-path-verify/task-t002-verify, exit 0): `5 passed, 5 skipped in 5.17s` for `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`. My own probes at this HEAD, rewriting only `current_milestone` in a copy of `roadmap.json` and running the module's live-surface test: `id` absent gives `KeyError: 'id'` at `tests/test_project_state_roadmap_freshness.py:341`; `id` empty gives `AssertionError: roadmap.md live marker names 'ci-fixture-fix' but roadmap.json current_milestone.id is ''` at `:349`; `current_milestone` absent gives `TypeError`. None passes silently. The derived pins behind E2 (`:133`, `:171`) skip on a checkout without `.gsd`, so the loud failure rests on `test_native_marker_names_the_operational_milestone`, which runs whenever `.project/STATE.md` names a milestone — verified present and loud on both phase pairings.

Warnings (non-blocking):
- The refresh drops the M003 `ci-honesty` record from `prd/project-state/roadmap.md`: the base live bullet at line 50 carried `pointer-refresh-m003` in flight plus the `ci-honesty` ship facts (`7786d5d3`, `7e200294`, archive `003-ci-honesty`), and after the diff neither string survives in the file (0 hits for `003-ci-honesty`, `pointer-refresh-m003`, `7786d5d3`, `7e200294`). M002 and M001 each got a dated `superseded` bullet; M003 and M004 got none, so the tracked projection lost two landed milestones from its history. No AC, SC or prohibition covers this, and the facts remain in `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` and the archives, so it does not block. Fix direction: add a dated `Local GSD workflow marker (superseded 2026-10-28)` bullet for `pointer-refresh-m003` / `003-ci-honesty` carrying the same ship and merge commits, as M002 and M001 already have.
- `current_milestone.status` stays `"active"` for a milestone the bullet calls shipped/archived/integrated. The freshness pin requires `"active"` (`tests/test_project_state_roadmap_freshness.py:346-350`), so this is the documented contract, not a defect; the mismatch between the JSON status word and the bullet's prose is the ambiguity worth tightening.

Contract violations (blocking):
- none — `git diff --name-only d276fb3d..f60bef3f` is `prd/project-state/data/roadmap.json`, `prd/project-state/roadmap.md` (both in the task `files`) and `.project/tasks/T002-roadmap-pointer.md`, whose diff is the orchestrator-owned `status`/`agent`/`base` fields plus one append-only Log entry. The task also lists `tests/test_project_state_roadmap_freshness.py` and `tests/test_post_ship_pointers.py`; neither was changed, which is a subset of the declared files.

## Intent coverage

### SC1 — SC1 — The main-branch governor honesty step accepts the shipped integrated surface of whichever milestone is current: it asserts the `kind=shipped-integrated;` shape and a `.project/archive/` path, never a milestone literal, and `tests/test_ci_runtime_restore.py` pins that shape.: pass
- ✅ The step asserts both facts, never a literal: `.github/workflows/repository-quality.yml:264-273` holds one fatal assertion per fact, and a milestone-pattern scan of the whole step returns nothing. Real integrated-main evidence, not just the definition: a fresh clone of `121a2006` with `origin/main` identical and no `.gsd` yields a governor report with `pass_count` 72 and observed `kind=shipped-integrated; ... archive .project/archive/005-ci-fixture-fix`; the landed step body exits 0 on it, and the base (df819312) step body exits 1 on the same report with "missing '.project/archive/001-001-native-workflow-acceptance'". So the change is what turns the main-branch step green, and the failure it removes is exactly the stale literal.
- ✅ Held-out boundary E1 — "A governor surface that reports shipped-integrated without any archive path fails the step; a later milestone's archive passes." Both halves reproduced against the landed step body: `archive absent.` gives exit 1; `.project/archive/006-red-ci-clear` gives exit 0; `.project/archive/005-ci-fixture-fix` gives exit 0. The same two cases driven through `check_workflow_state_surface` with a stubbed native-status payload give the same verdicts, so the assertion reads the adapter's real observed fact rather than a fixture string.
- ✅ Prohibition N1 — no milestone literal in the workflow or the pin test: the step contains none, and the pin's only occurrence of the M001 slug is the negative guard `tests/test_ci_runtime_restore.py:255`.
- ✅ Prohibition N2 — both assertions remain fatal and the step is not a no-op: each is its own `sys.exit` inside the `refs/heads/main` branch, `if: always()` is unchanged, and the step still runs the governor and prints its summary. The pin cannot prove fatality across future edits (warning above); at this commit fatality is reproduced directly.
- ✅ Prohibition N3 applies to SC3, not SC1: no `|| true`, no `continue-on-error`, `set -o pipefail` retained (`.github/workflows/repository-quality.yml:248`), and `test_no_suppression_around_restore_and_governor_exits` fails on an appended `|| true` — verified by mutation.

### SC2 — SC2 — The tracked roadmap projection agrees with shipped STATE.md: `prd/project-state/data/roadmap.json` (and `roadmap.md`) name the milestone recorded in `.project/STATE.md`.: pass
- ✅ `roadmap.json:615` id is `ci-fixture-fix`; `roadmap.md:50` live marker slug is `ci-fixture-fix`; the shipped STATE.md on integrated main (`121a2006`) records `milestone: ci-fixture-fix`. Re-read at this HEAD, the three agree, and the two derived pins pass on both the shipped/done and the bound-branch build/active STATE.md (verified by pointing the tests at each STATE.md). The bound-branch STATE.md records `red-ci-clear` in flight; N4 binds that reading — "The refresh names the shipped milestone, not an in-flight one" — so the projection correctly tracks the shipped milestone while `roadmap.md:54` names `red-ci-clear` as the active one.
- ✅ Prohibition N4 — the projection does not disagree with STATE.md: the only milestone the projection names as landed is the shipped one, and the in-flight milestone is described as in flight, matching the freshness suite's documented archive-keyed contract.
- ✅ Held-out empty edge E2 — recorded output: the T002 Log orchestrator Verify of `tests/test_project_state_roadmap_freshness.py` is `5 passed, 5 skipped`, exit 0 (sidecar gsd-path-verify/task-t002-verify). Absent `current_milestone.id` raises `KeyError: 'id'`, empty raises `AssertionError`, missing object raises `TypeError` — reproduced at this HEAD, no silent pass.

### SC3 — SC3 — `uv run --frozen pytest tests/test_ci_runtime_restore.py tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py tests/test_harness_governor.py tests/test_harness_preflight.py -q` reports 0 failures on the bound branch.: pass
- ✅ Ran the exact command on a clean clone of the bound branch at this HEAD (branch `gsd-path/M006`, `origin/main` set to `121a2006`, no `.gsd`): `293 passed, 7 skipped in 132.60s`, exit 0. The 7 skips are the pre-existing loud `no-pi-journal` pair and the five bootstrap-without-`.gsd` freshness skips, each reported under `-rs`.
- ✅ Load-bearing against base: the same command on a clean clone at base `df819312` gives `4 failed, 291 passed, 5 skipped` — `test_roadmap_json_current_milestone_tracks_the_latest_archive`, `test_native_marker_names_the_operational_milestone`, and the two `no-pi-journal` tests. This wave removes the two roadmap failures.
- ✅ Prohibition N3 — no failing test was weakened or skipped: the only assertion changes are in `tests/test_ci_runtime_restore.py:254-255` (shape instead of literal, plus the negative guard), and the roadmap tests were not touched by either commit; skip counts are identical at base and at this HEAD on the same checkout kind.
- ✅ Edge E3 — a test that still pins the M001 archive literal, or a roadmap still naming the previous milestone, makes the run fail rather than pass. Re-inserting the M001 literal assert against the landed step fails; rewriting `current_milestone.id` to `pointer-refresh-m003`, `003-ci-honesty` or `red-ci-clear` fails both `test_native_marker_names_the_operational_milestone` and `test_roadmap_json_current_milestone_tracks_the_latest_archive`. The suite is not blind to either stale shape.

## Summary for orchestrator

- blocked findings: none — wave passes.
- repeat offenders: none across cycles (cycle 1). Two carried-forward items from earlier milestones are still open and are not this wave's to fix: (a) the `no-pi-journal` pair fails whenever the frozen `.gsd` snapshot is on disk — reproduced at base as well, so pre-existing, and SC3's "on the bound branch" reads as a clean checkout, where both skip loudly; (b) the `rust-harness-quality` job has no "Prepare shipped-main integration proof inputs" step, so on main its governor/preflight live tests classify the checkout fail-closed — reproduced here on a main clone whose `refs/remotes/origin/HEAD` is not a symbolic ref (governor exit 1, workflow-state-surface conflicting-ownership), while the same tree with `origin/HEAD` set yields shipped-integrated. Outside this wave's files and criteria; it is the reason the recorded 2026-10-28 red Rust job stays red and it belongs in a follow-up task.
- warnings worth a human eye: the T001 pin proves text presence, not fatality (a `sys.exit` demoted to `print` keeps it green) and its literal guard covers only the M001 slug; the T002 refresh dropped the M003/M004 records from `prd/project-state/roadmap.md` instead of adding dated `superseded` bullets; `current_milestone.status` reads `"active"` for a milestone the bullet calls shipped.
- reviewed HEAD: `f60bef3f97740f2402219bdd3626546818b0ac15`; bases `df8193125af126d9cb7d1b1b7102ad1b897f508e` (T001) and `d276fb3dad28872984b27a4862ac52f30dbeb21b` (T002), both recorded in the task frontmatter and in each commit body.
