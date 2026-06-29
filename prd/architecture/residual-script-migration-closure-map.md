# Residual Script Migration Closure Map

## Purpose

This document closes M077 Residual Script Logic Migration Closure. It is the audit entrypoint for the final state of top-level `scripts/*.py` after the M077 wave.

The closure map does not mean every script was deleted or every historical script was rewritten. M077's accepted target state is narrower and safer:

- package-owned reusable logic for the seams selected in this milestone;
- retained script entrypoints when they are thin compatibility wrappers, proof/runtime wrappers, or explicitly deferred surfaces;
- full script type checking clean;
- no blanket script deletion without downstream compatibility proof.

## Final inventory snapshot

Source inventory: `prd/architecture/residual-script-migration-inventory.md`.

| Metric | Value |
|---|---:|
| Top-level Python scripts | 139 |
| Inventory rows | 139 |
| Missing inventory rows | 0 |
| Extra inventory rows | 0 |
| `migrate logic` rows | 49 |
| `proof runtime wrapper` rows | 61 |
| `thin wrapper` rows | 6 |
| `retire candidate` rows | 0 |
| `deferred` rows | 23 |
| Rows with extracted helper/seam marker | 16 |

The `migrate logic` rows are not silently treated as complete. They represent future cleanup candidates unless a row has an `extracted=yes` marker or an explicit bounded note. S07 closes M077 by documenting the final state and gates, not by converting all remaining rows into wrappers.

## Migration waves closed

| Slice | Commit | Closure |
|---|---|---|
| S01 Complete Script Inventory Research | `741b9d9` | Classified all 140 top-level scripts and created the durable residual migration backlog. |
| S02 Governance Projection Logic Migration | `5176b3e` | Added `law_nexus.adapters.governance.architecture_registry` and routed architecture graph/RDF projection helpers through package code. |
| S03 Parser Source Evaluation Logic Migration | `06a2eef` | Added `law_nexus.adapters.sources.parser_records`; `scripts/parser_records.py` became a compatibility re-export wrapper. |
| S04 Retrieval Evidence Evaluation Logic Migration | `65d8f89` | Added `law_nexus.adapters.retrieval.proof_helpers` and routed two retrieval proof wrappers through shared helper logic. |
| S05 FalkorDB Embedding Proof Logic Migration | `e5c029a` | Added `law_nexus.adapters.embeddings.proof_environment` and routed S09/S10 local embedding proof wrappers through environment/provenance helpers. |
| S06 Script Type Debt Closure | `5f7e27a` | Closed `uv run basedpyright scripts` from 72 errors across 19 scripts to 0 errors. |

## Package seams established

| Package seam | Purpose | Scripts affected |
|---|---|---|
| `law_nexus.adapters.governance.architecture_registry` | Architecture registry path loading, JSONL loading, edge rendering, and registry helper behavior. | `scripts/build-architecture-graph.py`, `scripts/export-architecture-rdf-projection.py` |
| `law_nexus.adapters.sources.parser_records` | Parser record schemas and JSONL loading/parsing contracts. | `scripts/parser_records.py` and parser/source tests/importers |
| `law_nexus.adapters.retrieval.proof_helpers` | Bounded path rendering, JSON loading, diagnostic code/payload extraction, and safe payload validation for retrieval proof wrappers. | `scripts/verify-retrieval-output-validator.py`, `scripts/verify-real-artifact-retrieval-proof.py` |
| `law_nexus.adapters.embeddings.proof_environment` | Local embedding proof environment/provenance helpers: cache roots, package probes, safe JSON logs, normalized paths, and model cache names. | `scripts/probe-s10-embedding-runtime-env.py`, `scripts/smoke-s09-local-embeddings.py` |
| `law_nexus.adapters.sources.parser_golden_cases` | Parser golden-case helper and core behavior: stable display paths, diagnostics, JSON/JSONL loading, SHA-256, build-case construction, evaluator loading, case mapping, fail-closed diagnostics, and result assembly. | `scripts/build-parser-golden-cases.py`, `scripts/evaluate-parser-golden-cases.py` |
| `law_nexus.adapters.sources.consultant_hierarchy` | Consultant hierarchy record builder plus M080 package-owned WordML paragraph streaming and bounded source diagnostics. | `scripts/build-consultant-hierarchy-records.py` |

These seams are adapter-level or source-level support seams. They do not make domain/application code depend on `scripts/`, and `uv run lint-imports` remains green.

## Retained wrapper policy

Retained scripts are acceptable only when they fit one of these states:

1. **Thin compatibility wrapper**: stable CLI/import surface delegates to package-owned logic.
2. **Proof/runtime wrapper**: script owns command-line proof orchestration, filesystem evidence production, external runtime setup, or compatibility reports.
3. **Deferred cleanup candidate**: script still has reusable logic but is explicitly bounded in the inventory and requires a later scoped migration.
4. **Retire candidate**: script should not be deleted until downstream references and compatibility parity are proven.

