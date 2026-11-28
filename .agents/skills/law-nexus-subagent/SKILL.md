---
name: law-nexus-subagent
description: "Parent dispatch and shared non-interactive contract for law-nexus subagents under Antigravity (AGY) and Compound Engineering. Use when spawning subagents via invoke_subagent, writing role briefs, or handling BLOCKED results."
---

<essential_principles>
## Split of authority (Antigravity + Compound Engineering)

- **Parent coordinator (`AGENTS.md` + active CE skill):** owns scope, edit permissions, GitNexus impact/change checks, verification, and post-subagent `git status` inspection.
- **Child subagent (`invoke_subagent` with `self` or `research`):** starts fresh without parent chat history; the dispatch prompt must be self-contained (scope, deliverable, output format, edit permission, evidence paths).
- **This skill:** shared non-interactive delegation contract and anti-hallucination guardrails for `law-nexus`.

## Shared contract (include in every delegated brief)

NON-INTERACTIVE. Complete the delegated task from the prompt and repository evidence. Do not ask, wait, or offer menus.

Must:
- Treat scope, constraints, output format, and edit permission as the full contract.
- Inspect real repository evidence before deciding the task is clear.
- Finish the deliverable in the same response when unambiguous.
- Return `BLOCKED` instead of guessing among material architectural or legal-domain interpretations.

`BLOCKED` keys (exact): `BLOCKED`, `Reason`, `Missing or ambiguous`, `Repository evidence checked`, `Work completed`, `Why no safe completion is possible`.
Incomplete evidence that still allows an honest bounded finding is a finding, not `BLOCKED`.

Must not:
- Ask blocking user questions (including inside `BLOCKED`).
- Invent answers, human approvals, evidence, or tool results.
- Return only a future-work plan when a concrete deliverable was requested.
- Spawn nested subagents unless explicitly authorized by the parent skill.

If edit permission is `no` or omitted on review / research / scout / plan work: do not edit, stage, or commit.

GitNexus: `repo: "law-nexus"` always. Prefer graph `query` / `context` / `impact` over dumping full files; never alias `root`.
</essential_principles>

<quick_reference>
| Subagent type | Use for | Do not |
|---|---|---|
| `research` | Read-only codebase/docs recon, targeted line-range maps | Edit files, run builds/tests, dump whole files |
| `self` (read-only brief) | CE code/doc review personas, validators, targeted read-only verification | Mutate project files, commit, or push |
| `self` (write-authorized brief) | One bounded implementation/fix slice with explicit file scope and tests | Expand scope, weaken tests, or push without parent check |
| `self` (isolated workspace `share`/`branch`) | Parallel non-overlapping implementation or mutation checks | Share a mutating checkout with concurrent read-only reviewers |
</quick_reference>

<routing>
| Intent | Follow |
|---|---|
| Parent is about to dispatch a subagent | `workflows/parent-dispatch.md` |
| Multi-reviewer code or doc review | Use Compound Engineering `ce-code-review` / `ce-doc-review` |
| Review-only child finished | Verify `git status` + `git log`; unexpected edits are unverified |
</routing>
