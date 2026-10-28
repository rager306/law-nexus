# Review — wave 1, cycle 1

<!-- Reviewer role, wave mode (full). PLAN.md Wave 1 Review depth is `full`, so no
     lens applies.

     SIDECAR HEAD: 7594043e33ecb125b2dd399e8c0c9647772aab1a (branch
     gsd-path/M009, tracked tree clean at start and end). One task landed:
     T001 7594043e on base 4931a6157f847596742935f57508826a33622c83. Serial
     round, so the sidecar tree equals base plus only that patch; no product had
     to be reconstructed separately.

     METHOD. `git diff 4931a615..7594043e` = 5 files, +64/-15:
     `.project/WORKFLOW-NOTES.md` (new, 17 lines), `prd/project-state/data/roadmap.json`
     +1/-1, `prd/project-state/roadmap.md` +11/-11, `tests/test_post_ship_pointers.py`
     +22/-0, and the task file (frontmatter + append-only Log). `.github/` is
     untouched (0 diff lines), and the tests diff adds no skip/xfail (0 matches).
     The recorded orchestrator Verify in the T001 Log (sidecar
     gsd-path-verify/task-t001-verify, exit 0, `5 passed, 5 skipped`) is the
     Verify evidence; no verdict rests on a repeat of it. (It was re-run once
     early and agreed; that repeat is discarded as evidence.)

     Independent re-runs of my own, only where the recorded output plus the
     isolated diff could not check the criterion, each in a throwaway copy of
     this sidecar under /tmp:
       1. Both pointer suites on the reviewed tree: `12 passed, 5 skipped`,
          exit 0. The five skips are the pre-existing `.gsd`-only guards, and
          `-rs` names them, so they are not newly silenced.
       2. E1 / AC1 — shipped surface with the previous milestone still named
          (`phase: shipped`, `status: done`, `archive: .project/archive/009-...`,
          projection `pointer-in-ci`): `test_native_marker_names_the_operational_milestone`
          fails with "roadmap.json current_milestone.id 'pointer-in-ci' != shipped
          STATE.md milestone 'projection-at-ship'". Naming the previous milestone
          is loud.
       3. E3 — the M008 shipped surface (`.project/STATE.md` from `4dd35d25`) plus
          this commit's projection: `12 passed, 5 skipped`. The shipped tree
          today is green.
       4. The consistent end state (`shipped/done` plus `archive/009` plus the
          projection refreshed to `projection-at-ship`): `12 passed, 5 skipped`.
          So a green shipped tree for M009 is reachable.
       5. E2 — a rule file that keeps all four pinned substrings and omits every
          numbered refresh step: the pin PASSES (`1 passed`). It only fails when
          a keyword is deleted or the file is emptied.
       6. Ship-gate probe on the bundled helper. In a faithful copy of the
          `prepare` end state (transaction directories moved into
          `archive/009-projection-at-ship`, pending `DOCS-AUDIT.md` carried back
          to the active `research/`), `archive_milestone.require_clean_active_root`
          raises `ArchiveError: unexpected active .project paths remain:
          WORKFLOW-NOTES.md`. Its allowlist is
          `{STATE.md, REPOSITORY.md, MEMBERS.md, archive, LESSONS.md, next}` plus
          the two settings files and, in program flow only, `CHARTER.md`,
          `ROADMAP.md`, `SYNTHESIS.md`; this checkout has no `CHARTER.md`, so
          program-flow names do not apply.
       7. Ordering probe on the bundled helper. In a synthetic repo, one `docs:`
          commit that changes `prd/project-state/data/roadmap.json` between the
          reviewed HEAD and the ship commit makes
          `_common.reviewed_head_covers(reviewed, ship)` return False. Preflight
          and validate both enforce that predicate.
       8. Regression sweep: `tests/test_harness_governor.py` +
          `tests/test_harness_preflight.py` = `267 passed, 2 skipped`.
      9. `git ls-files .project/WORKFLOW-NOTES.md` tracks it and
         `git check-ignore` does not ignore it, so the file does ship in the
         build commit. Grep across `.agents/skills/gsd-path-ship/` and
         `.agents/skills/gsd-path-build/` finds no reference to
         `WORKFLOW-NOTES`: no phase skill reads it. -->

Wave verdict: blocked
Cycle: 1
Depth: full
Tasks reviewed: 1

## T001 — Record the ship-time projection refresh and name the shipping milestone: fail

