# Archive — 005-ci-fixture-fix

Milestone: ci-fixture-fix
Shipped: 2026-10-28
Final verdict: all criteria met; project verify passed
Waves: 1  Tasks: 1 done / 1 total  Review cycles used: 1
Carried forward: 15 DOCS-AUDIT ruling(s)

## Success criteria at ship

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| SC1 — The live governor and preflight surface suites pass on the integrated main checkout: the roadmap-freshness fixture derives the current milestone from the tracked roadmap.json (no milestone literal), and the bound-branch surface pins accept both `build/active` and `shipped/done`. | met | .project/tasks/T001-ci-fixture-co-update.md Log; recorded orchestrator Verify. |
| SC2 — `uv run --frozen pytest tests/test_harness_governor.py tests/test_harness_preflight.py tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py -q` reports 0 failures on the bound branch. | met | .project/tasks/T001-ci-fixture-co-update.md Log. |

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
- tasks/T001-ci-fixture-co-update.md

## Notes

- none
