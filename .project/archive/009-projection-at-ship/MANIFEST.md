# Archive — 009-projection-at-ship

Milestone: projection-at-ship
Shipped: 2026-10-29
Final verdict: all criteria met; project verify passed
Waves: 1  Tasks: 3 done / 3 total  Review cycles used: 3
Carried forward: 15 DOCS-AUDIT ruling(s)

## Success criteria at ship

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| SC1 — The tracked projection names the milestone being shipped: after this milestone's ship, `roadmap.json` `current_milestone.id` equals the milestone in `.project/STATE.md`, and the live marker bullet names the same slug. | met | .project/review/wave-1.cycle3.md |
| SC2 — The refresh rule is recorded where the next ship reads it, so a future milestone refreshes the projection at ship rather than during build. | met | .project/review/wave-1.cycle3.md |
| SC3 — `uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py -q` reports 0 failures on the bound branch and on the shipped tree. | met | .project/review/wave-1.cycle3.md |

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
- review/wave-1.cycle1.repair-T002.json
- review/wave-1.cycle2.md
- review/wave-1.cycle2.repair-T003.json
- review/wave-1.cycle3.md
- tasks/T001-projection-at-ship.md
- tasks/T002-fix-wave-1-cycle-1.md
- tasks/T003-fix-wave-1-cycle-2.md

## Notes

- none
