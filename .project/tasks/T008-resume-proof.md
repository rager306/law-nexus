---
id: T008
title: Prove session resume from disk alone
wave: 3
deps: [T007]
status: done
agent: build_T008
base: 334caa661395e73035dc23dbee294de725e4e59a
worktree: null
task_branch: null
files:
  - .project/M001-RESUME-PROOF.md
---

# T008 — Prove session resume from disk alone

## Context

SC7 completes the acceptance proof: the session that ran the cycle (T007) closes with a handoff, and a fresh session must resume from disk alone. The proof is the new session's recorded on-disk verification output — re-reading chat history does not count (N8), and STATE.md stays the single journaled source with resume as read-only validation, so a repeated resume is harmless (E7). The worker dispatched for this task IS the fresh session by construction: its brief carries the handoff path and the repository, and no prior conversation.

## Approach

- Work exactly from .project/HANDOFF-M001-resume.md and the repository on disk. If the handoff is missing or ambiguous, block instead of reconstructing state from memory or chat.
- Run the handoff's resume verification commands in order and capture the real outputs: the status command (expect branch gsd-path/M001 and milestone 001-native-workflow-acceptance), the governor on the bound branch (expect exit 0 with 0 errors), the marker pytest, and the junk-absence check.
- Write .project/M001-RESUME-PROOF.md recording, per command: the command line, the exit status, and the material output, plus a dated statement that the recording session resumed from the handoff with no chat history (SC7). The file is data for final review — fixed sections, real outputs, no narrative padding.

## Interface contract

- Handoff file: `.project/HANDOFF-M001-resume.md` — written by T007, consumed by T008; UTF-8 Markdown with exactly these sections, in order: `Session context` (bound branch `gsd-path/M001`, milestone `001-native-workflow-acceptance`, handoff commit SHA), `State on disk` (STATE.md is the single journaled source; nothing is carried in conversation history), `Resume verification commands` (exactly: `python3 scripts/ai/path-run.py status`, `uv run --frozen python -m law_nexus_harness.governor`, `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`, `test -z "$(git ls-files a.txt b.txt c.txt)"`), and `Recording path` (`.project/M001-RESUME-PROOF.md`).
- Proof file: `.project/M001-RESUME-PROOF.md` — created by T008 only; T007 names the path in the handoff and never writes the file.

## Intent coverage

- SC7

## Acceptance criteria

1. The proof file exists with one recorded block per resume command, each carrying the command line, its exit status, and its real output — including the governor run with 0 errors and the status output naming branch gsd-path/M001 and milestone 001-native-workflow-acceptance (SC7).
2. The record states that the session resumed from .project/HANDOFF-M001-resume.md with no chat history, so the proof is disk-only (N8); STATE.md remains the single journaled source (E7).
3. The Verify command fails when the file is absent, empty, or missing the status and governor records.

## Verify

```bash
test -s .project/M001-RESUME-PROOF.md && grep -q "path-run.py status" .project/M001-RESUME-PROOF.md && grep -q "law_nexus_harness.governor" .project/M001-RESUME-PROOF.md
```

Heavy: no

## Log

- 2026-10-26 — created by planner
- 2026-10-26 — build_T008 (fresh session, no chat history): resumed from .project/HANDOFF-M001-resume.md (commit 7791ca6c) on branch gsd-path/M001 @ be2ee713. Ran the 4 resume verification commands in order: `python3 scripts/ai/path-run.py status` exit 0 (branch gsd-path/M001, milestone 001-native-workflow-acceptance); `uv run --frozen python -m law_nexus_harness.governor` exit 0, error_count=0, 75 checks pass; `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q` exit 0 (1 passed, 5 skipped); `test -z "$(git ls-files a.txt b.txt c.txt)"` exit 0 (empty). Recorded .project/M001-RESUME-PROOF.md; task Verify command passes (exit 0).
- 2026-10-26 — orchestrator Verify (sidecar gsd-path-verify/task-t008-verify): pass, exit 0
- 2026-10-26 — orchestrator Verify (sidecar gsd-path-verify/task-t008-verify): pass, exit 0
