# Plan — law-nexus

<!-- Written by the orchestrator (quick mode). Executed wave-by-wave by /gsd-path-build. -->

Project verify: `cargo fmt --all --check && cargo test --workspace --offline && uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py tests/test_repository_quality_gate.py -q`
<!-- Run once at ship, in a fresh sidecar worktree at the reviewed commit. -->

## Config

- max_review_cycles: 3
- wave_budget: none
- review_panel: off
- finding_skeptics: off

## Wave 1 — projection alignment and the honest front door

Goal: run the missed M011 ship-time projection refresh per the pinned procedure, make the current-state document and bootstrap checks tell the truth about CI, clear the 20 stale doc claims of audit rows #25-#49, re-pin the m221 binding, and regenerate the GitNexus block.
Review depth: full

## Intent coverage

| Criterion | Task | Acceptance |
|-----------|------|------------|
| SC1 | T001 | AC1 |
| SC2 | T001 | AC2 |
| SC3 | T002 | AC1 |
| SC4 | T002 | AC2 |
| SC5 | T002 | AC3 |

## Dependency notes

- T001 and T002 have disjoint file scopes and no shared landed effect; either may land first. A reviewer sees each row's doc claim re-verified at HEAD by the owning task's Verify and the wave review.

