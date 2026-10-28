# Review — wave 2, cycle 1

<!-- Reviewer role, wave mode (full). PLAN.md Wave 1 Review depth is `full`, so no
     lens applies.

     SIDECAR HEAD: 3c1295f20ab948f0a8e19e18a59c30c64e7266bb (recorded from
     `git rev-parse HEAD` inside this sidecar; tracked tree clean at start and
     end). Method: `git diff 4931a615..3c1295f2` = 9 files, +287/-13, read in
     the primary root; the reviewed product was reconstructed by
     `git archive HEAD` into a throwaway copy of this sidecar, so every probe
     below ran on the isolated product, never on a shared worktree.

     SCOPE NOTE. The brief names T001 and T002. T002's task file declares
     `wave: 2` and PLAN.md lists it under `## Wave 2`, so a wave 1 artifact may
     carry only T001: the bundled gate (`check_handoffs.py wave --review
     .project/review/wave-1.cycle2.md`) rejects a T002 section with "must
     review exactly T001 in task id order" (probe 9). T002's repair verdict and
     its evidence are therefore recorded in "Summary for orchestrator" and in
     the T001 AC2 line, and T002's own acceptance criteria are left to the
     wave 2 review.

     VERIFY EVIDENCE. No task Verify and no PLAN project Verify was re-run as
     Verify evidence. The recorded orchestrator Verifies in both Logs (T001
     sidecar `gsd-path-verify/task-t001-verify`, exit 0, `5 passed, 5 skipped`;
     T002 sidecar `gsd-path-verify/task-t002-verify`, exit 0, `5 passed, 5
     skipped`) are the Verify evidence, with the matching dispatch
     `verify.json` files. Commands re-run below are my own probes, needed
     because the recorded output plus the diff could not decide the criterion.

     PROBES (each in a throwaway copy under /tmp):
       1. Both pointer suites at the reviewed product: `12 passed, 5 skipped`,
          exit 0; `-rs` names the five skips as the pre-existing `.gsd`-only
          guards (tests/test_project_state_roadmap_freshness.py:126, 137, 171,
          201, 231), so nothing was newly silenced.
       2. E1 — shipped surface (phase shipped, status done, archive
          `.project/archive/009-projection-at-ship`) with the projection left
          at `pointer-in-ci`: `1 failed, 11 passed, 5 skipped`;
          `test_native_marker_names_the_operational_milestone` fails with
          "roadmap.json current_milestone.id 'pointer-in-ci' != shipped
          STATE.md milestone 'projection-at-ship'". Naming the previous
          milestone is loud.
       3. E3 — the M008 shipped surface (`.project/STATE.md` from `4dd35d25`)
          plus this product's projection: `12 passed, 5 skipped`.
       4. End state — shipped/done plus `archive/009-projection-at-ship` plus
          the projection refreshed to `projection-at-ship`: `12 passed,
          5 skipped`. A green shipped tree for M009 is reachable.
       5. E2, per-step deletion of docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md:
          step 1 deleted -> `1 failed`; step 2 deleted -> `1 failed`; step 3
          deleted -> `7 passed`, exit 0; all three steps deleted -> `1 failed`
          (only because step 1 carried the sole `prd/project-state/data/
          roadmap.json` mention).
       6. E2, prose rewrite keeping all nine pinned tokens and zero numbered
          steps -> `7 passed`, exit 0.
       7. Ship gate, `archive_milestone.require_clean_active_root` on a faithful
          `prepare` end state (transaction directories moved into the archive,
          pending `DOCS-AUDIT.md` carried back): at this HEAD the call returns
          clean; at `7594043e` (T001 only) it raises `ArchiveError: unexpected
          active .project paths remain: WORKFLOW-NOTES.md`.
       8. Ordering, `_common.reviewed_head_covers`: one `docs:` commit that
          touches `prd/project-state/data/roadmap.json` after the reviewed HEAD
          returns False, so a refresh landing after the final review
          invalidates it.
       9. Gate shape: a T001-only artifact validates
          (`{"cycle": 2, "owned": ["SC1", "SC2", "SC3"], "verdict": "blocked"}`);
          the same artifact with a T002 section is rejected.
      10. Changed paths across `4931a615..3c1295f2` are only the tasks' `files`
          plus their task files; `.github/` has a 0-line diff; the tests diff
          adds no `skip`/`xfail` and removes no test line. -->

Wave verdict: blocked
Cycle: 1
Depth: full
Tasks reviewed: 1

## T001 — Record the ship-time projection refresh and name the shipping milestone: fail