- ✅ The projection names the milestone being shipped (E1: naming the previous one fails the pointer suites). — In flight, `prd/project-state/data/roadmap.json:615` is `"id": "pointer-in-ci"`, the single live marker bullet `prd/project-state/roadmap.md:50` names `pointer-in-ci`, and `008-pointer-in-ci` is the highest archive, so the three-way in-flight anchor the suites enforce holds. Naming the previous milestone at the shipped surface is loud: probe 2 fails `test_native_marker_names_the_operational_milestone` with the exact message the M008 CI run produced. The end state is reachable: `shipped/done` plus `archive/009-projection-at-ship` plus the projection at `projection-at-ship` is `12 passed, 5 skipped` (probe 4). Recorded Verify exit 0 is consistent.
- ❌ The refresh rule lives in a tracked file and is pinned (E2, N2). — found: the file is tracked (`git ls-files` lists `.project/WORKFLOW-NOTES.md`) and N2 holds, but two defects break the criterion. (a) The pin does not implement E2: a rule file that keeps `current_milestone`, `docs:`, `ship commit` and `tests/test_post_ship_pointers.py` while omitting all three numbered refresh steps passes `test_ship_time_projection_refresh_rule_is_recorded` (`tests/test_post_ship_pointers.py:99-117` asserts four substrings only, no step), so "a rule file that omits the refresh step fails the pin that names it" is violated — probe 5 reports `1 passed`. (b) The file's home blocks the ship it describes: `archive_milestone.require_clean_active_root` allows only `STATE.md`, `REPOSITORY.md`, `MEMBERS.md`, `archive`, `LESSONS.md`, `next` (plus settings, plus `CHARTER.md`/`ROADMAP.md`/`SYNTHESIS.md` in program flow) at the `.project` top level, so once `prepare` moves the transaction directories the active root carries `WORKFLOW-NOTES.md` and preflight raises `unexpected active .project paths remain: WORKFLOW-NOTES.md` (probe 6). This is the same class of blocker M001 recorded in `.project/STATE.md` and cleared only by an owner ruling plus the relocation commit `f3c55d6d`.
  fix: move the rule into an archived or allowlisted location that a phase actually reads — for example a section of `.project/LESSONS.md` (allowlisted, ships, never archives) or a reference under the installed `gsd-path-ship` skill — and make the pin assert the executable content, not four substrings: require the numbered refresh steps and the ordering clause (refresh `docs:` commit, then final review at the new HEAD, then the ship commit), and require the ship/build skill to name the file so the next ship reads it.
