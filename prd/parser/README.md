# Parser Fixture Contract

This directory contains the canonical source-fixture inventory for M006 parser and graph staging work. Future parser slices should inspect the machine-readable manifest first and should not glob `law-source/` directly when choosing source paths.

## Canonical artifacts

- Manifest: `prd/parser/source_fixture_inventory.json`
- Human report: `prd/parser/source_fixture_inventory.md`
- Fixture generator/check command: `uv run python scripts/inventory-parser-fixtures.py --check`
- Parser record schema/example/report generator: `uv run python scripts/validate-parser-records.py --write`
- Parser record contract check: `uv run python scripts/validate-parser-records.py --check`
- Golden-test contract term check: `rg -n "evidence-present|no-answer|candidate-only|unresolved-reference|non-authoritative|parser completeness|retrieval quality|legal-answer correctness" prd/parser/golden_test_contract.md`
- Golden-case generator/check command: `uv run python scripts/build-parser-golden-cases.py --check`
- Full S01 fixture verification: `uv run python scripts/inventory-parser-fixtures.py --check && uv run pytest -q tests/test_parser_fixture_inventory.py`
- Full S02 parser-record verification: `uv run python scripts/validate-parser-records.py --check && test -s prd/parser/schemas/parser_record.schema.json && test -s prd/parser/parser_record_contract.md`
- ODT smoke artifact generator/check command: `uv run python scripts/build-odt-smoke-records.py --check`
- ODT smoke document validation: `uv run python scripts/validate-parser-records.py --kind document prd/parser/odt_document_records.jsonl`
- ODT smoke source-block validation: `uv run python scripts/validate-parser-records.py --kind source_block prd/parser/odt_source_block_records.jsonl`

## Source priority for M009

M009 treats Consultant Plus WordML as the primary source contract for full normative-act source-shape evidence. The canonical full-act fixture is `law-source/consultant/44-FZ-2026.xml`, and the canonical Consultant document-list fixture remains prior-art relation evidence only. Garant ODT work is lower-priority/deferred from M009; earlier ODT smoke/parser-record artifacts remain bounded evidence surfaces and must not be read as M009 multi-source readiness.

The tracked inventory and prior-art reports expose hashes, shape diagnostics, missing-file/hash-drift diagnostics, source-priority notes, and explicit non-claims. Passing checks do not claim parser completeness, legal correctness, Consultant WordML legal authority, product ETL readiness, FalkorDB loading/runtime readiness, citation-safe retrieval readiness, or multi-source parser readiness.

## Canonical source paths

| Path | Source kind | Contract |
|---|---|---|
| `law-source/garant/44-fz.odt` | `garant-odt` | Deferred/lower-priority M009 fixture retained from earlier ODT work with valid ZIP, `content.xml`, and `meta.xml` shape diagnostics in the manifest; not M009 source priority. |
| `law-source/garant/PP_60_27-01-2022.odt` | `garant-odt` | Deferred/lower-priority M009 PP fixture retained from earlier ODT work. The earlier stated filename `law-source/garant/PP_60_27-02-2022.odt` is documented as a mismatch and must not silently reappear. |
| `law-source/consultant/Список документов (5).xml` | `consultant-wordml-xml` | Canonical Consultant WordML relation fixture / prior-art evidence source. It is not an authoritative legal source. |
| `law-source/consultant/44-FZ-2026.xml` | `consultant-wordml-xml` | M009 primary Consultant Plus full normative-act WordML source-shape fixture. It is a hash/shape anchor only and does not prove parsed legal semantics, parser completeness, or multi-source readiness. |

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
| `prd/parser/schemas/consultant_hierarchy_record.schema.json` | Strict JSON Schema for `ConsultantHierarchyRecord`; Consultant WordML hierarchy/source records must preserve stable IDs, parent references, level enum, marker metadata, source hashes, excerpt hashes, and non-authoritative non-claims. |
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

## Parser/retrieval golden-test contract

