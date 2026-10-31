---
id: T001
title: Refresh the M011 projection and make the current-state document honest
wave: 1
deps: []
status: pending
agent: null
base: null
worktree: null
task_branch: null
files:
  - prd/project-state/roadmap.md
  - prd/project-state/data/roadmap.json
  - docs/agent-stack/POST-SHIP-STATE-2026-10-28.md
---

# T001 — Refresh the M011 projection and make the current-state document honest

## Context

The M011 ship skipped the pinned ship-time projection refresh, so `prd/project-state/roadmap.md` and `roadmap.json` still front `doc-consistency` (M010) while M011 `reference-front-door` is shipped, integrated (`ef17106b`), tagged (`milestone/011-reference-front-door`) and archived (`011-reference-front-door`; ship commit `38abe687`). The pointer suites are red locally and in CI on main (run 41198873586 at `ef17106b`, FAILURE on the projection suites), while `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` still asserts a live green state (runs 40805352394/40822037565) and its bootstrap step 4 says to expect all tests to pass. Audit rows #39-#43; rulings recorded in DOCS-AUDIT.md `## User rulings`.

## Approach

- Follow `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` to refresh `roadmap.md` and `prd/project-state/data/roadmap.json` with the M011 delivered record (milestone `reference-front-door`, ship `38abe687`, integration `ef17106b`, archive `.project/archive/011-reference-front-door`); keep marker-row conventions and E1 idempotency (the procedure is deterministic from recorded fields).
- POST-SHIP-STATE-2026-10-28.md: append the M011 delivered record after the existing dated records (N1: nothing rewritten or deleted); replace the live-green claims (lines 54-58, 207-211) with the honest current state — newest main run 41198873586 at `ef17106b` FAILURE on the projection suites, prior green runs kept as dated history; fix the bootstrap step-4 expectation (lines 191-196) to expect all tests to pass again once the refresh lands; update the header/role block (lines 5-7, 97-100) so the delivered record ends at M011.
- Touch only the declared files. No product code, no archives.

## Interface contract

None

## Intent coverage

- SC1
- SC2

## Acceptance criteria

1. `prd/project-state/roadmap.md` and `roadmap.json` front the M011 record (`reference-front-door`, ship `38abe687`, integration `ef17106b`, archive `011-reference-front-door`) and `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py tests/test_post_ship_pointers.py -q` reports 0 failures at HEAD.
2. POST-SHIP-STATE-2026-10-28.md carries the appended M011 record, names run 41198873586 at `ef17106b` as the newest main FAILURE with 40805352394/40822037565 kept as dated history, and the bootstrap step-4 text expects all tests to pass; the M011 record lands after the existing dated records.

## Verify

```bash
grep -q 'reference-front-door' prd/project-state/roadmap.md prd/project-state/data/roadmap.json && uv run --frozen pytest tests/test_project_state_roadmap_freshness.py tests/test_post_ship_pointers.py -q
```

Heavy: no

## Log

- 2026-10-31 — created by orchestrator (quick mode, rows #39-#43)
