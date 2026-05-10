# FalkorDB Algorithms Reference Notes

## Scope

BFS, Betweenness Centrality, Community Detection using Label Propagation (CDLP), PageRank, shortest path procedures, WCC, MSF, algorithm inputs/outputs, and verification fixtures.

## May 2026 evidence context

Use FalkorDB documentation and releases current to May 2026 as the freshness baseline. Relevant observed surfaces include FalkorDB core v4.18.x, FalkorDB docs updated 2026-05-09, falkordb-py v1.6.x, and FalkorDB Browser v2.x where applicable. Do not treat Neo4j documentation as FalkorDB evidence.

## Gotchas

- Do not call this Neo4j GDS-compatible unless a specific API/behavior is proven.
- Documented algorithm availability is not proof of suitability for a production graph.
- Use small fixtures to prove output shape before large graph runs.
- Local 2026-05-10 smoke evidence confirmed GraphBLAS-backed FalkorDB startup and procedure discovery on `falkordb/falkordb:edge`. Bounded algorithm fixtures confirmed output shape for `algo.pageRank('Page', 'LINKS')`, `algo.WCC({nodeLabels:['Page'], relationshipTypes:['LINKS']})`, `algo.bfs(source, -1, 'LINKS')`, `algo.betweenness({nodeLabels:['Page'], relationshipTypes:['LINKS']})`, `algo.labelPropagation({nodeLabels:['Page'], relationshipTypes:['LINKS']})`, `algo.SPpaths({...})`, and `algo.SSpaths({...})`. Observed synthetic outputs: PageRank ids `a,b,c,d` with positive scores; WCC and label propagation grouped linked `a,b,c` separately from isolated `d`; BFS from `a` returned node/edge counts `[2, 2]`; betweenness on `a->b->c` returned center score `b=1.0`; SPpaths returned two paths with weights `[1.0, 2.0]`; SSpaths returned three paths with weights `[1.0, 1.0, 2.0]`. Treat this as synthetic output-shape proof only; production graph suitability and performance still need target-data benchmarks.

## Required answer shape

- State the task scope and target FalkorDB version/surface.
- State evidence level for capability-sensitive claims.
- Provide a minimal example, checklist, query, request, or fixture when applicable.
- Provide verification and rollback/cleanup where writes, operations, generated output, or external integrations are involved.
