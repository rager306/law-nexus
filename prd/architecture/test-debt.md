# Test debt register

This document tracks test failures that are **not regressions of the current
milestone** and are deferred to out-of-scope resolution. New failures should
be added here; closed items should be moved to a "Resolved" section with the
fix milestone.

Last re-investigation: **M074 S01** (37 failures, was 25 before M072 S05
expanded the corpus to 4 in-scope fixtures and 7860 hierarchy records).

## Bounded scope rule (D098 anti-smoothing)

Test debt listed here is **not** a smoothing claim: every entry is
diagnostic, scoped, and traceable. Resolution requires an explicit
milestone or follow-up decision; "leaving it failing" is not acceptable
without a recorded reason.

## Classification legend

- **Type A**: M072-induced. The M072 parser work (S01 inventory schema v2
  or S05 hierarchy corpus expansion to 7860 records) caused these failures.
  Resolution is in scope for M074 S02: regenerate the affected proof
  artifact so its size/sha256 reflect the current corpus.
- **Type B**: Inherited from M003/M048/M049/M056/M061/M065/ACP era. Per
  D097 these belong to the git-lex-kit-acp profile-consumer contract; the
  fix must coordinate with that profile, not be done in isolation. M074
  documents them as Type B with explicit resolution paths but does NOT
  fix them.

## Type A: M072-induced (14 failures, fixable in M074 S02)

| # | Test | Cause | Fix |
|---|---|---|---|
| 1 | `test_consultant_hierarchy_prior_art_comparison.py::test_generator_build_is_deterministic_against_artifacts` | `prd/parser/consultant_hierarchy_prior_art_comparison.json` was generated pre-S05; corpus expanded from 2185 to 7860 records | Re-run `scripts/compare-consultant-hierarchy-prior-art.py --write` |
| 2 | `test_consultant_hierarchy_prior_art_comparison.py::test_compare_blocks_major_structure_parent_breakage` | Same as #1 | Same as #1 |
| 3 | `test_consultant_hierarchy_prior_art_comparison.py::test_cli_check_reports_fresh_artifacts_without_blocking_on_needs_review` | Same as #1 | Same as #1 |
| 4 | `test_consultant_parser_proof.py::test_proof_package_records_current_input_freshness` | `prd/parser/consultant_parser_proof.json` is a manual annotation; its `input_artifacts[1].size_bytes = 4175013` (pre-S05) vs actual 15004699 | Update the manual annotation: rewrite `input_artifacts` with current sizes and sha256 |
| 5 | `test_evidence_span_golden_retrieval_cases.py::test_verifier_accepts_fixture` | `evidence_span_golden_retrieval_cases.json` records pre-S05 hierarchy SHA | Re-run verifier/builder to refresh |
| 6 | `test_evidence_span_golden_retrieval_cases.py::test_verifier_cli_accepts_fixture` | Same as #5 | Same as #5 |
| 7 | `test_evidence_span_golden_retrieval_cases.py::test_verifier_fails_closed_for_bad_candidate_reference` | Same as #5 | Same as #5 |
| 8 | `test_evidence_span_golden_retrieval_cases.py::test_verifier_fails_closed_for_missing_case_class` | Same as #5 | Same as #5 |
| 9 | `test_evidence_span_local_retrieval_metrics.py::test_cli_passes_with_injected_confirmed_runtime` | `evidence_span_local_retrieval_metrics_proof.json` references pre-S05 hierarchy corpus | Re-run `scripts/verify-evidence-span-local-retrieval-metrics.py` to refresh |
| 10 | `test_evidence_span_local_retrieval_metrics.py::test_cli_reports_blocked_runtime_without_fallback` | Same as #9 | Same as #9 |
| 11 | `test_offline_citation_retrieval_cases.py::test_builder_check_mode_passes_for_checked_in_fixture` | `offline_citation_retrieval_cases.json` StopIteration on record lookup (pre-S05 reference) | Re-run `scripts/build-offline-citation-retrieval-cases.py --write` |
| 12 | `test_real_artifact_retrieval_cases.py::test_builder_check_mode_confirms_corpus_freshness` | `real_artifact_retrieval_cases.json` references pre-S05 hierarchy corpus | Re-run `scripts/build-real-artifact-retrieval-cases.py --write` |

