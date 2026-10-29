# Review — wave 1, cycle 3

<!-- Reviewer role, wave mode (full). PLAN.md Wave 1 Review depth is `full`, so no
     lens applies.

     SIDECAR HEAD: f8f0256bd89367f9166a1747c78e20c0ffe1f04f (the wave tip;
     tracked tree clean at start and end). History of this wave: 7594043e
     (T001 landing) → fd056ac5 (build: fix wave 1 cycle 1 findings in T002,
     product half) → 50530b64 (build: realign wave 2 repair task) → ef338d6d
     (build: reset repair task worktree field) → 3c1295f2 (T002 landing, its
     task file only) → 825b5096 (build: fix wave 1 cycle 2 findings in T003,
     product half) → 4c471673 (T003 landing, its task file only) → 2b499b1f
     (build: drop the duplicate rule constant and the dead task-file paths)
     → 9ec7612e (build: align the plan waves with the repair tasks) →
     f8f0256b (build: keep the repair tasks in wave 1 and record repair
     receipts). This cycle reviews ALL THREE tasks at the combined wave tip.

     METHOD. `git diff 4931a615..f8f0256b` = 13 files, +550/-14, read in the
     sidecar checkout. Product files in the diff: `docs/agent-stack/
     SHIP-TIME-PROJECTION-REFRESH.md` (+21), `prd/project-state/data/
     roadmap.json` (+1/-1), `prd/project-state/roadmap.md` (+23/-13),
     `tests/test_post_ship_pointers.py` (+79). The other nine are
     orchestrator-owned: the three task files, PLAN.md, the verify ledger,
     the two prior cycle reviews, and the two repair-evidence receipts.
     `.github/` is untouched (0 diff lines), and `tests/test_project_state_
     roadmap_freshness.py` is unchanged (0 diff lines). The tests diff adds
     no `skip`/`xfail` (0 matches).

     VERIFY EVIDENCE. The recorded orchestrator Verifies in all three Logs
     (T001 sidecar `gsd-path-verify/task-t001-verify`, exit 0, `5 passed, 5
     skipped`; T002 sidecar `gsd-path-verify/task-t002-verify`, exit 0, `5
     passed, 5 skipped`; T003 sidecar `gsd-path-verify/task-t003-verify`,
     exit 0, `5 passed, 5 skipped`) are the Verify evidence, with the
     matching dispatch `verify.json` files and the verify-ledger rows. No
     task Verify or PLAN project Verify was re-run as Verify evidence.
     Commands re-run below are my own probes, needed because the recorded
     output plus the diff could not decide the criterion.

     PROBES (each in the sidecar checkout, with all mutations restored):
       1. Both pointer suites at the wave tip: `12 passed, 5 skipped`, exit
          0. `-rs` names the five skips as the pre-existing `.gsd`-only
          guards (tests/test_project_state_roadmap_freshness.py:126, 137,
          171, 201, 231 — "no workflow state surface on this checkout"), so
          nothing was newly silenced.
       2. E1 — shipped surface (`phase: shipped`, `status: done`,
          `archive: .project/archive/009-projection-at-ship`) with the
          projection left at `pointer-in-ci`:
          `test_native_marker_names_the_operational_milestone` fails with
          "roadmap.json current_milestone.id 'pointer-in-ci' != shipped
          STATE.md milestone 'projection-at-ship'". Naming the previous
          milestone is loud.
       3. E3 — the M008 shipped surface (`.project/STATE.md` milestone
          `pointer-in-ci`, `phase: shipped`, `status: done`) plus this
          wave's projection (`pointer-in-ci`): `12 passed, 5 skipped`,
          exit 0. The shipped tree today is green.
       4. End state — shipped/done (`projection-at-ship`) plus
          `archive/009-projection-at-ship` plus the projection refreshed
          to `projection-at-ship`: `1 passed` for
          `test_native_marker_names_the_operational_milestone`. A green
          shipped tree for M009 is reachable.
       5. E2, per-step deletion of
          docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md, running
          `uv run --frozen pytest tests/test_post_ship_pointers.py -q`:
          step 1 deleted -> `1 failed`; step 2 deleted -> `1 failed`; step
          3 deleted -> `1 failed`. Every numbered step is pinned.
       6. E2, prose rewrite keeping all required tokens and zero numbered
          steps -> `1 failed` (the count assertion `len(steps) >= 3` fails
          before the per-step token checks). A pin that only asserted the
          union of its words no longer passes.
       7. Ship gate: `git ls-tree HEAD:.project` minus transaction
          directories is exactly `STATE.md` and `archive`; no
          `WORKFLOW-NOTES.md`. `.project/WORKFLOW-NOTES.md` does not exist
          physically. The pin at `tests/test_post_ship_pointers.py` asserts
          both facts.
       8. Changed paths across `4931a615..f8f0256b` are only the tasks'
          `files` plus their task files and orchestrator-owned PLAN.md,
          verify-ledger, review files, and repair receipts; `.github/` has
          a 0-line diff; the tests diff adds no `skip`/`xfail` and removes
          no test line. -->

