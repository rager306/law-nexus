# Parent dispatch (Antigravity + Compound Engineering)

1. Choose the smallest subagent capability that fits (`research` for read-only recon; `self` when write tools, command execution, or structured CE review artifacts are needed).
2. Make every brief self-contained — a spawned subagent does not inherit parent conversation history.
3. Required brief fields: concrete goal, deliverable + output format, acceptance criteria, constraints (including D098 lifecycle / non-claim ceilings), relevant file paths/anchors, **explicit edit permission** (`read-only` or named writable paths), and for reviewers an explicit **file list or diff path**.
4. Open delegated briefs with:

```text
NON-INTERACTIVE SUBAGENT
Do not ask questions or wait. If any material part of the task is unclear,
terminate with the structured BLOCKED result.
```

5. Launch independent subagents in parallel in a single turn; do not poll in a loop — rely on reactive completion notifications.
6. Keep read-only reviewers and tree-mutating workers isolated (use `Workspace: "share"` or `"branch"` if a worker mutates files concurrently).
7. After any read-only review / research / plan subagent finishes, inspect `git status` and `git log` rather than trusting self-reports.
8. Never convert a subagent output into human authority, ADR promotion, or Review Case human disposition.
