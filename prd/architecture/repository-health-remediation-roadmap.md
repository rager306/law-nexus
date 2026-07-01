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

## Remediation order draft

1. Architecture views refresh after diff review.
2. Retrieval/provenance proof fixture classification and targeted refresh.
3. ACP/git-lex diagnostic adapter classification and boundary repair.
4. Consultant hierarchy/source artifact classification.
5. Project state/environment freshness classification.
6. Final full-suite rerun and split remaining failures into repair milestones.

## Non-claims

This roadmap does not prove full-suite health, legal correctness, parser completeness, retrieval quality, FalkorDB production readiness, generated-Cypher correctness, or ACP/git-lex source-truth authority.
