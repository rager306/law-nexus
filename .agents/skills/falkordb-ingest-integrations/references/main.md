# FalkorDB Ingest/Integration Reference Notes

## Scope

LOAD CSV, Bulk Loader, Kafka Connect Sink, Apache Jena, Snowflake, PyTorch Geometric, BOLT support, Spring Data FalkorDB, batch loading, idempotency, and verification counts.

## May 2026 evidence context

Use FalkorDB documentation and releases current to May 2026 as the freshness baseline. Relevant observed surfaces include FalkorDB core v4.18.x, FalkorDB docs updated 2026-05-09, falkordb-py v1.6.x, and FalkorDB Browser v2.x where applicable. Do not treat Neo4j documentation as FalkorDB evidence.

## Gotchas

- Start with a tiny sample before bulk load.
- Idempotency keys and MERGE behavior must be explicit.
- Integration docs are not proof that user environment is configured.
- Choose batching strategy deliberately: small transactional batches for recoverability, larger bulk batches only with memory/error evidence.
- Verification counts must compare source rows, created nodes, created relationships, skipped rows, and failed rows.

## Required answer shape

- State the task scope and target FalkorDB version/surface.
- State evidence level for capability-sensitive claims.
- Provide a minimal example, checklist, query, request, or fixture when applicable.
- Provide verification and rollback/cleanup where writes, operations, generated output, or external integrations are involved.
