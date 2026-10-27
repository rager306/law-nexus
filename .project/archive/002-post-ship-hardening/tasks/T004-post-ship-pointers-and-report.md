---
id: T004
title: Make the post-ship pointers truthful and write the dated post-ship report
wave: 2
deps: []
status: done
agent: build_T004
base: 3b0d8527a6a9eb4d14a469525fa8cce5d046a241
worktree: null
task_branch: null
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
- 2026-10-27 — implemented by build_T004 (base 2bf3eafe, primary worktree, branch gsd-path/M002).
  - prd/project-state/roadmap.md: live marker bullet moved to `post-ship-hardening`
    (phase build, branch `gsd-path/M002`); the retired M001 bullet became the dated
    "(superseded 2026-10-27)" record carrying ship `886a36a8`, integration `4e0cd4db`,
    tag and archive; the GSD-Pi historical text is preserved verbatim (N4).
  - prd/project-state/data/roadmap.json: `current_milestone` is now exactly
    `{"id": "post-ship-hardening", "status": "active"}`; nothing else in the file moved.
  - docs/agent-stack/history/LEGACY_CROSSWALK.md: M225 obligations row updated in place
    (E6, never deleted): residual closed 2026-10-26 by M001's T004, links
    `prd/migration/rust-evidence/m225-validation-rerun-m001.json`, verdict
    `hermetic-pass-parity-unproven`, corpus parity explicitly unproven; the note's
    open-work paragraph replaced by a dated closure note ("Explicitly not the task"
    paragraph kept).
  - .project/research/DOCS-AUDIT.md: rulings rows #6/#19 Planned -> T005, #9 -> T006;
    all 19 rows and the 4-column shape intact.
  - docs/agent-stack/POST-SHIP-STATE-2026-10-27.md (new): dated current-state report
    superseding `CUTOVER-READINESS-M001.md` (untouched, N4); records the shipped M001
    (ship `886a36a8`, integration `4e0cd4db`, tag, archive), the CI failure (run
    40446077586) and the landed fix (T001 restore/diagnostics/shipped-main assertion,
    T002 shipped-integrated classification) with T003 named as still in flight, and
    the Contract D "Fresh-session bootstrap" section (restore procedure, status,
    governor, freshness pytest, in order; proof rule -> `.project/build/M002-ACCEPTANCE-PROOF.md`).
  - AGENTS.md and docs/agent-stack/AGENT_HANDOFF.md point at the report; the AGENTS.md
    GitNexus block is untouched (receipt hash pin still passes).
  - tests/test_post_ship_pointers.py (new): pins the exact current_milestone projection,
    the M225 closure row (receipt link + verdict + corpus-parity wording), the audit
    task-id references and queue shape, the supersession statement, the bootstrap
    heading/command order/proof rule, and both entry-point pointers.
  - tests/test_project_state_roadmap_freshness.py: marker pinning extended with
    `test_native_marker_has_one_dated_m001_superseded_bullet` (same native-state guard
    as the three-way identity test).
- 2026-10-27 — Verify (`uv run --frozen pytest tests/test_project_state_roadmap_freshness.py
  tests/test_post_ship_pointers.py -q`): `8 passed, 5 skipped in 4.13s` — the 5 skips are
  the documented legacy-surface skips under operational native state. Adjacent surfaces
  unbroken: `pytest tests/test_m001_cutover_readiness.py tests/test_documentation_navigation.py
  tests/test_gitnexus_block_receipt.py -q` -> `11 passed`; ruff check + ruff format clean
  on both test files; live `python -m law_nexus_harness.governor` exit 0 (0 non-pass
  findings) and `preflight` exit 0 on the bound branch.
- 2026-10-27 — orchestrator Verify (sidecar gsd-path-verify/task-t004-verify): pass, exit 0; output tail:
  ```
  sssss........                                                            [100%]
  8 passed, 5 skipped in 4.74s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t004-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t004-verify
  Installed 32 packages in 298ms
  ```
- 2026-10-27 — orchestrator Verify (sidecar gsd-path-verify/task-t004-verify): pass, exit 0; output tail:
  ```
  sssss........                                                            [100%]
  8 passed, 5 skipped in 4.57s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t004-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t004-verify
  Installed 32 packages in 261ms
  ```
- 2026-10-27 — orchestrator Verify (sidecar gsd-path-verify/task-t004-verify): pass, exit 0; output tail:
  ```
  sssss........                                                            [100%]
  8 passed, 5 skipped in 6.53s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t004-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t004-verify
  Installed 32 packages in 265ms
  ```
