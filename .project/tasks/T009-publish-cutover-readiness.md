---
id: T009
title: Write the cutover readiness assessment with publication and CI pending-ship
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

# T009 — Write the cutover readiness assessment with publication and CI pending-ship

## Context

SC8 (corrected 2026-10-26, owner ruling (a) in INTENT.md ## Corrections) produces the written cutover readiness assessment only: the repository's pre-push guard (.git/hooks/pre-push → .gsd-path/git_guard.py) is the enforcing contract — gsd-path/M001 reaches origin only as its ship commit through ship integration — and repository-quality CI triggers on main-push/pull_request only, with the CI acceptance surface being the integrated main per the documented M207 policy. This task therefore performs no push and no CI watch: publication and CI evidence are recorded as pending-ship and are produced at ship integration. The assessment cites the milestone's recorded per-criterion evidence (SC1–SC10, including held-out edges E1/E3/E5/E8/E9 and judgment prohibitions N4/N7), keeps the CI honesty (N1: M207 batteries report-only, the corpus job skipped and documented — green CI never proves corpus scenarios ran), records the settled runner-only corpus-delivery direction without building any of it, and concludes that cutover stays false (N2). E8's one-rerun ruling governs the future ship-phase run; the machine block pins it only in its pending-ship form.

## Approach

- Do not push and do not watch CI. `.git/hooks/pre-push` → `.gsd-path/git_guard.py` refuses any move of `gsd-path/M001` to origin before its strict ship commit (STATE shipped/done via `archive_milestone.py integrate`), and `.github/workflows/repository-quality.yml` triggers on push-to-main and pull_request only — no workaround, no authorization ref, no PR from this task. Publication and CI execute at ship integration; the assessment records both as pending-ship.
- Write docs/agent-stack/CUTOVER-READINESS-M001.md — a tracked repo document, so it survives milestone archiving — with: a per-SC readiness verdict for SC1 through SC10, each citing its recorded evidence (task Log entries, verify sidecars, wave-review verdicts, the GitNexus receipt, .project/M001-RESUME-PROOF.md); held-out edges E1, E3, E5, E8, E9 cited inside the verdicts they belong to; the judgment prohibitions N4 and N7 addressed explicitly (the marker-only roadmap diff verified in T002's landing; review independence per E6 evidenced in T007's record); the CI-policy honesty section per N1 — M207 batteries report-only (`continue-on-error`), the corpus-integration job skipped and documented as its own comment states, green CI never proves corpus scenarios ran — plus the pending-ship status of publication and CI; and the explicit conclusion that cutover remains false.
- Record the runner-only corpus-delivery direction settled by SYNTHESIS for a future milestone, without building any of it: a restricted self-hosted runner surface (explicit runner label, never `ubuntu-latest`; protected branches only; ephemeral secret-free runner), a single pinned zstd tarball of `consru_export/consru_export/exports/` (~0.30 GiB measured) with a recorded sha256 the consuming job verifies before strict tests run (workflow artifacts are never the delivery channel), and the on-runner layout contract: strict tests resolve `consru_export/consru_export/exports/` under the repo root (or `CONSULTANT_EXPORT_DIR`) and hard-fail under `LAW_NEXUS_REQUIRE_CORPUS=1`, so whichever channel is chosen must materialize exactly that path.
- End the document with exactly one fenced JSON block whose info string is law-nexus/cutover-readiness/v1, carrying: `cutover` (boolean, false); `ci_runs` (array; each entry records `status` "pending-ship", `final` null, `reruns` 0, `advisory_documented` true — E8's rerun budget is not consumed before ship — plus the surface the entry names, for example the integrated main per the M207 policy); `corpus_honesty` (boolean, true).
- Write tests/test_m001_cutover_readiness.py: the document exists; exactly one machine block parses; `cutover` is false (N2); every ci_runs entry records status "pending-ship" with `final` null, `reruns` 0, `advisory_documented` true; `corpus_honesty` is true; and the document cites every SC1–SC10 id plus E1, E3, E5, E8, E9, N4 and N7, so gutting the per-criterion content fails Verify.

## Interface contract

- None

## Intent coverage

- SC8

## Acceptance criteria

1. No publication step is performed by this task: it runs no push and no CI watch, and docs/agent-stack/CUTOVER-READINESS-M001.md records publication and CI as pending-ship — the pre-push guard is the enforcing contract, gsd-path/M001 publishes only through ship integration as its ship commit, and the CI acceptance surface is the integrated main per the documented M207 policy; cutover remains false (N2).
2. docs/agent-stack/CUTOVER-READINESS-M001.md exists with the per-SC readiness verdicts and evidence pointers for SC1–SC10 (held-out E1, E3, E5, E8, E9 and judgment N4, N7 included), the CI-policy honesty statement that green CI does not prove corpus scenarios ran (M207 batteries report-only, corpus-integration skipped and documented — N1), the runner-only corpus-delivery direction with the pinned-snapshot shape and the on-runner layout contract for a future milestone, and the cutover-false conclusion.
3. The fenced machine block (info string law-nexus/cutover-readiness/v1) parses with cutover false, corpus_honesty true, and every ci_runs entry recording status "pending-ship" with final null, reruns 0, and advisory_documented true — the pending-ship form of the E8 ruling.
4. tests/test_m001_cutover_readiness.py pins criteria 2 and 3 mechanically and fails if the assessment is absent or its citations are gutted, if cutover flips, or if any ci_runs entry records anything but pending-ship.

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
- 2026-10-26 — plan repair (planner, build-recovery base 7e994d3b): contract rewritten to the corrected SC8 (owner ruling (a), recorded above and in INTENT.md ## Corrections). Removed the push step and the CI watch entirely — the repository's pre-push guard is the enforcing contract; publication and CI evidence execute at ship integration and are recorded as pending-ship. The deliverable keeps the assessment shape (per-SC verdicts SC1–SC10 with E1/E3/E5/E8/E9 cited, N4/N7 addressed, N1 CI-policy honesty, runner-only corpus-delivery direction with pinned-snapshot shape and on-runner layout contract, cutover-false conclusion) and ends with the law-nexus/cutover-readiness/v1 block whose ci_runs entries record status "pending-ship" (final null, reruns 0, advisory_documented true); tests/test_m001_cutover_readiness.py pins that shape (cutover false; every row pending-ship; corpus_honesty true). files, wave, deps, Interface contract, Intent coverage, and the Verify command are unchanged. PLAN.md left byte-identical; no other task file touched.
