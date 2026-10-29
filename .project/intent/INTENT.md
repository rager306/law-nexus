# Intent — law-nexus

<!-- $gsd-path-define (quick lane). Scope: close the four documentation-consistency
     follow-ups recorded in the M009 final review. -->

Lane: quick
Review panel: off
Finding skeptics: off

Surfaces: ci workflow (repository-quality.yml), roadmap projection (prd/project-state)

## Summary

The M008/M009 CI work left four tracked surfaces describing an older world: the
CI suite inventory does not list the two pointer suites that CI now runs, the
agent entry point does not point at the ship-time refresh rule, the roadmap
marker history skips five shipments (M003-M006, M008), and the current-state
document pointer names a report frozen before M008. M010 aligns all four, so a
fresh reader sees one consistent shipped world.

## Problem

Each surface is a projection of the same facts, and they disagree; a fresh agent
either re-derives the missing history or trusts a stale document.

## Users

The owner and AI agents reading `AGENTS.md`, the roadmap, and the CI inventory.

## Success criteria

1. SC1 — The CI inventory names every suite the CI process list runs: the two
   post-ship pointer suites appear in `repository-quality-gate.json`
   `ci_process_suite` and in the pin that mirrors it.
2. SC2 — The agent entry point names the ship-time projection refresh rule, so
   the next ship reaches it from `AGENTS.md`, not only from a roadmap sentence.
3. SC3 — The roadmap marker history records every shipped milestone with its
   dated superseded bullet, and the current-state document pointer names a
   report that describes the shipped world after M009.
4. SC4 — `uv run --frozen pytest tests/test_post_ship_pointers.py
   tests/test_project_state_roadmap_freshness.py tests/test_repository_quality_gate.py
   -q` reports 0 failures on the bound branch.

## Edge coverage

| Edge | Criterion | Category | Disposition | Detail |
|------|-----------|----------|-------------|--------|
| E1 | SC1 | empty | held-out | An inventory that drops a pointer suite fails the pin rather than passing on the survivors. |
| E2 | SC2 | empty | criterion SC2 | An entry point that names no refresh rule fails the pin that requires the path. |
| E3 | SC3 | ordering | criterion SC3 | A history bullet whose milestone has no archive, or an archive with no bullet, fails the completeness pin. |
| E4 | SC4 | boundary | criterion SC4 | A surface left stale fails the run rather than passing quietly. |

## Prohibitions

| Prohibition | Criterion | Must not | Disposition | Detail |
|-------------|-----------|----------|-------------|--------|
| N1 | SC1 | shrink the CI process list to match a smaller inventory | criterion SC1 | The inventory grows to the CI list. |
| N2 | SC3 | delete a superseded history bullet to shorten the file | criterion SC3 | History is appended, never deleted. |
| N4 | SC2 | rely on a roadmap sentence as the only reader path to the rule | criterion SC2 | `AGENTS.md` names the rule. |
| N3 | SC4 | xfail or skip a failing pin | criterion SC4 | Failures are fixed at the surface. |

## Scope: in

- `prd/migration/decommission/repository-quality-gate.json`, `tests/test_repository_quality_gate.py`.
- `AGENTS.md`.
- `prd/project-state/roadmap.md`, `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md`.
- `tests/test_post_ship_pointers.py` pins.

## Scope: out (vetoes)

- Product/runtime changes; cutover stays `false`.
- Suppression of any non-zero exit (standing N3).
- `git stash` in this repository (standing owner rule).

## Constraints

- Bound branch `gsd-path/M010` at base 319a7b1a; integration `direct`.
- Python through `uv run --frozen`.

## Risks

- The history bullets must stay dated and must not duplicate the live marker,
  which `tests/test_project_state_roadmap_freshness.py` counts exactly.

## Open questions

- none.

## Corrections

- 2026-10-29: «поправь все что необходимо» — owner directive; scope = the four M009 follow-ups.