- ✅ The projection names the milestone being shipped (E1: naming the previous one fails the pointer suites). — In flight the projection is one consistent view anchored on the last landed milestone: `prd/project-state/data/roadmap.json:614-617` is `"id": "pointer-in-ci"` with `"status": "active"`, the single live marker bullet `prd/project-state/roadmap.md:50` names `pointer-in-ci`, and `008-pointer-in-ci` is the highest archive — the in-flight reading the suites enforce (probe 1, `12 passed, 5 skipped`). The after-ship half is reachable and demonstrated: shipped/done plus `archive/009-projection-at-ship` plus the projection at `projection-at-ship` is `12 passed, 5 skipped` (probe 4), while the same shipped surface left at `pointer-in-ci` fails `test_native_marker_names_the_operational_milestone` with the exact message the M008 CI run produced (probe 2). Held-out E1 — "A projection naming the previous milestone fails the pointer suites once STATE.md names the shipping milestone." — held, in its PLAN-assigned held-out test `tests/test_project_state_roadmap_freshness.py`. Prohibition N1 — "remove the pointer suites from CI to make the run pass" — held: `.github/` has a 0-line diff and both suites are still in the `Product and architecture harness tests` run block at `.github/workflows/repository-quality.yml:153-154`.
- ❌ The refresh rule lives in a tracked file and is pinned (E2, N2). — found: the tracked-file half now holds (`docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` is tracked at HEAD, `git check-ignore` does not ignore it) and the ship gate no longer rejects its home (probe 7: `require_clean_active_root` returns clean at this HEAD and still raises `unexpected active .project paths remain: WORKFLOW-NOTES.md` at `7594043e`), but the pin still does not implement E2, and the rule's recorded location is now a dead path. (a) Cycle-1 finding 2 is not repaired: `tests/test_post_ship_pointers.py:115-125` asserts nine substrings and no step, so deleting prescribed step 3 (`docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md:16`, "Commit with a `docs:` subject, then create the ship commit") leaves the pin green (`7 passed`, exit 0, probe 5), and a prose rewrite that keeps all nine tokens with zero numbered steps also passes (`7 passed`, probe 6). Only steps 1 and 2 now fail when deleted, because each uniquely carries a pinned token. E2 — "A rule file that omits the refresh step fails the pin that names it." — is therefore still violated for step 3, and step 3 is the step that orders the refresh against the ship commit. (b) `prd/project-state/roadmap.md:57` still says the rule lives at `.project/WORKFLOW-NOTES.md`, a path deleted in this wave (`fd056ac5` renamed it); the one in-repo description a cold reader is pointed at now names a nonexistent file, so the rule's recorded location is wrong in the artifact that introduces it.  fix: make the pin read the steps structurally, not by loose substring — assert the three numbered items (a regex over `^\d+\. ` items or the ordered tuple `("1. Set", "2. Rewrite", "3. Commit")` with the step text each item must contain) so deleting any one item fails, and assert the ordering clause that step 3 needs: the refresh `docs:` commit, then the final review at the new HEAD, then the ship commit (probe 8 shows a `docs:` refresh after the review makes `reviewed_head_covers` False and preflight blocks with a stale `Reviewed HEAD`). Then change `prd/project-state/roadmap.md:57` to name `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`.
- ✅ The pointer suites pass on the bound branch and on the shipped tree (E3, N3). — On the bound product at `3c1295f2`: `12 passed, 5 skipped`, exit 0 (probe 1). On the shipped tree (`.project/STATE.md` from the M008 ship `4dd35d25` plus this projection): `12 passed, 5 skipped`, exit 0 (probe 3). Held-out E3 — "A projection left at the build-time milestone fails the run rather than passing quietly." — held: at the shipped surface with the previous milestone still named, `test_native_marker_names_the_operational_milestone` fails naming both slugs (probe 2). Prohibition N3 — "mark the pointer suites xfail or skip on the shipped tree" — held: the tests diff adds no `skip`/`xfail`, removes no test line, and `-rs` shows the five skips are the pre-existing `.gsd`-only guards.

