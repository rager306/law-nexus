# Parent dispatch

1. Inspect available names (`/subagent` or discovery). Do not assume `architect`.
2. Load this skill. Child prompts come from `~/.gsd/agent/agents/<role>.md`.
   Paste the compact packet into `task` — the child does not inherit the parent chat.
3. Required packet fields: decision packet, deliverable + output format, acceptance, constraints, paths/evidence, **edit permission**, and for reviewers a **file or commit list**. Missing load-bearing field → child `BLOCKED`.
4. Start the task with:

```
NON-INTERACTIVE SUBAGENT
Do not ask questions or wait. If any material part of the task is unclear,
terminate with the structured BLOCKED result.
```

5. Independent ready tasks → parallel. Background → one `{agent, task}`. Do not pin a model id.
6. `planner` has `conflicts_with: plan-milestone, plan-slice, plan-task`. Do not dispatch planner inside those GSD units.
7. Instant 0-token / ~15–25 ms fail = rejected dispatch. Redispatch the unchanged contract through `planner` / `researcher` / `reviewer` / `scout` / `worker`. Do not retry an unknown name.
8. After review / research / scout / plan: `git status` and `git log`. Do not push or revert automatically. Do not trust the child self-report.
9. Do not fabricate a GSD Task Attempt from a generic subagent.
