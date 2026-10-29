# Intent — law-nexus

<!-- $gsd-path-define (quick lane). Scope: the roadmap projection must name the
     milestone being shipped, and the ship must refresh it, so the M008 CI
     guard stays green instead of catching its own milestone. -->

Lane: quick
Review panel: off
Finding skeptics: off

Surfaces: roadmap projection (prd/project-state)

## Summary

M008 put the pointer suites in CI, and the first run proved the guard works: the
rust job failed on `roadmap.json current_milestone.id 'ci-proof-inputs' !=
shipped STATE.md milestone 'pointer-in-ci'` (run 40715983380). The projection is
refreshed during build, when the milestone is still in flight, so the ship that
follows always lands a projection naming the previous milestone. M009 makes the
projection name the shipping milestone and records the rule so the refresh
happens at ship, not during build.

## Problem

Every milestone ends with a projection one milestone behind, and the guard that
was added to catch it now catches each milestone's own ship.

## Users

The owner and AI agents reading the CI run page and the roadmap.

## Success criteria

1. SC1 — The tracked projection names the milestone being shipped: after this
   milestone's ship, `roadmap.json` `current_milestone.id` equals the milestone
   in `.project/STATE.md`, and the live marker bullet names the same slug.
2. SC2 — The refresh rule is recorded where the next ship reads it, so a future
   milestone refreshes the projection at ship rather than during build.
3. SC3 — `uv run --frozen pytest tests/test_post_ship_pointers.py
   tests/test_project_state_roadmap_freshness.py -q` reports 0 failures on the
   bound branch and on the shipped tree.

## Edge coverage

| Edge | Criterion | Category | Disposition | Detail |
|------|-----------|----------|-------------|--------|
| E1 | SC1 | ordering | held-out | A projection naming the previous milestone fails the pointer suites once STATE.md names the shipping milestone. |
| E2 | SC2 | empty | criterion SC2 | A rule file that omits the refresh step fails the pin that names it. |
| E3 | SC3 | boundary | criterion SC3 | A projection left at the build-time milestone fails the run rather than passing quietly. |

## Prohibitions

| Prohibition | Criterion | Must not | Disposition | Detail |
|-------------|-----------|----------|-------------|--------|
| N1 | SC1 | remove the pointer suites from CI to make the run pass | criterion SC1 | The guard stays; the projection moves. |
| N2 | SC2 | encode the rule only in a chat message | criterion SC2 | The rule lives in a tracked file. |
| N3 | SC3 | mark the pointer suites xfail or skip on the shipped tree | criterion SC3 | Failures are fixed at the projection. |

## Scope: in

- `prd/project-state/data/roadmap.json` and `prd/project-state/roadmap.md`.
- The tracked ship-time refresh rule and its pin.

## Scope: out (vetoes)

- Product/runtime changes; cutover stays `false`.
- Suppression of any non-zero exit (standing N3).
- `git stash` in this repository (standing owner rule).

## Constraints

- Bound branch `gsd-path/M009` at base 4dd35d25; integration `direct`.
- Python through `uv run --frozen`.

## Risks

- The ship commit is `.project`-only, so the projection refresh must land in a
  `docs:` commit before the ship commit, not inside it.

## Open questions

- none.

## Corrections

- 2026-10-28: «продолжай» — owner standing delegation; scope = the projection-at-ship rule.
