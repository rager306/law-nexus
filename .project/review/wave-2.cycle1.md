# Review — wave 2, cycle 1

<!-- Review sidecar checkout HEAD (recorded per brief, confirmed via `git rev-parse HEAD`
     inside this sidecar): 3fffeaba43862969a5f9867f09653bf717f0bd05 — the T002 landing commit, equal to the brief's
     recorded commit. Method: `git diff 3b2e1e4c..3fffeaba` read inside the sidecar
     (byte-identical to the same diff in the primary root, sha256
     0233fb6f52aa2f4acf269900c3bc850b3c7d04f916b2730534ce9cf513389326), the
     orchestrator's recorded isolated Verify in the T002 Log plus the matching
     verify-ledger row, and independent re-execution of the step's own `run:` text
     under the GitHub bash default shell. No task Verify and no PLAN project Verify
     was re-run as Verify evidence; the one command re-run is SC3's own command,
     which SC3 names verbatim. The sidecar checkout sits on branch
     gsd-path-verify/wave-2-cycle-1, so the live governor reports
     `kind=conflicting-ownership` there — that report is the realistic input used
     to walk the step, not a claim about main. -->

Wave verdict: pass
Cycle: 1
Depth: full
Tasks reviewed: 1

## T002 — Make the governor honesty step name the missing proof input: pass

- ✅ A non-shipped surface exits non-zero and the log names the observed surface plus the proof-input state (E2). — recorded orchestrator Verify (sidecar `gsd-path-verify/task-t002-verify`, exit 0, `3 passed, 13 deselected in 1.54s`, ledger row at 3fffeaba) plus independent execution of the step's exact `run:` text at `.github/workflows/repository-quality.yml:261-303` under `bash --noprofile --norc -eo pipefail`: a conflicting-ownership surface on main exits 1 and the log carries `proof inputs: branch=... origin_head=refs/remotes/origin/main tags=6` (:267) together with the teed governor JSON holding `observed` `kind=conflicting-ownership; ... reason: current branch ... != STATE.branch ...`; a shipped-integrated surface with `.project/archive/` exits 0; a shipped-integrated surface without the archive path exits 1 naming the observed surface; `tool_error_count=1` exits 1. E2 held-out: with no `workflow-state-surface` finding at all, the step prints `workflow-state-surface: []` (:283) and exits 1 with `governor on main must report the shipped integrated state; workflow-state-surface observed: ''`; its held-out test file is `tests/test_ci_runtime_restore.py`, recorded output `3 passed` for the T002 Verify and `16 passed` for the full file re-run at 3fffeaba.
- ✅ No existing assertion is removed or weakened; the step still fails on a lying surface (N2). — the landing diff removes no line from either declared file (`.github/workflows/repository-quality.yml` 15 insertions / 0 deletions; `tests/test_ci_runtime_restore.py` 4 insertions / 0 deletions), so every pre-existing assertion and fatal condition survives verbatim: `if: always()` (:260), `set -o pipefail` (:262), the governor `tee` pipeline (:268), the `tool_error_count` exit (:285), the `refs/heads/main` shipped-integrated exit (:287-297), and the `.project/archive/` exit (:298-302); the new pins are appended after the existing ones at `tests/test_ci_runtime_restore.py:256-260`. Lying-surface probes at 3fffeaba each still fail the step: shipped-integrated without the archive path exit 1, bootstrap surface on main exit 1, no surface finding on main exit 1, `tool_error_count` exit 1; the migration job keeps no `continue-on-error`, no `|| true`, and the diagnostics upload stays its last step (N2).

Warnings (non-blocking):
- The two new `print` lines (`workflow-state-surface:` at `.github/workflows/repository-quality.yml:283` and `proof inputs: GITHUB_REF=` at :284) are unreachable in exactly the error path they were written for. GitHub's bash default shell already carries `-e` and `-o pipefail`, and the step re-asserts `set -o pipefail` at :262, so when the governor exits non-zero — the conflicting-ownership case — the step aborts at the `tee` pipeline (:268) and the heredoc never runs. Verified by executing the step text with a governor stub exiting 1: the `proof inputs: branch=` echo prints, the surface print does not. The criterion still holds because the teed raw governor JSON names the observed surface and the echo names the three proof inputs; if the friendly line is the intended artifact, print the surface before the pipeline or capture the governor exit instead of aborting on it.
- AC1 does not scope its non-zero exit to a push to main. On `pull_request` refs a non-shipped surface still exits 0, because the pre-existing honesty assertions are `GITHUB_REF`-scoped to `refs/heads/main` (:287). Passed on that reasonable reading (INTENT E1/E2 rule on SC1 and on the empty-report case, not on this one); the AC should say "on a push to main" so the next reader is not left to infer it.
- The E2 pin is textual: `tests/test_ci_runtime_restore.py:258` asserts the presence of the print-statement source text, so a refactor that keeps that string while changing behavior would still pass. The behavioral evidence for E2 above is the reviewer's own execution, not the pinned test. A pin that feeds a fixture report with no surface finding through the step logic would close it.