M008 adds `prd/parser/golden_test_contract.md` as the static contract for future parser/retrieval golden tests over tracked M006 parser artifacts and R032. The contract defines the allowed case classes (`evidence-present`, `no-answer`, `candidate-only`, `unresolved-reference`, and `non-authoritative`), required evaluator result/diagnostic fields, source-anchor rules, allowed non-claims, and explicit out-of-scope claims. It is implementation-ready for later executable tests, but it does not itself prove parser completeness, retrieval quality, legal-answer correctness, citation-safe retrieval, product ETL readiness, or FalkorDB loading/runtime readiness.

## Parser golden-case artifacts

S02 adds deterministic generated golden-case artifacts for future S03 evaluator work. The generator consumes only tracked M006 parser artifacts under `prd/parser/` and the static golden-test contract; future agents should use these tracked outputs instead of rescanning `law-source/`, reparsing raw ODT/XML fixtures, or globbing source directories to assemble golden tests.

| Path | Contract |
|---|---|
| `prd/parser/golden_cases.json` | Machine-readable S02 report with `status`, `artifact_freshness`, `case_count`, `case_class_counts`, `source_artifacts`, `stale_paths`, source anchors, blocked claims, and S01-shaped diagnostics. |
| `prd/parser/golden_cases.md` | Human-readable S02 report exposing case inventory, source anchors, source artifact hashes, diagnostics, and explicit non-claim boundaries. |

S02 commands:

- Generate/update artifacts: `uv run python scripts/build-parser-golden-cases.py --write`
- Check tracked artifact freshness: `uv run python scripts/build-parser-golden-cases.py --check`
- Full bounded parser/golden verification: `uv run python scripts/validate-parser-records.py --check && uv run python scripts/build-odt-smoke-records.py --check && uv run python scripts/build-consultant-relation-candidates.py --check && uv run python scripts/build-parser-staging-graph.py --check && uv run python scripts/build-parser-golden-cases.py --check && uv run pytest -q tests/test_parser_golden_contract.py tests/test_parser_golden_cases.py && uv run ruff check scripts/build-parser-golden-cases.py tests/test_parser_golden_cases.py`

Current canonical S02 golden-case result: five bounded cases, one for each allowed class (`evidence-present`, `no-answer`, `candidate-only`, `unresolved-reference`, and `non-authoritative`). These artifacts are evaluator inputs only. A passing golden-case check does not claim parser completeness, retrieval quality, legal-answer correctness, citation-safe retrieval readiness, product ETL readiness, FalkorDB loading/runtime readiness, Consultant WordML legal authority, relation correctness, or product graph truth.

## Parser golden-case evaluator

S03 adds an executable evaluator for the tracked golden cases. Use `uv run python scripts/build-parser-golden-cases.py --check` first to verify that `prd/parser/golden_cases.json` is fresh against the tracked parser artifacts, then use `uv run python scripts/evaluate-parser-golden-cases.py --check` to evaluate the bounded case outcomes against those artifacts.

The evaluator reads only tracked local inputs under `prd/parser/`: `golden_cases.json`, `odt_document_records.jsonl`, `odt_source_block_records.jsonl`, `consultant_relation_candidates.jsonl`, and `parser_staging_graph.json`. It does not rescan raw legal sources, call FalkorDB, invoke an LLM, use embeddings, or require network access.

`evaluate-parser-golden-cases.py --check` prints compact JSON diagnostics to stdout for agent/operator inspection. The report includes `status`, `case_count`, `evaluated_case_count`, `severity_counts`, `blocked_claims`, `non_authoritative`, and path-qualified `diagnostics[]` entries with `case_id`, `case_class`, `rule`, `artifact_path`, `expected_state`, `actual_state`, and `message` fields. Diagnostics use record ids, paths, hashes, statuses, and bounded excerpts already present in tracked artifacts; they must not print raw full legal text.

Current canonical S03 evaluator scope: it verifies the required evidence-present, no-answer, candidate-only, unresolved-reference, and non-authoritative outcomes for the current tracked M006/S02 parser artifacts. A passing evaluator run does not claim product retrieval readiness, citation-safe answer readiness, parser completeness, relation correctness, FalkorDB runtime readiness, legal-answer correctness, Consultant WordML legal authority, or product graph truth.

