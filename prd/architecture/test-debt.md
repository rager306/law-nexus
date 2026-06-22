# Test debt register

This document tracks test failures that are **not regressions of the current
milestone** and are deferred to out-of-scope resolution. New failures should
be added here; closed items should be moved to a "Resolved" section with the
fix milestone.

## Bounded scope rule (D098 anti-smoothing)

Test debt listed here is **not** a smoothing claim: every entry is
diagnostic, scoped, and traceable. Resolution requires an explicit
milestone or follow-up decision; "leaving it failing" is not acceptable
without a recorded reason.

## Categories

- **Pre-existing debt** — failures that existed before the current
  milestone's changes; carried over from earlier milestones (typically M003,
  M048, M049, M056, M065, M002, M061, M010, M038, etc.). Per D097 these
  are part of the inherited profile-consumer contract (git-lex-kit-acp);
  out of scope for parser hardening unless an explicit fix slice is opened.
- **M072-deferred** — failures introduced by the M072 S01 inventory
  schema v2 transition (4 → 53 fixtures, document_type taxonomy,
  discovery-based scanning) that are deferred because resolution requires
  cross-cutting changes to downstream artifacts.

## Pre-existing debt (23 failures)

| Test | Source | Why out of scope |
|---|---|---|
| `tests/test_architecture_analysis_views.py` (8) | M003 S05 / M003 S03 | Architecture graph/claims-ledger drift from earlier milestone evolution. Inherited. |
| `tests/test_git_lex_diagnostic_adapter.py` (5) | M048 / M056 | ACP/git-lex adapter. Per D097, inherited from git-lex-kit-acp profile. |
| `tests/test_acp_git_lex_backend.py` (1) | M061 | ACP backend. Per D097, inherited. |
| `tests/test_graph_filtered_retrieval_integration.py` (1) | M016 / S10 | Retrieval integration test that depends on graph container. Out of parser scope. |
| `tests/test_held_out_semantic_descriptor_ablation.py` (1) | S10 | Semantic-descriptor ablation, related to S10 embedding evaluation. Out of parser scope. |
| `tests/test_m048_s04_git_lex_isolated_fixtures.py` (1) | M048 S04 | Git-lex isolated fixtures. Inherited. |
| `tests/test_verify_m049_binding.py` (1) | M049 | Architecture registry binding. Inherited. |
| `tests/test_verify_m056_acp_kit.py` (1) | M056 | ACP kit scaffold. Inherited. |
| `tests/test_verify_m065_s02_release_install.py` (1) | M065 | Release-install state. Inherited. |
| `tests/test_verify_m065_s03_workflow_proof.py` (1) | M065 | Workflow-proof state. Inherited. |
| `tests/test_verify_m065_s04_stage2_closure.py` (1) | M065 | Stage-2 closure state. Inherited. |
| `tests/test_s04_tooling.py` (1) | S04 | LSP/uv discovery tooling metadata. Inherited. |

**Total pre-existing: 23 failures.**

## M072-deferred (2 failures)

| Test | Cause | Resolution path |
|---|---|---|
| `tests/test_representative_retrieval_corpus_manifest.py::test_source_artifact_hashes_match_tracked_inputs` | Manifest at `prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json` was generated before M072 S01 inventory schema v2 (4-fixture hardcoded), so it carries pre-S01 SHA `8680fd75...`. Regenerating would break 19 downstream tests (`test_observed_retrieval_output_metrics`, `test_observed_retrieval_provenance`, `test_representative_evidence_span_retrieval_corpus`, `test_representative_evidence_span_retrieval_metrics`) that validate the manifest's SHA against other checked-in artifacts. | Cross-cutting fix required: re-baseline the M016 corpus manifest under v2 inventory, then update downstream tests. Out of M072 scope. Defer to a follow-up milestone. |
| `tests/test_representative_retrieval_corpus_manifest.py::test_builder_check_success_outputs_compact_safe_json` | Same — `manifest_schema_mismatch` because the on-disk manifest is pre-S01. | Same as above. |

**Total M072-deferred: 2 failures.**

## M072 S01 regression — fixed (16 of 18 = 89%)

| Test | Fix |
|---|---|
| `test_consultant_relation_candidates` (5) | `scripts/build-consultant-relation-candidates.py`: removed `canonical is True` check (v2 inventory drops the `canonical` field; source_role `document-list-prior-art` is the source of truth). |
| `test_odt_smoke_records` (3) | `scripts/build-odt-smoke-records.py`: removed `canonical is True` check; kept `DOC_IDS_BY_PATH` bounded to 2 canonical Garant ODT (44-fz.odt, PP_60_27-01-2022.odt). |
| `test_validate_parser_records_cli` (3) | `scripts/validate-parser-records.py`: removed `canonical is not True` check (v2 inventory uses `exists is True` as the presence guarantee). |
| `test_parser_records` (2) | Same fix as above (the validate-parser-records.py regression). |
| `test_representative_retrieval_corpus_manifest` (2 of 4) | `scripts/build_representative_retrieval_corpus_manifest.py`: removed `canonical is True` check in `first_fixture_by_kind`. The other 2 tests (manifest schema) are deferred — see above. |

## Resolution ownership

- **Pre-existing debt**: out of M072 scope. Will be addressed in a future
  "test-debt-reduction" milestone that opens the inherited scope (M003 / M048
  / M049 / M056 / M061 / M065 / etc.) explicitly. Per D097 these belong to
  the git-lex-kit-acp profile-consumer contract; the fix must coordinate with
  that profile, not be done in isolation.
- **M072-deferred**: 2 failures, requires cross-cutting fix on
  `prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json`
  and the four downstream test files listed above. Could be a follow-up slice
  inside M072 (e.g. M072 S04 "re-baseline M016 corpus manifest under v2
  inventory") or a separate milestone. Decision deferred to user.

## Non-claim

This document does NOT claim that the listed failures are acceptable forever
or that they will resolve themselves. Every entry is a known problem with a
named resolution path; the absence of an active fix is a recorded
decision, not an implicit shrug.
