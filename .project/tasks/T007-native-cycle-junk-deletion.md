---
id: T007
title: Delete the junk files through the full native cycle
wave: 3
deps: []
status: pending     # orchestrator-owned: pending | in-progress | done | failed | blocked
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null   # orchestrator-owned: gsd-path-task/<id> while parallel; null when serial
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
