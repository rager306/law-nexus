# Residual Script Migration Inventory

**Milestone:** M077-6kzcz3  
**Slice:** S01  
**Status:** [bounded] research inventory  
**Source count:** 139 top-level `scripts/*.py` files
**Decision:** classify every script before migrating or retiring anything.

## Purpose

This inventory is the post-M076 backlog for finishing residual script cleanup. Its goal is to ensure reusable logic moves into `src/law_nexus` package seams while retained `scripts/` files are either thin CLI wrappers or explicitly justified proof/runtime wrappers.

S01 does not migrate code and does not authorize deletion. It creates the complete map needed by later M077 slices.

## Classification vocabulary

| Classification | Meaning | Allowed next action |
|---|---|---|
| migrate logic | Script appears to contain reusable business, architecture, parser, retrieval, graph, embedding, or governance logic that should move into package seams before wrapper thinning. | Plan targeted extraction in S02-S05. |
| thin wrapper | Script already appears package-backed and small enough to remain as a stable CLI wrapper. | Keep, verify compatibility. |
| proof runtime wrapper | Script is proof, smoke, benchmark, or runtime orchestration where entrypoint behavior may remain script-owned; reusable helpers may still be extracted. | Keep wrapper, review helper extraction. |
| retire candidate | Script is small enough to review for removal or replacement, but only after reference checks and compatibility proof. | Do not delete in S01. |
| deferred | Script needs manual review after high-priority migrations because the heuristic evidence is insufficient. | Keep until reviewed. |

## Summary

- Total scripts: `139`
- Package-backed scripts: `9`
- `migrate logic`: `49`
- `proof runtime wrapper`: `61`
- `thin wrapper`: `6`
- `retire candidate`: `0`
- `deferred`: `23`
- `high` priority: `47`
- `medium` priority: `86`
- `low` priority: `6`
- Broad planning-only type check: `basedpyright scripts` reported 80 error lines across 23 scripts.

## GitNexus research notes

Representative exact GitNexus contexts resolved during S01:

- `Function:scripts/evaluate-parser-golden-cases.py:evaluate_cases`
- `Function:scripts/build-architecture-graph.py:main`
- `Function:scripts/build-architecture-graph.py:run`
- `Function:scripts/run-s10-user-bge-m3-proof.py:run_falkordb_vector_proof`
- `Function:scripts/source_lifecycle.py:process_batch`

Caveats: use file-qualified UIDs for ambiguous names such as `main`, `run`, and `verify`; derive actual function names before lookup; avoid parallel GitNexus context calls in this workflow because S01 observed a transient LadybugDB initialization error under parallel access.

## Migration waves

| Wave | Scope | Input classifications |
|---|---|---|
| S02 | Governance and projection scripts | high-priority `migrate logic` in architecture, ACP, RDF, and projection scripts |
| S03 | Parser and legal source evaluation scripts | parser/source `migrate logic` and related proof wrappers |
| S04 | Retrieval and evidence evaluation scripts | retrieval/evidence `migrate logic` and proof wrappers |
| S05 | FalkorDB and embedding proof scripts | graph, vector, embedding, smoke, benchmark, and runtime proof scripts |
| S06 | Type debt and wrapper thinning | scripts with type errors and package-backed wrappers |
| S07 | Final closure | every script in this inventory |

## Complete script inventory

