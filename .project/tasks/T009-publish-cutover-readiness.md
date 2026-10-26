---
id: T009
title: Publish the milestone branch and write the cutover readiness assessment
wave: 3
deps: [T007, T008]
status: pending    
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null
files:
  - docs/agent-stack/CUTOVER-READINESS-M001.md
  - tests/test_m001_cutover_readiness.py
---

# T009 — Publish the milestone branch and write the cutover readiness assessment

## Context

SC8 turns the milestone into an owner decision: publish gsd-path/M001 to origin (explicitly in scope per INTENT; ship remains the only path into main), confirm CI on the pushed head within the documented policy (M207 batteries report-only, corpus job skipped and documented), and produce the written cutover readiness assessment — while cutover itself stays false (N2). E8 rules the CI edge: one rerun for a red run; persistently red means SC8 is unmet unless the failure is documented as advisory under the M207 policy. The assessment must carry the corpus honesty forward — green CI does not prove corpus scenarios ran (N1) — and record the corpus-delivery direction settled by SYNTHESIS (runner-only exposure, pinned snapshot shape, the strict tests' on-runner layout contract) without building any of it.

## Approach

- Push the bound branch with `git push origin gsd-path/M001` from the primary worktree after T007 and T008 have landed, so the published tip contains every M001 landing. If the dispatch context lacks push authorization, block with NEEDS-ORCHESTRATOR instead of improvising a workaround. Record the push and the CI run URLs in the task Log.
- Watch the pushed head's workflow run: green within policy meets SC8; a red run gets exactly one rerun (E8); a persistently red run blocks SC8 unless the failing job is one of the documented advisory surfaces and the assessment records it as such. Never add a suppression to make CI green (N3 rides along).
- Write docs/agent-stack/CUTOVER-READINESS-M001.md — a tracked repo document, so it survives milestone archiving — with: a per-SC readiness verdict for SC1 through SC10, each citing its recorded evidence (including every held-out edge E1, E3, E5, E8, E9 and the judgment prohibitions N4 and N7); the CI evidence table; the corpus honesty statement; the runner-only corpus-delivery direction with the pinned-snapshot shape and the on-runner layout contract recorded for a future milestone; and the explicit conclusion that cutover remains false.
- End the document with a fenced JSON block (schema law-nexus/cutover-readiness/v1) the test parses: cutover (boolean, false), ci_runs (array of objects with run_url, conclusion, reruns, final, advisory_documented), corpus_honesty (boolean, true).
- Write tests/test_m001_cutover_readiness.py: the document exists and parses; cutover is false (N2); every CI row has reruns of at most 1 (E8); every row whose final is not green carries advisory_documented true; corpus_honesty is true.

## Interface contract

- None

## Intent coverage

- SC8

## Acceptance criteria

1. gsd-path/M001 is published to origin and the task Log records the push with the CI run URLs; the head run is green within the documented policy — M207 batteries report-only, corpus job skipped and documented — with at most one rerun for any red run (E8), or a documented advisory record for a persistently red advisory surface; cutover remains false (N2).
2. docs/agent-stack/CUTOVER-READINESS-M001.md exists with the per-SC readiness verdicts and evidence pointers (held-out E1, E3, E5, E8, E9 and judgment N4, N7 included), the CI evidence table, the corpus honesty statement that green CI does not prove corpus scenarios ran, the runner-only corpus-delivery direction for a future milestone, and the cutover-false conclusion.
3. The fenced machine block parses with cutover false, corpus_honesty true, and every CI row at one rerun or fewer with non-green rows documented advisory — the exact E8 ruling.
4. tests/test_m001_cutover_readiness.py pins criterion 3 mechanically and fails if the assessment is absent, flips cutover, or records a second rerun.

## Verify

```bash
uv run --frozen pytest tests/test_m001_cutover_readiness.py -q
```

Heavy: no

## Log

- 2026-10-26 — build_T009 (coder): BLOCKED at the first Approach step, before any write to the declared files. `git push origin gsd-path/M001` from the primary worktree was rejected by the repository's own pre-push guard (.git/hooks/pre-push → .gsd-path/git_guard.py): "7ccc5262017b moves gsd-path/M001 off its ship commit; unshipped milestone work reaches a remote only as its ship commit (STATE shipped/done) through archive_milestone.py integrate". Guard source verified: refs/heads/gsd-path/M001 matches BOUND_BRANCH (^gsd-path/M\d{3,}$), so the ref may move to the remote only at its strict ship commit (ship_commit_at = STATE shipped/done + ship subject) — the build-phase push required by T009's Approach and AC1 is structurally impossible without bypassing the guard (vetoed). No refs/gsd-path/authorizations/* refs exist, the authorized-publication path explicitly excludes the bound branch, and this repo is the coordinator (no member marker). Secondary defect in the same step: repository-quality CI triggers only on push to main and pull_request events (.github/workflows/repository-quality.yml confirmed; GitHub API: 38 runs, all main-push or PR), and no PR from gsd-path/M001 exists — so even a successful push would produce no run on the pushed head; opening a PR needs credentials and is outside the declared files. Worktree kept; no declared path touched.
- NEEDS-ORCHESTRATOR: How should SC8's publication step be satisfied given the repository's own pre-push guard forbids moving gsd-path/M001 to origin before its ship commit (STATE shipped/done via archive_milestone.py integrate at the ship phase) and the CI workflow cannot fire on the branch (main-push/PR triggers only)? — readings: (a) publication + CI confirmation are ship-phase-gated: T009 writes the assessment now with publication/CI recorded as pending-ship and the orchestrator re-scopes AC1/SC8; (b) the owner records a sanctioned authorization and SC8 re-targets to a non-bound published ref (does not literally satisfy "gsd-path/M001 is published to origin"); (c) the orchestrator publishes through the sanctioned ship/integrate path out-of-band and returns the recorded push + CI evidence for T009 to cite.
- 2026-10-26 — created by planner
- 2026-10-26 — owner ruling (verbatim: «(a)»): publication+CI are ship-phase-gated — T009 writes the cutover readiness assessment now with publication and CI recorded as pending-ship (the bound branch publishes through ship integration; the CI acceptance surface is the integrated main per the documented M207 policy); AC1/SC8 re-scoped accordingly. Build entered build/blocked; intent corrections follow the build-recovery contract.