Wave verdict: pass
Cycle: 3
Depth: full
Tasks reviewed: 3

## T001 — Record the ship-time projection refresh and name the shipping milestone: pass

- ✅ The projection names the milestone being shipped (E1: naming the previous one fails the pointer suites). — In flight the projection is one consistent view anchored on the last landed milestone: `prd/project-state/data/roadmap.json:614-617` is `"id": "pointer-in-ci"` with `"status": "active"`, the single live marker bullet `prd/project-state/roadmap.md:50` names `pointer-in-ci`, and `008-pointer-in-ci` is the highest archive — the in-flight reading the suites enforce (probe 1, `12 passed, 5 skipped`). The after-ship half is reachable and demonstrated: shipped/done plus `archive/009-projection-at-ship` plus the projection at `projection-at-ship` is `1 passed` (probe 4), while the same shipped surface left at `pointer-in-ci` fails `test_native_marker_names_the_operational_milestone` with "roadmap.json current_milestone.id 'pointer-in-ci' != shipped STATE.md milestone 'projection-at-ship'" (probe 2). Held-out E1 held in its PLAN-assigned test `tests/test_project_state_roadmap_freshness.py`. Recorded Verify exit 0 is consistent.
- ✅ The refresh rule lives in a tracked file and is pinned (E2, N2). — The rule lives at `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`, tracked (`git ls-files` lists it) and not ignored (`git check-ignore` clean), outside `.project/` so the ship gate admits it. The pin at `tests/test_post_ship_pointers.py:96-131` reads the three numbered steps structurally: `_refresh_rule_steps()` parses `^\d+\.\s` lines, asserts `len(steps) >= 3`, then checks each step's required tokens. Deleting step 1, 2, or 3 each fails the pin (probe 5: `1 failed` per deletion). A prose rewrite with all required tokens and zero numbered steps also fails (probe 6: `1 failed`, count assertion). Prohibition N2 held: the rule is in a tracked, non-ignored file, not a chat message. The pin also asserts `.project/WORKFLOW-NOTES.md` does not exist and `roadmap.md` does not reference `WORKFLOW-NOTES`.
- ✅ The pointer suites pass on the bound branch and on the shipped tree (E3, N3). — On the bound branch at the wave tip: `12 passed, 5 skipped`, exit 0 (probe 1). On the M008 shipped tree (`.project/STATE.md` from the M008 ship `4dd35d25` with this wave's projection): `12 passed, 5 skipped`, exit 0 (probe 3). Held-out E3 held: a projection left at the build-time milestone at the shipped surface fails `test_native_marker_names_the_operational_milestone` (probe 2) rather than passing quietly. Prohibition N3 held: the tests diff adds no `skip`/`xfail`, removes no test line, and `-rs` shows the five skips are the pre-existing `.gsd`-only guards. Prohibition N1 held: `.github/` has a 0-line diff and both suites remain in CI at `.github/workflows/repository-quality.yml`.

Warnings (non-blocking):
- T001's `files` frontmatter still lists `.project/WORKFLOW-NOTES.md` (deleted in this wave by `fd056ac5`) and does not list `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`. PLAN.md's Wave 1 table at HEAD lists the correct files for T001. The stale frontmatter is task metadata, not a product defect: the actual product file is correct and the pin enforces its placement. The build commit `2b499b1f` dropped the duplicate `REFRESH_RULE` constant in the test but did not correct T001's frontmatter.
- `prd/project-state/roadmap.md:59-61` still points at `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` as the current-state document while the live bullet tracks M008; that report is dated to the M008 ship, so the pointer is one milestone behind in turn.

Contract violations (blocking):
- none — the combined diff `4931a615..f8f0256b` changes only paths in the tasks' `files` plus their task files and orchestrator-owned files. In T001's task file only `status`, `agent`, and `base` changed (orchestrator-owned) plus an append-only Log entry; Context, Approach, Interface contract, Intent coverage, Acceptance criteria, and Verify are byte-identical to the plan-approved original.

## T002 — Fix wave 1 cycle 1 review findings in T001: pass

- ✅ SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build. — T002 relocated the rule from `.project/WORKFLOW-NOTES.md` (which blocked the ship gate and which no phase reads) to `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` (outside `.project/`, tracked, not ignored). The ship gate no longer rejects its home: `git ls-tree HEAD:.project` carries no `WORKFLOW-NOTES.md`, and the pin asserts both that the file is absent from `.project/` and that `roadmap.md` does not reference the deleted path. The roadmap.md live marker bullet at L58 names the live file: `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`. Recorded Verify exit 0 is consistent.
- ✅ The refresh rule lives in a tracked file and is pinned (E2, N2). — The tracked-file half holds: `git ls-files` lists the file, `git check-ignore` is clean. The pin at `tests/test_post_ship_pointers.py:96-131` reads the three numbered steps structurally (probe 5: each step deletion fails; probe 6: prose rewrite with all tokens and no steps fails). The ship-gate half holds: `.project/` carries no unexpected entry. Prohibition N2 held: the rule is in a tracked, non-ignored file.

Warnings (non-blocking):
- T002's Verify (`uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`) does not run the suite the repair changed: the pin lives in `tests/test_post_ship_pointers.py`, so the recorded exit-0 output cannot show the new pin works. The pin is exercised by the PLAN project Verify and CI.
- Rule step 3 still omits the ordering constraint the bundled ship runtime enforces: after a `docs:` refresh commit, `_common.reviewed_head_covers` returns False for the pre-refresh reviewed HEAD, so a ship agent following the file literally invalidates the review it just obtained. Step 3 says "Commit with a `docs:` subject, then create the ship commit" without naming that the final review must follow the refresh and precede the ship commit.

Contract violations (blocking):
- none — T002's landing commit `3c1295f2` changes only `status`, `agent`, `base`, and its Log in the task file. Its product changes landed in the orchestrator commit `fd056ac5` before T002's recorded base `ef338d6d`; the reviewed product is the combined diff as the brief directs, so no verdict rests on the split, but the landing is not a single-commit task patch.

## T003 — Fix wave 1 cycle 2 review findings in T001: pass

- ✅ SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build. — T003 fixed the two cycle-2 blockers. (a) The roadmap pointer was corrected: `prd/project-state/roadmap.md:58` now names `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` (the live file), not the deleted `.project/WORKFLOW-NOTES.md`; the pin asserts `"WORKFLOW-NOTES" not in roadmap_md`. (b) The pin was made structural: `tests/test_post_ship_pointers.py:99-131` parses numbered steps via `_refresh_rule_steps()`, asserts `len(steps) >= 3`, and checks each step's required tokens; deleting any one of the three steps fails the pin (probe 5), and a prose rewrite with all tokens and no steps fails (probe 6). The cycle-2 defect — deleting step 3 left the pin green — is repaired. Recorded Verify exit 0 is consistent.
- ✅ The refresh rule lives in a tracked file and is pinned (E2, N2). — Same evidence as T002's AC2: the file is tracked and not ignored, the pin reads the steps structurally (probes 5 and 6), the ship gate is clean, and N2 holds.

Warnings (non-blocking):
- T003's Verify runs only `tests/test_project_state_roadmap_freshness.py`, not `tests/test_post_ship_pointers.py` where the repaired pin lives. The pin is exercised by the PLAN project Verify and CI.
- Rule step 3 still omits the final-review ordering constraint (same warning as T002).
- `AGENTS.md` does not reference `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`; the cycle-2 fix request suggested adding it to the agent-stack paragraph. The rule is discoverable through the `roadmap.md` live marker bullet (L58), which a ship agent refreshing the projection reads, so the SC2 criterion is met, but the file is not named in the repository's primary agent entry point.
- The dated `ci-fixture-fix` superseded record (ship `e890831e`, merge `121a2006`) is still absent from `prd/project-state/roadmap.md`. This pre-existing record-loss spans three cycles (cycle 1 first warned); it is unrelated to any success criterion in this milestone.

Contract violations (blocking):
- none — T003's landing commit `4c471673` changes only `status`, `agent`, `base`, and its Log in the task file, plus the `wave:` field correction from `3` to `1` made by the build commit `9ec7612e`. Its product changes landed in the orchestrator commit `825b5096` before T003's recorded base `825b5096`; the reviewed product is the combined diff, so no verdict rests on the split.

## Intent coverage

### SC1 — SC1 — The tracked projection names the milestone being shipped: after this milestone's ship, `roadmap.json` `current_milestone.id` equals the milestone in `.project/STATE.md`, and the live marker bullet names the same slug.: pass
- ✅ While `.project/STATE.md` is in flight on `projection-at-ship` (phase build, branch `gsd-path/M009`), the projection is the consistent in-flight view: `prd/project-state/data/roadmap.json:614-617` is `"id": "pointer-in-ci"` with `"status": "active"`, the single live marker bullet `prd/project-state/roadmap.md:50` names `pointer-in-ci`, and `008-pointer-in-ci` is the highest archive (probe 1, `12 passed, 5 skipped`). The after-ship half is reachable and demonstrated: shipped/done plus `archive/009-projection-at-ship` plus the projection at `projection-at-ship` is `1 passed` (probe 4), while the same shipped surface left at `pointer-in-ci` fails `test_native_marker_names_the_operational_milestone` with "roadmap.json current_milestone.id 'pointer-in-ci' != shipped STATE.md milestone 'projection-at-ship'" (probe 2). Held-out E1 — "A projection naming the previous milestone fails the pointer suites once STATE.md names the shipping milestone." — held, in its PLAN-assigned held-out test `tests/test_project_state_roadmap_freshness.py`. Prohibition N1 — "remove the pointer suites from CI to make the run pass" — held: `.github/` has a 0-line diff and both suites remain in the `Product and architecture harness tests` run block.

### SC2 — SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build.: pass
- ✅ The refresh rule lives at `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`, outside `.project/` (the ship gate's active-root check admits only its own entries), tracked (`git ls-files` lists it), and not ignored (`git check-ignore` clean). The `roadmap.md` live marker bullet at L58 names the live file, so a ship agent refreshing the projection reads the rule. The pin at `tests/test_post_ship_pointers.py:96-131` reads the three numbered steps structurally: deleting step 1, 2, or 3 each fails `uv run --frozen pytest tests/test_post_ship_pointers.py -q` (probe 5), and a prose rewrite with all required tokens and zero numbered steps also fails (probe 6). Edge E2 — "A rule file that omits the refresh step fails the pin that names it." — held: every step deletion is caught. Prohibition N2 — "encode the rule only in a chat message" — held: the rule is in a tracked, non-ignored file. The pin also asserts `.project/WORKFLOW-NOTES.md` does not exist and `roadmap.md` does not reference the deleted path.

### SC3 — SC3 — `uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py -q` reports 0 failures on the bound branch and on the shipped tree.: pass
- ✅ On the bound branch at the wave tip: `12 passed, 5 skipped`, exit 0 (probe 1). On the M008 shipped tree (`.project/STATE.md` from the M008 ship `4dd35d25` with this wave's projection): `12 passed, 5 skipped`, exit 0 (probe 3). Held-out E3 — "A projection left at the build-time milestone fails the run rather than passing quietly." — held: at the shipped surface with the previous milestone still named, `test_native_marker_names_the_operational_milestone` fails naming both slugs (probe 2). Prohibition N3 — "mark the pointer suites xfail or skip on the shipped tree" — held: the tests diff adds no `skip`/`xfail`, removes no test line, and `-rs` shows the five skips are the pre-existing `.gsd`-only guards.
