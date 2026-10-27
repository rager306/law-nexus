---
id: T002
title: Sync the workflow marker to the Path milestone
wave: 1
deps: []
status: done
agent: build_T002
base: 0c502255a94c188f29ef48019403ab7cd6308192
worktree: null
task_branch: null
files:
  - prd/project-state/roadmap.md
  - prd/project-state/data/roadmap.json
  - tests/test_project_state_roadmap_freshness.py
  - .gitignore
---

# T002 — Sync the workflow marker to the Path milestone

## Context

Define set the native milestone 001-native-workflow-acceptance in .project/STATE.md, but the tracked roadmap front still names the frozen Pi milestone M225-qrwdfv as active — the marker bullet near the top of prd/project-state/roadmap.md and the current_milestone block in prd/project-state/data/roadmap.json. The governor's roadmap-current-tracks-path check compares the roadmap data against the live native milestone by identity, so it fails on the bound branch until the sync lands; SYNTHESIS lists this as wave-1 blocker 3 because the branch-locked, fail-closed governor gates every later native claim. SC2 requires the marker to name this Path milestone slug exactly and the governor to report 0 errors with the milestone set. E2 makes a missing or mismatched marker a fail-closed blocking error. This is also the audit #15 ride-along named in INTENT Scope in.

## Approach

- N4 is the hard line: only the workflow-marker bullet changes in prd/project-state/roadmap.md — the bullet that begins with the words Local GSD workflow marker. The superseded 2026-10-16 marker bullet below it is historical and stays untouched; no M-number registry row, completed-milestone line, requirements status, or any other line in that file moves. The final reviewer diffs the file against exactly this rule.
- Update the current_milestone identity in prd/project-state/data/roadmap.json to id 001-native-workflow-acceptance with status active, plus its title and goal describing this Path milestone, so the governor comparison passes by identity and never by sequence-number guessing. Do not touch completed_milestone_groups, sanctioned_execution_chain, or any historical record.
- Extend tests/test_project_state_roadmap_freshness.py with a native marker test that reads the tracked .project/STATE.md milestone, the roadmap.json current_milestone.id, and the roadmap.md marker bullet, and asserts exact slug equality across all three (E2). The test reads tracked files directly so it runs in any sidecar; the legacy registry tests keep their skip behavior under operational native state.
- Record a bound-branch governor run (`uv run --frozen python -m law_nexus_harness.governor`) with 0 errors in the task Log as the SC2 evidence. A verify sidecar legitimately shows only the branch-ownership error — that is the documented fail-closed behavior — so the Verify below is sidecar-safe by design.

## Interface contract

- None

## Intent coverage

- SC2

## Acceptance criteria

1. The diff of prd/project-state/roadmap.md touches only the marker bullet (N4), and that bullet names the milestone 001-native-workflow-acceptance exactly — the full slug, not a prefix, suffix, or reworded variant (E2, fail-closed on mismatch).
2. prd/project-state/data/roadmap.json has current_milestone.id equal to 001-native-workflow-acceptance with status active; no historical row, completed group, or recorded hash changed.
3. The new native marker test asserts exact identity between the STATE.md milestone, the roadmap.json current_milestone.id, and the roadmap.md marker bullet, and does not skip when the native state is operational.
4. The task Log records a governor run on gsd-path/M001 reporting 0 errors with the milestone set and no pre-milestone exception in play.

## Verify

```bash
uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q
```

Heavy: no

## Log

- 2026-10-26 — plan-defect repair (orchestrator, per build-native step 2 and the finish preflight receipt): `files` gains `.gitignore` — this landing also anchors the legacy product rules `build/` → `/build/` and `archive/` → `/archive/` (exactly two lines, no other ignore changes), because unanchored rules swallow `.project/build/` and `.project/archive/` which GSD Path state must track; the landing must precede T001 whose Verify depends on this marker. Acceptance criterion added: the landing commit includes exactly that two-line `.gitignore` anchoring.