## Parser golden-test closure proof and S04 handoff

S04 closes the M008/R032 golden-test proof chain with `prd/parser/golden_test_proof_report.md`, a cold-reader inspection surface over the tracked parser golden-case artifacts and executable local checks. Use it as the handoff report that records the current command evidence, observed public evaluator fields, required case coverage, blocked claims, and downstream limitations without echoing raw full legal text or introducing runtime/network dependencies.

Final bounded command chain:

```bash
uv run python scripts/validate-parser-records.py --check
uv run python scripts/build-odt-smoke-records.py --check
uv run python scripts/build-consultant-relation-candidates.py --check
uv run python scripts/build-parser-staging-graph.py --check
uv run python scripts/build-parser-golden-cases.py --check
uv run python scripts/evaluate-parser-golden-cases.py --check
uv run pytest -q tests/test_parser_golden_contract.py tests/test_parser_golden_cases.py tests/test_parser_golden_evaluator.py tests/test_parser_golden_proof_report.py
uv run ruff check tests/test_parser_golden_proof_report.py
```

The three golden-test surfaces are intentionally separate:

- Generator freshness: `uv run python scripts/build-parser-golden-cases.py --check` verifies that `prd/parser/golden_cases.json` and `prd/parser/golden_cases.md` are fresh against the tracked parser artifacts and golden-test contract.
- Evaluator behavior: `uv run python scripts/evaluate-parser-golden-cases.py --check` evaluates the bounded `evidence-present`, `no-answer`, `candidate-only`, `unresolved-reference`, and `non-authoritative` cases and emits compact JSON diagnostics with path-qualified artifact references.
- Closure proof/handoff: `prd/parser/golden_test_proof_report.md` summarizes the passing command evidence, case coverage, blocked claims, and limitations for cold-reader M008/R032 closure review.

S04/R032 validation is bounded to executable golden tests over tracked artifacts. It does not validate parser completeness, product retrieval quality, citation-safe retrieval readiness, legal-answer correctness, relation correctness, Consultant WordML legal authority, FalkorDB loading/runtime readiness, product ETL readiness, or product graph truth. R031 remains the separate M006 parser proof/staging gate, R017 remains the separate Legal KnowQL/generated-Cypher proof gate, and future retrieval/product/FalkorDB work must provide its own proof before narrowing any of these non-claims.

## Consumer boundary for S03/S04/S05

- S03 ODT parsing should emit `DocumentRecord` and `SourceBlockRecord` JSONL that validates with `uv run python scripts/validate-parser-records.py --kind <kind> <file>` and preserves `non_authoritative: true`.
- S04 Consultant WordML work may emit only `RelationCandidateRecord` candidate evidence until later validation upgrades or rejects individual candidates.
- S05 NetworkX staging may consume validated parser records as deterministic staging/debug inputs, not as product graph truth, legal authority, or FalkorDB runtime proof.
- Later FalkorDB load-shape work may use the S05 node/edge kinds, keyed relation edge IDs, and path/rule-qualified diagnostics as a staging contract, but must run its own loading/runtime proof before narrowing the FalkorDB loading/runtime readiness non-claim.
- All downstream consumers must preserve bounded excerpts/hashes and non-claims unless a later proof slice explicitly narrows one claim.

## Non-claims and boundary

This fixture and parser-record contract is non-authoritative. It does not claim parser completeness, legal correctness, product ETL readiness, FalkorDB product runtime readiness, FalkorDB loading/runtime readiness, citation-safe retrieval readiness, or multi-source parser readiness. The Consultant Plus full-act WordML fixture is M009 primary only for full normative-act source-shape/hash evidence; it does not prove parsed legal semantics or Consultant WordML legal authority. The Consultant document-list WordML legal-authority non-claims mean the Consultant WordML XML fixture may only propose bounded relation-candidate evidence until later validation proves candidate relations. Garant ODT work is deferred/lower-priority from M009 and remains limited to earlier bounded ODT smoke/parser-record evidence.

Downstream parser, graph, or FalkorDB load work must preserve these non-claims in generated reports unless a later slice adds explicit proof for a narrower claim.
