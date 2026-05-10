---
name: falkordb-browser-rest
description: Use and debug FalkorDB Browser and REST API surfaces. Use when the user asks about FalkorDB Browser 2.x, REST API auth tokens, graph endpoints, session or connection handling, users/permissions, query history, chat panel, or browser-driven graph management.
---

<essential_principles>
## falkordb-browser-rest Operating Rules

### 1. Treat Browser/REST as an application/API surface distinct from core database commands.
### 2. Never expose bearer tokens, credentials, or uploaded files in logs.
### 3. Browser 2.x release notes include security/session/connection fixes; keep advice version-aware.
</essential_principles>

<quick_reference>
- Primary workflow → `workflows/main.md`
- Domain reference → `references/main.md`
- Eval rubric → `evals/evals.json`
- Cross-cutting proof skill → `.agents/skills/falkordb-capability-evidence/SKILL.md`
</quick_reference>

<routing>
Use this focused skill for: Browser UI, REST auth tokens, graph endpoints, graph node/property operations, config endpoints, sessions/connections, users/permissions, query history, chat panel, and Browser 2.x release caveats.

If a claim is capability-sensitive, load `falkordb-capability-evidence` or apply its evidence classes before recommending implementation.
</routing>

<reference_index>
- `references/main.md` — scope, gotchas, May 2026 evidence boundaries, and implementation notes.
</reference_index>

<workflows_index>
- `workflows/main.md` — Use or Debug FalkorDB Browser/REST.
</workflows_index>

<success_criteria>
A good answer using this skill:
- Names the FalkorDB evidence level for important claims.
- Avoids Neo4j-only or product-adjacent feature drift.
- Gives concrete verification steps.
- Separates documented support from runtime or quality proof.
</success_criteria>
