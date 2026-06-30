# Source Inventory JSONL Ledger Implementation Plan

**Milestone:** M084-jxs6mq  
**Status:** [bounded] implementation plan  
**Depends on:** M083-25gxp3, D101, D102, R060, R061, R062  
**Scope:** first source inventory JSONL job ledger prototype  

## Purpose

This plan maps the M083 reactive event vocabulary and local job ledger contract into a bounded implementation sequence. The implementation must remain traceable-before-concurrent: first pure package primitives, then append-only JSONL mechanics, then optional source inventory wrapper emission, then parser golden-case vocabulary reuse proof.

M084 must not introduce queues, workers, daemons, async APIs, external brokers, FalkorDB-backed job state, or production Legal Nexus runtime orchestration.

## GitNexus planning evidence

GitNexus was used before planning M084.

| Seam | Exact symbol / process evidence | Impact summary | M084 meaning |
|---|---|---:|---|
| Source inventory use case | `Class:src/law_nexus/application/parser_inventory.py:ParserInventoryUseCase` | LOW; direct upstream import from `src/law_nexus/composition.py` | Safe first pilot seam. |
| Source inventory use-case method | `Method:src/law_nexus/application/parser_inventory.py:ParserInventoryUseCase.build_parser_fixture_inventory#1` | LOW; current callers are tests / no high-risk process impact | Optional wrapper/use-case integration can be isolated. |
| Source inventory script wrapper | `Function:scripts/inventory-parser-fixtures.py:main` | LOW; no upstream callers in graph | CLI ledger flag can be added without changing package imports. |
| Filesystem inventory adapter | `Function:src/law_nexus/adapters/sources/filesystem_inventory.py:build_parser_fixture_inventory` | LOW; no upstream callers in graph | Adapter can stay deterministic; ledger should wrap around it. |
| Parser golden-case second family | `Function:src/law_nexus/adapters/sources/parser_golden_cases.py:build_evaluation_result` | LOW / zero upstream in current graph | Reuse proof only in M084, no CLI/runtime integration. |

## Implementation sequence

| Wave | Slice | Scope | Depends on | Code/scripts/tests touched |
|---|---|---|---|---|
| 1 | S01 | Implementation horizon and GitNexus fit | M083 | `prd/architecture/source-inventory-jsonl-ledger-implementation-plan.md` |
| 2 | S02 | Ledger vocabulary primitives | S01 | `src/law_nexus/adapters/observability/job_ledger.py`, tests |
| 3 | S03 | Validation, redaction, JSONL serialization/writer | S02 | same package module, tests |
| 4 | S04 | Source inventory event factory | S03 | package module or source inventory ledger adapter, tests |
| 5 | S05 | Optional source inventory CLI ledger flag | S04 | `scripts/inventory-parser-fixtures.py`, tests |
| 6 | S06 | Failure/freshness source inventory traces | S05 | script/package tests |
| 7 | S07 | Parser golden-case event family reuse proof | S03 | package event builders/tests only |
| 8 | S08 | Architecture contract alignment | S04, S07 | contract docs/tests |
| 9 | S09 | Full gates and closeout | S05, S06, S08 | all focused tests/gates |

## Architecture boundaries

### Allowed in M084

- Pure sync dataclasses/functions for ledger records.
- Stable event/status/reason vocabulary from M083.
- Local append-only JSONL writer for explicit ledger paths.
- Optional source inventory CLI flag/path for ledger emission.
- Fixture-backed parser golden-case event record builders.
- Tests proving validation, redaction, portability, non-claims, and no-runtime boundaries.

### Forbidden in M084

- Async-first rewrite.
- Queue, worker, daemon, scheduler, or event loop orchestration.
- External broker or service dependency.
- FalkorDB-backed job state.
- Legal Nexus runtime orchestration.
- Treating logs/ledger records as legal correctness, parser completeness, retrieval quality, generated-Cypher correctness, or FalkorDB production proof.
- Importing from `scripts/` inside package code.

## Touch-point rules

- `src/law_nexus` owns reusable ledger primitives.
- `scripts/inventory-parser-fixtures.py` may expose a ledger flag as wrapper behavior only.
- Existing source inventory output artifacts must not change unless the explicit ledger option is used.
- Existing source inventory tests remain authoritative for baseline behavior.
- Parser golden-case work in M084 is a vocabulary reuse proof only; its CLIs remain untouched unless a future milestone selects that integration.

## Verification plan

Each slice must produce `gsd_uat_exec` evidence. Focused checks:

- `uv run pytest tests/test_job_ledger*.py ...`
- `uv run pytest tests/test_parser_inventory_use_case.py ...`
- `uv run pytest tests/test_reactive_event_vocabulary_job_ledger_contract.py ...`
- `uv run ruff check ...`
- `uv run basedpyright ...` for touched Python scopes when feasible.
- `uv run lint-imports` before closeout.
- `gitnexus analyze --force --name law-nexus` and `gitnexus_detect_changes(repo="law-nexus", scope="all")` after commits.

## Non-claims

M084 implementation is operational/debug infrastructure only. It does not prove async/reactive runtime behavior, legal correctness, parser completeness, retrieval quality, model/embedding quality, generated-Cypher correctness, FalkorDB production readiness, or ACP/git-lex source-truth authority.
