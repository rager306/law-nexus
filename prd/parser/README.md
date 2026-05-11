# Parser Fixture Contract

This directory contains the canonical source-fixture inventory for M006 parser and graph staging work. Future parser slices should inspect the machine-readable manifest first and should not glob `law-source/` directly when choosing source paths.

## Canonical artifacts

- Manifest: `prd/parser/source_fixture_inventory.json`
- Human report: `prd/parser/source_fixture_inventory.md`
- Generator/check command: `uv run python scripts/inventory-parser-fixtures.py --check`
- Full S01 verification: `uv run python scripts/inventory-parser-fixtures.py --check && uv run pytest -q tests/test_parser_fixture_inventory.py`

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

## Non-claims and boundary

This fixture contract is non-authoritative. It does not claim parser completeness, legal correctness, product ETL readiness, or FalkorDB product runtime readiness. The Consultant WordML XML fixture may only propose bounded relation-candidate evidence until later validation proves candidate relations.

Downstream parser, graph, or FalkorDB load work must preserve these non-claims in generated reports unless a later slice adds explicit proof for a narrower claim.
