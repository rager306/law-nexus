# falkordb-py Reference Notes

## Scope

Python sync/async connection setup, from_url behavior, close/aclose, parameter handling, Unix socket use, result handling, UDF API, and observability.

## May 2026 evidence context

Use FalkorDB documentation and releases current to May 2026 as the freshness baseline. Relevant observed releases include FalkorDB core v4.18.x, falkordb-py v1.6.x, and FalkorDB Browser v2.x. Do not treat Neo4j documentation as FalkorDB evidence.

## Gotchas

- v1.6.1 fixed async from_url host handling; cite version when relevant.
- v1.6.x adds lifecycle improvements; close connections explicitly.
- Backtick-wrapped parameter/dict map keys matter for generated queries.
- Never log credentials, connection URLs, bearer tokens, or raw environment values.
- Use parameters for user values; do not format values into Cypher strings.
- Treat UDF API usage as capability-sensitive and route uncertain behavior through capability evidence.

## Required answer shape

- State the task scope.
- State evidence level for capability-sensitive claims.
- Provide a minimal example, checklist, or query when applicable.
- Provide verification and rollback/cleanup where writes or operational changes are involved.