Contract violations (blocking):
- none

## Intent coverage

### SC2 — SC2 — The migration job's governor honesty step names the exact missing proof input when the surface is not shipped-integrated, so a checkout-shape defect is diagnosable from the job log alone.: pass
- ✅ The step names the observed surface and the three proof inputs on the failing path at `.github/workflows/repository-quality.yml:267` and :275-284, and keeps every pre-existing fatal condition at :285-302 unchanged (zero deletions in the landing diff). Executed at 3fffeaba: conflicting-ownership on main exits 1 with the surface `observed` string and `branch`/`origin_head`/`tags` in the log; the real governor run in this sidecar (branch gsd-path-verify/wave-2-cycle-1, `tags=6`, `origin_head=refs/remotes/origin/main`) produced `kind=conflicting-ownership` with the reason naming the branch mismatch, which is the checkout-shape fact the criterion asks the log to expose.
- ✅ E2 (held-out, `tests/test_ci_runtime_restore.py`): recorded output `3 passed, 13 deselected in 1.54s` (T002 Verify, exit 0, ledger row at 3fffeaba) and `16 passed` for the full file re-run at 3fffeaba; independent execution with a report carrying no `workflow-state-surface` finding exits 1 and names the empty observed surface.
- ✅ N2 (prohibition): the step is not a no-op and suppresses no exit — `|| true` is absent, `continue-on-error` is absent on the step and the job, `set -o pipefail` is retained at :262, and each lying-surface probe above exits non-zero.

### SC3 — SC3 — `uv run --frozen pytest tests/test_ci_runtime_restore.py -q` passes and pins both job shapes.: pass
- ✅ `uv run --frozen pytest tests/test_ci_runtime_restore.py -q` at 3fffeaba in this sidecar: `16 passed in 2.21s`, exit 0. The suite pins both job shapes: rust checkout `fetch-depth: 0` plus `fetch-tags: true` and the origin/HEAD prepare step (`tests/test_ci_runtime_restore.py:277-292`), migration checkout `fetch-depth: 0` plus the origin/HEAD prepare step after the runtime restore (:263-274).
- ✅ E3 (boundary): dropping any single input fails the suite rather than passing quietly — mutations of the workflow at 3fffeaba each produced one failure: rust `fetch-tags` removed → `KeyError: 'fetch-tags'` at :290; rust `fetch-depth` removed → `KeyError: 'fetch-depth'` at :289; migration `Prepare shipped-main integration proof inputs` step removed → `_named_step` assertion at :92; migration `fetch-depth` removed → `KeyError: 'fetch-depth'` at :268.
- ✅ N3 (prohibition): the checkout-input pins are neither deleted nor weakened — the tests diff is 4 insertions and 0 deletions, and the pre-existing `fetch-tags`/`fetch-depth`/origin-HEAD assertions are byte-identical to the base.

## Summary for orchestrator

- blocked findings: none
- repeat offenders: none — first cycle for wave 2; wave 1's landed pins (T001) re-checked for regression through the full-file suite and the four mutation probes above, all still failing on a dropped input.
- warnings worth a human eye:
  - the two new diagnostic `print` lines do not run when the governor exits non-zero (GitHub bash `-e` plus `pipefail` aborts at the `tee` pipeline), so the intended friendly surface line is absent from the failing log; the teed JSON and the `proof inputs: branch=...` echo still make the defect diagnosable.
  - AC1 is unscoped as to ref: on pull-request runs a non-shipped surface still exits 0 by pre-existing design.
  - the E2 pin asserts source text, not behavior; consider a fixture-report pin.
