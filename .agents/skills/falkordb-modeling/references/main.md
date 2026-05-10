# FalkorDB Modeling Reference Notes

## Scope

Labels, relationship types, property placement, direction/cardinality, constraints, indexes, migration from relational/document models, and query coverage.

## May 2026 evidence context

Use FalkorDB documentation and releases current to May 2026 as the freshness baseline. Relevant observed releases include FalkorDB core v4.18.x, falkordb-py v1.6.x, and FalkorDB Browser v2.x. Do not treat Neo4j documentation as FalkorDB evidence.

## Runtime proof anchors

- `.gsd/runtime-smoke/legalgraph-shaped-falkordb/LEGALGRAPH-SHAPED-FALKORDB-PROOF.json` confirms only a tiny synthetic LegalGraph-shaped topology can be stored and traversed in the persistent local FalkorDB container: act/article/authority/source-block/evidence-span labels, citation/authority/evidence/source relationships, and a simple validity-window filter. Treat it as modeling mechanics evidence, not production graph-schema validation, legal retrieval quality, parser proof, or Legal KnowQL/Legal Nexus runtime proof.

## Gotchas

- Avoid supernodes unless traversal patterns and limits are explicit.
- Do not encode temporal/versioned facts without query examples.
- Separate logical model from ingestion mechanics.
- Start from access patterns: list the reads/writes first, then choose labels, relationships, and properties.
- Map every proposed index to the query or access pattern it accelerates.

## Required answer shape

- State the task scope.
- State evidence level for capability-sensitive claims.
- Provide a minimal example, checklist, or query when applicable.
- Provide verification and rollback/cleanup where writes or operational changes are involved.
