---
id: T002
title: Fix wave 1 cycle 1 review findings in T001
wave: 2
deps: [T001]
status: pending
agent: null
base: null
worktree: /root/law-nexus
task_branch: null
files:
  - docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md
  - prd/project-state/data/roadmap.json
  - prd/project-state/roadmap.md
  - tests/test_post_ship_pointers.py
  - tests/test_project_state_roadmap_freshness.py
---

# T002 — Fix wave 1 cycle 1 review findings in T001

## Context

Repair task created from the wave 1 cycle 1 review of T001.
The failed criteria and every reviewer observation are recorded verbatim under Review findings.
The source task contracts are unchanged; read them and .project/intent/INTENT.md before editing.

## Approach

- Fix only what the Review findings name, inside the listed files; do not change the source
  tasks' acceptance criteria or interface contracts.
- Re-run the source tasks' Verify commands after the fix and record the result in the Log.

## Interface contract

- None

## Intent coverage

- None

## Acceptance criteria

1. SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build.
2. The refresh rule lives in a tracked file and is pinned (E2, N2).

## Verify

```bash
set -e
(
uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q
)
```

Heavy: no

## Review findings

### sc2
Criterion: SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build.
- SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build. — found: the rule is recorded in `.project/WORKFLOW-NOTES.md`, which no phase reads and which the ship gate rejects. Grep across `.agents/skills/gsd-path-ship/` and `.agents/skills/gsd-path-build/` finds no reference to `WORKFLOW-NOTES`, so "where the next ship reads it" has no machine path. Worse, the placement blocks the ship rather than steering it: with the active root in the `prepare` end state, `archive_milestone.require_clean_active_root` raises `unexpected active .project paths remain: WORKFLOW-NOTES.md` because its top-level allowlist is `STATE.md`, `REPOSITORY.md`, `MEMBERS.md`, `archive`, `LESSONS.md`, `next` plus settings, and this checkout has no `CHARTER.md` to add the program-flow names — the same blocker M001 needed an owner ruling and relocation commit `f3c55d6d` to clear. So the rule does not prevent the recurrence; it stops the ship that would apply it. The pin also does not cover the recorded edge: E2 — "A rule file that omits the refresh step fails the pin that names it." — is violated, since a file with the four keywords and no steps passes `test_ship_time_projection_refresh_rule_is_recorded`. The rule's own step 2 (fold the previous shipment into a dated superseded record) was not applied either: `ci-proof-inputs` and its `e311f0ed` / `50386e26` / tag / archive record are absent from `prd/project-state/roadmap.md`. Prohibition N2 — "encode the rule only in a chat message" — held: the rule is in a tracked, non-ignored file. fix: relocate the rule to an allowlisted, ship-persistent location a phase reads (`.project/LESSONS.md`, which ships and never archives, or a reference inside the installed ship skill), name it from the ship phase so the next ship is pointed at it, and strengthen the pin to require the numbered refresh steps and the final-review ordering; also fold the M007 shipment into a dated superseded bullet so the rule's own step 2 is satisfied.

### t001_ac2
Criterion: The refresh rule lives in a tracked file and is pinned (E2, N2).
- The refresh rule lives in a tracked file and is pinned (E2, N2). — found: the file is tracked (`git ls-files` lists `.project/WORKFLOW-NOTES.md`) and N2 holds, but two defects break the criterion. (a) The pin does not implement E2: a rule file that keeps `current_milestone`, `docs:`, `ship commit` and `tests/test_post_ship_pointers.py` while omitting all three numbered refresh steps passes `test_ship_time_projection_refresh_rule_is_recorded` (`tests/test_post_ship_pointers.py:99-117` asserts four substrings only, no step), so "a rule file that omits the refresh step fails the pin that names it" is violated — probe 5 reports `1 passed`. (b) The file's home blocks the ship it describes: `archive_milestone.require_clean_active_root` allows only `STATE.md`, `REPOSITORY.md`, `MEMBERS.md`, `archive`, `LESSONS.md`, `next` (plus settings, plus `CHARTER.md`/`ROADMAP.md`/`SYNTHESIS.md` in program flow) at the `.project` top level, so once `prepare` moves the transaction directories the active root carries `WORKFLOW-NOTES.md` and preflight raises `unexpected active .project paths remain: WORKFLOW-NOTES.md` (probe 6). This is the same class of blocker M001 recorded in `.project/STATE.md` and cleared only by an owner ruling plus the relocation commit `f3c55d6d`. fix: move the rule into an archived or allowlisted location that a phase actually reads — for example a section of `.project/LESSONS.md` (allowlisted, ships, never archives) or a reference under the installed `gsd-path-ship` skill — and make the pin assert the executable content, not four substrings: require the numbered refresh steps and the ordering clause (refresh `docs:` commit, then final review at the new HEAD, then the ship commit), and require the ship/build skill to name the file so the next ship reads it.

## Log

- 2026-10-28 — created by dispatch_driver.py fix-tasks from wave 1 cycle 1
