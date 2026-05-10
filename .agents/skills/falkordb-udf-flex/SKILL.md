---
name: falkordb-udf-flex
description: Use and review FalkorDB UDF and FLEX functions. Use when the user asks about FalkorDB UDFs, FLEX bitwise/collection/date/JSON/map/similarity/text functions, QuickJS limits, graph object UDF support, graph.getNodeById, or Python UDF API usage.
---

<essential_principles>
## falkordb-udf-flex Operating Rules

### 1. UDF work is capability- and security-sensitive; classify evidence before use.
### 2. QuickJS stack/heap/resource limits and sandbox assumptions must be explicit.
### 3. Prefer built-in FLEX functions before custom code when they satisfy the task.
</essential_principles>

<quick_reference>
- Primary workflow → `workflows/main.md`
- Domain reference → `references/main.md`
- Eval rubric → `evals/evals.json`
- Cross-cutting proof skill → `.agents/skills/falkordb-capability-evidence/SKILL.md`
</quick_reference>

<routing>
Use this focused skill for: FLEX function reference, text/json/map/date/collection/similarity functions, custom UDF boundaries, QuickJS resource limits, graph object support in UDFs, graph.getNodeById, and Python client UDF API notes.

If a claim is capability-sensitive, load `falkordb-capability-evidence` or apply its evidence classes before recommending implementation.
</routing>

<reference_index>
- `references/main.md` — scope, gotchas, May 2026 evidence boundaries, and implementation notes.
</reference_index>

<workflows_index>
- `workflows/main.md` — Use or Review FalkorDB UDF/FLEX Functions.
</workflows_index>

<success_criteria>
A good answer using this skill:
- Names the FalkorDB evidence level for important claims.
- Avoids Neo4j-only or product-adjacent feature drift.
- Gives concrete verification steps.
- Separates documented support from runtime or quality proof.
</success_criteria>
