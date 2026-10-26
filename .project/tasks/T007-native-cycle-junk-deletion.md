---
id: T007
title: Delete the junk files through the full native cycle
wave: 3
deps: []
status: in-progress
agent: build_T007
base: 7791ca6c125005a2d03c1a46b8ffdb8eb9814028
worktree: /root/law-nexus
task_branch: null
files:
  - a.txt
  - b.txt
  - c.txt
  - .project/HANDOFF-M001-resume.md
  - .project/M001-RESUME-PROOF.md
---

# T007 — Delete the junk files through the full native cycle

## Context

SC10 is the deliberately trivial carrier SYNTHESIS names for the walking skeleton: deleting the three tracked one-byte junk files a.txt, b.txt, c.txt (zero references in scripts, CI, or tests per the codebase evidence; reversible through git history, so E10 is dismissed). Their deletion has no product value — the value is the full native cycle around it (SC6): dispatch, worker, native validators, and an independent review, the first practical proof that the merged bootstrap actually delivers a task. The evidence must be recorded under .project/ (task log, verify sidecar, review verdict). The session that runs this cycle is the session that closes, so this task also writes the handoff that the fresh T008 session resumes from (SC7).

## Approach

- The deliverable is the recorded cycle, not the diff. The task Log must capture the dispatch receipt, the worker result, the authoritative Verify rerun in the isolated verify sidecar — a different evidence path than the worker's own report, which satisfies E6's independence without needing a second model — the native validator outputs (the governor and preflight recorded on the bound branch, the Verify ledger line), and the wave review verdict with its evidence path or model family named. A same-family re-run or the worker accepting its own task does not count (N7).
- Delete exactly the three files; touch nothing else in the product tree. Deletion is reversible through git history (E10, dismissed in INTENT).
- Write .project/HANDOFF-M001-resume.md exactly per the Interface contract below so a fresh session can resume from disk alone. The handoff is data for T008, not a status report: exact paths, exact commands, no conversation references (N8: the proof must be recorded on-disk verification output, not chat history).

## Interface contract

- Handoff file: `.project/HANDOFF-M001-resume.md` — written by T007, consumed by T008; UTF-8 Markdown with exactly these sections, in order: `Session context` (bound branch `gsd-path/M001`, milestone `001-native-workflow-acceptance`, handoff commit SHA), `State on disk` (STATE.md is the single journaled source; nothing is carried in conversation history), `Resume verification commands` (exactly: `python3 scripts/ai/path-run.py status`, `uv run --frozen python -m law_nexus_harness.governor`, `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`, `test -z "$(git ls-files a.txt b.txt c.txt)"`), and `Recording path` (`.project/M001-RESUME-PROOF.md`).
- Proof file: `.project/M001-RESUME-PROOF.md` — created by T008 only; T007 names the path in the handoff and never writes the file.

## Intent coverage

- SC6
- SC10

## Acceptance criteria

1. a.txt, b.txt, and c.txt are deleted from the index and the worktree; no other product path changes (SC10).
2. The task Log records the complete native-cycle evidence for this task: dispatch, worker, the isolated Verify rerun as an independent evidence path (E6), native validators, and the independent review verdict with its evidence path or model family named (N7 — self-acceptance does not count).
3. .project/HANDOFF-M001-resume.md exists with the exact sections of the Interface contract, enabling disk-only resume.
4. The Verify command fails if any of the three files is still tracked or present.

## Verify

```bash
test -z "$(git ls-files a.txt b.txt c.txt)" && test ! -e a.txt && test ! -e b.txt && test ! -e c.txt
```

Heavy: no

## Log

- 2026-10-26 — created by planner
- 2026-10-26 — build_T007 (coder, worker session 01a177f4-38f0-7654-b320-293a746d9f24, serial round, primary worktree /root/law-nexus, base 7791ca6c125005a2d03c1a46b8ffdb8eb9814028): deleted `a.txt`, `b.txt`, `c.txt` via `git rm` — the removal is staged by design, because acceptance criterion 1 requires deletion from the index and the task Verify checks `git ls-files`; the dispatch instruction names `git rm` explicitly, so the generic coder no-staging rule yields to it. No other product path touched. Native-cycle evidence recorded around this task (SC6): dispatch receipt `build_T007` (`.project/research/dispatch-record-build-T007-2026-10-26.json`, role coder, scope 001-native-workflow-acceptance); worker = this session; the orchestrator's authoritative Verify rerun runs in the isolated wave-3 task-verify sidecar — a different evidence path from this worker report (E6); native validators = governor + preflight recorded on bound branch `gsd-path/M001`, Verify ledger line kept by the orchestrator; independent review = wave-3 independent reviewer with its evidence path or model family named in the wave review — this worker does not self-accept (N7). Wrote `.project/HANDOFF-M001-resume.md` per the Interface contract: sections `Session context` (branch `gsd-path/M001`, milestone `001-native-workflow-acceptance`, handoff commit SHA `7791ca6c125005a2d03c1a46b8ffdb8eb9814028` = the commit this task ran on), `State on disk`, `Resume verification commands` (the four exact commands), `Recording path` (`.project/M001-RESUME-PROOF.md`, not written by this task). Verify: `test -z "$(git ls-files a.txt b.txt c.txt)" && test ! -e a.txt && test ! -e b.txt && test ! -e c.txt` → pass, exit 0. RESULT: T007 ready
- 2026-10-26 — orchestrator Verify (sidecar gsd-path-verify/task-t007-verify): pass, exit 0
- 2026-10-26 — orchestrator Verify (sidecar gsd-path-verify/task-t007-verify): pass, exit 0
- 2026-10-26 — orchestrator Verify (sidecar gsd-path-verify/task-t007-verify): pass, exit 0
- 2026-10-26 — orchestrator Verify (sidecar gsd-path-verify/task-t007-verify): pass, exit 0