**Total Type A: 14 failures, fixable in M074 S02.**

## Type A: M072-deferred (2 failures, follow-up milestone)

| # | Test | Cause | Resolution path |
|---|---|---|---|
| 1 | `test_representative_retrieval_corpus_manifest.py::test_builder_check_success_outputs_compact_safe_json` | `representative_retrieval_corpus_manifest.json` was generated pre-S01 inventory SHA; regenerating breaks 19 downstream tests that validate manifest contents | Cross-cutting fix: re-baseline M016 corpus manifest under v2 inventory, then update downstream tests. Out of M074 scope. |
| 2 | `test_representative_retrieval_corpus_manifest.py::test_source_artifact_hashes_match_tracked_inputs` | Same as #1 | Same as #1 |

**Total Type A: M072-deferred: 2 failures.**

## Type B: Inherited (23 failures, out of scope per D097)

| Test | Source | Resolution path |
|---|---|---|
| `tests/test_architecture_analysis_views.py` (8) | M003 / S05 | Architecture graph/claims-ledger drift from earlier milestone evolution. Inherited per D097. |
| `tests/test_git_lex_diagnostic_adapter.py` (5) | M048 / M056 | ACP/git-lex adapter. Inherited per D097 (git-lex-kit-acp profile). |
| `tests/test_acp_git_lex_backend.py` (1) | M061 | ACP backend. Inherited per D097. |
| `tests/test_graph_filtered_retrieval_integration.py` (1) | M016 / S10 | Retrieval integration test that depends on graph container. Out of parser scope. |
| `tests/test_held_out_semantic_descriptor_ablation.py` (1) | S10 | Semantic-descriptor ablation. Out of parser scope. |
| `tests/test_m048_s04_git_lex_isolated_fixtures.py` (1) | M048 S04 | Git-lex isolated fixtures. Inherited. |
| `tests/test_verify_m049_binding.py` (1) | M049 | Architecture registry binding. Inherited. |
| `tests/test_verify_m056_acp_kit.py` (1) | M056 | ACP kit scaffold. Inherited. |
| `tests/test_verify_m065_s02_release_install.py` (1) | M065 | Release-install state. Inherited. |
| `tests/test_verify_m065_s03_workflow_proof.py` (1) | M065 | Workflow-proof state. Inherited. |
| `tests/test_verify_m065_s04_stage2_closure.py` (1) | M065 | Stage-2 closure state. Inherited. |
| `tests/test_s04_tooling.py` (1) | S04 | LSP/uv discovery tooling metadata. Inherited. |

**Total Type B: 23 failures.**

## Resolution ownership

- **Type A (M074 scope)**: M074 S02 applies the targeted fixes. Each fix
  is one commit; failure count decreases monotonically; gates stay green
  after every fix.
- **Type A: M072-deferred (2)**: requires cross-cutting fix on
  `representative_retrieval_corpus_manifest.json` and the four downstream
  tests. Out of M074 scope; follow-up milestone proposed.
- **Type B (inherited)**: requires coordination with the git-lex-kit-acp
  profile-consumer contract (D097). The fix cannot be done in isolation
  in law-nexus; it must be coordinated with the upstream profile. Out of
  M074 scope. Future "test-debt-reduction-profile-coordination" milestone
  proposed.

## Non-claim

This document does NOT claim that the listed failures are acceptable
forever or that they will resolve themselves. Every entry is a known
problem with a named resolution path; the absence of an active fix is a
recorded decision, not an implicit shrug.
