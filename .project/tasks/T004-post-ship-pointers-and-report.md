---
id: T004
title: Make the post-ship pointers truthful and write the dated post-ship report
wave: 2
deps: []
status: pending     # orchestrator-owned: pending | in-progress | done | failed | blocked
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null   # orchestrator-owned: gsd-path-task/<id> while parallel; null when serial
files:
  - prd/project-state/roadmap.md
  - prd/project-state/data/roadmap.json
  - .project/research/DOCS-AUDIT.md
  - docs/agent-stack/history/LEGACY_CROSSWALK.md
  - docs/agent-stack/POST-SHIP-STATE-2026-10-27.md
  - docs/agent-stack/AGENT_HANDOFF.md
  - AGENTS.md
  - tests/test_project_state_roadmap_freshness.py
  - tests/test_post_ship_pointers.py
---

# T004 — Make the post-ship pointers truthful and write the dated post-ship report

## Context

Main is shipped but every pointer a fresh agent reads still describes the pre-ship world. `prd/project-state/roadmap.md`'s live marker bullet names `001-native-workflow-acceptance` on `gsd-path/M001` at "phase build", and `prd/project-state/data/roadmap.json` `current_milestone` matches it — the three-way identity (STATE.md ↔ roadmap.json ↔ the single live marker bullet) is pinned by `tests/test_project_state_roadmap_freshness.py::test_native_marker_names_the_operational_milestone`, which is why the marker must move to `post-ship-hardening`/`gsd-path/M002` in the same edit. The crosswalk M225 row (`docs/agent-stack/history/LEGACY_CROSSWALK.md`) still demands "fill tested_source_revision, re-run validation" — closed on 2026-10-26 by M001's T004 with receipt `prd/migration/rust-evidence/m225-validation-rerun-m001.json`, verdict `hermetic-pass-parity-unproven`, corpus parity explicitly unproven (E6: the row is updated, never deleted). The DOCS-AUDIT queue rows #6/#19 (PDD `product-model/`) and #9 (GitNexus block) were made true by M001's T005/T006 but reference no task ids. `docs/agent-stack/CUTOVER-READINESS-M001.md` is the dated pre-ship snapshot — N4 says it remains untouched (its own pin `tests/test_m001_cutover_readiness.py` must keep passing unmodified), so the current-state document is a new dated report that supersedes it. Facts to record (verified 2026-10-27): M001 shipped/archived — ship commit `886a36a8`, integration merge `4e0cd4db` into main, tag `milestone/001-001-native-workflow-acceptance`, archive `.project/archive/001-001-native-workflow-acceptance`; M002 `post-ship-hardening` active on `gsd-path/M002` at base `4e0cd4db`.

## Approach

Contract constraints (the binding shapes are in Interface contract):

- Post-ship report: `docs/agent-stack/POST-SHIP-STATE-2026-10-27.md`, dated 2026-10-27, stating it supersedes `docs/agent-stack/CUTOVER-READINESS-M001.md` as the current-state document (that file remains untouched as the dated pre-ship snapshot).
- Fresh-session bootstrap section: headed `Fresh-session bootstrap`, listing exactly, in order: (1) the restore procedure above (vendored archive extraction + the installer's `--runtime-restore`); (2) `python3 scripts/ai/path-run.py status`; (3) `uv run --frozen python -m law_nexus_harness.governor`; (4) `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`; and the instruction to record every command with its real output at the proof file `M002-ACCEPTANCE-PROOF.md` in the pipeline `.project/build/` workspace.

## Interface contract

- Post-ship report: `docs/agent-stack/POST-SHIP-STATE-2026-10-27.md`, dated 2026-10-27, stating it supersedes `docs/agent-stack/CUTOVER-READINESS-M001.md` as the current-state document (that file remains untouched as the dated pre-ship snapshot).
- Fresh-session bootstrap section: headed `Fresh-session bootstrap`, listing exactly, in order: (1) the restore procedure above (vendored archive extraction + the installer's `--runtime-restore`); (2) `python3 scripts/ai/path-run.py status`; (3) `uv run --frozen python -m law_nexus_harness.governor`; (4) `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`; and the instruction to record every command with its real output at the proof file `M002-ACCEPTANCE-PROOF.md` in the pipeline `.project/build/` workspace.

## Intent coverage

- SC4

## Acceptance criteria

1. `prd/project-state/roadmap.md` carries exactly one live marker bullet naming `post-ship-hardening` on `gsd-path/M002` and one dated superseded bullet recording M001 shipped/archived/integrated (ship `886a36a8`, integration `4e0cd4db`); `roadmap.json` `current_milestone` is `{"id": "post-ship-hardening", "status": "active"}`; no other roadmap content moves (N4).
2. The crosswalk M225 row is updated in place (still present), records the residual closed by T004, links `prd/migration/rust-evidence/m225-validation-rerun-m001.json` with verdict `hermetic-pass-parity-unproven`, and states corpus parity remains unproven (E6).
3. DOCS-AUDIT queue rows #6/#19 reference T005 and row #9 references T006; the rows and the table shape are intact.
4. `docs/agent-stack/POST-SHIP-STATE-2026-10-27.md` exists, is dated 2026-10-27, states it supersedes `docs/agent-stack/CUTOVER-READINESS-M001.md` as the current-state document (that file unmodified), records the shipped M001, the CI state and its fix, the M002 continuation, and carries the Contract D "Fresh-session bootstrap" section; `AGENTS.md` and `docs/agent-stack/AGENT_HANDOFF.md` point at it.
5. `tests/test_post_ship_pointers.py` and the extended marker test pin the above and pass via this task's Verify; `tests/test_m001_cutover_readiness.py` passes unmodified; `tests/test_documentation_navigation.py` passes (no local/historical link targets).

## Verify

```bash
uv run --frozen pytest tests/test_project_state_roadmap_freshness.py tests/test_post_ship_pointers.py -q
```
<!-- Fails if the marker moved wrong, the crosswalk row is missing or unlinked, the
     audit rows lack task ids, the report/bootstrap section is absent, or the
     shipped-record pin is dropped. -->

Heavy: no

## Log

<!-- Append-only: coder summary, blocks (`NEEDS-ORCHESTRATOR: <question> —
     readings: <candidates>` for contract ambiguity), orchestrator answers,
     review verdicts, fixes. -->
- 2026-10-27 — created by planner
