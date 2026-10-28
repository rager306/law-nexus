# Archive — 003-ci-honesty

Milestone: ci-honesty
Shipped: 2026-10-28
Final verdict: all criteria met; project verify passed
Waves: 1  Tasks: 2 done / 2 total  Review cycles used: 1
Carried forward: 15 DOCS-AUDIT ruling(s)

## Success criteria at ship

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| SC1 — On the integrated main CI context (checkout of main, STATE.md `build/active` naming gsd-path/M002), the harness status and preflight suites pass: the SHIPPED_MAIN-scenario expectations key on the checkout's STATE.md phase semantics — `build/active` asserts the honest single-error roadmap finding (roadmap-current-tracks-path naming the M002 continuation), `shipped/done` asserts Contract A pass; the fail-closed pins for foreign/detached/sidecar contexts are unchanged. | met | .project/build/verify-ledger.jsonl (rows `c5d0bfc6…`, `c134ea3d…`); .project/review/wave-1.cycle1.md; tests/branch_context.py:70-96,186-205; tests/test_branch_context.py:202-298,361-445; tests/test_harness_governor.py:119-148; tests/test_harness_preflight.py:277-291 |
| SC2 — No milestone-branch literals remain in the live-suite expectations: `tests/test_harness_governor.py` and `tests/test_harness_preflight.py` contain no `gsd-path/M0NN` literals outside scenario-fixture payloads, and a grep pin test enforces this. | met | tests/test_branch_context.py:465,479-500; .project/review/wave-1.cycle1.md (independent zero-match scan at `c5d0bfc6`) |
| SC3 — The governor-diagnostics artifact publishes on any migration-job failure (including the pytest step that precedes the governor step), with the job exit preserved non-zero. | met | .github/workflows/repository-quality.yml:167-283 (esp. :246,:248,:273-282),:386,:426; tests/test_project_state_roadmap_freshness.py:438-483; .project/build/verify-ledger.jsonl (row `378a0def…`) |
| SC4 — The roadmap marker remains consistent after the fix: the three-way identity test (STATE ↔ roadmap.json ↔ live marker) passes and the live marker names the M002 continuation on gsd-path/M002. | met | prd/project-state/roadmap.md:50; prd/project-state/data/roadmap.json (`current_milestone.id`); .project/STATE.md; tests/test_project_state_roadmap_freshness.py:299-410; .project/review/final-gap-1.md (Gap verdict: pass at this HEAD) |

## Contents

- build/evidence.json
- build/verify-ledger.jsonl
- intent/INTENT.md
- plan/PLAN.md
- research/.dispatch-record-build-T001-2026-10-27.json.lock
- research/.dispatch-record-build-T002-2026-10-27.json.lock
- research/.dispatch-record-review-final-m003-2026-10-27.json.lock
- research/.dispatch-record-review-w1-2026-10-27.json.lock
- research/DOCS-AUDIT.md
- research/SYNTHESIS.md
- research/dispatch-record-build-T001-2026-10-27.json
- research/dispatch-record-build-T002-2026-10-27.json
- research/dispatch-record-review-final-m003-2026-10-27.json
- research/dispatch-record-review-w1-2026-10-27.json
- research/host-capabilities.json
- review/FINAL.md
- review/final-gap-1.md
- review/wave-1.cycle1.md
- tasks/T001-scenario-fix-state-phase-keyed.md
- tasks/T002-diagnostics-scope-roadmap-consistency.md

## Notes

- none
