---
name: falkordb-ingest-integrations
description: Plan FalkorDB ingestion and external integrations. Use when the user asks about LOAD CSV, Bulk Loader, Kafka Connect Sink, Apache Jena, Snowflake, PyTorch Geometric, BOLT support, Spring Data FalkorDB, or moving external data into FalkorDB.
---

<essential_principles>
## falkordb-ingest-integrations Operating Rules

### 1. Separate ingestion mechanism from graph model quality.
### 2. Every loader/integration needs source shape, idempotency, batching, error handling, and verification counts.
### 3. Do not assume Neo4j import tooling or admin commands apply to FalkorDB.
</essential_principles>

<quick_reference>
- Primary workflow → `workflows/main.md`
- Domain reference → `references/main.md`
- Eval rubric → `evals/evals.json`
- Cross-cutting proof skill → `.agents/skills/falkordb-capability-evidence/SKILL.md`
</quick_reference>

<routing>
Use this focused skill for: LOAD CSV, Bulk Loader, Kafka Connect Sink, Apache Jena, Snowflake, PyTorch Geometric, BOLT support, Spring Data FalkorDB, batch loading, idempotency, and verification counts.

If a claim is capability-sensitive, load `falkordb-capability-evidence` or apply its evidence classes before recommending implementation.
</routing>

<reference_index>
- `references/main.md` — scope, gotchas, May 2026 evidence boundaries, and implementation notes.
</reference_index>

<workflows_index>
- `workflows/main.md` — Plan FalkorDB Ingest or Integration Work.
</workflows_index>

<success_criteria>
A good answer using this skill:
- Names the FalkorDB evidence level for important claims.
- Avoids Neo4j-only or product-adjacent feature drift.
- Gives concrete verification steps.
- Separates documented support from runtime or quality proof.
</success_criteria>
