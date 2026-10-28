---
id: T001
title: Refresh roadmap marker and audit queue to M003 shipped state
wave: 1
deps: []
status: done
agent: build_T001
base: a10c02b4823438acfc72da664e470e3413532bdd
worktree: null
task_branch: null
files:
  - prd/project-state/roadmap.md
  - prd/project-state/data/roadmap.json
  - docs/agent-stack/history/LEGACY_CROSSWALK.md
  - .project/research/DOCS-AUDIT.md
  - tests/test_project_state_roadmap_freshness.py
  - tests/test_post_ship_pointers.py
---

# T001 — Refresh roadmap marker and audit queue to M003 shipped state

## Context

M003 shipped with milestone ci-honesty; the roadmap and queue trail behind.

## Approach

- Update roadmap.md live marker to ci-honesty/gsd-path/M004 (shipped); update roadmap.json current_milestone.id.
- Update DOCS-AUDIT queue rows for T005/T006/T001–T011 completed work.
- Update crosswalk M225 row linking the rerun receipt.

## Interface contract

- None

## Intent coverage

- SC1
- SC2

## Acceptance criteria

1. Roadmap marker names ci-honesty on gsd-path/M004; three-way identity test passes.
2. Held-out E2: the roadmap consistency test also confirms no stale `planned: no` rows for completed M001-M003 tasks.

## Verify

```bash
uv run --frozen pytest tests/test_project_state_roadmap_freshness.py::test_native_marker_names_the_operational_milestone -q
```

## Log

- 2026-10-28 — created by plan (quick mode)
- 2026-10-28 — plan-defect repair (orchestrator): `tests/test_post_ship_pointers.py` joins `files` — the M002-era pin on roadmap.json current_milestone must move with the marker refresh (same class as the M001 gitignore anchoring).
- 2026-10-28 — implemented by build_T001 (base a10c02b4, primary worktree, branch gsd-path/M004).
  - prd/project-state/roadmap.md: live marker bullet moved to `ci-honesty`
    (shipped/archived/integrated 2026-10-28: ship commit `7786d5d3`,
    integration merge `7e200294` into `main`, tag `milestone/003-ci-honesty`,
    archive `.project/archive/003-ci-honesty`; current-state document
    repointed to `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md`); the
    retired post-ship-hardening bullet became the dated
    "(superseded 2026-10-28)" record carrying ship `ba31ffb8`, integration
    `f9061889`, tag `milestone/002-post-ship-hardening`, archive
    `.project/archive/002-post-ship-hardening`; the M001
    "(superseded 2026-10-27)" bullet and all older history preserved
    verbatim (N1). Ship/integration facts cross-checked against git tags,
    merge parents, and `.project/archive/00{2,3}-*/MANIFEST.md`.
  - prd/project-state/data/roadmap.json: `current_milestone` is now exactly
    `{"id": "ci-honesty", "status": "active"}`; nothing else moved.
  - .project/research/DOCS-AUDIT.md: no edit needed — every queue row closed
    by an M001–M003 task already references its id (#6/#19 → T005, #9 → T006,
    #16 → T010); the 15 remaining `planned: no` rows were re-verified open
    against disk (README 45-members / M165 band / assessments 13–18 /
    `ln-product-cli -- health`; AGENTS.md 2,478-rows / 122-XML;
    ARCHITECTURE.md 10-source-modules + 327-line oracle; doc/adr/README
    table; cross-matrix ≤ 0024; npa-contract binding; roadmap.md M173 front;
    law-source `.deprecated`/sha256 wording) — none was completed by an
    M001–M003 task, so none may take a task id; rows are never deleted (the
    table's own header rule). Agrees with the M003 MANIFEST: "Carried
    forward: 15 DOCS-AUDIT ruling(s)".
  - docs/agent-stack/history/LEGACY_CROSSWALK.md: no edit needed — the M225
    row already links `prd/migration/rust-evidence/m225-validation-rerun-m001.json`
    with the T004 closure and the `hermetic-pass-parity-unproven` verdict
    (pinned by tests/test_post_ship_pointers.py, passing).
  - tests/test_post_ship_pointers.py: the M002-era literal pin
    `test_roadmap_json_current_milestone_is_the_exact_m002_projection` moved
    to `test_roadmap_json_current_milestone_tracks_the_latest_archive` — the
    projection must equal `{"id": <latest archived milestone slug>,
    "status": "active"}`, keyed on the `.project/archive/` directory scan,
    no milestone literal in the expectation (N5).
- 2026-10-28 — Verify (`uv run --frozen pytest
  tests/test_project_state_roadmap_freshness.py::test_native_marker_names_the_operational_milestone -q`):
  `1 passed in 0.33s`, exit 0. Adjacent: the full
  tests/test_project_state_roadmap_freshness.py + tests/test_post_ship_pointers.py
  → `11 passed, 5 skipped` (the 5 documented legacy-surface skips under
  operational native state); test_m001_cutover_readiness +
  test_documentation_navigation + test_gitnexus_block_receipt +
  test_m225_validation_residual + test_branch_context → `39 passed`;
  ruff check + ruff format clean on the edited test file.
- 2026-10-28 — Live governor on the bound branch, exit unmasked:
  `uv run --frozen python -m law_nexus_harness.governor` → exit 1, status
  failure with exactly one error — `roadmap-current-tracks-path`
  (roadmap_current=ci-honesty vs native_milestone=pointer-refresh-m003,
  native_phase=build; pass_count=74, warn=0, tool_error=0). This is the
  honest in-flight mismatch M003 SC1 pinned: while a milestone is in flight
  the projection must track the last landed milestone (the freshness suite's
  archive-keyed arm), so the finding is the designed steady state — recorded,
  not masked, and not "fixed" (pointing the projection at the in-flight
  milestone would break the three-way identity test). A first governor
  invocation piped through `tail` printed a masked `GOVERNOR_EXIT=0`
  (pipeline status, not the governor's); discarded — the unmasked re-run
  above is the evidence.
- 2026-10-28 — orchestrator Verify (sidecar gsd-path-verify/task-t001-verify): pass, exit 0; output tail:
  ```
  .                                                                        [100%]
  1 passed in 1.60s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
  Installed 32 packages in 1.11s
  ```
- 2026-10-28 — orchestrator Verify (sidecar gsd-path-verify/task-t001-verify): pass, exit 0; output tail:
  ```
  .                                                                        [100%]
  1 passed in 1.48s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t001-verify
  Installed 32 packages in 259ms
  ```
