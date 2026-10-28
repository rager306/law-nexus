# Intent — law-nexus

<!-- Written by $gsd-path-define (quick mode, supplied-spec: the owner-approved
     M003 scope = external-review items 1–2 as refined by the live CI failure
     40533158703 on integrated main). -->

Lane: quick   <!-- two deliverable-sized tasks, one wave, no RESEARCH/NEEDS-USER
                   items, no cross-wave risk. -->

Review panel: off   <!-- configured default. -->

Finding skeptics: off

Surfaces: terminal (native Path CLI: governor, pytest, git), GitHub Actions (repository-quality migration job on main: pytest result, diagnostics artifact)

## Summary

M002 made the harness suites context-independent, but the live CI run on
integrated main (40533158703) exposed the matrix's one remaining blind spot: the
SHIPPED_MAIN scenario keys on the branch name alone and expects Contract A
(exit 0), while the checkout's STATE.md on main during an active M002 says
`build/active` — so the real governor honestly reports the roadmap mismatch and
14 routed assertions fail. The same run also showed the governor-diagnostics
artifact step sits after the pytest step, so a pytest failure publishes nothing.
M003 keys the scenario expectations on the checkout's STATE.md phase semantics
(build/active → assert the honest single-error roadmap finding; shipped/done →
Contract A), moves the diagnostics publication to cover any migration-job
failure, and verifies no milestone literals remain in the expectations.

## Problem

A fresh agent on integrated main sees a red CI whose 14 failures are the
test-matrix's expectation mismatch, not product defects — and no diagnostics
artifact explains them. The next milestone cannot honestly declare CI green
until the assertions match the documented per-context contracts and the
diagnostics cover the failure path that actually occurs.

## Users

The owner and AI agents reading the CI run page and the terminal.

## Success criteria

1. SC1 — On the integrated main CI context (checkout of main, STATE.md
   `build/active` naming gsd-path/M002), the harness status and preflight
   suites pass: the SHIPPED_MAIN-scenario expectations key on the checkout's
   STATE.md phase semantics — `build/active` asserts the honest single-error
   roadmap finding (roadmap-current-tracks-path naming the M002 continuation),
   `shipped/done` asserts Contract A pass; the fail-closed pins for
   foreign/detached/sidecar contexts are unchanged.
2. SC2 — No milestone-branch literals remain in the live-suite expectations:
   `tests/test_harness_governor.py` and `tests/test_harness_preflight.py`
   contain no `gsd-path/M0NN` literals outside scenario-fixture payloads, and
   a grep pin test enforces this.
3. SC3 — The governor-diagnostics artifact publishes on any
   migration-job failure (including the pytest step that precedes the governor
   step), with the job exit preserved non-zero.
4. SC4 — The roadmap marker remains consistent after the fix: the three-way
   identity test (STATE ↔ roadmap.json ↔ live marker) passes and the live
   marker names the M002 continuation on gsd-path/M002.

## Edge coverage

| Edge | Criterion | Category | Disposition | Detail |
|------|-----------|----------|-------------|--------|
| E1 | SC1 | adjacency | criterion SC1 | `build/active` and `shipped/done` STATE phases assert different documented contracts; the predicate keys on the STATE.md phase field, never on a milestone literal. |
| E2 | SC1 | idempotency | held-out | The context classification is a pure function of (live branch, STATE phase, STATE branch); a test pins the classification for all five contexts × both STATE phases. |
| E3 | SC2 | adjacency | criterion SC2 | The grep pin fails on any `gsd-path/M0NN` literal outside an explicitly whitelisted fixture payload region. |
| E4 | SC3 | boundary | criterion SC3 | The artifact publishes when ANY step of the migration job fails (pytest, governor, restore), not only the governor step; `if: failure()` at job level. |
| E5 | SC4 | adjacency | criterion SC4 | The three-way identity (STATE ↔ roadmap.json ↔ live marker) is re-checked after the scenario fix; a mismatch fails the freshness test, never silently passes. |

## Prohibitions

| Prohibition | Criterion | Must not | Disposition | Detail |
|-------------|-----------|----------|-------------|--------|
| N1 | SC1 | weaken the fail-closed pins for foreign/detached/sidecar contexts | criterion SC1 | The M001 ruling (a) semantics are preserved verbatim. |
| N2 | SC2 | reintroduce milestone literals to make an assertion pass | criterion SC2 | The grep pin (SC2) enforces mechanically; SC1's scenario keying is also literal-free by construction. |
| N3 | SC3 | mask the non-zero job exit when publishing diagnostics | criterion SC3 | `if: failure()` + artifact upload never flips the exit code. |
| N4 | SC4 | rewrite the dated pre-ship snapshot while updating pointers | criterion SC4 | The CUTOVER-READINESS-M001.md pin test must keep passing unmodified; only the new dated report supersedes it. |
## Scope: in

- Scenario-expectation fix in the two live suites (STATE-phase-keyed).
- Grep pin test for milestone literals.
- Diagnostics artifact publication moved to job-failure scope.
- Roadmap consistency check after the fix (SC4).

## Scope: out (vetoes)

- Strict corpus run, PDD wrapper bootstrap, Allspark identity pilot — M004
  candidates (owner deferral standing).
- Product feature work; cutover stays `false`.
- Any suppression masking a non-zero exit (N3, standing).
- `git stash` in this repository (standing owner rule).

## Constraints

- Bound branch `gsd-path/M003` at base f9061889; integration `direct`.
- Python through `uv run --frozen`; Conventional Commits, English subjects.
- The M001 ruling (a) fail-closed branch-ownership pinning semantics are
  contract; only the SHIPPED_MAIN expectation keying changes.

## Risks

- The STATE-phase-keyed expectation must not weaken the roadmap-mismatch
  honesty: `build/active` on main asserts the single honest error, never a pass.

## Open questions

- none at define time.

## Corrections

- 2026-10-27: «продолжай» — owner approved the M003 scope (external-review
  items 1–2 refined by CI run 40533158703; stretch items deferred to M004).
