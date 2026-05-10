---
name: falkordb-modeling
description: Design and review FalkorDB graph data models. Use when the user needs labels, relationships, properties, direction, cardinality, constraints, indexes, relational-to-graph migration, or query-driven schema review for FalkorDB.
---

<essential_principles>
## falkordb-modeling Operating Rules

### 1. Model from access patterns, not nouns alone.
### 2. Every relationship direction and cardinality must be justified by queries.
### 3. Indexes and constraints belong to the query patterns they support.
</essential_principles>

<quick_reference>
- Primary workflow → `workflows/main.md`
- Domain reference → `references/main.md`
- Eval rubric → `evals/evals.json`
- Cross-cutting proof skill → `.agents/skills/falkordb-capability-evidence/SKILL.md`
</quick_reference>

<routing>
Use this focused skill for: Labels, relationship types, property placement, direction/cardinality, constraints, indexes, migration from relational/document models, and query coverage.

If a claim is capability-sensitive, load `falkordb-capability-evidence` or apply its evidence classes before recommending implementation.
</routing>

<reference_index>
- `references/main.md` — scope, gotchas, evidence boundaries, and implementation notes.
</reference_index>

<workflows_index>
- `workflows/main.md` — Design or Review a FalkorDB Graph Model.
</workflows_index>

<success_criteria>
A good answer using this skill:
- Names the FalkorDB evidence level for important claims.
- Avoids Neo4j-only or RedisGraph-legacy feature drift.
- Gives concrete verification steps.
- Stays within this skill's scope and routes other work to the right FalkorDB skill.
</success_criteria>
