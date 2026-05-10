# FalkorDB Ops and Debug Reference Notes

## Scope

GRAPH.EXPLAIN, PROFILE, INFO, MEMORY, SLOWLOG, CONFIG, ACL, connection/auth, Bolt/WebSocket, Docker/resource failures, and query fan-out.

## May 2026 evidence context

Use FalkorDB documentation and releases current to May 2026 as the freshness baseline. Relevant observed releases include FalkorDB core v4.18.x, falkordb-py v1.6.x, and FalkorDB Browser v2.x. Do not treat Neo4j documentation as FalkorDB evidence.

## Gotchas

- Recent 4.18.x releases include memory safety and Bolt/WebSocket hardening fixes.
- Do not guess performance; compare plan/profile before and after.
- Synthetic fixtures should isolate one variable.

## Required answer shape

- State the task scope.
- State evidence level for capability-sensitive claims.
- Provide a minimal example, checklist, or query when applicable.
- Provide verification and rollback/cleanup where writes or operational changes are involved.
