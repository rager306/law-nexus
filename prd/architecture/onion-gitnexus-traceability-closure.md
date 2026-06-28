# Onion GitNexus Traceability Closure

**Milestone:** M076-f3zxm8  
**Slice:** S22  
**Status:** [bounded] traceability closure artifact  
**Depends on:** S05, S12, S17, S21  
**Decision:** M076 closes with representative GitNexus addressability and boundary checks, not exhaustive proof over every historical script or legal source file.

## Purpose

This artifact closes the M076 onion migration program from a traceability perspective. It records representative GitNexus-addressable symbols, wrapper lookup rules, known index limits, and non-claim boundaries so future work can continue from stable evidence instead of re-discovering the migration map.

## Closure scope

S22 proves that representative M076 package, wrapper, and test surfaces are traceable in GitNexus and backed by static validators. It does not change runtime behavior. It does not delete scripts. It does not claim the full repository has been exhaustively modeled by GitNexus.

## Representative GitNexus addressability matrix

| Concern | Representative symbol or file-qualified UID | GitNexus result | Closure meaning |
|---|---|---:|---|
| Parser fixture inventory use case | `Class:src/law_nexus/application/parser_inventory.py:ParserInventoryUseCase` | exact | Parser inventory logic is addressable as application code. |
| Representative corpus manifest builder | `Class:src/law_nexus/application/representative_corpus_manifest.py:RepresentativeCorpusManifestBuilder` | exact | S12/S20 manifest seam is addressable. |
| Local embedding adapter boundary | `Class:src/law_nexus/adapters/embeddings/local_sentence_transformer.py:LocalSentenceTransformerEmbedder` | exact | S17 local/open-weight adapter seam is addressable. |
| Generated Cypher safety policy | `Class:src/law_nexus/application/generated_cypher_policy.py:GeneratedCypherPolicy` | exact | S16 static generated-query rejection policy is addressable. |
| Graph store port contract | `Class:src/law_nexus/ports/graph_store.py:GraphStore` | exact | S14 graph-store boundary is addressable as a port, not a production FalkorDB proof. |
| S20 shared CLI report writer | `Function:src/law_nexus/adapters/cli/runtime.py:write_json_report` | exact | S20 deterministic CLI utility seam is addressable. |
| S21 retirement guardrail validator | `Function:tests/test_script_retirement_candidates_review.py:test_script_retirement_review_blocks_premature_deletion` | exact | The no-premature-script-deletion guardrail is traceable. |
| FalkorDB CSV proof wrapper main | `Function:scripts/verify-falkordb-csv-ingest-proof.py:main` | exact | The runtime/proof wrapper remains traceable and is not retired by M076. |
| Representative manifest wrapper main | `Function:scripts/build_representative_retrieval_corpus_manifest.py:main` | exact | The stable CLI wrapper remains traceable while internals live in package code. |
| ACP backend wrapper normalization | `Function:scripts/acp_git_lex_backend.py:normalize_wrapper_record` | exact | ACP/git-lex wrapper diagnostics are traceable but remain derived/non-authoritative. |

## Slice-to-traceability closure

| Slice group | Closure evidence | Boundary retained |
|---|---|---|
| S02/S04 parser inventory and source hierarchy | Application/package symbols are addressable; CLI compatibility remains guarded by tests. | Parser source wrappers remain stable compatibility surfaces. |
| S05 parser source CLI compatibility | S22 points to wrapper-first traceability rather than deleting scripts. | CLI outputs and compatibility checks remain authoritative for current users. |
| S12 representative corpus manifest | Builder and wrapper main are GitNexus-addressable. | Manifest shape is validated; retrieval quality is not claimed. |
| S14/S15 graph and FalkorDB CSV seams | `GraphStore` and CSV proof wrapper are addressable. | Port contract and proof wrapper do not claim production FalkorDB readiness. |
| S16 generated Cypher safety | `GeneratedCypherPolicy` is addressable. | Static rejection policy only; no generated-query correctness proof. |
| S17 local embedding adapter | Local sentence-transformer adapter is addressable. | No managed GigaChat/GigaChat API path and no embedding quality proof. |
| S18/S19 governance and ACP projection review | ACP projection artifacts remain diagnostic/recovery surfaces. | ACP/git-lex/RDF/SPARQL/JSON-LD are not requirement-validation proof. |
| S20 shared CLI utilities | CLI utility functions are addressable. | Live FalkorDB orchestration remains script-owned. |
| S21 script retirement review | Static validator and review artifact are addressable. | No scripts are retired in M076. |

## GitNexus operational rules

1. Use repo name `law-nexus` for GitNexus tools.
2. Reindex with `gitnexus analyze --force --name law-nexus`.
3. Use file-qualified UIDs for ambiguous symbols such as `main`, `run`, `validate`, and script-local helpers.
4. Run `gitnexus_detect_changes(repo="law-nexus", scope="all")` before commit/closeout checks.
5. Large legal source files may be skipped by the default GitNexus file-size cap; that is an index boundary, not evidence that source parsing is complete or incomplete.
6. GitNexus addressability is navigation and traceability evidence, not product validation proof.

## Required validators after M076

These validators form the minimum traceability safety net for future onion work:

- `uv run pytest tests/test_parser_source_cli_compatibility.py -q`
- `uv run pytest tests/test_representative_corpus_manifest_use_case.py -q`
- `uv run pytest tests/test_local_embedding_adapter.py -q`
- `uv run pytest tests/test_generated_cypher_policy.py -q`
- `uv run pytest tests/test_cli_runtime_utilities.py -q`
- `uv run pytest tests/test_script_retirement_candidates_review.py -q`
- `uv run pytest tests/test_onion_gitnexus_traceability_closure.py -q`

## Milestone validation handoff

M076 validation should treat this artifact as a traceability closure checklist. It may support a milestone-level pass only for the migration program's structural goals: package seams, wrappers, validators, and GitNexus-addressable evidence. It must not be used to validate legal correctness, parser completeness, retrieval quality, model quality, production FalkorDB readiness, or ACP/git-lex authority.

## Non-claims

This closure does not prove:

- Exhaustive GitNexus coverage of every repository symbol.
- Full CLI completeness across all 140 top-level scripts.
- Safe script deletion.
- Legal correctness or authoritative legal advice.
- Consultant/Garant parser completeness.
- Retrieval answer faithfulness or quality.
- Embedding model availability or quality.
- Generated Cypher query correctness.
- Production FalkorDB readiness.
- ACP/git-lex/RDF/SPARQL/JSON-LD projection authority.

## Result

M076 has a bounded traceability closure: representative package and wrapper seams are GitNexus-addressable, static validators pin the migration boundaries, and future work has explicit guardrails for script retirement and proof-level claims.
