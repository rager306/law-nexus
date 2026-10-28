---
id: T003
title: Fix wave 1 cycle 2 review findings in T001
wave: 3
deps: [T001, T002]
status: done
agent: build_T003
base: 825b509629bf579950164db720c5288021a2178f
worktree: null
task_branch: null
files:
  - docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md
  - prd/project-state/data/roadmap.json
  - prd/project-state/roadmap.md
  - tests/test_post_ship_pointers.py
  - tests/test_project_state_roadmap_freshness.py
---

# T003 — Fix wave 1 cycle 2 review findings in T001

## Context

Repair task created from the wave 1 cycle 2 review of T001.
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
- SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build. — found: the home is repaired but the two things that make the rule reachable and enforced are not. (a) Nothing in the ship path reads the rule: a grep over the tracked tree at HEAD finds `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` named only by the pin (`tests/test_post_ship_pointers.py:96,111`), by PLAN.md's T002 row, by INTENT.md's scope line and by `prd/project-state/roadmap.md:57` — and that last reference names the deleted `.project/WORKFLOW-NOTES.md`, so the only reader-facing pointer in the repository is wrong. No phase skill, no AGENTS.md entry and no roadmap pointer resolves to the live file. (b) The pin does not fail a rule file that omits a prescribed step: deleting step 3 (`docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md:16`) leaves `test_ship_time_projection_refresh_rule_is_recorded` green (`7 passed`, exit 0, probe 5), and a prose rewrite with all nine pinned tokens and no numbered steps also passes (probe 6), so E2 — "A rule file that omits the refresh step fails the pin that names it." — is still violated. What did improve, and is why the gate half is closed: the rule left `.project/` (`fd056ac5` renamed it), `.project/` carries no unexpected entry (`git ls-tree 3c1295f2:.project` minus the seven transaction directories is `STATE.md` and `archive`), and a faithful `prepare` end state now passes `require_clean_active_root` where `7594043e` raised `unexpected active .project paths remain: WORKFLOW-NOTES.md` (probe 7). Prohibition N2 — "encode the rule only in a chat message" — held: the rule is in a tracked, non-ignored file. fix: (1) point the repository at the live file — change `prd/project-state/roadmap.md:57` to `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` and add the file to the AGENTS.md agent-stack paragraph next to the current-state document, so a fresh ship session reads it; (2) make the pin read the prescribed steps structurally (three numbered items with their text, plus the ordering clause) so deleting any one fails; (3) add to rule step 3 that the final review must follow the `docs:` refresh commit and precede the ship commit, since a refresh after the review makes `reviewed_head_covers` False and preflight blocks.

### t001_ac2
Criterion: The refresh rule lives in a tracked file and is pinned (E2, N2).
- The refresh rule lives in a tracked file and is pinned (E2, N2). — found: the tracked-file half now holds (`docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` is tracked at HEAD, `git check-ignore` does not ignore it) and the ship gate no longer rejects its home (probe 7: `require_clean_active_root` returns clean at this HEAD and still raises `unexpected active .project paths remain: WORKFLOW-NOTES.md` at `7594043e`), but the pin still does not implement E2, and the rule's recorded location is now a dead path. (a) Cycle-1 finding 2 is not repaired: `tests/test_post_ship_pointers.py:115-125` asserts nine substrings and no step, so deleting prescribed step 3 (`docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md:16`, "Commit with a `docs:` subject, then create the ship commit") leaves the pin green (`7 passed`, exit 0, probe 5), and a prose rewrite that keeps all nine tokens with zero numbered steps also passes (`7 passed`, probe 6). Only steps 1 and 2 now fail when deleted, because each uniquely carries a pinned token. E2 — "A rule file that omits the refresh step fails the pin that names it." — is therefore still violated for step 3, and step 3 is the step that orders the refresh against the ship commit. (b) `prd/project-state/roadmap.md:57` still says the rule lives at `.project/WORKFLOW-NOTES.md`, a path deleted in this wave (`fd056ac5` renamed it); the one in-repo description a cold reader is pointed at now names a nonexistent file, so the rule's recorded location is wrong in the artifact that introduces it. fix: make the pin read the steps structurally, not by loose substring — assert the three numbered items (a regex over `^\d+\. ` items or the ordered tuple `("1. Set", "2. Rewrite", "3. Commit")` with the step text each item must contain) so deleting any one item fails, and assert the ordering clause that step 3 needs: the refresh `docs:` commit, then the final review at the new HEAD, then the ship commit (probe 8 shows a `docs:` refresh after the review makes `reviewed_head_covers` False and preflight blocks with a stale `Reviewed HEAD`). Then change `prd/project-state/roadmap.md:57` to name `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`.

## Log

- 2026-10-28 — created by dispatch_driver.py fix-tasks from wave 1 cycle 2
- 2026-10-28 — orchestrator Verify (sidecar gsd-path-verify/task-t003-verify): pass, exit 0; output tail:
  ```
  sssss.....                                                               [100%]
  5 passed, 5 skipped in 4.65s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t003-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t003-verify
  Installed 32 packages in 332ms
  ```
- 2026-10-28 — orchestrator regression Verify of T001 (sidecar gsd-path-verify/task-t003-verify): pass, exit 0; output tail:
  ```
  sssss.....                                                               [100%]
  5 passed, 5 skipped in 3.94s
  ```
