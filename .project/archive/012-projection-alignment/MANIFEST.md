# Archive — 012-projection-alignment

Milestone: projection-alignment
Shipped: 2026-11-27
Final verdict: all criteria met; project verify passed
Waves: 1  Tasks: 2 done / 2 total  Review cycles used: 1
Carried forward: 36 DOCS-AUDIT ruling(s)

## Success criteria at ship

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| The ship-time projection refresh (per `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`) names the shipped M011 record — milestone `reference-front-door`, ship `38abe687`, integration `ef17106b`, archive `011-reference-front-door` — in `prd/project-state/roadmap.md` and `roadmap.json`, and `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py tests/test_post_ship_pointers.py -q` reports 0 failures at HEAD. | met | prd/project-state/roadmap.md:54-69; prd/project-state/data/roadmap.json (`current_milestone`); .project/build/verify-ledger.jsonl project entry at 450ee12d (exit 0, 2026-11-01T09:32:17Z); docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md steps 1-2 |
| `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` appends the M011 delivered record (ship `38abe687`, integration `ef17106b`, tag `milestone/011-reference-front-door`, archive `.project/archive/011-reference-front-door`) and records the newest main run 41198873586 at `ef17106b` as a FAILURE on the projection suites with prior green runs kept as dated history; the fresh-session bootstrap step 4 again tells the reader to expect all tests to pass. | met | docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:12-16, 133, 157-184, 225-231, 245-252 |
| Audit rows #25-#28, #30-#31, #36-#37, and #44-#49 are re-verified against the live tree: ARCHITECTURE parser counts or their removal, one-page oracle within the 325-line budget, ADR index table header, cross-matrix through ADR-0031, legacy-ledger line date-bound, law-source README checkout wording, PHASE-ADAPTER header aligned with its section 9, interface.md listing five subcommands, README status band and assessments range, AGENTS.md DB count and fixture counts, README ADR range 0004-0031 — the audit claim check passes for each. | met | per-row file:line above; .project/research/DOCS-AUDIT.md rows #25-#49; INTENT.md `## Prohibitions` N3 |
| `prd/architecture/m221-s05-docs-reconciliation.yaml` pins path+sha256 equal to the tracked `prd/architecture/npa-analysis-jsonl-contract.md` at HEAD, and the M221 s05 readiness battery passes with the re-pinned binding. | met | prd/architecture/m221-s05-docs-reconciliation.yaml:38-40; tests/test_m221_authority_reconciliation.py:154-155, 180-181, 214; .project/build/verify-ledger.jsonl T002 row (e486adfe, exit 0) |
| The AGENTS.md GitNexus block is regenerated from a fresh `node .gitnexus/run.cjs analyze --force --name law-nexus` run; its numbers equal that run's recorded meta.json (nodes/edges/processes) and the note that the index is local-excluded stays. | met | AGENTS.md:355-398; /root/law-nexus/.gitnexus/meta.json (recorded run artifact); commit e486adfe; .git/info/exclude |

## Contents

- build/evidence.json
- build/verify-ledger.jsonl
- intent/INTENT.md
- plan/PLAN.md
- research/DOCS-AUDIT.md
- research/SYNTHESIS.md
- research/evidence-codebase.md
- review/FINAL.md
- review/final-gap-1.md
- review/wave-1.cycle1.md
- tasks/T001-projection-refresh-and-honest-state.md
- tasks/T002-longtail-claims-m221-gitnexus.md

## Notes

- none
