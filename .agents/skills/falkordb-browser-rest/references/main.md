# FalkorDB Browser/REST Reference Notes

## Scope

Browser UI, REST auth tokens, graph endpoints, graph node/property operations, config endpoints, sessions/connections, users/permissions, query history, chat panel, and Browser 2.x release caveats.

## May 2026 evidence context

Use FalkorDB documentation and releases current to May 2026 as the freshness baseline. Relevant observed surfaces include FalkorDB core v4.18.x, FalkorDB docs updated 2026-05-09, falkordb-py v1.6.x, and FalkorDB Browser v2.x where applicable. Do not treat Neo4j documentation as FalkorDB evidence.

## Gotchas

- REST endpoints require bearer auth except credential token endpoint.
- Do not conflate Browser REST API with raw Redis/FalkorDB commands.
- File upload and session management had recent security/fix activity in Browser 2.x.

## Required answer shape

- State the task scope and target FalkorDB version/surface.
- State evidence level for capability-sensitive claims.
- Provide a minimal example, checklist, query, request, or fixture when applicable.
- Provide verification and rollback/cleanup where writes, operations, generated output, or external integrations are involved.
