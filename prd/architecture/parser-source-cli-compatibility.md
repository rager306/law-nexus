# Parser and Source CLI Compatibility Matrix

**Milestone:** M076-f3zxm8 / S05  
**Status:** bounded compatibility gate  
**Scope:** parser/source-related CLI surfaces after S02-S04 wrapper-first extraction

## Purpose

This matrix records which parser/source scripts are package-backed wrappers and
which remain script-owned proof surfaces. It is a compatibility artifact, not a
product validation artifact. A green command here does **not** validate legal
semantics, Garant ODT behavior, FalkorDB load readiness, citation correctness,
or parser completeness.

## Status vocabulary

- **package-backed wrapper**: the original CLI path remains stable and delegates
  migrated reusable logic to `src/law_nexus` through the package or composition
  root.
- **adapter-backed**: package adapter behavior is covered by tests, but there is
  no dedicated migrated CLI wrapper in this slice.
- **script-owned**: the script remains the source of implementation for this
  proof flow and is not migrated in M076 S02-S05.
- **known-debt**: the CLI/test surface has a documented non-green state or
  freshness mismatch that must not be smoothed into success.

## S02-S04 touched compatibility gates

| CLI or surface | Status | Package seam | Compatibility command | Expected result | Notes |
|---|---|---|---|---|---|
| `scripts/inventory-parser-fixtures.py --check` | package-backed wrapper | `ParserInventoryUseCase`, `FilesystemParserFixtureInventory`, `make_parser_inventory_use_case()` | `uv run python scripts/inventory-parser-fixtures.py --check` | exit `0`; JSON summary has `status: pass`, `fixture_count: 53`, `non_authoritative: true` | S02 wrapper-first extraction. |
| `src/law_nexus/adapters/parsers/consultant_wordml.py` | adapter-backed | `ConsultantWordMLParser`, `make_consultant_parser()` | `uv run pytest tests/test_consultant_wordml_adapter.py -q` | exit `0`; bounded adapter contract passes | S03 hardens document-level metadata only; no source hierarchy claim. |
| `scripts/build-consultant-hierarchy-records.py` | package-backed wrapper with known freshness debt | `SourceHierarchyUseCase`, `ConsultantHierarchyRecordBuilder`, `make_consultant_hierarchy_use_case()` | `uv run pytest tests/test_consultant_hierarchy_records.py tests/test_source_hierarchy_use_case.py -q`; `uv run python scripts/build-consultant-hierarchy-records.py --check` | tests exit `0`; `--check` JSON preserves counts `document=1`, `article=94`, `clause=997`, `fatal_error_count=0`; `--check` currently exits `1` because artifact freshness is false | S04 wrapper-first extraction. Do not treat freshness-false exit as parser failure unless S05+ chooses to refresh artifacts. |
| `tests/test_consultant_hierarchy_prior_art_comparison.py` | known-debt | none | `uv run pytest tests/test_consultant_hierarchy_prior_art_comparison.py -q` | currently `3 failed, 2 passed` | Debt existed before S05; remaining failures are `test_cli_check_reports_fresh_artifacts_without_blocking_on_needs_review`, `test_generator_build_is_deterministic_against_artifacts`, and `test_compare_blocks_major_structure_parent_breakage`. |

## Script-owned parser/source CLI surfaces

These commands remain script-owned proof surfaces after S05. They are not
package-backed wrappers yet and should not be described as migrated.

| Script | Status | Compatibility posture |
|---|---|---|
| `scripts/build-consultant-prior-art-expectations.py` | script-owned | Prior-art expectation builder; structural prior art only. |
| `scripts/build-consultant-relation-candidates.py` | script-owned | Relation candidate proof flow; no package seam in S02-S05. |
| `scripts/build-odt-smoke-records.py` | script-owned | ODT smoke record builder; does not validate full Garant parser behavior. |
| `scripts/build-parser-evidence-span-materialization.py` | script-owned | Evidence span materialization proof flow; future S09/S10 candidate. |
| `scripts/build-parser-golden-cases.py` | script-owned | Golden case builder; no package seam in S02-S05. |
| `scripts/build-parser-staging-graph.py` | script-owned | Parser staging graph proof flow; no package seam in S02-S05. |
| `scripts/build-source-id-uniqueness.py` | script-owned | Source id uniqueness proof flow; no package seam in S02-S05. |
| `scripts/build-source-record-cardinality-signal-inputs.py` | script-owned | Source record cardinality signal input builder; no package seam in S02-S05. |
| `scripts/compare-consultant-hierarchy-prior-art.py` | known-debt | Prior-art comparison surface has failing tests; not migrated. |
| `scripts/evaluate-parser-golden-cases.py` | script-owned | Golden case evaluator; no package seam in S02-S05. |
| `scripts/parser_records.py` | script-owned contract module | Script-side parser-record schema/validation utility; package code must not import it to avoid package-to-script dependency inversion. |
| `scripts/probe-consultant-parser.py` | script-owned | Consultant parser probe; no package seam in S02-S05. |
| `scripts/smoke-s05-odt-parser.py` | script-owned | ODT smoke proof surface; no full parser validation claim. |
| `scripts/source_cli.py` | script-owned | Source CLI helper surface; no package seam in S02-S05. |
| `scripts/source_hypothesis_verifier.py` | script-owned | Source hypothesis verification surface; no package seam in S02-S05. |
| `scripts/source_lifecycle.py` | script-owned | Source lifecycle proof/metadata surface; no package seam in S02-S05. |
| `scripts/validate-parser-records.py` | script-owned | Parser-record validation CLI; no package seam in S02-S05. |
| `scripts/verify-acp-records.py` | script-owned governance check | ACP/checkpoint governance surface, not parser product proof. |
| `scripts/verify-parser-evidence-span-materialization.py` | script-owned | Evidence span materialization verifier; future citation/retrieval candidate. |
| `scripts/verify-s03-reference-sources.py` | script-owned | Reference source proof verifier; no package seam in S02-S05. |
| `scripts/verify-s05-odt-parser.py` | script-owned | ODT parser verifier; bounded smoke only unless real-document proof is refreshed. |
| `scripts/verify-source-record-cardinality-signal-inputs.py` | script-owned | Cardinality signal input verifier; no package seam in S02-S05. |
| `scripts/verify-source-record-cardinality-signal-scoring.py` | script-owned | Cardinality signal scoring verifier; no package seam in S02-S05. |

## Required compatibility checks for S05 closeout

```bash
uv run python scripts/inventory-parser-fixtures.py --check
uv run pytest tests/test_consultant_wordml_adapter.py tests/test_parser_inventory_use_case.py -q
uv run pytest tests/test_consultant_hierarchy_records.py tests/test_source_hierarchy_use_case.py -q
uv run python scripts/build-consultant-hierarchy-records.py --check
uv run lint-imports
uv run basedpyright src/
```

For `build-consultant-hierarchy-records.py --check`, parse the JSON summary and
confirm the expected counts/fatal-error fields even when the command exits `1`
for existing `artifact_freshness: false`.

## Non-claims

- This matrix does not validate Russian legal correctness.
- This matrix does not validate Garant ODT parser completeness.
- This matrix does not validate FalkorDB import or graph runtime behavior.
- This matrix does not validate citation-safe retrieval answers.
- This matrix does not retire any script path.
