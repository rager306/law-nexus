---
id: T006
title: Re-index GitNexus and regenerate the AGENTS.md tool block
wave: 2
deps: [T004, T005]
status: done
agent: build_T006
base: 2a0ead24e812aba07b6e0e72897ae54eed35106e
worktree: null
task_branch: null
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
- 2026-10-26 — build_T006: re-indexed GitNexus at base HEAD 2a0ead24e812aba07b6e0e72897ae54eed35106e on the bound branch gsd-path/M001 (serial dispatch, primary worktree; deps T004/T005 present in that base). `.gitnexus/` was absent from the checkout (audit row 9), so first bootstrapped the documented fallback `bunx gitnexus@latest analyze` (bunx 1.4.3, gitnexus CLI 1.6.12, node v24.22.0): created `.gitnexus/run.cjs`, indexed successfully in 188.0s (43,047 nodes | 102,234 edges | 1512 clusters | 584 flows), and the tool itself rewrote the AGENTS.md block between the gitnexus markers (block sha256 082afed5d5b41c021fe7c0424c39f307080fe353f497f655089988a65afe5605 → 896a9503fdd8b45e8f67f465132cb2b22bd632ddd5d676622c4d5bfa01a328f). Then ran the tracked command `node .gitnexus/run.cjs analyze --force --name law-nexus` in the primary worktree: "Repository indexed successfully (123.0s)", 43,047 nodes | 102,234 edges | 1512 clusters | 584 flows, exit 0. The block was produced only by the tool; the coder never edited the block region (E5, N6); `git diff AGENTS.md` touches only the gitnexus block. New prd/project-state/data/gitnexus-index.json (schema law-nexus/gitnexus-index-receipt/v1), generated deterministically from the tool-written `.gitnexus/meta.json`: the exact tracked command, indexed_head 2a0ead24e812aba07b6e0e72897ae54eed35106e (full 40-hex, equal to the analyze HEAD), counts {symbols 43047, relationships 102234, execution_flows 584} from meta stats nodes/edges/processes, generated_at 2026-10-26T10:53:09.705Z (the tool's indexedAt), agents_block_sha256 896a9503fdd8b45e8f67f465132cb2b22bd632ddd5d676622c4d5bfa01a328f (sha256 of the block text between the gitnexus markers, markers included). New tests/test_gitnexus_block_receipt.py pins the receipt schema/command/40-hex head, the block-hash equality (a hand-edited block breaks exactly this), the counts-in-block, and the repo name law-nexus; `uv run --frozen ruff format` / `ruff check` clean on the new file.
- 2026-10-26 — preflight gitnexus-index-freshness record (AC3). Before: `.gitnexus/` absent entirely — the audit-row-9 metadata-missing condition, verified directly. After the tracked run, at the analyze HEAD: the stock preflight entry is `gitnexus-index-freshness | warn | observed: "GitNexus index may be stale: working tree has uncommitted changes."` — the check returns early on a non-empty `git status --porcelain` (preflight.py `_gitnexus_freshness_check`), and the tree carries exactly this task's in-flight edits (task-file dispatch edit, AGENTS.md block, receipt, test), which the coder may not commit. The check's own decision inputs at the analyze HEAD, verified on the identical fields it compares: `.gitnexus/meta.json` present and parses, `lastCommit` == `git rev-parse HEAD` == 2a0ead24e812aba07b6e0e72897ae54eed35106e → commit match, no metadata-missing warning, no commit-mismatch warning. After landing, HEAD sits one commit past `lastCommit` by construction: that one-commit drift warning is expected machine-local state, refreshed by the documented re-index command; the receipt pins the analyzed revision.
- 2026-10-26 — Verify: `uv run --frozen pytest tests/test_gitnexus_block_receipt.py -q` → `4 passed in 0.27s`, exit 0, run at HEAD 2a0ead24e812aba07b6e0e72897ae54eed35106e on gsd-path/M001.
- 2026-10-26 — orchestrator Verify (sidecar gsd-path-verify/task-t006-verify): pass, exit 0; output tail:
  ```
  ....                                                                     [100%]
  4 passed in 1.20s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t006-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t006-verify
  Installed 32 packages in 350ms
  ```