- 2026-10-26 — build_T002 implemented: roadmap.md now names 001-native-workflow-acceptance in the live workflow-marker bullet (only that bullet changed — N4; superseded bullets and all other lines untouched); roadmap.json current_milestone synced to id 001-native-workflow-acceptance / status active with a Path-milestone title and goal (no completed group, sanctioned chain, or recorded hash changed); tests/test_project_state_roadmap_freshness.py gains test_native_marker_names_the_operational_milestone asserting exact three-way slug identity (.project/STATE.md milestone ↔ roadmap.json current_milestone.id ↔ roadmap.md live marker bullet; skip only when the checkout has no .project/STATE.md milestone — negative checks confirmed fail-closed on id mismatch, missing slug, prefix/suffix variant, and duplicate live bullets). Verify `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q` → exit 0, 1 passed, 5 skipped (legacy registry tests keep their skip under operational native state). SC2 evidence: `uv run --frozen python -m law_nexus_harness.governor` in this authorized task worktree (native state operational-valid, milestone 001-native-workflow-acceptance, phase build, STATE.branch gsd-path/M001) → status ok, 0 errors, 0 warns, 72 passes; roadmap-current-tracks-path passes by identity (comparison=path); workflow-state-surface reports operational mode — no pre-milestone/bootstrap exception in play. Baseline before the change: same full run reported exactly one error, roadmap-current-tracks-path (roadmap_current=M225-qrwdfv).
- 2026-10-26 — orchestrator Verify (isolate gsd-path-task/T002): pass, exit 0; output tail:
  ```
  sssss.                                                                   [100%]
  1 passed, 5 skipped in 4.26s
  ```
- 2026-10-26 — build_T002 r1 (base 0c502255a94c188f29ef48019403ab7cd6308192; r0 product edits were reset with the earlier base, so the sync was re-applied here): roadmap.md live marker bullet again names 001-native-workflow-acceptance (only that bullet changed — N4; superseded bullet and all other lines untouched); roadmap.json current_milestone synced to id 001-native-workflow-acceptance / status active with the Path-milestone title and goal (no completed group, sanctioned chain, or recorded hash changed); tests/test_project_state_roadmap_freshness.py gains test_native_marker_names_the_operational_milestone asserting exact three-way slug identity (.project/STATE.md milestone ↔ roadmap.json current_milestone.id ↔ roadmap.md live marker bullet; skip only when the checkout has no .project/STATE.md milestone). NEW in r1 per the plan-defect repair: .gitignore anchors exactly two legacy product rules, `build/` → `/build/` and `archive/` → `/archive/` — byte-minimal two-line diff, no other ignore rule touched; `git check-ignore` proves `.project/build/…` and `.project/archive/…` are no longer swallowed (trackable — the r0 landing-preflight blocker) while root `build/`/`archive/` stay ignored via the anchored rules, and the anchoring surfaces no new untracked path (the only on-disk build/archive-named tree is tracked `prd/archive/`). Negative checks run through the task's own uv env against temp copies (no repository file mutated): pristine passes; id mismatch, missing live bullet, prefix variant (X001-…), suffix variant (…-x), and duplicate live bullets each fail the test (fail-closed); absent native STATE.md → skip. Verify `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q` → exit 0, 1 passed, 5 skipped (legacy registry tests keep their skip under operational native state). SC2 evidence: `uv run --frozen python -m law_nexus_harness.governor` in this authorized task worktree (native state operational-valid, milestone 001-native-workflow-acceptance, phase build, STATE.branch gsd-path/M001) → exit 0, status ok, 0 errors, 71 passes, 1 advisory warn: document-freshness-triggers trigger archive-policy-change — the r1 .gitignore anchoring itself matches that catalog entry (sources include .gitignore), whose companion surfaces (src/law_nexus_harness/governor.py, tests/test_harness_governor.py, assessment/07-adr-archive-governor-audit.md) are T001's files, so the advisory clears when T001 lands; SC2's 0-errors bar holds. roadmap-current-tracks-path passes by identity (comparison=path, roadmap_current=001-native-workflow-acceptance); workflow-state-surface reports operational native mode (backend=gsd-path, legacy_gsd=absent) — no pre-milestone/bootstrap exception in play. Delta vs the r0 recorded governor run (72 passes, 0 warns): the single advisory warn is introduced by the r1 anchoring itself.
- 2026-10-26 — orchestrator Verify (isolate gsd-path-task/T002): pass, exit 0; output tail:
  ```
  sssss.                                                                   [100%]
  1 passed, 5 skipped in 3.72s
  ```
