# Script Retirement Candidates Review

**Milestone:** M076-f3zxm8  
**Slice:** S21  
**Status:** [bounded] retirement review artifact  
**Depends on:** `prd/architecture/onion-migration-contract.md`, `prd/architecture/acp-projection-helper-extraction-review.md`  
**Decision:** review now; retire later only under dedicated compatibility gates.

## Purpose

This review classifies script wrappers after the M076 wrapper-first migration and S20 shared CLI utility seam. It does not delete, rename, or retire any script. Scripts remain stable CLI/proof compatibility surfaces until downstream callers, tracked reports, tests, and GitNexus traceability confirm a safe migration path.

## Scope

S21 reviews the package-backed script wrappers that now import `law_nexus` modules. It does not classify all top-level scripts in `scripts/` because the repository has a large historical proof-script surface and many scripts remain active architecture, ACP, parser, retrieval, and FalkorDB proof commands.

## Classification labels

| Label | Meaning | Allowed action now |
|---|---|---|
| keep-wrapper | The script should remain as a stable CLI/proof surface. | Keep; may delegate more internals to package code later. |
| retire-later | The script may eventually be replaced by a package API or shared CLI entrypoint, but only after downstream callers and compatibility gates are migrated. | Keep now; open future migration task if needed. |
| do-not-retire | The script is a proof/runtime/safety surface that should remain script-owned unless a new architecture decision supersedes it. | Keep. |
| review-later | The script is package-backed but not enough evidence exists in S21 to classify it safely. | Keep; revisit with targeted discovery. |

## Candidate matrix

| Script | Package dependency | Classification | Required compatibility gate before any future retirement |
|---|---|---|---|
| `scripts/inventory-parser-fixtures.py` | `law_nexus.adapters.sources.filesystem_inventory`, `law_nexus.composition` | keep-wrapper | `tests/test_parser_source_cli_compatibility.py`; script `--check`; downstream parser inventory proof callers migrated. |
| `scripts/build-consultant-hierarchy-records.py` | `law_nexus.composition`, `law_nexus.ports.source_hierarchy` | keep-wrapper | Consultant hierarchy record tests and stale-output behavior reviewed; known artifact-freshness debt resolved before retirement. |
| `scripts/build-offline-citation-retrieval-cases.py` | `law_nexus.application.offline_retrieval_cases`, ports | keep-wrapper | Offline retrieval compatibility and stale-output behavior resolved; generated fixture ownership clarified. |
| `scripts/build-real-artifact-retrieval-cases.py` | `law_nexus.application.real_artifact_retrieval_cases`, ports | keep-wrapper | Real artifact retrieval compatibility and fixture freshness resolved. |
| `scripts/build_representative_retrieval_corpus_manifest.py` | representative corpus application/ports + S20 CLI utilities | retire-later | `tests/test_representative_corpus_manifest_use_case.py`; canonical `--check`; downstream references to script path migrated or wrapped. |
| `scripts/retrieval_output_validator.py` | citation-safe answer validator application | retire-later | `tests/test_citation_safe_answer_validator_use_case.py`; existing retrieval output validator tests; downstream CLI callers migrated. |
| `scripts/verify-falkordb-csv-ingest-proof.py` | FalkorDB CSV adapter + S20 CLI utilities | do-not-retire | Live runtime/container/no-write semantics preserved; `CSV_FILE_ACCESS_BLOCKED` blocked behavior retained; any retirement requires a dedicated runtime proof decision. |
| `scripts/verify-semantic-descriptor-scoring.py` | local sentence-transformers adapter | do-not-retire | Local model availability and runtime proof remain script-owned; no managed embedding API path introduced. |
| `scripts/acp_git_lex_backend.py` | ACP/git-lex backend wrapper mechanics | do-not-retire | ACP/git-lex projections remain non-authoritative; backend wrapper is diagnostic/runtime integration, not product source truth. |
| `scripts/verify-m051-s08-acp-ontology-prototype.py` | package import not classified by current inventory | review-later | Targeted ACP/generic-core/profile boundary review required. |
| `scripts/verify-m063-l2-pilot.py` | package import not classified by current inventory | review-later | Targeted pilot-runtime boundary review required. |
| `scripts/verify-m065-s03-workflow-proof.py` | package import not classified by current inventory | review-later | Targeted workflow proof boundary review required. |

## No-premature-deletion guardrails

No script may be deleted, renamed, or hidden from CLI users solely because reusable logic moved into `src/law_nexus`.

Before any future retirement:

1. Identify all tracked tests, reports, docs, and GitNexus flows that name the script path.
2. Provide a replacement CLI or documented package API.
3. Run the old and replacement paths against the same fixture inputs.
4. Preserve or explicitly migrate failure codes and bounded diagnostics.
5. Preserve non-claim language and proof-boundary wording.
6. Confirm `gitnexus_detect_changes(repo="law-nexus", scope="all")` reports only expected affected symbols/flows.
7. Record a decision if the script is a proof/runtime safety surface.

## Compatibility gates to keep

These gates must remain green while wrappers stay in place:

- `uv run pytest tests/test_parser_source_cli_compatibility.py -q`
- `uv run pytest tests/test_representative_corpus_manifest_use_case.py -q`
- `uv run python scripts/build_representative_retrieval_corpus_manifest.py --check`
- `uv run pytest tests/test_falkordb_csv_loader_adapter.py tests/test_falkordb_csv_ingest_proof.py -q`
- `uv run python scripts/verify-falkordb-csv-ingest-proof.py --container never --no-write` exits `1` with `CSV_FILE_ACCESS_BLOCKED`
- `uv run pytest tests/test_citation_safe_answer_validator_use_case.py -q`
- `uv run pytest tests/test_semantic_descriptor_scoring.py -q`

## GitNexus traceability notes

Exact GitNexus evidence used in S21:

- `Function:scripts/acp_git_lex_backend.py:normalize_wrapper_record` resolved exactly; upstream impact is LOW through the ACP backend main flow.
- `Function:scripts/build_representative_retrieval_corpus_manifest.py:main` upstream impact is LOW.
- `Function:scripts/verify-falkordb-csv-ingest-proof.py:main` upstream impact is LOW.
- The script inventory found package-backed wrappers importing `law_nexus` modules and a broader set of 140 top-level scripts.

Common script entrypoint names such as `main` require file-qualified GitNexus UIDs. Do not rely on bare-name lookups for retirement decisions.

## S22 handoff

S22 should use this review as a traceability checklist. The expected S22 work is to prove package/use-case symbols are GitNexus-addressable and that M076 wrapper migrations have clean detect/reindex evidence. S22 should not delete scripts unless a new explicit retirement plan is created.

## Non-claims

This review does not prove:

- Broad CLI completeness.
- External downstream caller migration.
- Parser completeness.
- Retrieval quality or answer faithfulness.
- Legal correctness or authoritative legal advice.
- FalkorDB production readiness.
- ACP/git-lex projection authority.
- Safe script deletion.
