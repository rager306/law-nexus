# FalkorDB Cypher Reference Notes

## Scope

Core Cypher, GRAPH.QUERY/RO_QUERY, EXPLAIN/PROFILE, parameters, LOAD CSV, procedures/functions, and Neo4j-to-FalkorDB translation review.

## May 2026 evidence context

Use FalkorDB documentation and releases current to May 2026 as the freshness baseline. Relevant observed releases include FalkorDB core v4.18.x, falkordb-py v1.6.x, and FalkorDB Browser v2.x. Do not treat Neo4j documentation as FalkorDB evidence.

## Gotchas

- Parameterize values; do not interpolate user input into query strings.
- Route vector/full-text/procedure uncertainty to falkordb-capability-evidence.
- Use EXPLAIN/PROFILE before performance claims.

## Required answer shape

- State the task scope.
- State evidence level for capability-sensitive claims.
- Provide a minimal example, checklist, or query when applicable.
- Provide verification and rollback/cleanup where writes or operational changes are involved.