M077 intentionally did not delete all scripts. Proof and runtime wrappers are part of the repository's evidence surface and may remain script-owned when deleting or moving them would lose compatibility, reproducibility, or audit history.

## Retirement map

| Disposition | Count | Current action |
|---|---:|---|
| Thin wrapper | 6 | Keep. These are package-backed or stable compatibility surfaces. |
| Proof runtime wrapper | 61 | Keep. These are retained evidence/runtime entrypoints unless a future migration proves parity. |
| Retire candidate | 0 | Resolved in M078 S03: `scripts/build-representative-retrieval-corpus.py` was retired after canonical command parity proof and runtime handoff update. |
| Deferred | 23 | Keep bounded. Defer to future product/backlog slices with explicit scope. |
| Migrate logic | 49 | Keep as backlog unless already marked `extracted=yes`; future waves should pick bounded seams rather than big-bang rewrites. |

## Verification closure

S07 closure relies on these gates:

- `uv run basedpyright scripts` must pass with 0 errors.
- `uv run pytest tests/test_residual_script_migration_closure_map.py tests/test_residual_script_migration_inventory.py -q` must pass.
- Touched document/tests must pass ruff or be excluded when not Python.
- `uv run lint-imports` must keep all onion contracts.
- `gitnexus_detect_changes(repo="law-nexus", scope="all")` must be clean after commit and reindex.
- GSD UAT must cite objective `gsd_uat_exec` evidence.

S06 also established a broader static baseline: script type debt is closed without broad pyright/type suppressions. Full-script ruff still has unrelated pre-existing lint findings in untouched scripts and is not a closure claim for M077.

## GitNexus traceability notes

- Use GitNexus repo name `law-nexus`.
- Reindex command is `gitnexus analyze --force --name law-nexus`.
- Helper symbols with common names such as `normalized_path` or `bounded_path` may miss by bare lookup; use file-qualified symbols or exact UIDs.
- S06 pre-commit GitNexus detect reported CRITICAL risk because 19 script/proof entrypoints were intentionally touched. The risk was mitigated by full script type gate, touched lint, targeted tests, UAT, reindex, and post-commit clean detect.

## Deferred backlog boundaries

Future cleanup should be planned as new bounded slices. Do not infer from this closure map that the remaining `migrate logic` scripts are package-complete.

Recommended future work:

1. Convert additional high-value `migrate logic` rows into package seams only when a slice owns their proof contract.
2. Review the single retire candidate with reference search and CLI parity proof before deletion.
3. Address unrelated full-script ruff findings as a separate lint cleanup, not as part of M077 closure.
4. Keep proof/runtime wrappers when they are evidence surfaces rather than reusable library logic.

## Non-claims

This closure map does not prove:

- legal correctness;
- parser completeness;
- retrieval quality or answer faithfulness;
- model/embedding quality;
- generated-Cypher correctness;
- FalkorDB production readiness;
- ACP/git-lex authority over source truth;
- safe deletion of all scripts.

Authoritative proof remains source code, tests, runtime evidence, GSD requirements/decisions, and real source-document evidence where applicable. ACP/RDF/JSONL/graph projections remain derived diagnostics, not source truth.

## M080 Consultant hierarchy wrapper update

M080 reviewed remaining package-backed wrapper boundaries in `prd/architecture/residual-script-wrapper-boundary-review.md` and selected `scripts/build-consultant-hierarchy-records.py` as the next bounded seam after LOW GitNexus impact. M080 moved WordML paragraph streaming and bounded source diagnostics into `law_nexus.adapters.sources.consultant_hierarchy`, removed script-local dead hierarchy-core leftovers, and kept corpus/report/write/check orchestration in the script. The committed artifact freshness gate for this wrapper is `uv run python scripts/build-consultant-hierarchy-records.py --corpus --check`; plain `--check` is the legacy single-fixture compatibility mode. This is a bounded migration and does not claim legal correctness or parser completeness.

## M079 parser golden-case core update

M079 moved parser golden-case core behavior into `law_nexus.adapters.sources.parser_golden_cases`. `scripts/build-parser-golden-cases.py` delegates build-case construction to package code while retaining report/render/write/check wrapper behavior. `scripts/evaluate-parser-golden-cases.py` delegates evaluator artifact loading, case mapping, fail-closed diagnostics, and result assembly to package code while retaining CLI compatibility. This is a bounded migration and does not claim parser completeness.

## M078 S04 parser golden-case update

M078 S04 extracted shared parser golden-case utility helpers into `law_nexus.adapters.sources.parser_golden_cases`. M079 later moved build/evaluate core behavior into the same package seam. The scripts remain CLI/report wrappers. This is a bounded migration and does not claim parser completeness.

## M078 S03 retirement update

M078 S03 retired `scripts/build-representative-retrieval-corpus.py`. The accepted builder/check command is now the canonical underscore command: `uv run python scripts/build_representative_retrieval_corpus_manifest.py --check`. The legacy wrapper path is no longer emitted in the generated representative corpus manifest runtime handoff.
