# Repository Health Remediation Roadmap

**Milestone:** M085-3xekmd  
**Status:** [bounded] remediation classification  
**Baseline:** `prd/architecture/repository-health-triage-baseline.md`  

## Purpose

This roadmap classifies current repository health failures into remediation waves. It does not claim the repository is fully green. It must preserve law-nexus proof boundaries: generated reports are derived diagnostics, not source truth or product proof.

## S03 architecture views classification

**Evidence:** `gsd_uat_exec:e171c9e3-5c8f-4b83-8e84-041169226be4`

### Failing tests

`tests/test_architecture_analysis_views.py` currently has 8 failures:

1. `test_high_risk_nodes_appear_in_dashboard`
2. `test_high_risk_count_matches_report`
3. `test_node_and_edge_counts_present`
4. `test_non_claims_summary_counts_present`
5. `test_generated_output_matches_stored_file`
6. `test_claims_ledger_matches_stored_file`
7. `test_blockers_report_matches_stored_file`
8. `test_generate_script_supports_check_flag`

### Mapped scripts and artifacts

| Role | Path |
|---|---|
| Generator | `scripts/generate-architecture-views.py` |
| Test | `tests/test_architecture_analysis_views.py` |
| Dashboard artifact | `prd/architecture/architecture_health.md` |
| Claims ledger artifact | `prd/architecture/architecture_claims_ledger.md` |
| Blockers report artifact | `prd/architecture/architecture_blockers.md` |
| Source report JSON | architecture analysis report loaded by the generator/test fixtures |

### Observed failure class

The generator `--check` path reports stale generated artifacts, including:

```text
stale architecture health dashboard: prd/architecture/architecture_health.md; regenerate with `uv run python scripts/generate-architecture-views.py` and review the diff
```

The stale dashboard is also missing expected high-risk node content such as `ACP-AHF-0001`. This indicates generated architecture view artifacts are behind the current source report/generator logic.

### Classification

- **Likely cause:** generated architecture view artifacts are stale relative to `scripts/generate-architecture-views.py` and the current architecture analysis source report.
- **Risk:** medium. These artifacts summarize architecture/proof health and can create false confidence if blindly refreshed without review.
- **Recommended remediation:** dedicated architecture-view refresh slice in a follow-on remediation milestone:
  1. run `uv run python scripts/generate-architecture-views.py --check` and save current failure output;
  2. run the generator without `--check`;
  3. review diffs in `prd/architecture/architecture_health.md`, `architecture_claims_ledger.md`, and `architecture_blockers.md`;
  4. verify no lifecycle/proof-level overclaims were introduced;
  5. rerun `uv run pytest tests/test_architecture_analysis_views.py -q`.
- **Do not:** treat refreshed architecture views as product/runtime/legal proof; they remain derived diagnostics.

## S04 retrieval and provenance classification

**Evidence:** `gsd_uat_exec:42da1cc9-6332-42e8-94f7-b8b4b409bc0f`

### Failing test clusters

Targeted retrieval/provenance run produced 26 failures:

| Count | Test file | Initial classification |
|---:|---|---|
| 8 | `tests/test_observed_retrieval_output_metrics.py` | Observed retrieval output metrics proof harness drift. |
| 5 | `tests/test_representative_evidence_span_retrieval_corpus.py` | Representative EvidenceSpan corpus fixture/schema/reference drift. |
| 5 | `tests/test_representative_evidence_span_retrieval_metrics.py` | Representative EvidenceSpan runtime metric proof drift. |
| 3 | `tests/test_observed_retrieval_provenance.py` | Observed retrieval provenance manifest/source-record drift. |
| 2 | `tests/test_representative_retrieval_runtime_benchmark_cli.py` | Runtime benchmark CLI/report safety drift. |
| 1 | `tests/test_real_artifact_retrieval_cases.py` | Real artifact retrieval case shape/namespace drift. |
| 1 | `tests/test_graph_filtered_retrieval_integration.py` | Graph-filtered retrieval integration proof boundary. |
| 1 | `tests/test_held_out_semantic_descriptor_ablation.py` | Held-out semantic descriptor CLI/report drift. |

### Mapped scripts and artifacts

| Area | Likely scripts/artifacts |
|---|---|
| Observed retrieval output/provenance | `scripts/verify-observed-retrieval-provenance.py`, `scripts/verify-observed-retrieval-proof.py`, observed retrieval proof fixtures/reports under `prd/retrieval/` |
| Representative EvidenceSpan corpus | `prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json`, `scripts/build-representative-retrieval-corpus.py`, representative corpus markdown/JSON reports |
| Representative runtime benchmark | `scripts/verify-representative-retrieval-runtime-benchmark.py`, representative runtime report artifacts |
| Real artifact retrieval cases | `scripts/build-real-artifact-retrieval-cases.py`, real artifact retrieval fixture artifacts |
| Graph-filtered retrieval integration | `scripts/verify-graph-filtered-retrieval-integration.py`, graph-filtered proof artifact |
| Semantic descriptor ablation | semantic descriptor scoring/ablation scripts and reports |

### Classification

- **Likely cause:** a mix of stale retrieval proof fixtures, stricter safety/provenance validators, source-manifest drift, and environment/runtime proof assumptions.
- **Risk:** high for overclaiming. These failures are close to retrieval quality/provenance proof boundaries and must not be repaired by loosening validators or promoting generated reports.
- **Recommended remediation:** split into at least two future repair slices:
  1. representative corpus/provenance fixture repair with strict source-record and safe-payload checks;
  2. runtime metrics/report repair with managed-API and raw-vector non-claims preserved.
