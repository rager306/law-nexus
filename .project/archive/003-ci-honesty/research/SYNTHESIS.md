# Synthesis

<!-- Quick-lane milestone: research and decide phases skipped per the quick-lane contract.
     Settled decisions come directly from the approved INTENT and the owner's define-round rulings. -->

Phase: research
Status: complete
Intent: `.project/intent/INTENT.md`

## Settled

- Scenario-expectation keying — the SHIPPED_MAIN scenario keys on STATE.md phase semantics (`build/active` → honest roadmap finding; `shipped/done` → Contract A pass), not on milestone-branch literals (INTENT.md SC1, E1; SYNTHESIS of the owner's ruling 3 in the M003 define round).
- Fail-closed pinning — foreign/detached/sidecar contexts pin the fail-closed branch-ownership contract verbatim (M001 ruling (a), INTENT.md N1).
- No suppression — the diagnostics artifact publishes on any migration-job failure with the exit preserved non-zero (INTENT.md SC3, E4, N3).
- Post-ship pointers — the roadmap marker and the three-way identity test are consistent after the fix (INTENT.md SC4, E5, N4).
- Deferred to M004 — PDD wrapper bootstrap, Allspark identity pilot, strict corpus run (owner deferral, INTENT.md Scope out).

## For the planner

- Walking skeleton: T001 (scenario fix + matrix + grep pin) is the thinnest proof that the expectations match reality.
- T002 (diagnostics artifact scope) is independent and can run in parallel.
