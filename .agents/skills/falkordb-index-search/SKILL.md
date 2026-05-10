---
name: falkordb-index-search
description: Design and verify FalkorDB range, full-text, and vector indexes. Use when the user asks about FalkorDB indexing, full-text search, vector search, hybrid retrieval, index-backed query plans, or whether a search/index capability is supported.
---

<essential_principles>
## falkordb-index-search Operating Rules

### 1. Separate docs-backed support from runtime-confirmed behavior.
### 2. Every index must name the query it accelerates and the proof command.
### 3. Vector/full-text advice needs version and smoke-test evidence before production claims.
</essential_principles>

<quick_reference>
- Primary workflow → `workflows/main.md`
- Domain reference → `references/main.md`
- Eval rubric → `evals/evals.json`
- Cross-cutting proof skill → `.agents/skills/falkordb-capability-evidence/SKILL.md`
</quick_reference>

<routing>
Use this focused skill for: Range indexes, full-text indexes, vector indexes, query patterns, proof layers, hybrid retrieval boundaries, and index verification.

If a claim is capability-sensitive, load `falkordb-capability-evidence` or apply its evidence classes before recommending implementation.
</routing>

<reference_index>
- `references/main.md` — scope, gotchas, evidence boundaries, and implementation notes.
</reference_index>

<workflows_index>
- `workflows/main.md` — Design or Verify FalkorDB Index/Search Behavior.
</workflows_index>

<success_criteria>
A good answer using this skill:
- Names the FalkorDB evidence level for important claims.
- Avoids Neo4j-only or RedisGraph-legacy feature drift.
- Gives concrete verification steps.
- Stays within this skill's scope and routes other work to the right FalkorDB skill.
</success_criteria>
