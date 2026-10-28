# Intent — law-nexus

<!-- $gsd-path-define (quick lane). Scope: clear the two remaining red CI causes
     on integrated main (run 40685637304 at 121a2006). -->

Lane: quick
Review panel: off
Finding skeptics: off

Surfaces: ci workflow (repository-quality.yml), roadmap projection (prd/project-state)

## Summary

The CI on integrated main still fails two jobs for two independent reasons that
both belong to one class: a moving fact is pinned as a literal.
(1) The governor honesty step in `.github/workflows/repository-quality.yml`
requires the literal archive path `.project/archive/001-001-native-workflow-acceptance`,
so it fails for every later milestone; its pin test in
`tests/test_ci_runtime_restore.py` copies the same literal.
(2) `prd/project-state/data/roadmap.json` still names
`pointer-refresh-m003` while shipped STATE.md names `ci-fixture-fix`, so the
roadmap-freshness suites fail. M006 pins the archive path shape instead of a
milestone, and refreshes the roadmap pointer to the shipped milestone.

## Problem

A fresh agent sees red CI whose failures are stale literals, not product
defects; each milestone leaves the next one a red main.

## Users

The owner and AI agents reading the CI run page.

## Success criteria

1. SC1 — The main-branch governor honesty step accepts the shipped integrated
   surface of whichever milestone is current: it asserts the
   `kind=shipped-integrated;` shape and a `.project/archive/` path, never a
   milestone literal, and `tests/test_ci_runtime_restore.py` pins that shape.
2. SC2 — The tracked roadmap projection agrees with shipped STATE.md:
   `prd/project-state/data/roadmap.json` (and `roadmap.md`) name the milestone
   recorded in `.project/STATE.md`.
3. SC3 — `uv run --frozen pytest tests/test_ci_runtime_restore.py
   tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py
   tests/test_harness_governor.py tests/test_harness_preflight.py -q` reports
   0 failures on the bound branch.

## Edge coverage

| Edge | Criterion | Category | Disposition | Detail |
|------|-----------|----------|-------------|--------|
| E1 | SC1 | boundary | criterion SC1 | A governor surface that reports shipped-integrated without any archive path fails the step; a later milestone's archive passes. |
| E2 | SC2 | empty | held-out | A roadmap whose `current_milestone.id` is absent or empty fails the freshness test loudly instead of passing silently. |
| E3 | SC3 | boundary | criterion SC3 | A test that still pins the M001 archive literal, or a roadmap still naming the previous milestone, makes the run fail rather than pass. |

## Prohibitions

| Prohibition | Criterion | Must not | Disposition | Detail |
|-------------|-----------|----------|-------------|--------|
| N1 | SC1 | reintroduce a milestone literal in the workflow or its pin test | criterion SC1 | The pin asserts the shape only. |
| N2 | SC1 | drop the shipped-integrated assertion or make the step a no-op | criterion SC1 | Both the shape and the archive-path assertions remain fatal. |
| N3 | SC3 | weaken or skip any failing test to make CI green | criterion SC3 | Only the stale literals move to derived values. |
| N4 | SC2 | leave the roadmap projection disagreeing with STATE.md | criterion SC2 | The refresh names the shipped milestone, not an in-flight one. |

## Scope: in

- `.github/workflows/repository-quality.yml` governor honesty step.
- `tests/test_ci_runtime_restore.py` pin for that step.
- `prd/project-state/data/roadmap.json` and `prd/project-state/roadmap.md`.

## Scope: out (vetoes)

- Product/runtime changes; cutover stays `false`.
- Suppression of any non-zero exit (standing N3).
- `git stash` in this repository (standing owner rule).

## Constraints

- Bound branch `gsd-path/M006` at base 121a2006; integration `direct`.
- Python through `uv run --frozen`.

## Risks

- none material.

## Open questions

- none.

## Corrections

- 2026-10-28: «продолжай» — owner standing delegation; scope = the two red CI causes.
