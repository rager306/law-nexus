# Archive — 010-doc-consistency

Milestone: doc-consistency
Shipped: 2026-10-29
Final verdict: all criteria met; project verify passed
Waves: 1  Tasks: 2 done / 2 total  Review cycles used: 1
Carried forward: 15 DOCS-AUDIT ruling(s)

## Success criteria at ship

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| SC1 — The CI inventory names every suite the CI process list runs: the two post-ship pointer suites appear in `repository-quality-gate.json` `ci_process_suite` and in the pin that mirrors it. | met | .project/review/wave-1.cycle1.md |
| SC2 — The agent entry point names the ship-time projection refresh rule, so the next ship reaches it from `AGENTS.md`, not only from a roadmap sentence. | met | .project/review/wave-1.cycle1.md |
| SC3 — The roadmap marker history records every shipped milestone with its dated superseded bullet, and the current-state document pointer names a report that describes the shipped world after M009. | met | .project/review/wave-1.cycle1.md |
| SC4 — `uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py tests/test_repository_quality_gate.py -q` reports 0 failures on the bound branch. | met | .project/review/wave-1.cycle1.md |

## Contents

- build/evidence.json
- build/verify-ledger.jsonl
- intent/INTENT.md
- plan/PLAN.md
- research/DOCS-AUDIT.md
- research/SYNTHESIS.md
- review/FINAL.md
- review/final-gap-1.md
- review/wave-1.cycle1.md
- tasks/T001-ci-inventory-and-agents.md
- tasks/T002-roadmap-history.md

## Notes

- none
