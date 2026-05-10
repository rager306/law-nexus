# FalkorDB UDF/FLEX Reference Notes

## Scope

FLEX function reference, text/json/map/date/collection/similarity functions, custom UDF boundaries, QuickJS resource limits, graph object support in UDFs, graph.getNodeById, and Python client UDF API notes.

## May 2026 evidence context

Use FalkorDB documentation and releases current to May 2026 as the freshness baseline. Relevant observed surfaces include FalkorDB core v4.18.x, FalkorDB docs updated 2026-05-09, falkordb-py v1.6.x, and FalkorDB Browser v2.x where applicable. Do not treat Neo4j documentation as FalkorDB evidence.

## Gotchas

- Do not import APOC function expectations.
- Resource limits are operational constraints, not implementation details.
- Custom UDFs need security review and minimal fixtures.

## Required answer shape

- State the task scope and target FalkorDB version/surface.
- State evidence level for capability-sensitive claims.
- Provide a minimal example, checklist, query, request, or fixture when applicable.
- Provide verification and rollback/cleanup where writes, operations, generated output, or external integrations are involved.
