# Archive — 008-pointer-in-ci

Milestone: pointer-in-ci
Shipped: 2026-10-28
Final verdict: all criteria met; project verify passed
Waves: 1  Tasks: 2 done / 2 total  Review cycles used: 1
Carried forward: 15 DOCS-AUDIT ruling(s)

## Success criteria at ship

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| SC1 — The CI suite list runs both pointer suites, so a projection that disagrees with the shipped STATE.md fails a job instead of reaching main. | met | .project/review/wave-1.cycle1.md |
| SC2 — The tracked projection names the shipped milestone: `roadmap.json` `current_milestone.id` equals the milestone in `.project/STATE.md`, and the live marker bullet in `roadmap.md` names the same slug. | met | .project/review/wave-1.cycle1.md |
| SC3 — `uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py tests/test_ci_runtime_restore.py -q` reports 0 failures on the bound branch. | met | .project/review/wave-1.cycle1.md |

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
- tasks/T001-pointer-suites-in-ci.md
- tasks/T002-refresh-projection.md

## Notes

- none