| # | Script | Lines | Funcs | Classes | Package imports | Classification | Priority | Target seam |
|---:|---|---:|---:|---:|---:|---|---|---|
| 1 | `scripts/acp_git_lex_backend.py` | 402 | 15 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 2 | `scripts/analyze-session-learning.py` | 303 | 13 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 3 | `scripts/build-acp-canonical-integration.py` | 392 | 22 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 4 | `scripts/build-acp-composition-staging.py` | 333 | 20 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 5 | `scripts/build-acp-integrated-registry-fixture.py` | 285 | 16 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 6 | `scripts/build-architecture-graph.py` | 669 | 29 | 2 | no | migrate logic | high | S02 extracted shared registry path and JSONL helpers; deeper graph/report logic still pending |
| 7 | `scripts/build-consultant-hierarchy-records.py` | 865 | 30 | 3 | yes | migrate logic | medium | thin existing package-backed script further |
| 8 | `scripts/build-consultant-prior-art-expectations.py` | 542 | 21 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 9 | `scripts/build-consultant-relation-candidates.py` | 530 | 24 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 10 | `scripts/build-independent-structural-signal-inputs.py` | 213 | 11 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 11 | `scripts/build-local-retrieval-quality-benchmark.py` | 309 | 15 | 0 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 12 | `scripts/build-materialized-descriptor-inputs.py` | 211 | 11 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 13 | `scripts/build-odt-smoke-records.py` | 636 | 26 | 3 | no | migrate logic | high | new package seam required before wrapper thinning |
| 14 | `scripts/build-offline-citation-retrieval-cases.py` | 103 | 8 | 0 | yes | thin wrapper | low | retain wrapper around existing package seam |
| 15 | `scripts/build-ontology-graphrag-proof-cases.py` | 366 | 13 | 0 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 16 | `scripts/build-parser-evidence-span-materialization.py` | 200 | 12 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 17 | `scripts/build-parser-golden-cases.py` | 831 | 17 | 0 | no | migrate logic | high | new package seam required before wrapper thinning |
| 18 | `scripts/build-parser-staging-graph.py` | 774 | 24 | 4 | no | migrate logic | high | new package seam required before wrapper thinning |
| 19 | `scripts/build-real-artifact-retrieval-cases.py` | 103 | 9 | 0 | yes | thin wrapper | low | retain wrapper around existing package seam |
| 20 | `scripts/build-safe-structural-descriptor-remediation-inputs.py` | 227 | 12 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 21 | `scripts/build-semantic-descriptor-inputs.py` | 384 | 15 | 0 | no | deferred | medium | needs manual review after high-priority migrations |
| 22 | `scripts/build-source-id-uniqueness.py` | 113 | 4 | 0 | no | deferred | medium | needs manual review after high-priority migrations |
| 23 | `scripts/build-source-record-cardinality-signal-inputs.py` | 237 | 12 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 24 | `scripts/build_representative_retrieval_corpus_manifest.py` | 217 | 13 | 0 | yes | thin wrapper | low | retain wrapper around existing package seam |
| 25 | `scripts/check-gsd-sync-drift.py` | 411 | 16 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 26 | `scripts/check-local-retrieval-runtime.py` | 363 | 15 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 27 | `scripts/compare-consultant-hierarchy-prior-art.py` | 571 | 22 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 28 | `scripts/evaluate-falkordb-pack-quality.py` | 196 | 6 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 29 | `scripts/evaluate-falkordb-skill-quality.py` | 215 | 6 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 30 | `scripts/evaluate-falkordb-trigger-proxy.py` | 165 | 4 | 0 | no | deferred | medium | needs manual review after high-priority migrations |
| 31 | `scripts/evaluate-parser-golden-cases.py` | 826 | 21 | 0 | no | migrate logic | high | new package seam required before wrapper thinning |
| 32 | `scripts/evaluate-s09-local-embeddings.py` | 788 | 37 | 3 | no | migrate logic | high | new package seam required before wrapper thinning |
| 33 | `scripts/export-acp-architecture-projection.py` | 538 | 24 | 0 | no | migrate logic | high | new package seam required before wrapper thinning |
| 34 | `scripts/export-acp-recovery-view.py` | 186 | 11 | 0 | no | deferred | medium | needs manual review after high-priority migrations |
| 35 | `scripts/export-architecture-rdf-projection.py` | 716 | 38 | 1 | no | migrate logic | high | S02 extracted shared registry path and JSONL helpers; RDF projection builder logic still pending |
| 36 | `scripts/extract-prd-architecture-items.py` | 3162 | 26 | 2 | no | migrate logic | high | new package seam required before wrapper thinning |
| 37 | `scripts/generate-architecture-closure-roadmap.py` | 267 | 10 | 0 | no | deferred | medium | needs manual review after high-priority migrations |
| 38 | `scripts/generate-architecture-remediation-matrix.py` | 434 | 12 | 0 | no | deferred | medium | needs manual review after high-priority migrations |
| 39 | `scripts/generate-architecture-track-split.py` | 384 | 10 | 0 | no | deferred | medium | needs manual review after high-priority migrations |
| 40 | `scripts/generate-architecture-views.py` | 1201 | 30 | 0 | no | migrate logic | high | new package seam required before wrapper thinning |
| 41 | `scripts/generate-m065-s02-install-manifest.py` | 302 | 12 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 42 | `scripts/git_lex_diagnostic_adapter.py` | 467 | 22 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 43 | `scripts/inventory-parser-fixtures.py` | 117 | 2 | 0 | yes | thin wrapper | low | retain wrapper around existing package seam |
| 44 | `scripts/parser_records.py` | 52 | 0 | 0 | yes | thin wrapper | low | S03 moved parser record contracts to `src/law_nexus.adapters.sources.parser_records`; script remains compatibility re-export wrapper |
| 45 | `scripts/probe-consultant-parser.py` | 400 | 12 | 1 | yes | migrate logic | medium | thin existing package-backed script further |
| 46 | `scripts/probe-s10-embedding-runtime-env.py` | 512 | 28 | 0 | yes | migrate logic | high | S05 extracted shared local embedding proof environment helpers; wrapper still owns S10 runtime readiness semantics |
| 47 | `scripts/prove-legalgraph-shaped-falkordb.py` | 486 | 19 | 3 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 48 | `scripts/prove-m002-s04-minimax-pyo3.py` | 1104 | 39 | 5 | no | migrate logic | high | new package seam required before wrapper thinning |
| 49 | `scripts/prove-m003-s01-minimax-baseline.py` | 693 | 24 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 50 | `scripts/prove-m003-s02-minimax-pyo3-endpoint.py` | 1046 | 33 | 3 | no | migrate logic | high | new package seam required before wrapper thinning |
| 51 | `scripts/prove-m003-s03-reasoning-safe-candidate.py` | 1503 | 42 | 3 | no | migrate logic | high | new package seam required before wrapper thinning |
| 52 | `scripts/prove-m003-s04-validation-readonly-execution.py` | 764 | 45 | 4 | no | migrate logic | high | new package seam required before wrapper thinning |
| 53 | `scripts/prove-m003-s05-r017-proof-closure.py` | 532 | 24 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 54 | `scripts/retrieval_output_validator.py` | 70 | 1 | 0 | yes | thin wrapper | low | retain wrapper around existing package seam |
| 55 | `scripts/run-m048-s04-git-lex-proof.py` | 484 | 14 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 56 | `scripts/run-m048-s05-git-lex-workflows.py` | 392 | 9 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 57 | `scripts/run-s10-gigaembeddings-proof.py` | 766 | 51 | 5 | no | migrate logic | high | new package seam required before wrapper thinning |
| 58 | `scripts/run-s10-user-bge-m3-proof.py` | 1112 | 47 | 5 | no | migrate logic | high | new package seam required before wrapper thinning |
| 59 | `scripts/run_m048_s09_git_lex_functional_fit.py` | 486 | 11 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 60 | `scripts/smoke-m002-text-to-cypher-pyo3.py` | 454 | 13 | 2 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 61 | `scripts/smoke-s04-falkordb-capabilities.py` | 1784 | 43 | 4 | no | migrate logic | high | new package seam required before wrapper thinning |
| 62 | `scripts/smoke-s05-odt-parser.py` | 652 | 29 | 0 | no | migrate logic | high | new package seam required before wrapper thinning |
| 63 | `scripts/smoke-s09-local-embeddings.py` | 564 | 28 | 2 | yes | migrate logic | high | S05 extracted shared local embedding proof environment helpers; wrapper still owns S09 smoke/encode semantics |
| 64 | `scripts/source_cli.py` | 207 | 11 | 0 | no | deferred | medium | needs manual review after high-priority migrations |
| 65 | `scripts/source_hypothesis_verifier.py` | 318 | 16 | 1 | no | deferred | medium | needs manual review after high-priority migrations |
| 66 | `scripts/source_lifecycle.py` | 2259 | 80 | 3 | no | migrate logic | high | new package seam required before wrapper thinning |
| 67 | `scripts/validate-parser-records.py` | 559 | 19 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 68 | `scripts/verify-acp-ci-contract.py` | 189 | 8 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 69 | `scripts/verify-acp-records.py` | 387 | 18 | 2 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 70 | `scripts/verify-acp-schema-extension-fixtures.py` | 289 | 13 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 71 | `scripts/verify-adr-conformance.py` | 412 | 12 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 72 | `scripts/verify-architecture-graph.py` | 1670 | 77 | 5 | no | migrate logic | high | new package seam required before wrapper thinning |
| 73 | `scripts/verify-evidence-span-golden-retrieval-cases.py` | 363 | 14 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 74 | `scripts/verify-evidence-span-local-retrieval-metrics.py` | 380 | 15 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 75 | `scripts/verify-falkordb-bulk-loader-proof.py` | 420 | 23 | 3 | no | migrate logic | high | new package seam required before wrapper thinning |
| 76 | `scripts/verify-falkordb-csv-ingest-proof.py` | 309 | 22 | 3 | yes | proof runtime wrapper | medium | retain proof wrapper, extract only reusable helpers if still large |
| 77 | `scripts/verify-falkordb-pack.py` | 173 | 6 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 78 | `scripts/verify-falkordb-skill.py` | 252 | 10 | 0 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 79 | `scripts/verify-graph-filtered-retrieval-integration.py` | 598 | 33 | 4 | no | migrate logic | high | new package seam required before wrapper thinning |
| 80 | `scripts/verify-held-out-semantic-descriptor-ablation.py` | 243 | 12 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 81 | `scripts/verify-held-out-semantic-descriptor-inputs.py` | 398 | 12 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 82 | `scripts/verify-held-out-semantic-descriptor-scoring.py` | 421 | 19 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 83 | `scripts/verify-independent-structural-signal-inputs.py` | 403 | 13 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 84 | `scripts/verify-independent-structural-signal-scoring.py` | 456 | 20 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 85 | `scripts/verify-local-retrieval-quality-benchmark.py` | 393 | 15 | 0 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 86 | `scripts/verify-m002-cypher-safety-contract.py` | 531 | 28 | 2 | no | migrate logic | high | new package seam required before wrapper thinning |
| 87 | `scripts/verify-m002-s04-recommendation.py` | 286 | 15 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 88 | `scripts/verify-m003-s01-minimax-baseline.py` | 285 | 14 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 89 | `scripts/verify-m003-s02-minimax-pyo3-endpoint.py` | 301 | 15 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 90 | `scripts/verify-m003-s03-reasoning-safe-candidate.py` | 422 | 20 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 91 | `scripts/verify-m003-s04-validation-readonly-execution.py` | 444 | 20 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 92 | `scripts/verify-m003-s05-r017-recommendation.py` | 406 | 23 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 93 | `scripts/verify-m049-binding.py` | 328 | 18 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 94 | `scripts/verify-m051-s08-acp-ontology-prototype.py` | 226 | 8 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 95 | `scripts/verify-m056-acp-kit.py` | 326 | 16 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 96 | `scripts/verify-m061-s04-overlay-runtime.py` | 983 | 32 | 2 | no | migrate logic | high | new package seam required before wrapper thinning |
| 97 | `scripts/verify-m063-l2-pilot.py` | 894 | 42 | 4 | no | migrate logic | high | new package seam required before wrapper thinning |
| 98 | `scripts/verify-m065-s01-install-contract.py` | 237 | 12 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 99 | `scripts/verify-m065-s02-release-install.py` | 326 | 11 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 100 | `scripts/verify-m065-s03-workflow-proof.py` | 302 | 12 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 101 | `scripts/verify-m065-s04-stage2-closure.py` | 334 | 12 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 102 | `scripts/verify-m065-s04-stage3-handoff.py` | 294 | 12 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 103 | `scripts/verify-m066-s01-adoption-contract.py` | 329 | 14 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 104 | `scripts/verify-m066-s02-main-repo-adoption.py` | 318 | 13 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 105 | `scripts/verify-m066-s03-stage3-closure.py` | 276 | 12 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 106 | `scripts/verify-m066-s03-stage4-handoff.py` | 199 | 11 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 107 | `scripts/verify-m067-s01-externalization.py` | 204 | 6 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 108 | `scripts/verify-m067-s02-profile-layer.py` | 168 | 10 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 109 | `scripts/verify-m067-s03-externalization-integrity.py` | 104 | 7 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 110 | `scripts/verify-materialized-descriptor-inputs.py` | 350 | 13 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 111 | `scripts/verify-materialized-descriptor-scoring.py` | 436 | 20 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 112 | `scripts/verify-observed-retrieval-output-metrics.py` | 365 | 16 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 113 | `scripts/verify-observed-retrieval-provenance.py` | 316 | 14 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 114 | `scripts/verify-offline-citation-retrieval-proof.py` | 313 | 14 | 0 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 115 | `scripts/verify-ontology-graphrag-integration-proof.py` | 368 | 13 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 116 | `scripts/verify-ontology-graphrag-proof.py` | 383 | 16 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 117 | `scripts/verify-ontology-graphrag-runtime-integration-proof.py` | 1083 | 41 | 2 | no | migrate logic | high | new package seam required before wrapper thinning |
| 118 | `scripts/verify-parser-evidence-span-materialization.py` | 303 | 10 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 119 | `scripts/verify-real-artifact-retrieval-proof.py` | 263 | 11 | 0 | yes | proof runtime wrapper | medium | S04 extracted shared retrieval proof helpers; wrapper and case-specific proof logic remain script-owned |
| 120 | `scripts/verify-representative-evidence-span-retrieval-corpus.py` | 332 | 13 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 121 | `scripts/verify-representative-evidence-span-retrieval-metrics.py` | 284 | 14 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 122 | `scripts/verify-representative-retrieval-runtime-benchmark.py` | 714 | 19 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 123 | `scripts/verify-retrieval-output-validator.py` | 234 | 9 | 0 | yes | proof runtime wrapper | medium | S04 extracted shared retrieval proof helpers; wrapper and validator-specific proof logic remain script-owned |
| 124 | `scripts/verify-s02-skills.py` | 484 | 11 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 125 | `scripts/verify-s03-reference-sources.py` | 282 | 11 | 2 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 126 | `scripts/verify-s04-falkordb-smoke.py` | 391 | 11 | 3 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 127 | `scripts/verify-s05-odt-parser.py` | 357 | 18 | 2 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 128 | `scripts/verify-s06-skill-refresh.py` | 260 | 8 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 129 | `scripts/verify-s08-final-report.py` | 457 | 19 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 130 | `scripts/verify-s09-local-embeddings.py` | 533 | 24 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 131 | `scripts/verify-s10-embedding-runtime-proof.py` | 493 | 23 | 2 | no | migrate logic | high | new package seam required before wrapper thinning |
| 132 | `scripts/verify-safe-structural-descriptor-remediation-inputs.py` | 390 | 13 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 133 | `scripts/verify-safe-structural-descriptor-remediation-scoring.py` | 438 | 20 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |
| 134 | `scripts/verify-semantic-descriptor-inputs.py` | 334 | 11 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 135 | `scripts/verify-semantic-descriptor-scoring.py` | 435 | 20 | 1 | yes | proof runtime wrapper | medium | retain proof wrapper, extract only reusable helpers if still large |
| 136 | `scripts/verify-semantic-observed-retrieval-scoring.py` | 386 | 18 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 137 | `scripts/verify-semantic-retrieval-safe-inputs.py` | 298 | 9 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 138 | `scripts/verify-source-record-cardinality-signal-inputs.py` | 447 | 14 | 1 | no | proof runtime wrapper | medium | retain runtime proof entrypoint, review helper extraction |
| 139 | `scripts/verify-source-record-cardinality-signal-scoring.py` | 471 | 20 | 1 | no | migrate logic | high | new package seam required before wrapper thinning |

