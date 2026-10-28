# Intent — law-nexus

<!-- $gsd-path-define (quick lane). Scope: fix the CI fixture co-update defect
     exposed by the post-M004 CI run 40669688711. -->

Lane: quick
Review panel: off
Finding skeptics: off

Surfaces: terminal (native Path CLI: pytest, governor)

## Summary

The CI on integrated main (run 40669688711) fails in the harness status/preflight
step because two live-surface tests hardcode the previous milestone's phase and
milestone name: `TestRoadmapFreshnessAgainstNativePath` copies the live
`prd/project-state` but fakes a stale `native_milestone`, and the bound-branch
surface pins assume `BUILD_ACTIVE` while a shipped bound branch is
`SHIPPED_DONE`. M005 makes those fixtures derive the live milestone and accept
both bound-branch phases, so the live suites pass on integrated main.

## Problem

A fresh agent sees a red CI whose failures are fixture staleness, not product
defects; the pointer refresh in M004 fixed the docs but the tests still pinned
the old world.

## Users

The owner and AI agents reading the CI run page.

## Success criteria

1. SC1 — The live governor and preflight surface suites pass on the integrated
   main checkout: the roadmap-freshness fixture derives the current milestone
   from the tracked roadmap.json (no milestone literal), and the bound-branch
   surface pins accept both `build/active` and `shipped/done`.
2. SC2 — `uv run --frozen pytest tests/test_harness_governor.py
   tests/test_harness_preflight.py tests/test_post_ship_pointers.py
   tests/test_project_state_roadmap_freshness.py -q` reports 0 failures on the
   bound branch.

## Edge coverage

| Edge | Criterion | Category | Disposition | Detail |
|------|-----------|----------|-------------|--------|
| E1 | SC1 | empty | held-out | The fixture reads the milestone from roadmap.json; a missing or empty `current_milestone.id` fails the test loudly instead of silently passing. |
| E2 | SC2 | boundary | criterion SC2 | Both bound-branch phases (build/active, shipped/done) are accepted; any other phase fails. |

## Prohibitions

| Prohibition | Criterion | Must not | Disposition | Detail |
|-------------|-----------|----------|-------------|--------|
| N1 | SC1 | reintroduce milestone literals in the fixtures | criterion SC1 | The milestone is derived from the tracked roadmap.json at import time. |
| N2 | SC2 | weaken any substantive assertion to make CI green | criterion SC2 | Only the phase set is widened; every other assertion is unchanged. |

## Scope: in

- The two test files' fixture/pin co-update.

## Scope: out (vetoes)

- Product changes; cutover stays `false`.
- Suppression of any non-zero exit (standing N3).
- `git stash` in this repository (standing owner rule).

## Constraints

- Bound branch `gsd-path/M005` at base 57bb2282; integration `direct`.
- Python through `uv run --frozen`.

## Risks

- none material.

## Open questions

- none.

## Corrections

- 2026-10-28: «продолжай» — owner standing delegation; scope = the CI fixture co-update.
