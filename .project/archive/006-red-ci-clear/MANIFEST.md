# Archive — 006-red-ci-clear

Milestone: red-ci-clear
Shipped: 2026-10-28
Final verdict: all criteria met; project verify passed
Waves: 1  Tasks: 2 done / 2 total  Review cycles used: 1
Carried forward: 15 DOCS-AUDIT ruling(s)

## Success criteria at ship

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| SC1 — The main-branch governor honesty step accepts the shipped integrated surface of whichever milestone is current: it asserts the `kind=shipped-integrated;` shape and a `.project/archive/` path, never a milestone literal, and `tests/test_ci_runtime_restore.py` pins that shape. | met | .project/review/wave-1.cycle1.md |
| SC2 — The tracked roadmap projection agrees with shipped STATE.md: `prd/project-state/data/roadmap.json` (and `roadmap.md`) name the milestone recorded in `.project/STATE.md`. | met | .project/review/wave-1.cycle1.md |
| SC3 — `uv run --frozen pytest tests/test_ci_runtime_restore.py tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py tests/test_harness_governor.py tests/test_harness_preflight.py -q` reports 0 failures on the bound branch. | met | .project/review/wave-1.cycle1.md |

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
- tasks/T001-ci-governor-shape.md
- tasks/T002-roadmap-pointer.md

## Notes

- none
