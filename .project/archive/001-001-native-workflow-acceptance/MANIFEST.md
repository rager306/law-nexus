# Archive — 001-001-native-workflow-acceptance

Milestone: 001-native-workflow-acceptance
Shipped: 2026-10-27
Final verdict: all criteria met; project verify passed
Waves: 4  Tasks: 11 done / 11 total  Review cycles used: 1/1/1/1
Carried forward: 18 DOCS-AUDIT ruling(s)

## Success criteria at ship

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| SC1 — The five pre-milestone fixes are landed as task commits on `gsd-path/M001`; `uv run --frozen pytest tests/test_harness_governor.py tests/test_phase_dispatch_adapter.py` reports 0 failures on the bound branch. | met | .project/tasks/T001-land-pre-milestone-fixes.md; .project/tasks/T011-branch-aware-governor-tests.md; .project/build/verify-ledger.jsonl (rows 9cb5107a, 069c2ba8, 2eed79ab); .project/review/wave-1.cycle1.md; .project/review/wave-4.cycle1.md |
| SC2 — The workflow marker in `prd/project-state/roadmap.md` names this Path milestone slug exactly; the governor reports 0 errors on the bound branch with the milestone set (no pre-milestone exception in play). | met | prd/project-state/roadmap.md:50; .project/tasks/T002-sync-workflow-marker.md; .project/build/M001-RESUME-PROOF.md; .project/review/wave-1.cycle1.md |
| SC3 — The M225 validation residual is closed natively: the battery records a filled `tested_source_revision`, the source pin is re-bound to the exact validation HEAD, native validation is re-run and an honest verdict (with its measurement class) is recorded; S02 code is unchanged. | met | prd/migration/rust-evidence/m225-validation-battery-2026-10-18.json; prd/migration/rust-evidence/m225-validation-rerun-m001.json; .project/tasks/T004-m225-validation-residual.md; .project/review/wave-2.cycle1.md |
| SC4 — `product-model/` exists with a minimal PDD model of the already established product behavior (stubs modeled as stubs, nothing aspirational); the PDD statements in AGENTS.md and docs/agent-stack/WORKFLOW.md are true (audit #6/#19). | met | product-model/ (28 tracked files); .project/tasks/T005-minimal-pdd-model.md; .project/review/wave-2.cycle1.md |
| SC5 — GitNexus is re-indexed and the tool block in AGENTS.md matches the live index (audit #9). | met | prd/project-state/data/gitnexus-index.json; AGENTS.md gitnexus block; .project/tasks/T006-gitnexus-reindex.md; .project/build/verify-ledger.jsonl (row 55ec0072); .project/review/wave-2.cycle1.md |
| SC6 — One limited task runs the full native cycle: dispatch, worker, native validators, and an independent review (different evidence path or different model family; a same-family re-run does not count), with evidence recorded under `.project/` (task log, verify sidecar, review verdict). | met | .project/research/dispatch-record-build-T007-2026-10-26.json; .project/tasks/T007-native-cycle-junk-deletion.md; .project/build/verify-ledger.jsonl (row 105b3d6c); .project/review/wave-3.cycle1.md |
| SC7 — The session is closed with a handoff and a fresh session resumes from disk alone; the proof is the new session's recorded verification output. | met | .project/build/M001-RESUME-PROOF.md; .project/build/HANDOFF-M001-resume.md; .project/tasks/T008-resume-proof.md; .project/build/verify-ledger.jsonl (row 2ce3b6d7); .project/review/wave-3.cycle1.md |
| SC8 — a written cutover readiness assessment exists recording the milestone's per-criterion evidence, the CI policy honesty (M207 advisory, corpus job skipped — green CI never proves corpus scenarios ran), the settled corpus-delivery direction (runner-only, pinned zstd snapshot shape, on-runner layout contract), and the CI/publication evidence status; the bound branch publishes through ship integration only (the repository's pre-push guard is the enforcing contract and CI runs on the integrated main surface), so publication and CI evidence are recorded as pending-ship, not produced inside this milestone; `cutover` remains `false`. | met | docs/agent-stack/CUTOVER-READINESS-M001.md; INTENT.md ## Corrections (2026-10-26, «(a)»); .project/tasks/T009-publish-cutover-readiness.md; .project/build/verify-ledger.jsonl (row d5c46c1b); .project/review/wave-3.cycle1.md |
| SC9 — Small package landed: the m207 schema check no longer runs under an unconditional `\|\| true`; the corpus job config matches its comment (or the comment states the actual setup); `workflow_state.py` rejects a present optional field of the wrong type while accepting missing/null, with a regression test; no new blanket suppression may be introduced. | met | .github/workflows/repository-quality.yml (m207 step; corpus-integration job); src/law_nexus_harness/workflow_state.py (_identity_field); .project/tasks/T003-ci-policy-payload-package.md; .project/build/verify-ledger.jsonl (row 2e1e3c58); .project/review/wave-1.cycle1.md |
| SC10 — `a.txt`, `b.txt`, `c.txt` are deleted from the repository root. | met | .project/tasks/T007-native-cycle-junk-deletion.md; .project/build/verify-ledger.jsonl (row 105b3d6c); .project/build/M001-RESUME-PROOF.md |

## Contents

- build/HANDOFF-M001-resume.md
- build/M001-RESUME-PROOF.md
- build/evidence.json
- build/verify-ledger.jsonl
- intent/INTENT.md
- plan/PLAN.md
- plan/build-recovery-7e994d3b42560d25d4413604a9cb19a6bd2e3d64/review/wave-1.cycle1.md
- plan/build-recovery-7e994d3b42560d25d4413604a9cb19a6bd2e3d64/review/wave-2.cycle1.md
- plan/gate-plan-receipt.json
- research/.dispatch-record-2026-10-26.json.lock
- research/.dispatch-record-build-T001-2026-10-26.json.lock
- research/.dispatch-record-build-T002-2026-10-26.json.lock
- research/.dispatch-record-build-T003-2026-10-26.json.lock
- research/.dispatch-record-build-T004-2026-10-26.json.lock
- research/.dispatch-record-build-T005-2026-10-26.json.lock
- research/.dispatch-record-build-T006-2026-10-26.json.lock
- research/.dispatch-record-build-T007-2026-10-26.json.lock
- research/.dispatch-record-build-T008-2026-10-26.json.lock
- research/.dispatch-record-build-T009-2026-10-26.json.lock
- research/.dispatch-record-build-T010-2026-10-26.json.lock
- research/.dispatch-record-decide-2026-10-26.json.lock
- research/.dispatch-record-plan-2026-10-26.json.lock
- research/.dispatch-record-review-final-2026-10-27.json.lock
- research/.dispatch-record-review-w1c1-2026-10-26.json.lock
- research/.dispatch-record-review-w1c2-2026-10-26.json.lock
- research/.dispatch-record-review-w2c1-2026-10-26.json.lock
- research/.dispatch-record-review-w2c2-2026-10-26.json.lock
- research/.dispatch-record-review-w3c1-2026-10-26.json.lock
- research/.dispatch-record-review-w3c2-2026-10-26.json.lock
- research/.dispatch-record-review-w4c1-2026-10-26.json.lock
- research/DOCS-AUDIT.md
- research/HANDOFF-2026-10-25.md
- research/HANDOFF-2026-10-26.md
- research/RESEARCH.md
- research/SYNTHESIS.md
- research/dispatch-record-2026-10-26.json
- research/dispatch-record-build-T001-2026-10-26.json
- research/dispatch-record-build-T002-2026-10-26.json
- research/dispatch-record-build-T003-2026-10-26.json
- research/dispatch-record-build-T004-2026-10-26.json
- research/dispatch-record-build-T005-2026-10-26.json
- research/dispatch-record-build-T006-2026-10-26.json
- research/dispatch-record-build-T007-2026-10-26.json
- research/dispatch-record-build-T008-2026-10-26.json
- research/dispatch-record-build-T009-2026-10-26.json
- research/dispatch-record-build-T010-2026-10-26.json
- research/dispatch-record-decide-2026-10-26.json
- research/dispatch-record-plan-2026-10-26.json
- research/dispatch-record-review-final-2026-10-27.json
- research/dispatch-record-review-w1c1-2026-10-26.json
- research/dispatch-record-review-w1c2-2026-10-26.json
- research/dispatch-record-review-w2c1-2026-10-26.json
- research/dispatch-record-review-w2c2-2026-10-26.json
- research/dispatch-record-review-w3c1-2026-10-26.json
- research/dispatch-record-review-w3c2-2026-10-26.json
- research/dispatch-record-review-w4c1-2026-10-26.json
- research/evidence-codebase.md
- research/evidence-stack.md
- research/host-capabilities.json
- research/supplied-spec-2026-10-26.md
- review/FINAL.md
- review/PATCH-FINDINGS.md
- review/final-gap-1.md
- review/wave-1.cycle1.md
- review/wave-2.cycle1.md
- review/wave-3.cycle1.md
- review/wave-4.cycle1.md
- tasks/T001-land-pre-milestone-fixes.md
- tasks/T002-sync-workflow-marker.md
- tasks/T003-ci-policy-payload-package.md
- tasks/T004-m225-validation-residual.md
- tasks/T005-minimal-pdd-model.md
- tasks/T006-gitnexus-reindex.md
- tasks/T007-native-cycle-junk-deletion.md
- tasks/T008-resume-proof.md
- tasks/T009-publish-cutover-readiness.md
- tasks/T010-reword-corpus-glob-guard-claim.md
- tasks/T011-branch-aware-governor-tests.md

## Notes

- none
