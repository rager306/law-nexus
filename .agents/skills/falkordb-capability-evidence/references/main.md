# FalkorDB Capability Evidence Reference Notes

## Scope

Claim classification, proof planning, source/docs/runtime/smoke evidence, release freshness, and drift control for FalkorDB features.

## May 2026 evidence context

Use FalkorDB documentation and releases current to May 2026 as the freshness baseline. Relevant observed releases include FalkorDB core v4.18.x, falkordb-py v1.6.x, and FalkorDB Browser v2.x. Do not treat Neo4j documentation as FalkorDB evidence.

## Gotchas

- Evidence classes: runtime-confirmed, source-backed, docs-backed, smoke-needed, blocked-environment, neo4j-only, redisgraph-legacy, unknown.
- Docs-backed is not production proof.
- Runtime smoke tests prove mechanics, not necessarily product quality.

## Required answer shape

- State the task scope.
- State evidence level for capability-sensitive claims.
- Provide a minimal example, checklist, or query when applicable.
- Provide verification and rollback/cleanup where writes or operational changes are involved.
