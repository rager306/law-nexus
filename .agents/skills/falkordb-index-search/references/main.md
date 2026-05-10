# FalkorDB Index/Search Reference Notes

## Scope

Range indexes, full-text indexes, vector indexes, query patterns, proof layers, hybrid retrieval boundaries, and index verification.

## May 2026 evidence context

Use FalkorDB documentation and releases current to May 2026 as the freshness baseline. Relevant observed releases include FalkorDB core v4.18.x, falkordb-py v1.6.x, and FalkorDB Browser v2.x. Do not treat Neo4j documentation as FalkorDB evidence.

## Gotchas

- Do not copy Neo4j vector syntax.
- Distinguish embedding model quality from vector storage/query mechanics.
- Use GRAPH.EXPLAIN/PROFILE or smoke queries to prove index usage.
- Treat range, full-text, and vector support as docs-backed until the exact target version is runtime-confirmed.
- Local 2026-05-10 smoke evidence confirmed synthetic full-text index, vector index, and vector-distance behavior on `falkordb/falkordb:edge` image `sha256:4246e809a5fd74d233196e08c879885adc47bde499a8e25fa5ff83fd39644d80`; cite it only as bounded synthetic runtime proof, not product retrieval quality.
- Record separate proof for model encoding, vector storage, index creation, vector query, and product quality.

## Required answer shape

- State the task scope.
- State evidence level for capability-sensitive claims.
- Provide a minimal example, checklist, or query when applicable.
- Provide verification and rollback/cleanup where writes or operational changes are involved.
