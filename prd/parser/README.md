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

## Consumer boundary for S03/S04/S05

- S03 ODT parsing should emit `DocumentRecord` and `SourceBlockRecord` JSONL that validates with `uv run python scripts/validate-parser-records.py --kind <kind> <file>` and preserves `non_authoritative: true`.
- S04 Consultant WordML work may emit only `RelationCandidateRecord` candidate evidence until later validation upgrades or rejects individual candidates.
- S05 NetworkX staging may consume validated parser records as deterministic staging/debug inputs, not as product graph truth, legal authority, or FalkorDB runtime proof.
- All downstream consumers must preserve bounded excerpts/hashes and non-claims unless a later proof slice explicitly narrows one claim.

## Non-claims and boundary

This fixture and parser-record contract is non-authoritative. It does not claim parser completeness, legal correctness, product ETL readiness, or FalkorDB loading/runtime readiness. The Consultant WordML legal-authority non-claims mean the Consultant WordML XML fixture may only propose bounded relation-candidate evidence until later validation proves candidate relations.

Downstream parser, graph, or FalkorDB load work must preserve these non-claims in generated reports unless a later slice adds explicit proof for a narrower claim.
