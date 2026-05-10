---
name: falkordb-python
description: Implement and review Python applications using falkordb-py. Use when the user asks about sync or async FalkorDB Python connections, from_url, close/aclose lifecycle, parameters, Unix sockets, UDF API, or safe app integration.
---

<essential_principles>
## falkordb-python Operating Rules

### 1. Use current falkordb-py release behavior, not Neo4j driver APIs.
### 2. Never log credentials; take connection settings from environment or secret stores.
### 3. Prefer parameters and explicit lifecycle close/aclose handling.
</essential_principles>

<quick_reference>
- Primary workflow → `workflows/main.md`
- Domain reference → `references/main.md`
- Eval rubric → `evals/evals.json`
- Cross-cutting proof skill → `.agents/skills/falkordb-capability-evidence/SKILL.md`
</quick_reference>

<routing>
Use this focused skill for: Python sync/async connection setup, from_url behavior, close/aclose, parameter handling, Unix socket use, result handling, UDF API, and observability.

If a claim is capability-sensitive, load `falkordb-capability-evidence` or apply its evidence classes before recommending implementation.
</routing>

<reference_index>
- `references/main.md` — scope, gotchas, evidence boundaries, and implementation notes.
</reference_index>

<workflows_index>
- `workflows/main.md` — Use falkordb-py Safely.
</workflows_index>

<success_criteria>
A good answer using this skill:
- Names the FalkorDB evidence level for important claims.
- Avoids Neo4j-only or RedisGraph-legacy feature drift.
- Gives concrete verification steps.
- Stays within this skill's scope and routes other work to the right FalkorDB skill.
</success_criteria>
