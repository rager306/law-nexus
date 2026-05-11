# Parser Fixture Contract

This directory contains the canonical source-fixture inventory for M006 parser and graph staging work. Future parser slices should inspect the machine-readable manifest first and should not glob `law-source/` directly when choosing source paths.

## Canonical artifacts

- Manifest: `prd/parser/source_fixture_inventory.json`
- Human report: `prd/parser/source_fixture_inventory.md`
- Fixture generator/check command: `uv run python scripts/inventory-parser-fixtures.py --check`
- Parser record schema/example/report generator: `uv run python scripts/validate-parser-records.py --write`
- Parser record contract check: `uv run python scripts/validate-parser-records.py --check`
- Full S01 fixture verification: `uv run python scripts/inventory-parser-fixtures.py --check && uv run pytest -q tests/test_parser_fixture_inventory.py`
- Full S02 parser-record verification: `uv run python scripts/validate-parser-records.py --check && test -s prd/parser/schemas/parser_record.schema.json && test -s prd/parser/parser_record_contract.md`
- ODT smoke artifact generator/check command: `uv run python scripts/build-odt-smoke-records.py --check`
- ODT smoke document validation: `uv run python scripts/validate-parser-records.py --kind document prd/parser/odt_document_records.jsonl`
- ODT smoke source-block validation: `uv run python scripts/validate-parser-records.py --kind source_block prd/parser/odt_source_block_records.jsonl`

## Canonical source paths

| Path | Source kind | Contract |
|---|---|---|
| `law-source/garant/44-fz.odt` | `garant-odt` | Canonical ODT document fixture with valid ZIP, `content.xml`, and `meta.xml` shape diagnostics in the manifest. |
| `law-source/garant/PP_60_27-01-2022.odt` | `garant-odt` | Canonical observed PP fixture. The earlier stated filename `law-source/garant/PP_60_27-02-2022.odt` is documented as a mismatch and must not silently reappear. |
| `law-source/consultant/Список документов (5).xml` | `consultant-wordml-xml` | Canonical Consultant WordML relation fixture / prior-art evidence source. It is not an authoritative legal source. |

## Removed duplicate status

- Removed duplicate path: `law-source/Список документов (5).xml`
- Canonical replacement: `law-source/consultant/Список документов (5).xml`
- Classification: `removed-root-level-byte-identical-duplicate-must-remain-absent`
- The inventory fails if the duplicate reappears, and the manifest records any such path under `fixture_hygiene.unexpected_duplicate_paths`.

## Parser record contract artifacts

Generated parser record artifacts live alongside the fixture inventory and are checked by `scripts/validate-parser-records.py`.

| Path | Contract |
|---|---|
| `prd/parser/schemas/document_record.schema.json` | Strict JSON Schema for `DocumentRecord`; rejects unexpected properties and requires provenance/non-claim fields. |
| `prd/parser/schemas/source_block_record.schema.json` | Strict JSON Schema for `SourceBlockRecord`; ODT examples must remain `content.xml`-scoped with bounded excerpts and hashes. |
| `prd/parser/schemas/relation_candidate_record.schema.json` | Strict JSON Schema for candidate-only `RelationCandidateRecord`; no authoritative/product-ready statuses are valid. |
| `prd/parser/schemas/parser_record.schema.json` | Discriminated union schema over `record_kind`. |
| `prd/parser/examples/document_records.jsonl` | Positive document examples seeded only from canonical manifest paths and hashes. |
| `prd/parser/examples/source_block_records.jsonl` | Positive source-block examples with bounded placeholder excerpts, not legal evidence. |
| `prd/parser/examples/relation_candidate_records.jsonl` | Positive relation-candidate examples using the Consultant WordML fixture as prior-art/candidate evidence only. |
| `prd/parser/parser_record_contract.md` | Human-readable contract report, CLI usage, downstream notes, diagnostics, and explicit non-claims. |

## ODT smoke parser artifacts

S03 adds deterministic smoke artifacts for only the two canonical Garant ODT fixtures. The generator reads raw `content.xml` heading/paragraph traversal order, emits bounded `DocumentRecord` and `SourceBlockRecord` JSONL that validates against the S02 parser-record CLI, and writes a compact JSON/Markdown report with schema version, generator name, status, cap, per-document raw/emitted counts, source hashes, table counts, truncation state, first/last emitted excerpt hashes, non-claims, and artifact freshness diagnostics.

| Path | Contract |
|---|---|
| `prd/parser/odt_document_records.jsonl` | S02-valid non-authoritative `DocumentRecord` rows for the canonical Garant ODT documents. |
| `prd/parser/odt_source_block_records.jsonl` | S02-valid non-authoritative `SourceBlockRecord` rows capped per document and ordered by raw `content.xml` selectors. |
| `prd/parser/odt_smoke_records.json` | Machine-readable S03 report for downstream staging/debug checks, including stale-artifact diagnostics from `--check`. |
| `prd/parser/odt_smoke_records.md` | Human-readable S03 report with the same bounded counts, hashes, truncation, and non-claim boundaries. |

S03 advances only the ODT portion of R031 by proving that the canonical Garant ODT fixtures can produce deterministic, bounded parser-record smoke artifacts. It does not prove parser completeness, legal correctness, product ETL readiness, FalkorDB readiness, legal answer generation, or citation-safe retrieval. S05 may consume these validated records as NetworkX/FalkorDB staging/debug inputs, but S05 still owns graph compatibility proof and any later narrowing of these non-claims.

## Consultant WordML relation candidate artifacts

