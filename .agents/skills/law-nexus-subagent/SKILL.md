---
name: law-nexus-subagent
description: "Parent dispatch and shared non-interactive contract for law-nexus subagents. Use when spawning, reviewing, or writing ~/.gsd/agent/agents role prompts or BLOCKED results."
---

<essential_principles>
## Split of authority

- **Parent always-on (AGENTS.md):** inspect names, packet fields, no `architect`, no model pin, verify git after review-only, no fabricated Attempt.
- **Child system prompt (`~/.gsd/agent/agents/*.md`):** self-contained contract + role method. This is what GSD actually loads.
- **This skill:** parent router + full contract + log-derived efficiency. Load before dispatch. Do not assume the child will open this file.

D125 behavioral requirements still apply. Live discovery path is `~/.gsd/agent/agents/`, not project `.pi/agents` or `.gsd/agents`.

## Shared contract (copy into every role prompt)

NON-INTERACTIVE. Complete the delegated task from the prompt and repository evidence. Do not ask, wait, or offer menus.

Must: treat scope / constraints / output format / edit permission as the full contract; inspect evidence before deciding the task is clear; finish the deliverable in the same response when unambiguous; `BLOCKED` instead of guessing among material interpretations.

BLOCKED keys (exact): `BLOCKED`, `Reason`, `Missing or ambiguous`, `Repository evidence checked`, `Work completed`, `Why no safe completion is possible`.
Incomplete evidence that still allows an honest deliverable is a bounded finding, not BLOCKED.

Must not: `ask_user_questions`; ask questions (including inside BLOCKED); invent answers / approvals / evidence / tool results; return only a future-work plan when the deliverable was requested; spawn nested subagents.

If edit permission is `no` or omitted on review / research / scout / plan: do not edit, stage, or commit.

GitNexus: `repo: "law-nexus"` always. Prefer query / context / impact over dumping files. Never alias `root`.
</essential_principles>

<quick_reference>
| Role | Use | Do not |
|---|---|---|
| `scout` | cheap recon, line-range map | cargo test, full-file dumps, edits |
| `reviewer` | findings on a named file/commit list | edits, repo-wide rediscovery, TS style nits |
| `worker` | one bounded implement/fix | nest subagents, expand scope, review-as-worker |
| `researcher` | external search + citations | treat search as product/legal proof |
| `tester` | ADR-0015 tests | 100% coverage, mix Consultant/Garant |
| `planner` | plans only | code; GSD `plan-*` units (conflicts_with) |
| `tester` / `security` / `doc-writer` / `debugger` / `git-ops` / `refactorer` | as named | invent missing roles |
| `architect` | **does not exist** | dispatch; use `planner` |
| `javascript-pro` / `typescript-pro` | only real JS/TS harness work | product Rust work |

Week of 2026-08-11 logs (law-nexus cwd): reviewer n=66 median in 101k max 389k; worker n=11 median 228k max 781k / out max 114k; scout n=22 median 138k (too fat for recon); architect 3× 0-token reject; first `security` batch 13 ms / 0 tokens then retry ok.
</quick_reference>

<routing>
| Intent | Follow |
|---|---|
| Parent is about to dispatch | `workflows/parent-dispatch.md` |
| Edit a role prompt | copy Shared contract into `~/.gsd/agent/agents/<role>.md`, then role method |
| Child returned 0 tokens in <30 ms | unknown role or confirm gate — inspect names, do not treat as a review |
| Review-only child finished | `git status` + `git log`; unexpected commits are unverified |
</routing>
