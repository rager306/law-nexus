---
name: falkordb-ops-debug
description: Debug and operate FalkorDB runtime behavior. Use when the user reports slow queries, errors, memory issues, connection/Bolt/WebSocket problems, GRAPH.SLOWLOG, GRAPH.INFO, GRAPH.MEMORY, GRAPH.CONFIG, ACL, EXPLAIN, or PROFILE.
---

<essential_principles>
## falkordb-ops-debug Operating Rules

### 1. Reproduce the exact graph, query, runtime mode, data shape, and version before fixing.
### 2. Use one-change verification loops.
### 3. Keep operational advice version-aware because 4.18.x includes runtime hardening fixes.
</essential_principles>

<quick_reference>
- Primary workflow → `workflows/main.md`
- Domain reference → `references/main.md`
- Eval rubric → `evals/evals.json`
- Cross-cutting proof skill → `.agents/skills/falkordb-capability-evidence/SKILL.md`
</quick_reference>

<routing>
Use this focused skill for: GRAPH.EXPLAIN, PROFILE, INFO, MEMORY, SLOWLOG, CONFIG, ACL, connection/auth, Bolt/WebSocket, Docker/resource failures, and query fan-out.

If a claim is capability-sensitive, load `falkordb-capability-evidence` or apply its evidence classes before recommending implementation.
</routing>

<reference_index>
- `references/main.md` — scope, gotchas, evidence boundaries, and implementation notes.
</reference_index>

<workflows_index>
- `workflows/main.md` — Debug FalkorDB Runtime or Performance.
</workflows_index>

<success_criteria>
A good answer using this skill:
- Names the FalkorDB evidence level for important claims.
- Avoids Neo4j-only or RedisGraph-legacy feature drift.
- Gives concrete verification steps.
- Stays within this skill's scope and routes other work to the right FalkorDB skill.
</success_criteria>
