# Repository Health and Proof Artifact Freshness Baseline

**Milestone:** M085-3xekmd  
**Status:** [bounded] measured baseline  
**Evidence:** `gsd_uat_exec:90965607-efa5-47e8-af73-c1f2a8ac31f5`  
**Scope:** full-suite health, lint/type/import gates, GitNexus cleanliness, failure clustering  

## Purpose

This artifact captures the current repository health state before remediation. It is a measurement baseline, not a repair claim. Failures are classified as candidates for later slices; M085 must not blindly regenerate proof artifacts or promote derived reports into product proof.

## Current measured gates

| Gate | Command | Result | Notes |
|---|---|---:|---|
| Full pytest | `uv run pytest -q --tb=short` | FAIL | 53 failing tests clustered below. |
| Full ruff | `uv run ruff check src/law_nexus scripts tests` | FAIL | 14 files with lint findings; 18 total ruff errors in prior full check. |
| Package type check | `uv run basedpyright src/law_nexus` | PASS | Package source type-checks clean. |
| Import-linter | `uv run lint-imports` | PASS | Onion contracts kept. |
| GitNexus detect | `gitnexus_detect_changes(repo="law-nexus", scope="all")` | PASS | changed_count=0, affected_count=0, risk_level=none. |
| Git status | `git status --short --branch` | PASS | Clean working tree, branch ahead of origin. |

## Pytest failure clusters

| Count | Test file | Initial cluster |
|---:|---|---|
| 8 | `tests/test_architecture_analysis_views.py` | Architecture views / generated report freshness. |
| 8 | `tests/test_observed_retrieval_output_metrics.py` | Observed retrieval metrics proof harness. |
| 5 | `tests/test_git_lex_diagnostic_adapter.py` | git-lex diagnostic adapter / ACP-facing JSON. |
| 5 | `tests/test_representative_evidence_span_retrieval_corpus.py` | Representative EvidenceSpan corpus fixture validation. |
| 5 | `tests/test_representative_evidence_span_retrieval_metrics.py` | Representative EvidenceSpan retrieval metrics. |
| 3 | `tests/test_consultant_hierarchy_prior_art_comparison.py` | Consultant hierarchy/prior-art artifact freshness. |
| 3 | `tests/test_observed_retrieval_provenance.py` | Observed retrieval provenance proof harness. |
| 2 | `tests/test_project_state_roadmap_freshness.py` | GSD/project roadmap freshness projection. |
| 2 | `tests/test_representative_retrieval_runtime_benchmark_cli.py` | Representative retrieval runtime CLI proof harness. |
| 1 each | ACP/git-lex, graph filtered retrieval, held-out semantic descriptor, M048 isolated fixtures, S10 embedding env, real artifact retrieval, S04 tooling, M049/M056/M065 verification tests | Mixed legacy proof/freshness/environment clusters. |

## Ruff failure clusters

| Count | File | Likely class |
|---:|---|---|
| 3 | `tests/test_architecture_analysis_views.py` | Unused import / assertion string hygiene / unused variable. |
| 3 | `tests/test_source_id_collision.py` | Test hygiene. |
| 1 each | `tests/test_consultant_document_type_classification.py`, `tests/test_gsd_sync_drift.py`, `tests/test_hierarchy_metadata_completeness.py`, `tests/test_offline_citation_retrieval_cases.py`, `tests/test_parser_fixture_inventory.py`, `tests/test_r035_evidence_audit.py`, `tests/test_real_artifact_retrieval_cases.py`, `tests/test_representative_retrieval_corpus_contract.py`, `tests/test_verify_acp_ci_contract.py`, `tests/test_verify_m049_binding.py`, `tests/test_verify_m056_acp_kit.py`, `tests/test_verify_m065_s04_stage2_closure.py` | Mostly test lint hygiene; must still avoid proof-text semantic changes. |

## GitNexus planning evidence

GitNexus query results grouped current failures into separate process families:

- Architecture/generated reports: processes such as `Main -> Freshness_map` and report rendering flows.
- Retrieval/provenance: `Build_report -> Run_json_command`, `Build_report -> Walk`, and `Build_report -> Load_json` style flows.
- ACP/git-lex: `Main -> Main_state`, `Main -> Is_inside_main_repo`, `Main -> Sha256`, and negative-case wrapper flows.

Use exact symbol/context queries before editing any function/class in later slices.

## S09 final measured status

**Evidence:** `gsd_uat_exec:684fb484-e730-4251-b71f-1ecc877b2718`

After S02 lint hygiene and S03-S08 classification, the final measured state is:

| Gate | Result | Notes |
|---|---:|---|
| Full pytest | FAIL | 53 failures remain, matching the baseline cluster count. |
| Full ruff | PASS | `uv run ruff check src/law_nexus scripts tests` passes. |
| Package type check | PASS | `uv run basedpyright src/law_nexus` passes. |
| Import-linter | PASS | Onion contracts kept. |

M085 improved lint signal and produced a remediation roadmap, but did not repair full-suite proof/freshness failures.

## Non-claims

This baseline does **not** claim the full repository is green. It does **not** validate legal correctness, parser completeness, retrieval quality, FalkorDB production readiness, generated-Cypher correctness, ACP/git-lex source-truth authority, or product readiness.

## S02 lint hygiene outcome

**Evidence:** `gsd_uat_exec:b6266c16-257e-4184-b0fc-fc4f1a4bfdc7`

S02 applied safe ruff hygiene to test files only. Full ruff now passes for `src/law_nexus`, `scripts`, and `tests`. Focused pytest over touched files still reports 12 failures: 8 architecture analysis view failures plus one each in real artifact retrieval, M049 binding, M056 ACP kit, and M065 S04 stage2 closure. These are treated as pre-existing proof/freshness clusters for later classification, not lint regressions.

## Initial remediation ordering hypothesis

1. Safe lint hygiene in tests, with proof-boundary text guarded. **S02 complete: full ruff passes.**
2. Architecture views freshness classification before artifact regeneration.
3. Retrieval/provenance fixture classification before proof artifact updates.
4. ACP/git-lex diagnostic classification while preserving no-main-mutation boundaries.
5. Consultant/source artifact classification using correct corpus/check commands.
6. Project-state/environment freshness classification.
7. Follow-on repair milestone(s) after M085 classification if changes are broad.
