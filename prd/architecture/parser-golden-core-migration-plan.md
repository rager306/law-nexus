# Parser Golden Case Core Migration Plan

## Purpose

M079 moves the parser golden-case core engines from top-level scripts into package-owned adapter code. This follows M078, which extracted shared parser golden-case utility helpers into `law_nexus.adapters.sources.parser_golden_cases`.

The target state is:

- `scripts/build-parser-golden-cases.py` remains a CLI/report wrapper;
- `scripts/evaluate-parser-golden-cases.py` remains a CLI/report wrapper;
- reusable `build_cases` and `evaluate_cases` core behavior is package-owned;
- package code imports package-owned parser record contracts, not `scripts/`;
- generated artifact and `--check` behavior remains stable.

## Baseline gates

Current pre-migration gates passed:

```bash
uv run python scripts/build-parser-golden-cases.py --check
uv run python scripts/evaluate-parser-golden-cases.py --check
uv run pytest tests/test_parser_golden_cases_package.py tests/test_residual_script_migration_inventory.py tests/test_residual_script_migration_closure_map.py -q
uv run ruff check scripts
uv run basedpyright scripts
uv run lint-imports
```

Baseline results:

- targeted tests: 14 passed;
- full script ruff: pass;
- full script basedpyright: 0 errors, 0 warnings, 0 notes;
- import-linter: 4 contracts kept;
- build/evaluate `--check`: pass.

## GitNexus impact baseline

File-qualified GitNexus impact was run before source edits:

| Symbol | Risk | Notes |
|---|---:|---|
| `Function:scripts/build-parser-golden-cases.py:build_cases` | LOW | Upstream through `build_report` and script wrapper only. |
| `Function:scripts/build-parser-golden-cases.py:build_report` | LOW | Upstream through output/write/check/main wrapper flow. |
| `Function:scripts/evaluate-parser-golden-cases.py:evaluate_cases` | LOW | Upstream through `build_result` and script wrapper only. |
| `Function:scripts/evaluate-parser-golden-cases.py:build_result` | LOW | Upstream through evaluate script `main`. |

No HIGH or CRITICAL impact was reported.

## Package API target

Use the existing package module:

```text
law_nexus.adapters.sources.parser_golden_cases
```

Planned package-owned APIs:

```python
def build_cases_core(...): ...
def build_report_core(...): ...
def evaluate_cases_core(...): ...
def build_evaluation_result_core(...): ...
```

Names may be adjusted during implementation if the existing script contracts favor smaller compatibility wrappers. The architectural constraint is stable: package code must not import `scripts/` and must use `law_nexus.adapters.sources.parser_records` for record contracts/loaders.

## Migration waves

### S02 build core

Move build-case construction behavior first:

- package owns case construction/report payload behavior;
- build script delegates through compatibility wrappers;
- `build-parser-golden-cases.py --check` remains green;
- package tests prove representative core behavior and non-claims.

### S03 evaluate core

Move evaluator behavior after build core is stable:

- package owns evaluator status/diagnostic semantics;
- evaluate script delegates through compatibility wrappers;
- `evaluate-parser-golden-cases.py --check` remains green;
- package tests prove PASS/FAIL status and bounded diagnostics.

### S04 closure

Update inventory/closure artifacts only after both engines are package-backed.

## Verification gates

Every implementation slice must run:

```bash
uv run python scripts/build-parser-golden-cases.py --check
uv run python scripts/evaluate-parser-golden-cases.py --check
uv run pytest tests/test_parser_golden_cases_package.py -q
uv run ruff check scripts src/law_nexus/adapters/sources/parser_golden_cases.py tests/test_parser_golden_cases_package.py
uv run basedpyright scripts src/law_nexus/adapters/sources/parser_golden_cases.py tests/test_parser_golden_cases_package.py
uv run lint-imports
```

Final closure also runs inventory/closure validators:

```bash
uv run pytest tests/test_residual_script_migration_inventory.py tests/test_residual_script_migration_closure_map.py -q
```

## M079 result

M079 completed the planned core migration:

- S02 moved build-case construction into `law_nexus.adapters.sources.parser_golden_cases.build_cases`.
- S03 moved evaluator core behavior into `law_nexus.adapters.sources.parser_golden_cases.build_evaluation_result` and related package helpers.
- `scripts/build-parser-golden-cases.py` and `scripts/evaluate-parser-golden-cases.py` remain CLI/report wrappers.
- Existing wrapper checks, evaluator fail-closed tests, full script ruff, basedpyright, import-linter, and GitNexus detect gates passed.

## Non-claims

M079 does not prove:

- legal correctness;
- parser completeness;
- retrieval quality or answer faithfulness;
- citation-safe retrieval readiness;
- product ETL readiness;
- model/embedding quality;
- generated-Cypher correctness;
- FalkorDB production readiness;
- ACP/git-lex authority over source truth.

Parser golden cases remain bounded tracked artifacts for regression/proof support, not authoritative legal truth.
