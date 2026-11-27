# Synthesis — law-nexus M012 projection-alignment

<!-- Quick lane: settled lines only, written by define. No invented decisions. -->

## Settled

- Intent (approved 2026-10-31): refresh the missed M011 ship-time projection per the pinned procedure, record the honest CI state, clear audit rows #25-#50, re-pin the m221 binding, regenerate the GitNexus block — INTENT.md SC1-SC5.
- Rulings #25-#50 recorded in DOCS-AUDIT.md `## User rulings` from the delegated owner directive (2026-10-31); fix-doc #25-#49, fix-code #50; judgment calls #26 (trim to budget), #29 (re-pin current digest), #30 (date-bound legacy line).
- Constraints (INTENT.md): archives read-only; dated history append-only; no product behavior changes; green offline workspace suite must not break; lifecycle tags per D098; ship-time refresh re-runs for M012's own ship.
- Brownfield map (research/evidence-codebase.md): 47-crate Rust workspace, docs entry points README/AGENTS/POST-SHIP-STATE/PRD/ADR; the changed set since the prior audit is M011's T001/T002/T003 surface (crates/ln-product-cli, tests/test_post_ship_pointers.py) plus .project bookkeeping.

## For the planner

Walking skeleton: two disjoint docs tasks in one wave — T001 refreshes the projection and the current-state document (prd/project-state/, docs/agent-stack/POST-SHIP-STATE-2026-10-28.md); T002 clears the long-tail claims (README/AGENTS/PRD/ADR/law-source/PHASE-ADAPTER/product-model), re-pins the m221 binding, and regenerates the GitNexus block. No file overlap; no cross-wave risk.
