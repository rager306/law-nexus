---
pipeline: gsd-path/v2
project: law-nexus
milestone: ci-honesty
phase: ship
                    # inspect only for brownfield; greenfield starts at define
                    # roadmap only in program flow (CHARTER.md exists)
status: active
branch: gsd-path/M003
                    # the router rebinds before any next-milestone file change
                    # the bound branch is never main; ship integrates it there
archive: null
integration_default: direct
integration: direct
integration_source: default
default_branch: main # origin default branch; initialization records it once, nothing changes it
---

# Project State

One file, always current. The router reads this first; every phase updates
it on completion. If this file and the artifacts disagree, the artifacts win
— fix this file.

## Log

<!-- append one line per transition: date, phase, event -->
- 2026-10-25 — inspect — project initialized
- 2026-10-25 — inspect — router bound initial milestone
- 2026-10-26 — inspect — inspection artifacts passed
- 2026-10-26 — define — definition started
- 2026-10-26 — define — milestone intent approved
- 2026-10-26 — research — research started
- 2026-10-26 — research — research done: manifest .project/research/RESEARCH.md; dispatched stack; skipped domain,pitfalls,similar; 1 question
- 2026-10-26 — decide — decision synthesis started
- 2026-10-26 — decide — decision synthesis validated: .project/research/SYNTHESIS.md; 3 decisions, 4 user rulings recorded, no open user items
- 2026-10-26 — plan — planning started
- 2026-10-26 — plan — plan approved
- 2026-10-26 — build — build started
- 2026-10-26 — build — build blocked: T009 NEEDS-ORCHESTRATOR — publication collides with the pre-push guard and CI trigger design; owner ruling required on SC8
- 2026-10-26 — define — build intent corrections requested
- 2026-10-26 — define — build recovery: {"base": "7e994d3b42560d25d4413604a9cb19a6bd2e3d64", "branch": "gsd-path/M001", "kind": "define", "source": "build"}
- 2026-10-26 — define — intent corrected from build recovery (owner ruling a: SC8 publication/CI pending-ship)
- 2026-10-26 — research — research started (recovery re-gate; settled evidence unchanged)
- 2026-10-26 — research — research re-gated: manifest complete, evidence unchanged
- 2026-10-26 — decide — decision synthesis started (recovery re-gate)
- 2026-10-26 — decide — decision synthesis re-gated: no open user items
- 2026-10-26 — plan — planning started
- 2026-10-26 — plan — plan approved
- 2026-10-26 — build — build started
- 2026-10-26 — ship — build done; final review pending
- 2026-10-26 — ship — ship blocked: lean gate refuses 5 tracked top-level .project artifacts (2 handoffs, supplied spec, T007/T008 landed resume pair); relocation proven safe in a probe worktree but its commit has no sanctioned slot at ship/active; owner ruling required
- 2026-10-26 — ship — ship unblocked: owner ruled (a) — one sanctioned pre-ship relocation commit (5 top-level artifacts into allowlisted dirs), then prepare-final at the new head
- 2026-10-26 — ship — ship blocked: project Verify gap blocked — 14 live-governor/preflight assertions fail in the gsd-path-verify sidecar (fail-closed branch ownership; environment contract, not a product defect); owner policy ruling required
- 2026-10-27 — plan — patch plan reopened
- 2026-10-27 — plan — patch plan approved
- 2026-10-27 — build — build started
- 2026-10-27 — ship — build done; final review pending
- 2026-10-27 — ship — final gate passed; shipping approval pending
- 2026-10-27 — shipped — archive preflight passed; shipment recorded
- 2026-10-27 — define — router bound next milestone
- 2026-10-27 — define — milestone intent approved
- 2026-10-27 — plan — planning started
- 2026-10-27 — plan — plan approved
- 2026-10-27 — build — build started
- 2026-10-27 — ship — build done; final review pending
- 2026-10-27 — ship — final gate passed; shipping approval pending
- 2026-10-27 — shipped — archive preflight passed; shipment recorded
- 2026-10-27 — define — router bound next milestone
- 2026-10-27 — define — milestone intent approved
- 2026-10-27 — plan — planning started
- 2026-10-28 — plan — plan approved
- 2026-10-28 — build — build started
- 2026-10-28 — ship — build done; final review pending
