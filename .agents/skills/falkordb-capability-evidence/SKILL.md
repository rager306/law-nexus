---
name: falkordb-capability-evidence
description: Classify and verify FalkorDB capability claims. Use when the user asks whether FalkorDB supports a feature, when translating Neo4j/RedisGraph assumptions, or before relying on algorithms, UDFs, vector/full-text search, integrations, GraphRAG, MCP, or client behavior.
---

<essential_principles>
## falkordb-capability-evidence Operating Rules

### 1. Every important claim gets an evidence class.
### 2. Unknown and smoke-needed claims need an owner, proof command, and acceptance criterion.
### 3. Neo4j-only and RedisGraph-legacy assumptions must be named, not silently adapted.
</essential_principles>

<quick_reference>
- Primary workflow → `workflows/main.md`
- Domain reference → `references/main.md`
- Eval rubric → `evals/evals.json`
- Cross-cutting proof skill → `.agents/skills/falkordb-capability-evidence/SKILL.md`
</quick_reference>

<routing>
Use this focused skill for: Claim classification, proof planning, source/docs/runtime/smoke evidence, release freshness, and drift control for FalkorDB features.

If a claim is capability-sensitive, load `falkordb-capability-evidence` or apply its evidence classes before recommending implementation.
</routing>

<reference_index>
- `references/main.md` — scope, gotchas, evidence boundaries, and implementation notes.
</reference_index>

<workflows_index>
- `workflows/main.md` — Verify a FalkorDB Capability Claim.
</workflows_index>

<success_criteria>
A good answer using this skill:
- Names the FalkorDB evidence level for important claims.
- Avoids Neo4j-only or RedisGraph-legacy feature drift.
- Gives concrete verification steps.
- Stays within this skill's scope and routes other work to the right FalkorDB skill.
</success_criteria>
