# Residual Script Cleanup Wave Baseline

## Purpose

This document starts M078 Residual Script Cleanup Waves. It records the baseline for the next bounded cleanup after M077 and fixes the scope for the first execution waves:

1. close global `scripts/` ruff debt;
2. resolve the single representative retrieval corpus retire candidate safely;
3. migrate one high-priority parser/source script logic seam into package code.

This is not a blanket migration of all remaining `migrate logic` inventory rows.

## Source baseline

Authoritative prior state:

- `prd/architecture/residual-script-migration-inventory.md`
- `prd/architecture/residual-script-migration-closure-map.md`

M077 final inventory remains:

| Metric | Value |
|---|---:|
| Top-level Python scripts | 140 |
| Inventory rows | 140 |
| `migrate logic` rows | 49 |
| High-priority `migrate logic` rows not extracted | 45 |
| `proof runtime wrapper` rows | 61 |
| `thin wrapper` rows | 6 |
| `retire candidate` rows | 1 |
| `deferred` rows | 23 |

## Ruff baseline

Baseline command:

```bash
uv run ruff check scripts --output-format=json
```

Current result before M078 edits:

| Metric | Value |
|---|---:|
| Ruff exit code | 1 |
| Violations | 9 |
| Files affected | 8 |

Rules:

| Rule | Count |
|---|---:|
| F401 | 4 |
| I001 | 2 |
| F841 | 1 |
| F402 | 1 |
| F541 | 1 |

Files:

| File | Count | Rules |
|---|---:|---|
| `scripts/probe-consultant-parser.py` | 2 | I001 x2 |
| `scripts/build-source-id-uniqueness.py` | 1 | F401 |
| `scripts/run-m048-s04-git-lex-proof.py` | 1 | F401 |
| `scripts/run_m048_s09_git_lex_functional_fit.py` | 1 | F841 |
| `scripts/verify-architecture-graph.py` | 1 | F402 |
| `scripts/verify-m067-s01-externalization.py` | 1 | F541 |
| `scripts/verify-m067-s02-profile-layer.py` | 1 | F401 |
| `scripts/verify-m067-s03-externalization-integrity.py` | 1 | F401 |

S02 is limited to these current findings unless a direct fix produces a new same-file lint consequence.

## Retire candidate baseline

The sole retire candidate from M077 is:

```text
scripts/build-representative-retrieval-corpus.py
```

Initial reference scan found that this file delegates to:

```text
scripts/build_representative_retrieval_corpus_manifest.py
```

Documented command surfaces reference the manifest builder, especially:

```text
prd/retrieval/representative_retrieval_corpus_contract.md
uv run python scripts/build_representative_retrieval_corpus_manifest.py --check
```

GitNexus resolved the relevant manifest script helper:

```text
Function:scripts/build_representative_retrieval_corpus_manifest.py:build_payload
```

S03 must not delete the retire candidate unless it proves:

- no durable docs/tests still require the hyphenated wrapper path;
- the underscore manifest builder command is the accepted replacement;
- parity between old wrapper invocation and replacement command is verified;
- relevant tests still pass.

If any condition fails, S03 should retain the wrapper and update closure documentation with the reason.

## Selected parser/source migration seam for S04

Selected bounded seam:

```text
Parser golden-case build/evaluate helper logic
```

Primary scripts to inspect and potentially thin:

```text
scripts/build-parser-golden-cases.py
scripts/evaluate-parser-golden-cases.py
```

Adjacent scripts are context only unless impact analysis shows the same helper seam is already shared safely:

```text
scripts/build-odt-smoke-records.py
scripts/build-parser-staging-graph.py
scripts/build-consultant-prior-art-expectations.py
scripts/build-consultant-relation-candidates.py
scripts/compare-consultant-hierarchy-prior-art.py
```

GitNexus query evidence for this seam surfaced parser evaluation/build flows including:

- `Evaluate_cases -> Diagnostic`
- `Evaluate_cases -> Display_path`
- `Evaluate_cases -> Expected_list`
- `Build_payload -> Diagnostic`
- `Build_payload -> _evidence_path_ids_from_output`

S04 must run GitNexus impact before editing any function/class/method symbol. If impact analysis reports high or critical risk, stop and narrow or replan.

## Wave boundaries

| Slice | Boundary |
|---|---|
| S02 | Fix only the current full-script ruff debt. |
| S03 | Resolve only `scripts/build-representative-retrieval-corpus.py`. |
| S04 | Migrate only the selected parser golden-case build/evaluate seam. |

## Required gates

Per implemented slice:

- targeted tests for touched files;
- `uv run ruff check scripts`;
- `uv run basedpyright scripts`;
- `uv run lint-imports` when package boundaries change;
- GitNexus reindex with `gitnexus analyze --force --name law-nexus` after commit;
- `gitnexus_detect_changes(repo="law-nexus", scope="all")` after reindex;
- GSD UAT evidence via `gsd_uat_exec` and `gsd_uat_result_save`.

## Non-claims

M078 does not claim:

- legal correctness;
- parser completeness;
- retrieval quality or answer faithfulness;
- model/embedding quality;
- generated-Cypher correctness;
- FalkorDB production readiness;
- ACP/git-lex authority over source truth;
- safe deletion of scripts beyond the single S03 retire candidate.

## S03 result

The retire candidate was resolved in M078 S03. `scripts/build-representative-retrieval-corpus.py` was deleted after old and canonical commands both passed `--check`, `runtime_handoff()` was updated to emit the canonical underscore command for both builder fields, generated representative corpus artifacts were refreshed, and representative corpus tests passed.
