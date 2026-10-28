# Review — wave 3, cycle 1

<!-- Reviewer role, wave mode (full). PLAN.md Wave 1 Review depth is `full`, so no
     lens applies.

     SIDECAR HEAD: 4c471673787c3cbca8536a16dc0fd282ceb4dd5d (recorded from
     `git rev-parse HEAD` inside this sidecar; tracked tree clean at start and
     end). History of this wave: 3c1295f2 (T002 landing) → 825b5096
     ("build: fix wave 1 cycle 2 findings in T003", the product half of the
     repair) → 4c471673 (T003 landing, its task file only).

     SCOPE NOTE. The brief names T003, whose task file declares `wave: 3`.
     PLAN.md `## Wave 1` owns exactly one task (T001, `wave: 1`), and the bundled
     gate (`check_handoffs.py wave --review .project/review/wave-1.cycle3.md`)
     rejects any other section, so this artifact carries T001 only — the same
     shape cycle 2 used. T003's verdict and its evidence are recorded in the
     T001 AC2 line and in "Summary for orchestrator".

     METHOD. `git diff 825b5096..4c471673` is one file (T003's task file), so the
     reviewed product is the combined diff `git diff 3c1295f2..4c471673` = 6
     files, +270/-15. Product files in that diff: `prd/project-state/roadmap.md`
     (+2/-1) and `tests/test_post_ship_pointers.py` (+66/-9); the other four are
     the orchestrator's ledger, PLAN.md, the cycle-2 review and the T003 task
     file. The product was reconstructed with `git archive HEAD` into throwaway
     copies under /tmp, so every probe below ran on the isolated product, never
     on the shared worktree.

     VERIFY EVIDENCE, AND ITS LIMIT. The recorded orchestrator Verify in T003's
     Log is exit 0, `5 passed, 5 skipped` for `uv run --frozen pytest
     tests/test_project_state_roadmap_freshness.py -q`. It cannot check the
     repaired criterion: that command never runs
     `tests/test_post_ship_pointers.py`, where the pin lives. The ledger
     (`.project/build/verify-ledger.jsonl`) carries no T003 row at all — its two
     rows are T001 at `7594043e` and T002 at `3c1295f2`, and
     `git show 3c1295f2:tests/test_post_ship_pointers.py` has no
     `REFRESH_STEPS` — so no recorded Verify output in this repository ever
     exercised the new pin. The dispatch receipt
     (`.git/gsd-path/dispatch/gsd-path-M009/T003/attempt-1/verify.json`) also
     names `worktree: /root/law-nexus`, the primary worktree, not an isolated
     sidecar. No task Verify and no PLAN project Verify
     was re-run as Verify evidence here; the probes below are my own, needed
     because that recorded output plus the diff could not decide the criterion.

     PROBES (each in a throwaway copy of `git archive HEAD`):
       1. Both pointer suites at the reviewed product: `12 passed, 5 skipped`,
          exit 0. `-rs` names the five skips as the pre-existing `.gsd`-only
          guards (tests/test_project_state_roadmap_freshness.py:126, 137, 171,
          201, 231), so nothing was newly silenced.
       2. Cycle-2 finding 1, per-step deletion of
          docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md, one step at a time:
          step 1 deleted -> `1 failed`; step 2 deleted -> `1 failed`; step 3
          deleted -> `1 failed`. All three now fail on the step-structure
          assertion at tests/test_post_ship_pointers.py:152-159, not on a
          surviving keyword.
       3. Cycle-2 finding 1, shapes the old pin accepted: a prose rewrite with
          every pinned token and zero numbered steps -> `1 failed` (0 steps); a
          rewrite that folds step 3 into step 2 -> `1 failed` (2 steps); the
          three steps reordered -> `1 failed` ("step 1 (roadmap.json) must name
          'prd/project-state/data/roadmap.json'"); step 1 gutted -> `1 failed`;
          step 2 gutted -> `1 failed`; step 3 gutted -> `1 failed`; delete step 1
          and append a fourth step -> `1 failed` (the shifted slots do not match).
          Residual hole: step 3 rewritten to "Commit with a `docs:` subject, then
          land it." still passes, because "ship commit" survives in the trailing
          prose the pin never scopes to a step. Adding a fourth step passes by
          design (`len(steps) >= len(REFRESH_STEPS)`).
       4. Cycle-2 finding 2, the dead pointer: `grep -n WORKFLOW-NOTES
          prd/project-state/roadmap.md` returns nothing; roadmap.md:57-58 now
          reads "records the ship-time refresh rule
          (`docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`)". Putting
          `.project/WORKFLOW-NOTES.md` back fails the pin with "the roadmap must
          not point at the deleted .project/WORKFLOW-NOTES.md". Removing the
          pointer entirely still passes: the pin asserts the absence of the dead
          path, not the presence of the live one.
       5. E1 — shipped surface (phase shipped, status done, archive
          `.project/archive/009-projection-at-ship`) with the projection left at
          `pointer-in-ci`: `2 failed, 10 passed, 5 skipped`; one message is
          "roadmap.json current_milestone.id 'pointer-in-ci' != shipped STATE.md
          milestone 'projection-at-ship'", the exact shape of the M008 CI run.
       6. E3 — the M008 shipped surface (`.project/STATE.md` from `4dd35d25`)
          plus this product's projection: `12 passed, 5 skipped`, exit 0.
       7. End state — shipped/done plus `archive/009-projection-at-ship` plus the
          projection refreshed to `projection-at-ship`: `12 passed, 5 skipped`,
          exit 0. A green shipped tree for M009 is reachable.
       8. In-flight drift — HEAD's in-flight STATE with the projection moved
          forward to `projection-at-ship`: `2 failed` ("does not match the last
          landed (archived) milestone 'pointer-in-ci' while STATE.md is in
          flight"), so the projection cannot be pre-refreshed during build.
       9. Ordering, `_common.reviewed_head_covers` on a scratch repo: a `docs:`
          commit that touches the projection after the reviewed HEAD returns
          False, so a refresh landing after the final review invalidates it.
      10. Changed paths: 3c1295f2..4c471673 touches only `files` of T002/T003
          plus orchestrator artifacts; `.github/` has a 0-line diff and both
          suites remain in the `Product and architecture harness tests` run
          block at .github/workflows/repository-quality.yml:153-154; the tests
          diff adds no `skip`/`xfail` and removes no test line; `ruff check` and
          `ruff format --check` pass on the changed test module.
      11. `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` is tracked
          (`git ls-files`) and not ignored (`git check-ignore` exits 1); the
          `.project` top level at HEAD is `STATE.md` plus the seven transaction
          directories, so the ship gate's active-root allowlist is not violated. -->

Wave verdict: pass
Cycle: 1
Depth: full
Tasks reviewed: 1

## T001 — Record the ship-time projection refresh and name the shipping milestone: pass

- ✅ The projection names the milestone being shipped (E1: naming the previous one fails the pointer suites). — In flight the projection is one consistent view anchored on the last landed milestone: `prd/project-state/data/roadmap.json` `current_milestone` is `pointer-in-ci`/`active`, the single live marker bullet at prd/project-state/roadmap.md:50 names `pointer-in-ci`, and `008-pointer-in-ci` is the highest archive under `.project/archive/` — the in-flight reading the suites enforce (probe 1, `12 passed, 5 skipped`). The after-ship half is reachable and demonstrated: shipped/done plus `archive/009-projection-at-ship` plus the projection refreshed to `projection-at-ship` is `12 passed, 5 skipped` (probe 7), while the same shipped surface left at `pointer-in-ci` fails with "roadmap.json current_milestone.id 'pointer-in-ci' != shipped STATE.md milestone 'projection-at-ship'" (probe 5). Held-out E1 — "A projection naming the previous milestone fails the pointer suites once STATE.md names the shipping milestone." — held, in its PLAN-assigned held-out test `tests/test_project_state_roadmap_freshness.py`. Prohibition N1 — "remove the pointer suites from CI to make the run pass" — held: `.github/` has a 0-line diff and both suites are still in CI at .github/workflows/repository-quality.yml:153-154. No regression from the cycle-2 repair: the repair left `roadmap.json` untouched.
- ✅ The refresh rule lives in a tracked file and is pinned (E2, N2). — Both halves hold at this HEAD, and cycle 2's blocking finding is repaired for the pin. (a) The pin now reads the rule's numbered steps structurally: `_refresh_rule_steps()` at tests/test_post_ship_pointers.py:117-132 splits the file on `^\d+\.\s` items, `REFRESH_STEPS` at tests/test_post_ship_pointers.py:104-115 binds each slot to the artifacts its step must name, and the count check at tests/test_post_ship_pointers.py:152 fails a rule with fewer than three steps. Deleting step 1, step 2 or step 3 each fails the pin (probe 2), as does the prose rewrite with all nine old tokens and no numbered steps, the 2-step merge, the reorder, and every gutted-step shape I tried (probe 3). E2 — "A rule file that omits the refresh step fails the pin that names it." — therefore holds for every step, including step 3, the ordering step cycle 2 found unpinned. (b) The rule's recorded location is live again: prd/project-state/roadmap.md:57-58 names `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`, `grep -n WORKFLOW-NOTES prd/project-state/roadmap.md` returns nothing, and reinstating `.project/WORKFLOW-NOTES.md` in the roadmap fails the new assertion at tests/test_post_ship_pointers.py:172-175 (probe 4). The file is tracked and not ignored (probe 11). Prohibition N2 — "encode the rule only in a chat message" — held: the rule is a tracked, non-ignored Markdown file.
- ✅ The pointer suites pass on the bound branch and on the shipped tree (E3, N3). — On the bound product at this HEAD: `12 passed, 5 skipped`, exit 0 (probe 1). On the shipped tree (`.project/STATE.md` from the M008 ship `4dd35d25` plus this projection): `12 passed, 5 skipped`, exit 0 (probe 6). Held-out E3 — "A projection left at the build-time milestone fails the run rather than passing quietly." — held: at the shipped surface with the previous milestone still named, two tests fail and name both slugs (probe 5); at the in-flight surface with the projection moved forward to the build-time milestone, two tests fail as well (probe 8), so neither direction passes quietly. Prohibition N3 — "mark the pointer suites xfail or skip on the shipped tree" — held: the tests diff adds no `skip`/`xfail`, removes no test line, and `-rs` shows the five skips are the pre-existing `.gsd`-only guards.

Warnings (non-blocking):
- The recorded T003 Verify cannot show the repair. It runs `tests/test_project_state_roadmap_freshness.py` only — never `tests/test_post_ship_pointers.py`, where the pin lives — and the ledger carries no T003 row, so no recorded output in this repository ever exercised the new pin; the dispatch receipt also names the primary worktree `/root/law-nexus` rather than an isolated sidecar. Two repair cycles have now passed a repair whose recorded Verify could not reach the changed assertion; the pin was proven only by this review's probes and by the PLAN project Verify.
- The reader path for the next ship is still indirect and unpinned. `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` is named only by the pin, PLAN.md, INTENT.md and prd/project-state/roadmap.md:58; no phase skill, no AGENTS.md entry and no WORKFLOW.md line resolves to it. Cycle 2's fix direction asked for an AGENTS.md agent-stack entry, and AGENTS.md is in no task's `files`, so no coder could land it. What makes the reading defensible is the runtime order: PLAN.md's project Verify runs the pointer suites at ship, a stale projection fails them, and the fix requires editing roadmap.md, whose line 58 names the rule. Tighten by adding the AGENTS.md pointer and by asserting the live pointer's presence, not only the dead path's absence.
- The pin does not scope step 3 to its own text: rewriting step 3 to "Commit with a `docs:` subject, then land it." still passes because "ship commit" survives in the paragraph above it (probe 3). Deleting the step fails, so E2 holds, but the step-level binding is looser than the count check suggests.
- Rule step 3 still omits the ordering the bundled ship runtime enforces: after a `docs:` refresh commit, `_common.reviewed_head_covers` returns False for the pre-refresh reviewed HEAD (probe 9), so a ship agent following the file literally invalidates the review it just obtained. The file needs "refresh `docs:` commit, then final review at the new HEAD, then the ship commit". Raised in cycle 2 and not applied.
- `tests/test_post_ship_pointers.py:96` and `:99` assign `REFRESH_RULE` twice; the first assignment is dead. `ruff check` and `ruff format --check` still pass, so this is cosmetic.
- `prd/project-state/roadmap.md:59-60` still points at `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` as the current-state document while the live bullet moves to M008; that report is dated to the M008 ship, so the pointer is one milestone behind in turn.
- The dated `ci-fixture-fix` record (ship `e890831e`, merge `121a2006`) that sat in the live bullet's "Superseded bullet (2026-10-28)" clause at `4931a615` is still absent; T003 restored no shipment record. Third cycle carrying this observation.
- T003's `files` frontmatter still lists `.project/WORKFLOW-NOTES.md`, the path the repair deleted, while `tests/test_post_ship_pointers.py:168` fails if it exists again. Same for T001's `files`. Harmless as a permission list, but `review_findings.py collect` hands that path to a fix batch.

Contract violations (blocking):
- none — `git diff 3c1295f2..4c471673` touches only product paths in T002's and T003's `files` (`prd/project-state/roadmap.md`, `tests/test_post_ship_pointers.py`) plus orchestrator artifacts (`.project/build/verify-ledger.jsonl`, `.project/plan/PLAN.md`, `.project/review/wave-1.cycle2.md`) and the task files. T003's own landing commit changes only `status`, `agent`, `base` and its Log; its contract body is unchanged. As in cycle 2, the product half landed in the orchestrator commit `825b5096` before T003's recorded base, so the landing is not a single-commit task patch; no verdict rests on the split because the brief directs the combined diff.

## Intent coverage

### SC1 — SC1 — The tracked projection names the milestone being shipped: after this milestone's ship, `roadmap.json` `current_milestone.id` equals the milestone in `.project/STATE.md`, and the live marker bullet names the same slug.: pass
- ✅ While `.project/STATE.md` is in flight on `projection-at-ship` (phase build, branch `gsd-path/M009`), the projection is the consistent in-flight view: `prd/project-state/data/roadmap.json` `current_milestone` is `pointer-in-ci`/`active`, the single live marker bullet prd/project-state/roadmap.md:50 names `pointer-in-ci`, and `008-pointer-in-ci` is the highest archive. The after-ship half is reachable: shipped/done plus `archive/009-projection-at-ship` plus the projection at `projection-at-ship` is `12 passed, 5 skipped` (probe 7), while the same shipped surface left at `pointer-in-ci` fails naming both slugs (probe 5). Held-out E1 held in `tests/test_project_state_roadmap_freshness.py`. Prohibition N1 held: `.github/` has a 0-line diff and both suites remain in CI at .github/workflows/repository-quality.yml:153-154. No regression from the cycle-2 repair.

### SC2 — SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build.: pass
- ✅ The rule is a tracked, non-ignored file at `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` (probe 11) that prescribes exactly three numbered steps — set `prd/project-state/data/roadmap.json` `current_milestone`, rewrite the live marker in `prd/project-state/roadmap.md`, then commit with a `docs:` subject before the ship commit — and the pin now reads each of them, so deleting any single step fails it (probes 2 and 3), which is E2. The reader path is live: prd/project-state/roadmap.md:57-58 names the file, and the ship runtime runs PLAN.md's project Verify (the two pointer suites), which fails on a stale projection and forces the agent into roadmap.md, the artifact whose line 58 points at the rule (probes 5 and 8). Prohibition N2 held. Reaching this verdict requires the indirect reading; the warnings record the residual gap (no AGENTS.md, WORKFLOW.md or phase-skill entry, and the pin asserts only the dead path's absence), so the criterion is satisfied but needs tightening.

### SC3 — SC3 — `uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py -q` reports 0 failures on the bound branch and on the shipped tree.: pass
- ✅ On the bound product at this HEAD: `12 passed, 5 skipped`, exit 0 (probe 1). On the shipped tree (`.project/STATE.md` from the M008 ship `4dd35d25` with this product's projection): `12 passed, 5 skipped`, exit 0 (probe 6). Held-out E3 held: at the shipped surface with the previous milestone still named, two tests fail naming both slugs rather than passing quietly (probe 5), and the in-flight surface with a forward-moved projection fails too (probe 8). Prohibition N3 held: the tests diff adds no `skip`/`xfail`, removes no test line, and `-rs` shows the five skips are the pre-existing `.gsd`-only guards.

## Fixed since last cycle

- Cycle-2 blocking finding 1 (the pin must fail when any single numbered step of the rule is deleted) — confirmed fixed, re-checked by mutation, not assumed. `_refresh_rule_steps()` plus the `REFRESH_STEPS` slot table plus the count check replace the nine-substring union. Deleting step 1, step 2 or step 3 each fails (probe 2); the prose rewrite with all nine old tokens and no numbered steps now fails at 0 steps, the 2-step merge fails at 2 steps, the reorder fails on slot 1's artifact, and every gutted-step shape fails (probe 3). The one residual loosening is step 3 rewritten while "ship commit" survives in the surrounding prose; the step deletion itself fails, so E2 holds.
- Cycle-2 blocking finding 2 (`prd/project-state/roadmap.md` must no longer name the deleted `.project/WORKFLOW-NOTES.md`) — confirmed fixed. prd/project-state/roadmap.md:57-58 names `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`; `grep -n WORKFLOW-NOTES prd/project-state/roadmap.md` returns nothing; and the pin now fails if the dead path returns (probe 4). Note the pin guards the old path's absence only — removing the live pointer entirely still passes.
- Regressions introduced by the repair: none observed. Both pointer suites are green at the reviewed product and on the M008 shipped tree (probes 1 and 6), the `.github/` workflow is untouched, no test was skipped or removed, `roadmap.json` was not touched, and the `.project` active root still carries only `STATE.md` plus the transaction directories. The dead duplicate `REFRESH_RULE` assignment at tests/test_post_ship_pointers.py:96 is new but cosmetic.

## Summary for orchestrator

- T003 — Fix wave 1 cycle 2 review findings in T001: pass (no section: its task file declares `wave: 3`, so a wave 1 artifact may not carry it; the gate rejects such a section, as cycle 2 recorded). Judged from the combined product diff against its own two acceptance criteria: "SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build." passes on the indirect reading recorded under SC2 above, with the reader-path gap carried as a warning; "The refresh rule lives in a tracked file and is pinned (E2, N2)." passes — the pin fails a deletion of each of the three numbered steps.
- blocked findings: none. The wave is green; the two cycle-2 blocking findings are both repaired and re-proven by mutation.
- repeat offenders: (a) "the recorded Verify cannot show the repair" now spans T002 and T003 — both repair tasks verified a suite that does not contain the pin, and T003 has no ledger row at all; (b) rule step 3 still omits the final-review ordering, raised in cycle 2 and not applied; (c) each refresh still drops the immediately previous shipment's dated record (`ci-fixture-fix`, ship `e890831e`, merge `121a2006`, absent for three cycles); (d) the reader path for the rule depends on one unpinned roadmap sentence, and AGENTS.md is in no task's `files`. All four are plan-level, not coder-level, and belong in LESSONS.md at ship.
- warnings worth a human eye: (a) the recorded T003 Verify ran the freshness suite only, with no T003 ledger row, in the primary worktree; (b) the pin asserts the dead pointer's absence, not the live pointer's presence, and does not scope step 3 to its own text; (c) rule step 3 omits that the final review must follow the `docs:` refresh commit, which preflight enforces (probe 9); (d) `prd/project-state/roadmap.md:59-60` still points at the M008-dated current-state report; (e) `REFRESH_RULE` is assigned twice at tests/test_post_ship_pointers.py:96 and :99.
