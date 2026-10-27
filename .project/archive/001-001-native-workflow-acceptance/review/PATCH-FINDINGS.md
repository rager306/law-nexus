# Patch Findings

<!-- Written by final review when it blocks and consumed by patch planning. -->

Reviewed HEAD: f3c55d6dc0c5d7756dd43bc31840194e11e5bfc4
State: ship/blocked

## Findings

<!-- Copy only evidenced, selected findings. Keep IDs contiguous and ordered. -->
### P001 — Project Verify blocked by the fail-closed governor branch lock in the verify sidecar

- **Source**: `.project/review/final-gap-1.md`
- **Locator**: Risk: project Verify
- **Evidence**: Project Verify failed at the reviewed commit.
- **Fix direction**: Resolve the recorded command failure before shipping.
- **Note (orchestrator, non-normative)**: exact failure 14 failed / 634 passed / 7 skipped — live-governor ×12 + preflight ×2,
  all asserting `error_count == 0` on a `gsd-path-verify/*` sidecar branch where the documented fail-closed branch
  ownership fires; identical suite green on the bound branch (r2: 278/0; wave-gate governor 0 errors). Environment
  contract mismatch, not a product defect. Candidate fix shape for patch planning: make the live-governor/preflight
  modules branch-environment-aware (pin the fail-closed branch-ownership behavior on non-operational branches, or skip
  with a loud recorded reason — mirroring the corpus-absent skip-visible pattern); full assertions unchanged on the
  bound branch; no assertion weakened where the governor is operational; no suppression added (N3).