## Type debt seed list

The planning-only `basedpyright scripts` run found errors in at least these script clusters and should guide S06 after extraction slices reduce false positives from embedded reusable logic:

- `scripts/build-architecture-graph.py`
- `scripts/build-consultant-hierarchy-records.py`
- `scripts/evaluate-parser-golden-cases.py`
- `scripts/generate-architecture-views.py`
- `scripts/parser_records.py`
- `scripts/prove-m003-s01-minimax-baseline.py`
- `scripts/prove-m003-s03-reasoning-safe-candidate.py`
- `scripts/run-s10-gigaembeddings-proof.py`
- `scripts/run-s10-user-bge-m3-proof.py`
- `scripts/verify-acp-records.py`
- `scripts/verify-falkordb-bulk-loader-proof.py`
- `scripts/verify-falkordb-csv-ingest-proof.py`
- `scripts/verify-falkordb-skill.py`
- `scripts/verify-graph-filtered-retrieval-integration.py`
- `scripts/verify-local-retrieval-quality-benchmark.py`
- `scripts/verify-m003-s04-validation-readonly-execution.py`
- `scripts/verify-observed-retrieval-provenance.py`
- `scripts/verify-offline-citation-retrieval-proof.py`
- `scripts/verify-ontology-graphrag-integration-proof.py`
- `scripts/verify-ontology-graphrag-proof.py`

## Non-claims

This inventory does not prove legal correctness, parser completeness, retrieval quality, embedding model quality, generated query correctness, production FalkorDB readiness, safe script deletion, or ACP/git-lex projection authority. It is a migration planning artifact only.

## S01 result

Every current top-level Python script is represented exactly once. Later slices must use GitNexus impact/context before editing concrete symbols and must update this inventory or the final closure map when classifications change.

## S03 update

M078 S03 retired `scripts/build-representative-retrieval-corpus.py` after parity proof showed the canonical underscore builder command passes and the generated runtime handoff now points to `scripts/build_representative_retrieval_corpus_manifest.py --check`. The live inventory now covers 139 top-level scripts and has no remaining `retire candidate` row.