S04 adds deterministic Consultant WordML relation-candidate artifacts for future S05 consumers. These artifacts are generated only from the canonical prior-art fixture `law-source/consultant/Список документов (5).xml`; future consumers should use the tracked outputs below instead of reparsing or globbing Consultant XML directly.

| Path | Contract |
|---|---|
| `prd/parser/consultant_relation_candidates.jsonl` | S02-valid `RelationCandidateRecord` JSONL with candidate-level status and bounded evidence excerpts/hashes. |
| `prd/parser/consultant_relation_candidates.json` | Machine-readable S04 report with status, candidate count, artifact freshness, diagnostics, and `non_authoritative`. |
| `prd/parser/consultant_relation_candidates.md` | Human-readable S04 report with the same current fixture result, artifact freshness state, diagnostics, and non-claim boundaries. |

S04 commands:

- Generate/update artifacts: `uv run python scripts/build-consultant-relation-candidates.py --write`
- Check tracked artifact freshness: `uv run python scripts/build-consultant-relation-candidates.py --check`
- Validate relation-candidate JSONL: `uv run python scripts/validate-parser-records.py --kind relation_candidate prd/parser/consultant_relation_candidates.jsonl`

Current fixture result: the canonical Consultant WordML fixture currently yields one candidate relation record preserving `LAW:179581@11.05.2026` as `consultant:LAW:179581@11.05.2026`. No ODT endpoint match is asserted or fabricated in S04; S04 does not assert that the Consultant WordML target is authoritative legal evidence, and does not resolve this candidate to S03 ODT `DocumentRecord` identifiers; endpoint matching to S03 ODT document IDs is deferred to S05.

S04 remains non-authoritative. It does not claim parser completeness, legal correctness, product ETL readiness, FalkorDB product runtime readiness, FalkorDB loading/runtime readiness, Consultant WordML legal authority, relation correctness, NetworkX graph invariants, ODT endpoint resolution, or product graph truth.

## NetworkX parser staging graph artifacts

S05 adds deterministic NetworkX `MultiDiGraph` staging/debug reports over the S02-valid S03 ODT records and S04 Consultant relation candidates. The builder preserves keyed relation-candidate edges, emits unresolved-reference nodes instead of rewriting Consultant references into ODT document IDs, and reports graph invariant diagnostics before any later FalkorDB load-shape work.

| Path | Contract |
|---|---|
| `prd/parser/parser_staging_graph.json` | Machine-readable S05 report with status, artifact freshness, `document_count`, `source_block_count`, `relation_candidate_count`, keyed relation edge IDs, unresolved endpoints, diagnostics, and explicit non-claims. |
| `prd/parser/parser_staging_graph.md` | Human-readable S05 report with bounded counts, current warning set, R031 scope, future FalkorDB load-shape notes, and non-authoritative boundaries. |

S05 commands:

- Generate/update reports: `uv run python scripts/build-parser-staging-graph.py --write`
- Check tracked report freshness and graph invariant status: `uv run python scripts/build-parser-staging-graph.py --check`
- Full S05 closure chain: `uv run python scripts/inventory-parser-fixtures.py --check && uv run python scripts/validate-parser-records.py --check && uv run python scripts/build-odt-smoke-records.py --check && uv run python scripts/build-consultant-relation-candidates.py --check && uv run python scripts/build-parser-staging-graph.py --check && uv run pytest -q tests/test_parser_staging_graph.py tests/test_parser_records.py tests/test_validate_parser_records_cli.py tests/test_odt_smoke_records.py tests/test_consultant_relation_candidates.py && uv run ruff check scripts/build-parser-staging-graph.py tests/test_parser_staging_graph.py`

Current canonical S05 result: `document_count=2`, `source_block_count=48`, `relation_candidate_count=1`, keyed relation edge `REL-CONS-0001`, and zero graph-build errors. The current warning set is expected: unresolved Consultant subject/object references and missing Consultant source-block provenance remain warnings so the keyed relation candidate stays visible without asserting relation correctness.

S05 advances R031 only for deterministic NetworkX `MultiDiGraph` staging invariants over the current validated parser-record artifacts. It does not claim parser completeness, legal correctness, product ETL readiness, FalkorDB loading/runtime readiness, relation correctness, legal answer generation, citation-safe retrieval, or product graph truth.

## Consumer boundary for S03/S04/S05

- S03 ODT parsing should emit `DocumentRecord` and `SourceBlockRecord` JSONL that validates with `uv run python scripts/validate-parser-records.py --kind <kind> <file>` and preserves `non_authoritative: true`.
- S04 Consultant WordML work may emit only `RelationCandidateRecord` candidate evidence until later validation upgrades or rejects individual candidates.
- S05 NetworkX staging may consume validated parser records as deterministic staging/debug inputs, not as product graph truth, legal authority, or FalkorDB runtime proof.
- Later FalkorDB load-shape work may use the S05 node/edge kinds, keyed relation edge IDs, and path/rule-qualified diagnostics as a staging contract, but must run its own loading/runtime proof before narrowing the FalkorDB loading/runtime readiness non-claim.
- All downstream consumers must preserve bounded excerpts/hashes and non-claims unless a later proof slice explicitly narrows one claim.

## Non-claims and boundary

This fixture and parser-record contract is non-authoritative. It does not claim parser completeness, legal correctness, product ETL readiness, FalkorDB product runtime readiness, or FalkorDB loading/runtime readiness. The Consultant WordML legal-authority non-claims mean the Consultant WordML XML fixture may only propose bounded relation-candidate evidence until later validation proves candidate relations.

Downstream parser, graph, or FalkorDB load work must preserve these non-claims in generated reports unless a later slice adds explicit proof for a narrower claim.
