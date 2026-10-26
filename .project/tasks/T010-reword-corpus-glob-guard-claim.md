---
id: T010
title: Reword the corpus-glob-guard claim in law-source/consultant/README.md
wave: 2
deps: []            # task ids whose output or landed effect this task needs
status: pending     # orchestrator-owned: pending | in-progress | done | failed | blocked
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null   # orchestrator-owned: gsd-path-task/<id> while parallel; null when serial
files:
  - law-source/consultant/README.md
  - .project/research/DOCS-AUDIT.md
---

# T010 — Reword the corpus-glob-guard claim in law-source/consultant/README.md

## Context

The docs audit row #16 flags law-source/consultant/README.md:34-35: the rule-4 claim «Governor-проверка `law-source-corpus-glob-guard` это отмечает» names a governor probe that was never built — the audit found no `law-source-corpus-glob-guard` anywhere in src/, scripts/, tests/, or .github/ (verdict: aspirational; evidence: the existing `law-source-fixture-guard` checks only the README marker). That real check (`check_law_source_fixture_guard`, src/law_nexus_harness/governor.py:5108) covers only the fixture-vault README marker and the `.deprecated/` gitignore state; it does not detect globbing the fixture directory as corpus. The owner ruled fix-doc: «продолжаем - двигай проект» (2026-10-26), п.5 — «аудит #16 — поправить формулировку README»; nothing is implemented, the claim is reworded so it states only what the existing check covers. The audit's User rulings table is the alignment queue's ledger: when a ruling becomes a task its row records the task id in the Planned column and the row is never deleted.

## Approach

- Reword only the rule-4 claim at law-source/consultant/README.md:34-35, in Russian matching the doc's register: the reworded claim states that the existing governor check `law-source-fixture-guard` covers only the fixture-vault README marker (plus the `.deprecated/` gitignore state) and does not detect globbing this directory as corpus; treating the directory as a corpus source remains a review-time defect under rule 4 itself. The name `law-source-corpus-glob-guard` disappears entirely.
- Do not touch the marker substrings the existing check reads in the same README (`НЕ КОРПУС`, `consru_export`, `43 785`) — removing or rewording them would flip `law-source-fixture-guard` to README-marker-incomplete. No other line of the README changes.
- In .project/research/DOCS-AUDIT.md set the User rulings queue row 16 Planned cell from `no` to `T010`; touch nothing else in the audit (the Remediation queue row and its evidence stay as recorded history; the ruling table is append-only by its own comment).
- The landing diff covers exactly the two declared files; no code, no new probe, no test harness changes.

## Interface contract

- None

## Intent coverage

- None

## Acceptance criteria

1. law-source/consultant/README.md no longer contains the string `law-source-corpus-glob-guard`; the rule-4 claim names only `law-source-fixture-guard` and states that this check covers the README fixture-vault marker, not corpus globbing.
2. The marker substrings `НЕ КОРПУС`, `consru_export`, and `43 785` remain in the README, so `check_law_source_fixture_guard`'s marker test still passes; no other README line changed.
3. .project/research/DOCS-AUDIT.md User rulings row 16 shows Planned `T010`; the rest of the audit file is unchanged.
4. The landing diff touches exactly law-source/consultant/README.md and .project/research/DOCS-AUDIT.md.
5. The Verify command passes.

## Verify

```bash
! grep -q 'law-source-corpus-glob-guard' law-source/consultant/README.md && grep -q 'law-source-fixture-guard' law-source/consultant/README.md && grep -q 'НЕ КОРПУС' law-source/consultant/README.md && grep -qE '^\| 16 \|.*\| T010 \|' .project/research/DOCS-AUDIT.md
```
<!-- Re-runs the audit's row-#16 claim check for that doc: the never-built probe name must be gone, the real guard named, the fixture-guard marker intact, and the queue row drained. -->

Heavy: no

## Log

- 2026-10-26 — created by planner
