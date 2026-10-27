# Review — wave 4, cycle 1

<!-- Independent wave review, cycle 1 (full depth). Review sidecar checkout HEAD
     (review base): 069c2ba80a22e9971ce045affd6382c60c3ee37b (re-read:
     `git rev-parse HEAD` in the sidecar worktree; clean status; identical to the
     primary worktree HEAD on gsd-path/M001). Isolated review diff
     e85cf2b49dc3686e72789ba97fc34dec892c1103..069c2ba80a22e9971ce045affd6382c60c3ee37b
     (single commit 069c2ba8 "T011: Make the governor and preflight suites
     branch-environment-aware"). No task Verify and no project Verify re-run;
     verdicts rest on the recorded orchestrator Verify outputs in the T011 Log,
     re-read at the review base (.project/tasks/T011-branch-aware-governor-tests.md
     and the authoritative rows in .project/build/verify-ledger.jsonl: commit
     069c2ba8 exit 0, 265 passed / 2 skipped, sidecar gsd-path-verify/task-t011-verify;
     T001 regression exit 0, 276 passed / 2 skipped), plus this reviewer's own
     read-only diff inspection and re-read of the on-disk sources at the review
     base (tests/test_harness_governor.py, tests/test_harness_preflight.py,
     src/law_nexus_harness/governor.py, src/law_nexus_harness/workflow_state.py,
     .project/STATE.md, .gitignore, .project/review/PATCH-FINDINGS.md).
     Branch-context note for the brief's "gsd-path-task/*" reading: that naming
     exists only as the frontmatter comment for hypothetical parallel dispatch
     (`task_branch: gsd-path-task/<id> while parallel`); T011 ran serial
     (`task_branch: null`) and no such branch exists in the repository, so the
     one operational context this pipeline defines is the bound branch
     gsd-path/M001 (.project/STATE.md `branch: gsd-path/M001`) — exactly the
     predicate the patch encodes. -->

Wave verdict: pass
Cycle: 1
Depth: full
Tasks reviewed: 1

## T011 — Make the governor and preflight suites branch-environment-aware: pass

- ✅ Both modules resolve the live branch at test time and split on exactly the bound predicate: on gsd-path/M001 every pre-change assertion of the live-surface tests is preserved unchanged; on any other branch the live-governor and preflight tests pin the fail-closed contract — the blocking workflow-state-surface error present and honest error-count semantics — and no assertion on that path asserts `error_count == 0`, live status "ok", or exit code 0. — Diff re-inspected at the review base: both modules add one identical predicate (`BOUND_BRANCH = "gsd-path/M001"`, `_current_branch` via read-only `git rev-parse --abbrev-ref HEAD`, `_on_bound_branch()` equality check — no sidecar-name enumeration, no env/pytest-metadata signal, matching the Approach); all twelve `test_live_governor_*` tests take the pinned path via `_assert_fail_closed_branch_contract` (exactly one `workflow-state-surface` finding, status fail, severity error, rule `workflow-state-surface.blocking`, `observed` starting `kind=`, non-empty remediation, `report.status == "failure"`, `error_count == len(fail+error findings)` and `>= 1` — derived from the report, never a guessed constant; fields cross-checked against `check_workflow_state_surface` in src/law_nexus_harness/governor.py:28112+), and the preflight tests pin `code == 1`, `status == "failure"`, the same blocking finding, and honest counting (`error_count >= 1`; cargo-fmt test keeps its injected failure asserted alongside the environment error, `error_count >= 2`). The pinned contract is real, not nominal: the recorded orchestrator Verify in the gsd-path-verify/task-t011-verify sidecar (the non-operational context) passed with these pins exercised (265 passed / 2 skipped, exit 0, Log + ledger row at commit 069c2ba8). On the bound branch the gate evaluates true (primary worktree branch re-read: gsd-path/M001) and the original assertions — `error_count == 0`, `status == "ok"`, `code == 0` — stand verbatim (see AC2). Misclassification fails loud in both directions, never silently: an operational report routed to the pinned path fails the `status == "fail"` pin (a pass finding has `workflow-state-surface.operational`), and a blocking report routed to the full path fails `error_count == 0`.
- ✅ No weakening where the governor is operational: no pre-change operational assertion is deleted or loosened; no test is removed; no unconditional skip, xfail, or suppression added (N3); the journal-gated skips behave exactly as before. — numstat at the review base: tests/test_harness_governor.py 84 insertions / 0 deletions (gates are pure insertions above byte-untouched bodies — no original character changed); tests/test_harness_preflight.py 68 insertions / 2 deletions, and the 2 deleted lines are exactly the two moved asserts `assert code == 0` and `assert payload["status"] == "ok"`, re-added verbatim below the gate (diff hunk re-read); test counts unchanged (232 → 232, 19 → 19 via `git grep -c "^def test_"` at both refs); the only skip surface in both files remains the pre-existing `_skip_without_pi_journal` pair (tests/test_harness_governor.py:5215-5274, no diff hunks near it; the 2 skipped in the recorded sidecar run are exactly these, skipped because `.gsd` is gitignored and absent from sidecars per .gitignore:92 — recorded-reason skip semantics unchanged); no pytest.skip/xfail/mark added anywhere in the diff (N3 holds; SC9's no-suppression rule intact in the touched modules).
- ✅ `uv run --frozen pytest tests/test_harness_governor.py tests/test_harness_preflight.py -q` passes in both environments: on a governor-operational branch (the task isolate; full-assertion path exercised, run's branch recorded in the Log) and on a non-operational branch (the orchestrator's gsd-path-verify/* verify sidecar at finish; pinned-contract path exercised). — Non-operational leg: recorded orchestrator Verify, sidecar gsd-path-verify/task-t011-verify, branch recorded in the Log, exit 0, 265 passed / 2 skipped (Log + ledger row 069c2ba8 re-read) — the pinned-contract path exercised and green. Operational leg: the r1 coder's in-flight Verify on the bound branch never returned (disclosed in the Log takeover note), so no post-change recorded run exists on gsd-path/M001; the pass there rests on checked structural evidence, not assumption — the bound-branch execution path is byte-identical pre/post change (84/0 insertions in the governor module; the two moved preflight asserts reappear verbatim), the predicate is provably true on that branch (branch re-read at the review base), and the identical assertions were recorded green on the same branch pre-change (PATCH-FINDINGS.md P001 note: r2 278/0; wave-gate governor 0 errors). Warning recorded below.
- ✅ T001's Verify still passes: `uv run --frozen pytest tests/test_harness_governor.py tests/test_phase_dispatch_adapter.py tests/test_path_isolation_recovery.py -q` (file-overlap landing rule). — Recorded orchestrator regression Verify of T001 in the same sidecar (Log, re-read): pass, exit 0, 276 passed / 2 skipped; ledger-consistent.
- ✅ The landing diff touches exactly the two declared test modules. — `git diff --stat e85cf2b4..069c2ba8` re-read: exactly tests/test_harness_governor.py (+84/−0) and tests/test_harness_preflight.py (+68/−2) plus the task file's own frontmatter state and Log appends (+30/−5) — the task file is the task's own orchestrator-maintained record (status/agent/base/Log), the same bookkeeping every landing commit in this milestone carries (precedent: T001 landing 9cb5107a); no product or third path touched.

Warnings (non-blocking):
- AC3's operational-branch leg has no completed post-change recorded run: the coder exited before its in-flight bound-branch Verify returned (disclosed in the Log; the orchestrator's sidecar run is the binding evidence). The pass rests on the byte-identical bound-branch path plus the recorded pre-change green (278/0, PATCH-FINDINGS.md). Worth one cheap close-out: before ship, record one post-change run of the task Verify (or at minimum SC1's command `uv run --frozen pytest tests/test_harness_governor.py tests/test_phase_dispatch_adapter.py -q`) on the bound branch, so the full-assertion path carries direct recorded evidence — the finish Project Verify re-run only exercises the pinned sidecar path.
- AC5 read strictly counts the task file in the landing diff; treated as the established landing-bookkeeping exception (frontmatter + Log only, zero prose changes), consistent with every prior landing in this milestone.

Contract violations (blocking):
- none

## Intent coverage

### SC1 — SC1 — The five pre-milestone fixes are landed as task commits on `gsd-path/M001`; `uv run --frozen pytest tests/test_harness_governor.py tests/test_phase_dispatch_adapter.py` reports 0 failures on the bound branch.: pass
- ✅ The five fixes are landed (T001 commit 9cb5107a on gsd-path/M001, proven in wave 1) and the SC1 command's touched file remains green in both environments after this patch: the command's tests/test_harness_governor.py keeps its bound-branch assertions byte-identical (84/0 numstat, re-inspected at the review base), was recorded 278/0 green on the bound branch pre-change (PATCH-FINDINGS.md), and the recorded post-change sidecar run (exit 0, 265 passed / 2 skipped, ledger row 069c2ba8) proves the suite reports 0 failures where the branch lock fires — the patch exists precisely so SC1's recorded-evidence integrity survives the verify-sidecar environment (P001 discharged for the recorded evidence; the 14 exact failures of P001 — live-governor ×12 + preflight ×2 — are all gated and green in the recorded run).

## Summary for orchestrator

- blocked findings: none
- repeat offenders: none
- warnings worth a human eye: (1) no completed post-change recorded run of the task Verify on the bound branch (coder exit, disclosed) — recommend recording one before ship so the full-assertion path has direct evidence; (2) AC5's "exactly the two declared test modules" read with the standard task-file bookkeeping exception (frontmatter/Log only).
