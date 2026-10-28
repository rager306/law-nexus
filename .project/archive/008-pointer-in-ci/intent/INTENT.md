# Intent — law-nexus

<!-- $gsd-path-define (quick lane). Scope: close the recurring post-ship pointer
     drift by putting the pointer suites in CI and refreshing the pointer at ship. -->

Lane: quick
Review panel: off
Finding skeptics: off

Surfaces: ci workflow (repository-quality.yml), roadmap projection (prd/project-state)

## Summary

The roadmap projection has drifted after every ship since M003, and each time it
was found late. The two suites that pin it —
`tests/test_post_ship_pointers.py` and
`tests/test_project_state_roadmap_freshness.py` — are not in the CI suite list,
so the drift reaches main silently; it was found again after the M007
integration. M008 puts both suites in CI and refreshes the projection so the
shipped milestone is named, so the drift fails in CI instead of being
rediscovered by hand.

## Problem

A shipped milestone leaves main with a projection that names the previous
milestone, and nothing in CI notices; each milestone pays the same manual
detection cost.

## Users

The owner and AI agents reading the CI run page and the roadmap.

## Success criteria

1. SC1 — The CI suite list runs both pointer suites, so a projection that
   disagrees with the shipped STATE.md fails a job instead of reaching main.
2. SC2 — The tracked projection names the shipped milestone: `roadmap.json`
   `current_milestone.id` equals the milestone in `.project/STATE.md`, and the
   live marker bullet in `roadmap.md` names the same slug.
3. SC3 — `uv run --frozen pytest tests/test_post_ship_pointers.py
   tests/test_project_state_roadmap_freshness.py tests/test_ci_runtime_restore.py -q`
   reports 0 failures on the bound branch.

## Edge coverage

| Edge | Criterion | Category | Disposition | Detail |
|------|-----------|----------|-------------|--------|
| E1 | SC1 | empty | held-out | A CI suite list that omits either pointer suite fails the pin that names them. |
| E2 | SC2 | empty | criterion SC2 | A projection whose `current_milestone.id` is absent or empty fails the freshness test loudly. |
| E3 | SC3 | boundary | criterion SC3 | A suite that still fails on the refreshed projection fails the run rather than passing quietly. |

## Prohibitions

| Prohibition | Criterion | Must not | Disposition | Detail |
|-------------|-----------|----------|-------------|--------|
| N1 | SC1 | remove a suite from the CI list to make it pass | criterion SC1 | Both pointer suites stay listed and the pin enforces it. |
| N2 | SC2 | edit a test to accept the stale projection | criterion SC2 | The projection moves to the shipped milestone; no assertion is relaxed. |
| N3 | SC3 | skip or xfail a failing pointer test | criterion SC3 | Failures are fixed at the projection, never silenced. |

## Scope: in

- `.github/workflows/repository-quality.yml` CI suite list.
- `prd/project-state/data/roadmap.json` and `prd/project-state/roadmap.md`.
- `tests/test_ci_runtime_restore.py` pin for the suite list.

## Scope: out (vetoes)

- Product/runtime changes; cutover stays `false`.
- Suppression of any non-zero exit (standing N3).
- `git stash` in this repository (standing owner rule).

## Constraints

- Bound branch `gsd-path/M008` at base 50386e26; integration `direct`.
- Python through `uv run --frozen`.

## Risks

- The pointer suites are slow (about 8 s); the added CI time is accepted for
  catching the drift where it happens.

## Open questions

- none.

## Corrections

- 2026-10-28: «продолжай» — owner standing delegation; scope = the recurring pointer drift.