- ✅ The pointer suites pass on the bound branch and on the shipped tree (E3, N3). — On the bound branch at `7594043e`: `12 passed, 5 skipped`, exit 0 (probe 1). On the shipped tree (the M008 surface from `4dd35d25` with this commit's projection): `12 passed, 5 skipped` (probe 3). E3 is loud: a projection left at the build-time milestone at the shipped surface fails both suites (probe 2, and the same shape on the freshness suite). N3 holds: `git diff 4931a615..7594043e -- tests/` contains no `skip`/`xfail`, and the five skips are the pre-existing `.gsd`-only guards reported by `-rs`. `.github/` is untouched, so N1 holds as well.

Warnings (non-blocking):
- The rule's own step 2 was not applied by this commit. `prd/project-state/roadmap.md:50-60` replaces the live bullet with the M008 record and does not fold the previous shipment into a dated superseded record: `ci-proof-inputs`, ship `e311f0ed`, merge `50386e26`, tag `milestone/007-ci-proof-inputs` and `archive/007-ci-proof-inputs` no longer appear anywhere in the file, and `006-red-ci-clear` was already missing. Step 2 says "fold the previous shipment into a dated superseded record", so the very first application of the rule skipped it. This repeats the record-loss warning the M008 wave review raised.
- The rule's step 3 ordering is incomplete for the bundled ship runtime. "Commit with a `docs:` subject, then create the ship commit" leaves out that FINAL.md's `Reviewed HEAD` must still cover the ship parent: a `docs:` refresh after the final review makes `reviewed_head_covers` false (probe 7) and preflight blocks with "FINAL.md Reviewed HEAD ... does not match current HEAD". A ship agent following the file literally invalidates the review it just obtained.
- The pin lives in `tests/test_post_ship_pointers.py`, a suite the wave did not need to extend for AC3; it is CI-listed, so the substring pin is at least enforced.
- `prd/project-state/roadmap.md:59-60` still points at `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` as the current-state document while the live bullet moves to M008; that report is dated to the M008 ship, so the pointer is now one milestone behind in turn.

Contract violations (blocking):
- none — the commit changes only paths in the task's `files` plus its own task file, where `status`, `agent` and `base` are orchestrator-owned and the `## Log` entry is append-only; Context, Approach, Interface contract, Intent coverage, Acceptance criteria and Verify are byte-identical.

## Intent coverage

### SC1 — SC1 — The tracked projection names the milestone being shipped: after this milestone's ship, `roadmap.json` `current_milestone.id` equals the milestone in `.project/STATE.md`, and the live marker bullet names the same slug.: pass
- ✅ While `.project/STATE.md` is in flight on `projection-at-ship`, the projection is one consistent view anchored on the last landed milestone: `prd/project-state/data/roadmap.json:615` is `"pointer-in-ci"` with `"status": "active"`, the single live marker bullet `prd/project-state/roadmap.md:50` names `pointer-in-ci`, and `008-pointer-in-ci` is the highest archive — the in-flight reading the suites enforce. The after-ship half is reachable and demonstrated: `shipped/done` plus `archive/009-projection-at-ship` plus the projection at `projection-at-ship` is `12 passed, 5 skipped`, while the same shipped surface left at `pointer-in-ci` fails with "roadmap.json current_milestone.id 'pointer-in-ci' != shipped STATE.md milestone 'projection-at-ship'". Held-out E1 — "A projection naming the previous milestone fails the pointer suites once STATE.md names the shipping milestone." — held. Prohibition N1 — "remove the pointer suites from CI to make the run pass" — held: `.github/` has a 0-line diff and both suites are still in the `Product and architecture harness tests` run block at `.github/workflows/repository-quality.yml:152-154`.

### SC2 — SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build.: fail
- ❌ SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build. — found: the rule is recorded in `.project/WORKFLOW-NOTES.md`, which no phase reads and which the ship gate rejects. Grep across `.agents/skills/gsd-path-ship/` and `.agents/skills/gsd-path-build/` finds no reference to `WORKFLOW-NOTES`, so "where the next ship reads it" has no machine path. Worse, the placement blocks the ship rather than steering it: with the active root in the `prepare` end state, `archive_milestone.require_clean_active_root` raises `unexpected active .project paths remain: WORKFLOW-NOTES.md` because its top-level allowlist is `STATE.md`, `REPOSITORY.md`, `MEMBERS.md`, `archive`, `LESSONS.md`, `next` plus settings, and this checkout has no `CHARTER.md` to add the program-flow names — the same blocker M001 needed an owner ruling and relocation commit `f3c55d6d` to clear. So the rule does not prevent the recurrence; it stops the ship that would apply it. The pin also does not cover the recorded edge: E2 — "A rule file that omits the refresh step fails the pin that names it." — is violated, since a file with the four keywords and no steps passes `test_ship_time_projection_refresh_rule_is_recorded`. The rule's own step 2 (fold the previous shipment into a dated superseded record) was not applied either: `ci-proof-inputs` and its `e311f0ed` / `50386e26` / tag / archive record are absent from `prd/project-state/roadmap.md`. Prohibition N2 — "encode the rule only in a chat message" — held: the rule is in a tracked, non-ignored file.
  fix: relocate the rule to an allowlisted, ship-persistent location a phase reads (`.project/LESSONS.md`, which ships and never archives, or a reference inside the installed ship skill), name it from the ship phase so the next ship is pointed at it, and strengthen the pin to require the numbered refresh steps and the final-review ordering; also fold the M007 shipment into a dated superseded bullet so the rule's own step 2 is satisfied.

### SC3 — SC3 — `uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py -q` reports 0 failures on the bound branch and on the shipped tree.: pass
- ✅ On the bound branch at `7594043e`: `12 passed, 5 skipped`, exit 0. On the shipped tree (`.project/STATE.md` from the M008 ship `4dd35d25` with this commit's projection): `12 passed, 5 skipped`, exit 0. Held-out E3 — "A projection left at the build-time milestone fails the run rather than passing quietly." — held: at the shipped surface with the previous milestone still named, `test_native_marker_names_the_operational_milestone` fails naming both slugs. Prohibition N3 — "mark the pointer suites xfail or skip on the shipped tree" — held: the tests diff adds no `skip`/`xfail`, and `-rs` shows the five skips are the pre-existing `.gsd`-only guards.

## Summary for orchestrator

- blocked findings: T001 AC2 and SC2, both in one file scope (`.project/WORKFLOW-NOTES.md` plus its pin at `tests/test_post_ship_pointers.py:96-117` and the `roadmap.md` marker bullet). The defect is plan-level, not coder-level: the task executed its `files` faithfully, but the chosen home for the rule is outside the ship gate's allowlist and outside every phase's reading path, so the next ship blocks instead of refreshing. Fix by relocating the rule and strengthening the pin; do not re-run the task Verify.
- repeat offenders: the "each refresh drops the immediately previous milestone's dated record" defect now fails to self-apply across two cycles — the M008 review warned that `ci-fixture-fix` was absorbed and `006-red-ci-clear` went unrecorded, and this commit drops `ci-proof-inputs`/`007` the same way, so it is a plan defect worth a lesson entry at ship.
- warnings worth a human eye: (a) the rule's step 3 omits that the final review must follow the `docs:` refresh commit, or preflight rejects the stale `Reviewed HEAD`; (b) `prd/project-state/roadmap.md:59-60` still points at `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md`, now one milestone behind.