Warnings (non-blocking):
- T002's Verify (`uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`) does not run the suite the repair changed: the pin lives in `tests/test_post_ship_pointers.py`, so the recorded exit-0 output cannot show the new pin works. The pin is exercised only by the PLAN project Verify and CI.
- Rule step 3 still omits the ordering constraint the bundled ship runtime enforces: after a `docs:` refresh commit, `_common.reviewed_head_covers` returns False for the pre-refresh reviewed HEAD (probe 8), so a ship agent following the file literally invalidates the review it just obtained. A ship agent needs "refresh `docs:` commit, then final review at the new HEAD, then the ship commit".
- The dated `ci-fixture-fix` record (ship `e890831e`, merge `121a2006`) that sat in the live bullet's "Superseded bullet (2026-10-28)" clause at `4931a615` is gone at this HEAD: `7594043e` dropped it and T002 restored only the M007 record. The same record-loss defect now spans three cycles (cycle 1 warned that `ci-fixture-fix` absorbed `006-red-ci-clear`).
- `prd/project-state/roadmap.md:59-60` still points at `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` as the current-state document while the live bullet moves to M008; that report is dated to the M008 ship, so the pointer is one milestone behind in turn.
- T001's `files` frontmatter still lists `.project/WORKFLOW-NOTES.md`, the path the repair deleted, and does not list `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`. `review_findings.py collect` therefore hands a T001-derived fix batch that path as a file to change, while `tests/test_post_ship_pointers.py:128` fails if it exists again. The fix for this review must land in T002's scope, or T001's `files` needs a plan-level correction.
- T002's product changes landed in the orchestrator commit `fd056ac5`, before T002's recorded base `ef338d6d`; T002's own landing commit `3c1295f2` carries only its task file. The reviewed product is the combined diff as the brief directs, so no verdict rests on the split, but the landing is not a single-commit task patch.

Contract violations (blocking):
- none — every changed path is in the tasks' `files` plus its own task file. In T001's task file only `status`, `agent` and `base` changed (orchestrator-owned) plus an append-only Log entry; its Intent coverage `- SC2` line was removed by `fd056ac5` and restored verbatim by `50530b64`, so the net commit body is unchanged. T002's landing commit changes only `status`, `agent`, `base` and its Log.

## Intent coverage

### SC1 — SC1 — The tracked projection names the milestone being shipped: after this milestone's ship, `roadmap.json` `current_milestone.id` equals the milestone in `.project/STATE.md`, and the live marker bullet names the same slug.: pass
- ✅ While `.project/STATE.md` is in flight on `projection-at-ship` (phase build, branch `gsd-path/M009`), the projection is the consistent in-flight view: `prd/project-state/data/roadmap.json:614-617` is `"pointer-in-ci"` with status active, the single live marker bullet `prd/project-state/roadmap.md:50` names `pointer-in-ci`, and `008-pointer-in-ci` is the highest archive. The after-ship half is reachable: shipped/done plus `archive/009-projection-at-ship` plus the projection at `projection-at-ship` is `12 passed, 5 skipped` (probe 4), while the same shipped surface left at `pointer-in-ci` fails with "roadmap.json current_milestone.id 'pointer-in-ci' != shipped STATE.md milestone 'projection-at-ship'" (probe 2). Held-out E1 held in `tests/test_project_state_roadmap_freshness.py`. Prohibition N1 held: `.github/` has a 0-line diff and both suites remain in CI at `.github/workflows/repository-quality.yml:153-154`. No regression from the cycle-1 repair: T002 left `roadmap.json` untouched.

### SC2 — SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build.: fail
- ❌ SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build. — found: the home is repaired but the two things that make the rule reachable and enforced are not. (a) Nothing in the ship path reads the rule: a grep over the tracked tree at HEAD finds `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` named only by the pin (`tests/test_post_ship_pointers.py:96,111`), by PLAN.md's T002 row, by INTENT.md's scope line and by `prd/project-state/roadmap.md:57` — and that last reference names the deleted `.project/WORKFLOW-NOTES.md`, so the only reader-facing pointer in the repository is wrong. No phase skill, no AGENTS.md entry and no roadmap pointer resolves to the live file. (b) The pin does not fail a rule file that omits a prescribed step: deleting step 3 (`docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md:16`) leaves `test_ship_time_projection_refresh_rule_is_recorded` green (`7 passed`, exit 0, probe 5), and a prose rewrite with all nine pinned tokens and no numbered steps also passes (probe 6), so E2 — "A rule file that omits the refresh step fails the pin that names it." — is still violated. What did improve, and is why the gate half is closed: the rule left `.project/` (`fd056ac5` renamed it), `.project/` carries no unexpected entry (`git ls-tree 3c1295f2:.project` minus the seven transaction directories is `STATE.md` and `archive`), and a faithful `prepare` end state now passes `require_clean_active_root` where `7594043e` raised `unexpected active .project paths remain: WORKFLOW-NOTES.md` (probe 7). Prohibition N2 — "encode the rule only in a chat message" — held: the rule is in a tracked, non-ignored file.
  fix: (1) point the repository at the live file — change `prd/project-state/roadmap.md:57` to `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` and add the file to the AGENTS.md agent-stack paragraph next to the current-state document, so a fresh ship session reads it; (2) make the pin read the prescribed steps structurally (three numbered items with their text, plus the ordering clause) so deleting any one fails; (3) add to rule step 3 that the final review must follow the `docs:` refresh commit and precede the ship commit, since a refresh after the review makes `reviewed_head_covers` False and preflight blocks.

