---
id: T006
title: Re-index GitNexus and regenerate the AGENTS.md tool block
wave: 2
deps: [T004, T005]
status: pending     # orchestrator-owned: pending | in-progress | done | failed | blocked
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null   # orchestrator-owned: gsd-path-task/<id> while parallel; null when serial
files:
  - AGENTS.md
  - prd/project-state/data/gitnexus-index.json
  - tests/test_gitnexus_block_receipt.py
---

# T006 — Re-index GitNexus and regenerate the AGENTS.md tool block

## Context

The GitNexus tool block in AGENTS.md claims a live index (23577 symbols, 50919 relationships) that no longer exists anywhere: the whole .gitnexus tree is excluded from Git and absent from the primary checkout and every sidecar, and preflight warns that GitNexus metadata is missing (audit row 9). SC5 re-indexes and makes the tracked tool block match the live index again. E5 rules the failure path: if analyze fails, keep the previous AGENTS.md block, report the error, and never hand-edit the block. N6 forbids presenting a stale or hand-edited block as live. The index is machine-local, so this task runs in a serial dispatch round on the bound branch in the primary worktree — the deps on T004 and T005 force exactly that scheduling.

## Approach

- After T004 and T005 have landed and a clean base is recorded, bootstrap the index if absent (the runner bootstrap is documented in the GitNexus section of AGENTS.md; npm 11 npx is known to crash there, so bunx is the documented fallback), then run the tracked command `node .gitnexus/run.cjs analyze --force --name law-nexus` in the primary worktree on the bound branch. The tool regenerates the AGENTS.md block between its gitnexus markers itself; the coder never edits that block by hand (E5, N6).
- Write prd/project-state/data/gitnexus-index.json — the tracked, sidecar-checkable receipt (schema law-nexus/gitnexus-index-receipt/v1): the exact command, the indexed head as a full 40-hex SHA read from the index metadata the tool wrote, the symbol, relationship, and execution-flow counts, the generation timestamp, and the sha256 of the exact AGENTS.md block text between the gitnexus markers.
- If analyze fails: keep the previous AGENTS.md block untouched, record the error verbatim in the task Log, and block — never hand-edit the block into agreement (E5). If the tool version does not regenerate the block, block with NEEDS-ORCHESTRATOR rather than editing it by hand.
- Record in the task Log the preflight line for gitnexus-index-freshness at the analyze HEAD (clean tree, index matches — no metadata-missing warning). After landing, the index sits one commit behind by construction; that drift is expected machine-local state refreshed by the documented command, and the receipt pins the analyzed revision.
- Write tests/test_gitnexus_block_receipt.py: the receipt exists with its schema and a full 40-hex indexed head; the sha256 of the AGENTS.md block between the gitnexus markers equals the receipt's recorded hash — a hand-edited block breaks exactly this; the receipt's counts appear in the block text; the block still names the repo law-nexus. E5 is pinned by construction: a failed analyze leaves the previous block and the previous receipt untouched and consistent.

## Interface contract

- None

## Intent coverage

- SC5

## Acceptance criteria

1. The index is rebuilt with the tracked command in the primary worktree on gsd-path/M001, and prd/project-state/data/gitnexus-index.json records the command, a full 40-hex indexed head, the counts, the timestamp, and the sha256 of the AGENTS.md block between the gitnexus markers.
2. The AGENTS.md tool block between the gitnexus markers matches the receipt — equal hash, counts present, repo name law-nexus — and was produced by the tool, not by hand (E5, N6: on analyze failure the previous block and receipt stay untouched and consistent, and the error is reported, never hand-patched away).
3. The task Log records the preflight gitnexus-index-freshness result at the analyze HEAD showing a match with no metadata-missing warning, and states the expected one-commit drift after landing.
4. tests/test_gitnexus_block_receipt.py pins criteria 1 and 2 mechanically and fails if the receipt is absent or the block changed without the tool.

## Verify

```bash
uv run --frozen pytest tests/test_gitnexus_block_receipt.py -q
```

Heavy: no

## Log

- 2026-10-26 — created by planner
