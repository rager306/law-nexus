# Residual Script Wrapper Boundary Review

**Milestone:** M080-3wvcnw  
**Status:** [bounded] planning and migration review  
**Source:** `prd/architecture/residual-script-migration-inventory.md` plus GitNexus impact checks  

## Purpose

This review plans two follow-up actions after M079:

1. Select the next bounded script-to-package migration seam.
2. Review remaining package-backed script wrapper boundaries so future waves do not big-bang unrelated script logic.

This document is architecture-maintenance evidence only. It does not validate legal correctness, parser completeness, retrieval quality, generated-Cypher correctness, FalkorDB production readiness, or ACP/git-lex source-truth authority.

## Package-backed wrapper candidates

| Script | Classification | Priority | Boundary state | M080 action |
|---|---|---:|---|---|
| `scripts/build-consultant-hierarchy-records.py` | migrate logic | medium | M080 moved WordML paragraph streaming and bounded source diagnostics into `law_nexus.adapters.sources.consultant_hierarchy`; script still owns corpus orchestration, reports, writes, and checks. | **Completed in M080 S02.** Preserve CLI/report behavior; committed artifact gate is `--corpus --check`. |
| `scripts/build-offline-citation-retrieval-cases.py` | thin wrapper | low | Retained wrapper around an existing package seam. | Keep; no M080 code change. |
| `scripts/build-parser-golden-cases.py` | migrate logic | high | M079 moved build-case core into `law_nexus.adapters.sources.parser_golden_cases`; report/render/write/check wrapper remains script-owned. | Keep wrapper; only future compatibility-wrapper cleanup after reference proof. |
| `scripts/build-real-artifact-retrieval-cases.py` | thin wrapper | low | Retained wrapper around an existing package seam. | Keep; no M080 code change. |
| `scripts/build_representative_retrieval_corpus_manifest.py` | thin wrapper | low | Retained wrapper around an existing package seam. | Keep; no M080 code change. |
| `scripts/evaluate-parser-golden-cases.py` | migrate logic | high | M079 moved evaluator core into `law_nexus.adapters.sources.parser_golden_cases`; CLI wrapper remains script-owned. | Keep wrapper; only future compatibility-wrapper cleanup after reference proof. |
| `scripts/inventory-parser-fixtures.py` | thin wrapper | low | Retained wrapper around an existing package seam. | Keep; no M080 code change. |
| `scripts/parser_records.py` | thin wrapper | low | Compatibility re-export wrapper after parser record contracts moved to package code. | Keep unless a separate reference/deprecation proof proves safe removal. |
| `scripts/probe-consultant-parser.py` | migrate logic | medium | Existing package-backed parser adapter; probe still owns fixture/probe reporting. | Candidate for later bounded wave; not selected before hierarchy wrapper. |
| `scripts/probe-s10-embedding-runtime-env.py` | migrate logic | high | Shared local embedding proof environment helpers exist; wrapper owns S10 runtime readiness semantics. | Defer; runtime proof semantics are higher risk. |
| `scripts/retrieval_output_validator.py` | thin wrapper | low | Retained wrapper around existing package seam. | Keep; no M080 code change. |
| `scripts/smoke-s09-local-embeddings.py` | migrate logic | high | Shared local embedding proof environment helpers exist; wrapper owns S09 smoke/encode semantics. | Defer; runtime proof semantics are higher risk. |
| `scripts/verify-falkordb-csv-ingest-proof.py` | proof runtime wrapper | medium | Proof wrapper; reusable helpers may still be extracted. | Defer; proof-runtime behavior should be separately scoped. |
| `scripts/verify-real-artifact-retrieval-proof.py` | proof runtime wrapper | medium | Shared retrieval proof helpers exist; case-specific proof logic remains script-owned. | Defer; proof-runtime behavior should be separately scoped. |
| `scripts/verify-retrieval-output-validator.py` | proof runtime wrapper | medium | Shared retrieval proof helpers exist; validator-specific proof logic remains script-owned. | Defer; proof-runtime behavior should be separately scoped. |
| `scripts/verify-semantic-descriptor-scoring.py` | proof runtime wrapper | medium | Proof wrapper; reusable helpers may still be extracted. | Defer; proof-runtime behavior should be separately scoped. |

## Selected bounded seam

M080 selected `scripts/build-consultant-hierarchy-records.py` because:

- it is already package-backed through `SourceHierarchyUseCase` and `ConsultantHierarchyRecordBuilder`;
- GitNexus found `SourceHierarchyUseCase` exactly at `Class:src/law_nexus/application/source_hierarchy.py:SourceHierarchyUseCase`;
- file-qualified GitNexus impact for the relevant script functions was LOW:
  - `Function:scripts/build-consultant-hierarchy-records.py:stream_wordml_paragraphs` → LOW, upstream through `build_corpus` / `main` only;
  - `Function:scripts/build-consultant-hierarchy-records.py:build_for_fixture` → LOW, upstream through `build_corpus` / `main` only;
  - `Function:scripts/build-consultant-hierarchy-records.py:build_corpus` → LOW, upstream through `main` only;
  - `Function:scripts/build-consultant-hierarchy-records.py:render_report` → LOW, upstream through `build_corpus` / `main` only;
  - `Function:scripts/build-consultant-hierarchy-records.py:check_artifacts` → LOW, upstream through `main` only.

## M080 migration boundary

Completed in M080 S02:

- Moved WordML paragraph streaming and bounded source diagnostics into package code.
- Removed script-local dead hierarchy-core leftovers that were already package-owned.
- Kept CLI argument parsing, report rendering, artifact writing, corpus orchestration, and command exit behavior in the script.

Forbidden in M080 S02:

- Do not change hierarchy record semantics.
- Do not claim Consultant hierarchy records are legally authoritative.
- Do not change parser completeness claims.
- Do not delete the script or retire the CLI.
- Do not import `scripts/` from package code.

## Verification plan

S02 must run at minimum:

- targeted Consultant hierarchy tests;
- `uv run python scripts/build-consultant-hierarchy-records.py --corpus --check` for the committed corpus artifacts; plain `--check` is the legacy single-fixture compatibility mode and should only be used after regenerating single-fixture artifacts in an isolated check;
- `uv run ruff check scripts src/law_nexus/adapters/sources/consultant_hierarchy.py tests/test_consultant_hierarchy_records.py tests/test_source_hierarchy_use_case.py`;
- `uv run basedpyright scripts src/law_nexus/adapters/sources/consultant_hierarchy.py tests/test_consultant_hierarchy_records.py tests/test_source_hierarchy_use_case.py`;
- `uv run lint-imports`;
- `gitnexus analyze --force --name law-nexus`, then `gitnexus_detect_changes(repo="law-nexus", scope="all")` after commit.