- **Do not:** treat passing synthetic/representative retrieval tests as production retrieval quality or legal-answer correctness.

## S05 ACP/git-lex diagnostic classification

**Evidence:** `gsd_uat_exec:2a37da4b-5882-407a-836d-a64a68825d1e`

### Failing test clusters

Targeted ACP/git-lex run produced 7 failures:

| Count | Test file | Initial classification |
|---:|---|---|
| 5 | `tests/test_git_lex_diagnostic_adapter.py` | Diagnostic adapter JSON/classification contract drift. |
| 1 | `tests/test_acp_git_lex_backend.py` | ACP backend denied-command JSON surface drift. |
| 1 | `tests/test_m048_s04_git_lex_isolated_fixtures.py` | Isolated fixture negative-boundary drift. |

### Mapped scripts and artifacts

| Area | Likely scripts/artifacts |
|---|---|
| Diagnostic adapter | `scripts/git_lex_diagnostic_adapter.py`, `tests/test_git_lex_diagnostic_adapter.py` |
| ACP git-lex backend | ACP/git-lex backend tests and `.lex` projection fixtures |
| M048 isolated fixtures | `prd/architecture/acp/fixtures/git-lex-isolated-proof`, `tests/test_m048_s04_git_lex_isolated_fixtures.py` |
| GitNexus process evidence | `Main -> Main_state`, `Main -> Is_inside_main_repo`, `Run_negative_case -> Main_residue_paths` |

### Classification

- **Likely cause:** diagnostic schema/classification expectations drifted around denied commands, main-repo blocking, missing expected inputs, bounded query IDs, and validation-overclaim negative cases.
- **Risk:** medium/high. Repairs must preserve D098 and ACP/git-lex boundaries: checkpoint/diagnostic only, no main-repo mutation, no ACP/git-lex source-truth promotion.
- **Recommended remediation:** dedicated ACP/git-lex diagnostic repair slice:
  1. inspect `scripts/git_lex_diagnostic_adapter.py` with exact GitNexus impact before edits;
  2. repair wrapper classification/schema output or test fixture expectations, whichever is actually stale;
  3. rerun targeted ACP/git-lex tests;
  4. verify no `.lex` main mutation and no validation-overclaim language.
- **Do not:** run blind `git lex init`, mutate main `.lex` state, or treat git-lex/ACP projections as authoritative product proof.

## S06 Consultant and source artifact classification

**Evidence:** `gsd_uat_exec:31d613ac-ef75-4377-9c6d-33e51b2102c4`

### Failing test clusters

Targeted Consultant/source run produced 3 failures, all in `tests/test_consultant_hierarchy_prior_art_comparison.py`:

1. `test_cli_check_reports_fresh_artifacts_without_blocking_on_needs_review`
2. `test_generator_build_is_deterministic_against_artifacts`
3. `test_compare_blocks_major_structure_parent_breakage`

### Mapped scripts and artifacts

| Role | Path |
|---|---|
| Prior-art comparison script | `scripts/compare-consultant-hierarchy-prior-art.py` |
| Test | `tests/test_consultant_hierarchy_prior_art_comparison.py` |
| JSON artifact | `prd/parser/consultant_hierarchy_prior_art_comparison.json` |
| Markdown report | `prd/parser/consultant_hierarchy_prior_art_comparison.md` |
| Expectations | `prd/parser/consultant_prior_art_expectations.json` |
| Related hierarchy generator | `scripts/build-consultant-hierarchy-records.py` |

### Classification

- **Likely cause:** Consultant hierarchy prior-art comparison artifacts or expectations are stale relative to script logic/current hierarchy records, or the check path is now stricter around `needs_review`/parent breakage diagnostics.
- **Risk:** medium. Prior-art is explicitly not trusted implementation; repairs must not promote Old_project/Consultant assumptions as product truth or Garant ODT parity.
- **Known command gotcha:** for committed Consultant hierarchy records, use corpus mode (`uv run python scripts/build-consultant-hierarchy-records.py --corpus --check`) rather than legacy single-fixture `--check`.
- **Recommended remediation:** dedicated Consultant prior-art freshness repair slice:
  1. run `uv run python scripts/compare-consultant-hierarchy-prior-art.py --check` and inspect failure output;
  2. verify related hierarchy artifacts with the correct corpus-mode command;
  3. refresh prior-art comparison artifacts only after reviewing diffs and confirming no Old_project/source-truth overclaim;
  4. rerun `uv run pytest tests/test_consultant_hierarchy_prior_art_comparison.py -q`.
- **Do not:** treat Old_project or prior-art comparison output as keep-as-is implementation authority.

## Remediation order draft

1. Architecture views refresh after diff review.
2. Retrieval/provenance proof fixture classification and targeted refresh. **S04 complete: classify as high-risk proof fixture/runtime drift.**
3. ACP/git-lex diagnostic adapter classification and boundary repair. **S05 complete: classify as diagnostic schema/boundary drift.**
4. Consultant hierarchy/source artifact classification. **S06 complete: classify as prior-art comparison freshness/boundary drift.**
5. Project state/environment freshness classification.
6. Final full-suite rerun and split remaining failures into repair milestones.

## Non-claims

This roadmap does not prove full-suite health, legal correctness, parser completeness, retrieval quality, FalkorDB production readiness, generated-Cypher correctness, or ACP/git-lex source-truth authority.
