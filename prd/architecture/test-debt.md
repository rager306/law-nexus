# Test debt register

This document tracks test failures that are **not regressions of the current
milestone** and are deferred to out-of-scope resolution. New failures should
be added here; closed items should be moved to a "Resolved" section with the
fix milestone.

Last re-investigation: **M074 S02** (30 failures remaining; was 56 at start
of M074 S02, 37 at M072 closeout, 25 at end of M003 era).

## Bounded scope rule (D098 anti-smoothing)

Test debt listed here is **not** a smoothing claim: every entry is
diagnostic, scoped, and traceable. Resolution requires an explicit
milestone or follow-up decision; "leaving it failing" is not acceptable
without a recorded reason.

## Classification legend

- **Type A: M072-induced — FIXED in M074 S02** (M072 S01/S05 caused these
  failures; M074 S02 applied targeted fixes that updated stale sha256/size
  values in fixture chains).
- **Type A: M072-induced — blocked, defer follow-up** (root cause
  identified; fix requires external data or substantive script refactor
  beyond S02 scope).
- **Type A: M072-deferred** (cross-cutting fix on
  representative_retrieval_corpus_manifest.json; out of M074 scope).
- **Type B: Inherited** (M003/M048/M049/M056/M061/M065/ACP era; per
  D097 these belong to the git-lex-kit-acp profile-consumer contract;
  the fix must coordinate with that profile, not be done in isolation).

## M074 S02 fix log

Baseline: 56 failures at start of M074 S02.
Post-S02: 30 failures.
Net change: **26 tests fixed in S02** (56 - 30 = 26).

| Commit | Affected fixtures | Approach |
|---|---|---|
| `ec148b1` | evidence_span_golden_retrieval_cases.json | Update 1 source_artifacts sha256 (consultant_hierarchy_records.json) |
| `b9603d7` | consultant_parser_proof.json | Update 1 input_artifacts size_bytes + sha256 (consultant_hierarchy_records.jsonl) |
| `ce221d7` | observed_retrieval_source_provenance_manifest.json, observed_retrieval_query_provenance_registry.json, observed_retrieval_outputs.json, representative_evidence_span_retrieval_corpus.json | Update sha256 chain across 4 retrieval-provenance fixtures |
| `95c7235` | semantic_descriptor_inputs.json, semantic_retrieval_safe_inputs.json | Update sha256 chain across 2 semantic-input fixtures |
| **Total** | **7 fixture files updated** | **M072 S05 sha256 cascade fully repaired** |

The cascade pattern: M072 S05 expanded the parser corpus and changed
record-ID scheme. This invalidated the recorded sha256 values for
consultant_hierarchy_records.json/.jsonl, which cascaded through every
fixture that referenced it via source_artifacts / source_fixture /
query_registry chains. The 4 commits update 7 fixture files; the
remaining 30 failures break down as 23 Type B (inherited, D097 out of
scope), 2 Type A: M072-deferred (cross-cutting manifest fix), 5 Type A:
blocked (require external data or substantive script refactor).

## Type A: M072-deferred (2 failures, follow-up milestone)

| # | Test | Cause | Resolution path |
|---|---|---|---|
| 1 | `test_representative_retrieval_corpus_manifest.py::test_builder_check_success_outputs_compact_safe_json` | `representative_retrieval_corpus_manifest.json` was generated pre-S01 inventory SHA; regenerating breaks 19 downstream tests that validate manifest contents | Cross-cutting fix: re-baseline M016 corpus manifest under v2 inventory, then update downstream tests. Out of M074 scope. |
| 2 | `test_representative_retrieval_corpus_manifest.py::test_source_artifact_hashes_match_tracked_inputs` | Same as #1 | Same as #1 |

**Total Type A: M072-deferred: 2 failures.**

## Type A: blocked, follow-up milestone (5 failures)

| # | Test | Cause | Resolution path |
|---|---|---|---|
| 1 | `test_consultant_hierarchy_prior_art_comparison.py::test_generator_build_is_deterministic_against_artifacts` | `consultant_hierarchy_prior_art_comparison.json` and its source `consultant_prior_art_expectations.json` cannot be regenerated; the expectations builder depends on external `/root/law-parser/` data (M072 S05 changed corpus from 2185 to 7860 records, invalidating 5 prior-art expectations) | Re-run `scripts/build-consultant-prior-art-expectations.py` against current corpus when law-parser data is available; then re-run `scripts/compare-consultant-hierarchy-prior-art.py --write`. Out of M074 scope (requires external data). |
| 2 | `test_consultant_hierarchy_prior_art_comparison.py::test_compare_blocks_major_structure_parent_breakage` | Same as #1 | Same as #1 |
| 3 | `test_consultant_hierarchy_prior_art_comparison.py::test_cli_check_reports_fresh_artifacts_without_blocking_on_needs_review` | Same as #1 | Same as #1 |
| 4 | `test_offline_citation_retrieval_cases.py::test_builder_check_mode_passes_for_checked_in_fixture` | `build-offline-citation-retrieval-cases.py` hardcodes `HIER-CONS-DOCUMENT`/`HIER-CONS-ARTICLE-0001` etc; M072 S05 changed record-ID scheme to per-fixture scope_id (`HIER-CONS-44-FZ-2026-DOCUMENT`); builder raises StopIteration on lookup; fixture regeneration would also change the fixture content, breaking other tests that compare against it | Substantive script refactor: replace hardcoded IDs with dynamic first-record / first-children lookups, regenerate fixture, verify downstream tests. Out of M074 scope (cross-cutting fixture regeneration). |
| 5 | `test_real_artifact_retrieval_cases.py::test_builder_check_mode_confirms_corpus_freshness` | Same as #4 (same hardcoded-ID pattern in `build-real-artifact-retrieval-cases.py`) | Same as #4 |

**Total Type A: blocked: 5 failures.**

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

- **Type A: FIXED**: M074 S02 commits `ec148b1`, `b9603d7`, `ce221d7`,
  `95c7235` restored 26 tests across 12 files via sha256 chain updates
  in 7 fixture files. (Cascade: 7 fixture updates restored tests in 12
  test files because some scripts call sub-verifiers that were also
  failing transitively.)
- **Type A: blocked (5)**: requires either external law-parser data
  (#1-3) or substantive script refactor (#4-5). Out of M074 scope;
  follow-up milestone proposed.
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
