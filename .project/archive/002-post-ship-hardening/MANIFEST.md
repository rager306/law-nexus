# Archive — 002-post-ship-hardening

Milestone: post-ship-hardening
Shipped: 2026-10-27
Final verdict: all criteria met; project verify passed
Waves: 2  Tasks: 5 done / 5 total  Review cycles used: 1/1
Carried forward: 15 DOCS-AUDIT ruling(s)

## Success criteria at ship

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| SC1 — On a fresh checkout of integrated `main` the `repository-quality` migration job restores the pinned GSD Path runtime (version and sha256 digest recorded in `.gsd-path/runtime.json`, installed from the vendored archive in the repository) before any operational check, and the real governor run on integrated `main` exits 0 reporting `shipped/done` with the archive path; a digest mismatch or missing archive fails loudly. | met | .github/workflows/repository-quality.yml:99,198,214,242-274` at Reviewed HEAD; `.project/tasks/T001-ci-runtime-restore-and-diagnostics.md` (Log: live probe, rehearsals, recorded Verify); `.project/tasks/T003-context-independent-scenario-matrix.md` (Log: r1 cross-context runs); `tests/test_ci_runtime_restore.py`; `.gsd-path/runtime.json`; E1, E2, N1 evidence as above |
| SC2 — The governor and preflight test suites are context-independent: five scenario groups (active milestone on its bound branch, foreign branch, detached checkout, verify sidecar, shipped integrated main) each pin their documented contract; on `gsd-path/M001`-class branches the fail-closed branch-ownership contract itself is pinned (per owner ruling (a), M001); substantive product assertions run in every context where the governor is operational; nothing is skipped or suppressed without a loud recorded reason. | met | tests/branch_context.py`, `tests/test_branch_context.py` at Reviewed HEAD; `.project/tasks/T003-context-independent-scenario-matrix.md` (Log: recorded runs with branch per run, orchestrator sidecar Verify passes); `.project/review/wave-1.cycle1.md` (SC2 section); E3, E4, N2 evidence as above |
| SC3 — When the governor fails in CI its diagnostic JSON is published as a workflow artifact and printed to the job log, and the job exit stays non-zero (no suppression; N3). | met | .github/workflows/repository-quality.yml:242-274,379,419` at Reviewed HEAD; `.project/tasks/T001-ci-runtime-restore-and-diagnostics.md` (Log: recorded Verify, rehearsals); `.project/review/wave-1.cycle1.md` (SC3 section); E5, N3 evidence as above |
| SC4 — Post-ship pointers are truthful at the shipped state: `roadmap.md` records M001 shipped/archived and the M002 continuation; the DOCS-AUDIT queue rows closed by T005/T006 reference their task ids; the crosswalk M225 row links the T004 rerun receipt (`hermetic-pass-parity-unproven`, corpus parity explicitly unproven); a dated post-ship report supersedes the pre-ship cutover snapshot as the current-state document (the pre-ship file remains as a dated snapshot). | met | prd/project-state/roadmap.md`; `prd/project-state/data/roadmap.json`; `docs/agent-stack/history/LEGACY_CROSSWALK.md` (M225 obligations row); `.project/research/DOCS-AUDIT.md` (rows 6, 9, 19); `docs/agent-stack/POST-SHIP-STATE-2026-10-27.md`; `.project/tasks/T004-post-ship-pointers-and-report.md` (Log: recorded Verify); E6, N4 evidence as above |
| SC5 — A fresh session, given only the repository and a minimal pointer, executes the M002 acceptance walkthrough: restores the pinned runtime per the documented bootstrap, runs the status/governor/freshness commands recognizing the shipped M001 and the M002 continuation, and records the proof on disk (same recording discipline as M001's resume proof, N8). | met | .project/build/M002-ACCEPTANCE-PROOF.md`; `docs/agent-stack/POST-SHIP-STATE-2026-10-27.md` ("Fresh-session bootstrap"); `.project/tasks/T005-fresh-session-acceptance-walkthrough.md` (Log: fresh-session walkthrough + two orchestrator Verify passes exit 0); E2, E7, N5 evidence as above |

## Contents

- build/M002-ACCEPTANCE-PROOF.md
- build/evidence.json
- build/verify-ledger.jsonl
- intent/INTENT.md
- plan/PLAN.md
- plan/gate-plan-receipt.json
- research/.dispatch-record-build-T001-2026-10-27.json.lock
- research/.dispatch-record-build-T002-2026-10-27.json.lock
- research/.dispatch-record-build-T002-m002-2026-10-27.json.lock
- research/.dispatch-record-build-T003-2026-10-27.json.lock
- research/.dispatch-record-build-T003-m002-2026-10-27.json.lock
- research/.dispatch-record-build-T003-r2-2026-10-27.json.lock
- research/.dispatch-record-build-T004-2026-10-27.json.lock
- research/.dispatch-record-build-T004-m002-2026-10-27.json.lock
- research/.dispatch-record-build-T005-2026-10-27.json.lock
- research/.dispatch-record-review-final-m002-2026-10-27.json.lock
- research/.dispatch-record-review-w1-m002-2026-10-27.json.lock
- research/DOCS-AUDIT.md
- research/SYNTHESIS.md
- research/dispatch-record-build-T001-2026-10-27.json
- research/dispatch-record-build-T002-2026-10-27.json
- research/dispatch-record-build-T003-2026-10-27.json
- research/dispatch-record-build-T003-m002-2026-10-27.json
- research/dispatch-record-build-T003-r2-2026-10-27.json
- research/dispatch-record-build-T004-m002-2026-10-27.json
- research/dispatch-record-build-T005-2026-10-27.json
- research/dispatch-record-review-final-m002-2026-10-27.json
- research/dispatch-record-review-w1-m002-2026-10-27.json
- research/host-capabilities.json
- review/FINAL.md
- review/final-gap-1.md
- review/wave-1.cycle1.md
- review/wave-2.cycle1.md
- tasks/T001-ci-runtime-restore-and-diagnostics.md
- tasks/T002-shipped-integrated-state-contract.md
- tasks/T003-context-independent-scenario-matrix.md
- tasks/T004-post-ship-pointers-and-report.md
- tasks/T005-fresh-session-acceptance-walkthrough.md

## Notes

- none
