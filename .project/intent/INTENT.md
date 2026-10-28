# Intent — law-nexus

<!-- $gsd-path-define (quick lane). Scope: make the two remaining red CI jobs
     prove the shipped integrated state on main (run 40697747035 at 3e047fe8). -->

Lane: quick
Review panel: off
Finding skeptics: off

Surfaces: ci workflow (repository-quality.yml)

## Summary

CI on integrated main still fails two jobs for the same root cause: the jobs do
not give the pinned runtime the evidence it needs to prove the shipped
integration. The rust job checks out with `fetch-depth: 0` absent (depth 1, no
tags), so the milestone tag is missing and the native status helper reports the
integration unverified; the migration job passes `fetch-depth: 0` and
`origin/HEAD`, yet its governor still reports conflicting-ownership. M007 makes
both jobs supply the same proof inputs and adds a diagnostic that names the
exact missing fact instead of a generic block.

## Problem

A fresh agent reads a red main whose failures come from checkout shape, not
product defects; the honest fix is to give the proof inputs, never to relax the
governor.

## Users

The owner and AI agents reading the CI run page.

## Success criteria

1. SC1 — The rust workspace job checks out the full history and tags, so the
   pinned native status helper can prove the shipped integration on main and the
   governor reports the shipped-integrated surface.
2. SC2 — The migration job's governor honesty step names the exact missing
   proof input when the surface is not shipped-integrated, so a checkout-shape
   defect is diagnosable from the job log alone.
3. SC3 — `uv run --frozen pytest tests/test_ci_runtime_restore.py -q` passes and
   pins both job shapes.

## Edge coverage

| Edge | Criterion | Category | Disposition | Detail |
|------|-----------|----------|-------------|--------|
| E1 | SC1 | boundary | criterion SC1 | A shallow checkout that cannot see the milestone tag must fail the governor step, not pass silently. |
| E2 | SC2 | empty | held-out | A governor report with no workflow-state-surface finding fails the step with the observed surface named. |
| E3 | SC3 | boundary | criterion SC3 | A pin that drops either checkout input fails the suite rather than passing quietly. |

## Prohibitions

| Prohibition | Criterion | Must not | Disposition | Detail |
|-------------|-----------|----------|-------------|--------|
| N1 | SC1 | weaken or skip a failing test to make CI green | criterion SC1 | The proof inputs are supplied; no assertion moves. |
| N2 | SC2 | suppress a non-zero exit or make the honesty step a no-op | criterion SC2 | The step still fails on a lying surface. |
| N3 | SC3 | delete or weaken the checkout-input pin | criterion SC3 | Both inputs stay pinned. |

## Scope: in

- `.github/workflows/repository-quality.yml` checkout inputs for both jobs.
- `tests/test_ci_runtime_restore.py` pins for those inputs.

## Scope: out (vetoes)

- Product/runtime changes; cutover stays `false`.
- Suppression of any non-zero exit (standing N3).
- `git stash` in this repository (standing owner rule).

## Constraints

- Bound branch `gsd-path/M007` at base 3e047fe8; integration `direct`.
- Python through `uv run --frozen`.

## Risks

- The migration job's governor failure is not fully reproduced locally; T002
  must make the failure self-diagnosing before any further assumption.

## Open questions

- none.

## Corrections

- 2026-10-28: «продолжай» — owner standing delegation; scope = the two red CI jobs.