### SC3 — SC3 — `uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py -q` reports 0 failures on the bound branch and on the shipped tree.: pass
- ✅ On the bound product at `3c1295f2`: `12 passed, 5 skipped`, exit 0 (probe 1). On the shipped tree (`.project/STATE.md` from the M008 ship `4dd35d25` with this product's projection): `12 passed, 5 skipped`, exit 0 (probe 3). Held-out E3 held: at the shipped surface with the previous milestone still named, `test_native_marker_names_the_operational_milestone` fails naming both slugs rather than passing quietly (probe 2). Prohibition N3 held: the tests diff adds no `skip`/`xfail`, removes no test line, and `-rs` shows the five skips are the pre-existing `.gsd`-only guards.

## Fixed since last cycle

- Cycle-1 finding 1 (the refresh rule must not sit in `.project/`, and `.project/` must carry no unexpected entry) — confirmed fixed. `fd056ac5` renamed `.project/WORKFLOW-NOTES.md` to `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`; `git ls-tree 3c1295f2:.project` minus the transaction directories is exactly `STATE.md` and `archive`; and probe 7 shows `require_clean_active_root` clean at this HEAD against `ArchiveError: unexpected active .project paths remain: WORKFLOW-NOTES.md` at `7594043e`.
- Cycle-1 finding 2 (the pin must read every step the rule prescribes, so deleting a step fails it) — partially repaired, still failing. Steps 1 and 2 now fail the pin when deleted; step 3 does not (probe 5), and a prose rewrite with all nine pinned tokens and no numbered steps passes (probe 6). Recorded above as the T001 AC2 failure and the SC2 failure; the same criterion fails for a narrower reason than in cycle 1 (the tracked-file and gate halves now hold).
- Cycle-1 finding 3 (the dated M007 superseded record must be restored in the live marker block) — confirmed fixed. `prd/project-state/roadmap.md:61-64` carries "Local GSD workflow marker (superseded 2026-10-28): ci-proof-inputs" with ship commit `e311f0ed`, integration merge `50386e26`, tag `milestone/007-ci-proof-inputs` and archive `.project/archive/007-ci-proof-inputs`, and the file keeps exactly one live marker bullet so `test_native_marker_names_the_operational_milestone` still passes.
- Regressions introduced by the repair: `prd/project-state/roadmap.md:57` now points at the deleted `.project/WORKFLOW-NOTES.md`; and the dated `ci-fixture-fix` record present at `4931a615` is absent at this HEAD (warning above).

## Summary for orchestrator

- T002 — Fix wave 1 cycle 1 review findings in T001: fail (no section: its task file declares `wave: 2`, so a wave 1 artifact may not carry it; the gate rejects such a section, probe 9). Judged from its recorded base `ef338d6d` plus the combined diff against its own two acceptance criteria: "SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build." fails for the two reasons recorded under SC2 above, and "The refresh rule lives in a tracked file and is pinned (E2, N2)." fails for the same pin defect. Its relocation of the rule out of `.project/` and its restoration of the M007 record are real repairs and are credited under "Fixed since last cycle".
- blocked findings: one group, one file scope. T001 AC2 and SC2 both resolve to `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` plus its pin `tests/test_post_ship_pointers.py:96-131` plus the stale pointer `prd/project-state/roadmap.md:57`. The remaining defect is narrow and mechanical: the pin asserts nine loose substrings instead of the three numbered steps, so deleting step 3 passes; and the roadmap still names the deleted `.project/WORKFLOW-NOTES.md`. Do not re-run the task Verifies; fix the pin and the pointer.
- repeat offenders: "the pin must read every prescribed step" now fails in two cycles — the cycle-1 fix added tokens that happen to sit inside steps 1 and 2 but never reads the step structure, so step 3 stayed unpinned. Also still open across cycles: each refresh drops the immediately previous shipment's dated record (`ci-fixture-fix`, ship `e890831e`, merge `121a2006`, is now missing). Both are plan-level defects worth a LESSONS.md entry at ship.
- warnings worth a human eye: (a) T002's Verify does not run the suite its repair changed; (b) rule step 3 omits that the final review must follow the `docs:` refresh commit, which preflight enforces; (c) `prd/project-state/roadmap.md:59-60` still points at the M008-dated current-state report.
