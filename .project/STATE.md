---
pipeline: gsd-path/v2
project: law-nexus
milestone: reference-front-door
phase: shipped
                    # inspect only for brownfield; greenfield starts at define
                    # roadmap only in program flow (CHARTER.md exists)
status: done
branch: gsd-path/M011
                    # the router rebinds before any next-milestone file change
                    # the bound branch is never main; ship integrates it there
archive: .project/archive/011-reference-front-door
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
- 2026-10-28 — ship — final gate passed; shipping approval pending
- 2026-10-28 — shipped — archive preflight passed; shipment recorded
- 2026-10-28 — define — router bound next milestone
- 2026-10-28 — define — milestone intent approved
- 2026-10-28 — plan — planning started
- 2026-10-28 — plan — plan approved
- 2026-10-28 — build — build started
- 2026-10-28 — ship — build done; final review pending
- 2026-10-28 — shipped — archive preflight passed; shipment recorded
- 2026-10-28 — shipped — archive preflight passed; shipment recorded
- 2026-10-28 — define — router bound next milestone
- 2026-10-28 — define — milestone intent approved
- 2026-10-28 — plan — planning started
- 2026-10-28 — plan — plan approved
- 2026-10-28 — build — build started
- 2026-10-28 — ship — build done; final review pending
- 2026-10-28 — shipped — archive preflight passed; shipment recorded
- 2026-10-28 — define — router bound next milestone
- 2026-10-28 — define — milestone intent approved
- 2026-10-28 — plan — planning started
- 2026-10-28 — plan — plan approved
- 2026-10-28 — build — build started
- 2026-10-28 — ship — build done; final review pending
- 2026-10-28 — shipped — archive preflight passed; shipment recorded
- 2026-10-28 — define — router bound next milestone
- 2026-10-28 — define — milestone intent approved
- 2026-10-28 — plan — planning started
- 2026-10-28 — plan — plan approved
- 2026-10-28 — build — build started
- 2026-10-28 — ship — build done; final review pending
- 2026-10-28 — shipped — archive preflight passed; shipment recorded
- 2026-10-28 — define — router bound next milestone
- 2026-10-28 — define — milestone intent approved
- 2026-10-28 — plan — planning started
- 2026-10-28 — plan — plan approved
- 2026-10-28 — build — build started
- 2026-10-28 — ship — build done; final review pending
- 2026-10-28 — shipped — archive preflight passed; shipment recorded
- 2026-10-28 — define — router bound next milestone
- 2026-10-28 — define — milestone intent approved
- 2026-10-28 — plan — planning started
- 2026-10-28 — plan — plan approved
- 2026-10-28 — build — build started
- 2026-10-29 — ship — build done; final review pending
- 2026-10-29 — shipped — archive preflight passed; shipment recorded
- 2026-10-29 — define — router bound next milestone
- 2026-10-29 — define — milestone intent approved
- 2026-10-29 — plan — planning started
- 2026-10-29 — plan — plan approved
- 2026-10-29 — build — build started
- 2026-10-29 — ship — build done; final review pending
- 2026-10-29 — shipped — archive preflight passed; shipment recorded
- 2026-10-30 — inspect — router bound next milestone; base=3a39fd70294c34d072b2aaa448ee226691dbaeae; landing=3a39fd70294c34d072b2aaa448ee226691dbaeae; previous branch gsd-path/M010 retired
- 2026-10-30 — inspect — inspect blocked: docs-audit artifact gate failed after 3 redispatches (last: duplicate section ## Remediation queue at lines 771-772 of sidecar DOCS-AUDIT.md)
- 2026-10-31 — inspect — inspect resumed: owner authorized one final targeted redispatch of inspect_docs (duplicate ## Remediation queue header removal only)
- 2026-10-31 — inspect — inspect blocked: docs-audit gate failed after authorized final redispatch (queue binds 20 of 21 non-verified claims; one row claim text drifted from its Doc-section source)
- 2026-10-31 — inspect — inspect resumed: owner authorized one surgical iteration of inspect_docs with mandatory validator-equivalent self-check before reply
- 2026-10-31 — inspect — inspection artifacts passed
- 2026-10-31 — define — definition started
- 2026-10-31 — define — milestone intent approved
- 2026-10-31 — plan — planning started
- 2026-10-31 — plan — plan approved
- 2026-10-31 — build — build started
- 2026-10-31 — ship — build done; final review pending
- 2026-10-31 — ship — ship blocked: project verify failed - tests/test_post_ship_pointers.py pins DOCS-AUDIT rulings to exactly rows 1-19 while the approved M011 define flow appended owner rulings #20-#24; gap evidence .project/review/final-gap-1.md
- 2026-10-31 — plan — patch plan reopened
- 2026-10-31 — plan — patch plan approved
- 2026-10-31 — build — build started
- 2026-10-31 — ship — build done; final review pending
- 2026-10-31 — ship — final gate passed; shipping approval pending
- 2026-10-31 — ship — milestone named reference-front-door (owner delegated the ruling: "похоже мы застряли - реши оптимально и элегантно в соотвествии с требованиями и задачами репозитория"; backfill of the milestone field skipped at the M011 define approval, verified against pipeline_state TRANSITIONS)
- 2026-10-31 — shipped — archive preflight passed; shipment recorded
