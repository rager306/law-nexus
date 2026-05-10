---
name: falkordb-cypher
description: Write, review, translate, and debug FalkorDB Cypher queries. Use when the user asks for FalkorDB Cypher syntax, query plans, GRAPH.QUERY, GRAPH.RO_QUERY, GRAPH.EXPLAIN, GRAPH.PROFILE, LOAD CSV, procedures, functions, or Neo4j Cypher translation safety.
---

<essential_principles>
## falkordb-cypher Operating Rules

### 1. Use FalkorDB Cypher evidence first: docs, Cypher coverage, known limitations, and runtime smoke tests.
### 2. Do not copy Neo4j APOC, GDS, Aura, GenAI, driver, or Cypher 25 assumptions unless FalkorDB evidence confirms equivalent behavior.
### 3. For writes or migrations, include fixture data, rollback/cleanup, and verification queries.
</essential_principles>

<quick_reference>
- Primary workflow → `workflows/main.md`
- Domain reference → `references/main.md`
- Eval rubric → `evals/evals.json`
- Cross-cutting proof skill → `.agents/skills/falkordb-capability-evidence/SKILL.md`
</quick_reference>

<routing>
Use this focused skill for: Core Cypher, GRAPH.QUERY/RO_QUERY, EXPLAIN/PROFILE, parameters, LOAD CSV, procedures/functions, and Neo4j-to-FalkorDB translation review.

If a claim is capability-sensitive, load `falkordb-capability-evidence` or apply its evidence classes before recommending implementation.
</routing>

<reference_index>
- `references/main.md` — scope, gotchas, evidence boundaries, and implementation notes.
</reference_index>

<workflows_index>
- `workflows/main.md` — Write or Review FalkorDB Cypher.
</workflows_index>

<success_criteria>
A good answer using this skill:
- Names the FalkorDB evidence level for important claims.
- Avoids Neo4j-only or RedisGraph-legacy feature drift.
- Gives concrete verification steps.
- Stays within this skill's scope and routes other work to the right FalkorDB skill.
</success_criteria>
