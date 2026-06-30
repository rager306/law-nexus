# Reactive Event Vocabulary and Job Ledger Contract

**Milestone:** M083-25gxp3  
**Status:** [proposed] architecture contract  
**Depends on:** D101, R060, R061, R062  
**Scope:** event vocabulary and local job ledger shape for a future bounded reactive shell  

## Purpose

This contract defines the first event vocabulary and local job ledger shape for the law-nexus reactive shell direction. It is a design contract only: M083 does not implement a runtime queue, worker, async API, production Legal Nexus orchestrator, or durable job store.

## Non-claims

This contract does **not** prove:

- async/reactive runtime behavior exists;
- legal correctness;
- parser completeness;
- retrieval quality;
- model or embedding quality;
- generated-Cypher correctness;
- FalkorDB production readiness;
- ACP/git-lex source-truth authority.

Event logs and job ledger records are operational/debug evidence only. They must not be promoted into legal/product proof.

## Source-truth and guardrail context

- **D101:** use a bounded reactive shell around the synchronous deterministic core, not an async-first rewrite.
- **R060:** future async work requires durable job state with fingerprints, lifecycle status, phase, attempts, last error, produced artifacts, proof level, and non-claims.
- **R061:** deterministic domain/policy/validation boundaries remain synchronous or pure unless a seam proves async value.
- **R062:** future reactive work must emit structured decision/failure traces with trace IDs, correlation IDs, job IDs, reason codes, fingerprints, lifecycle/proof tags, redaction status, produced artifacts, and compact trace bundles.

## Pilot seam selection

### First pilot: source inventory

M083 selects **source inventory** as the first event/job pilot family.

Why this seam first:

- Source inventory is naturally event-like: a source file can appear, disappear, or change fingerprint.
- It is lower risk than graph/retrieval/embedding runtime jobs.
- It can produce useful trace/job records without legal-answering claims.
- It aligns with R060/R062: source paths, fingerprints, inventory outputs, and diagnostics are safe bounded job metadata when redacted and path-normalized.
- GitNexus found `ParserInventoryUseCase` exactly at `Class:src/law_nexus/application/parser_inventory.py:ParserInventoryUseCase`.
- GitNexus impact for `ParserInventoryUseCase` was LOW, with direct upstream impact limited to `src/law_nexus/composition.py` import.
- GitNexus impact for `ParserInventoryUseCase.build_parser_fixture_inventory` was LOW, with direct upstream impact limited to tests.

### Second family: parser golden-case jobs

M083 records **parser golden-case jobs** as the second event family, not the first implementation pilot.

Why second:

- M079 made parser golden-case build/evaluate core package-owned.
- GitNexus found `build_evaluation_result` exactly at `Function:src/law_nexus/adapters/sources/parser_golden_cases.py:build_evaluation_result`.
- GitNexus impact for `build_evaluation_result` was LOW/zero upstream in the current graph.
- Golden-case jobs are useful regression events, but they depend on source/parser artifact stability.

### Deferred event families

The following remain deferred until source/parser contracts are more stable:

- graph ingest/proof jobs;
- retrieval quality jobs;
- embedding batch jobs;
- Legal Nexus runtime orchestration.

These surfaces involve external dependencies, quality claims, or production-readiness risks and need separate proof milestones.

## S02 contract sections to complete

S02 must complete the following sections in this artifact:

1. event family definitions;
2. event names and reason codes;
3. job lifecycle state machine;
4. local ledger record schema;
5. trace bundle shape;
6. storage option comparison;
7. idempotency and single-writer rules;
8. redaction and portability rules;
9. adoption ladder;
10. validator expectations.
