# Plan — law-nexus, milestone post-ship-hardening

<!-- Written by the planner role (GSD Path plan, 2026-10-27). Executed
     wave-by-wave by the build orchestrator. Task id, title, deps, and files
     live only in each `.project/tasks/T###-slug.md` frontmatter; `wave: N`
     there assigns the task to a wave here. -->

Project verify: `uv sync --frozen && cargo fmt --all -- --check && cargo clippy --workspace --offline --all-targets -- -D warnings && cargo build --workspace --offline && cargo test --workspace --offline && uv run ruff check src/ && uv run ruff format --check src/ && uv run basedpyright src/ && uv run ty check src/ && uv run pyrefly check src/ && uv run python scripts/verify-crate-dependency-allowlist.py && uv run python scripts/verify-adr-conformance.py && uv run pytest -q tests/test_harness_subprocess_failure_modes.py tests/test_harness_status_tracer.py tests/test_harness_governor.py tests/test_harness_preflight.py tests/test_harness_review_case_cli.py tests/test_review_case_governor.py tests/test_review_case_schema.py tests/test_review_case_delta_fixture.py tests/test_verify_crate_dependency_allowlist.py tests/test_verify_port_contract_coverage.py tests/test_verify_hostile_negative_suite_coverage.py tests/test_verify_multi_adapter_port_coverage.py tests/test_verify_live_adapter_readiness.py tests/test_architecture_views.py tests/test_architecture_analysis_views.py tests/test_architecture_remediation_matrix.py tests/test_architecture_track_split.py tests/test_architecture_closure_roadmap.py tests/test_architecture_registry_schema.py tests/test_verify_adr_conformance.py tests/test_harness_workflow_state.py tests/test_phase_dispatch_adapter.py tests/test_verify_source_snapshot_v2.py tests/test_harness_cli_entrypoints.py tests/test_harness_no_forbidden_imports.py tests/test_documentation_navigation.py tests/test_repository_quality_gate.py tests/test_project_state_roadmap_freshness.py tests/test_path_isolation_recovery.py tests/test_m225_validation_residual.py tests/test_product_model.py tests/test_gitnexus_block_receipt.py tests/test_m001_cutover_readiness.py tests/test_ci_runtime_restore.py tests/test_branch_context.py tests/test_post_ship_pointers.py`

<!-- Run once at ship, in a fresh sidecar worktree at the reviewed commit.
     This is CI's hermetic green surface (repository-quality.yml, portable
     parts of all three jobs) plus this milestone's own tests. The live
     governor/preflight suites are context-independent after T003, so the
     sidecar run is meaningful: on a gsd-path-verify/* branch they exercise the
     pinned fail-closed contract by design (M001 ruling (a)); on the bound
     branch they exercise the full assertions. The advisory M207 batteries and
     the strict corpus job are deliberately absent — green here never proves
     corpus scenarios ran. -->

## Config

- max_review_cycles: 3
- wave_budget: none
- review_panel: off
- finding_skeptics: off

## Wave 1 — risk burn-down

Goal: Burn the three plan-invalidating risks. (1) The vendored-archive restore route: `.ai/local/vendor/gsd-path/` computes exactly the pinned digest `6f95a31e…` (verified 2026-10-27) and the installer route was rehearsed end-to-end — T001 turns it into a tracked archive plus CI steps that restore the pinned runtime before any operational check, publish the governor's diagnostic JSON only on failure, keep the exit non-zero (SC1 restore half, SC3, E1, E5, N1, N3), and assert the shipped-main governor contract in the migration job. If the digest does not match or the installer cannot run hermetically in CI, the restore design changes — that is why this lands first. (2) The shipped-integrated classification: the typed adapter today maps integrated main's verified `block` route to a blocking `conflicting-ownership`, so the governor can never exit 0 on main (probed 2026-10-27 on a fresh named-branch checkout of 4e0cd4db); T002 adds the honest `shipped-integrated` kind without weakening any fail-closed path (SC1 product half, N2). (3) The context regression: the suites pinned to `gsd-path/M001` fail today on the operational bound branch `gsd-path/M002` (2 preflight tests verified failing) and would fail on main's shipped scenario; T003 replaces the broad `startswith("kind=")` pinning with the five-scenario matrix behind one shared predicate (SC2, E3, E4, N2).

Review depth: full

## Wave 2 — post-ship pointers and acceptance

Goal: Make the shipped state truthful at every pointer a fresh agent reads, then prove the handoff works. T004 updates the roadmap marker to the M002 continuation with M001 recorded shipped/archived/integrated, links the crosswalk M225 row to the T004 rerun receipt with corpus parity explicitly unproven (E6), references T005/T006 on the closed audit queue rows, and writes the dated post-ship report that supersedes the pre-ship cutover snapshot (SC4, N4). T005 then runs the M002 acceptance walkthrough as a fresh session — restore/verify the pinned runtime from the vendored archive, status/governor/freshness recognizing shipped M001 and the M002 continuation — and records the proof on disk (SC5, E7, N5). Review depth is verify-only: both tasks are docs plus recorded proof whose Verify commands (marker/pointer tests, proof-file checks) fail when the work is skipped, and the GitHub Actions surface is exercised by wave 1's recorded CI evidence.

Review depth: verify-only

## Surface contract

### terminal (native Path CLI: path-run.py status, governor, pytest, git) — T005

Criteria: SC5
Entry: a terminal in the primary worktree on the bound branch `gsd-path/M002`; the commands of the post-ship report's "Fresh-session bootstrap" section — the vendored-archive restore, `python3 scripts/ai/path-run.py status`, `uv run --frozen python -m law_nexus_harness.governor`, `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`.
States: missing runtime store — the documented restore creates it from the vendored archive, and an existing valid store is reused untouched (idempotent, E2); missing or ambiguous bootstrap — the walkthrough records the failure on disk verbatim and blocks instead of improvising (E7); error — any failing command is recorded verbatim in the proof, never smoothed over; success — status names branch `gsd-path/M002` and milestone `post-ship-hardening` with M001 recorded shipped/archived, the governor exits 0, the freshness tests pass, and `.project/build/M002-ACCEPTANCE-PROOF.md` holds each command with its real output, produced by a session with no chat history (N5).
Walkthrough:
1. Open a fresh session given only the repository and the pointer to the post-ship report's "Fresh-session bootstrap"; follow it exactly — restore/verify the pinned runtime, then run the three commands in order.
2. Confirm status recognizes branch `gsd-path/M002`, milestone `post-ship-hardening`, and the shipped/archived M001 (ship commit `886a36a8`, integration `4e0cd4db`).
3. Confirm the governor exits 0 and the freshness pytest passes; open `.project/build/M002-ACCEPTANCE-PROOF.md` and confirm it records exactly these commands with their real outputs (SC5, N5).

### GitHub Actions (repository-quality run on main: job result, governor diagnostics) — T001

Criteria: SC1, SC3
Entry: the Actions run page for a push to `main` of `repository-quality`; the migration-layer-quality job (restore → suite steps → governor step) and the rust-harness-quality job's harness-test step.
States: runtime absent (pre-fix behavior) — the governor step fails `runtime-unavailable` and, after this milestone, the diagnostic JSON is published and printed instead of hidden; digest mismatch or missing archive — the restore step fails the job loudly naming the recorded version+digest pair from `.gsd-path/runtime.json` (E1, N1); running — restore precedes every operational check in both jobs that run the live suites; success — on main the governor step is green with the report's workflow-state-surface observed carrying `kind=shipped-integrated;` and the archive path, exit 0 (SC1); governor failure — the `governor-diagnostics` artifact is published, the JSON is printed to the job log, and the job exit stays non-zero (SC3, N3). PR-triggered runs check out a detached merge ref where the documented fail-closed branch ownership fires; red PR runs with published diagnostics are the documented honest behavior, not a defect.
Walkthrough:
1. Open the latest push-to-main run of `repository-quality` and confirm both the migration-layer-quality and rust-harness-quality jobs executed the runtime-restore step before their operational checks.
2. Confirm the migration job's governor step is green on main and its log shows the governor exiting 0 with `kind=shipped-integrated;` and the archive path `.project/archive/001-001-native-workflow-acceptance` in the workflow-state-surface observed (SC1).
3. Inspect the workflow definition for the failure path: the governor step pipes the report to the log with `pipefail`, the `governor-diagnostics` artifact step carries `if: failure()`, and no step adds a suppression (`|| true`, `continue-on-error`) around the restore or the governor exit (SC3, E5, N3).

## Intent coverage

| Criterion | Task | Acceptance |
|-----------|------|------------|
| SC1 | T001 | AC1 |
| SC1 | T001 | AC2 |
| SC1 | T001 | AC4 |
| SC1 | T002 | AC1 |
| SC1 | T002 | AC2 |
| SC2 | T003 | AC1 |
| SC2 | T003 | AC2 |
| SC2 | T003 | AC3 |
| SC2 | T003 | AC4 |
| SC3 | T001 | AC3 |
| SC4 | T004 | AC1 |
| SC4 | T004 | AC2 |
| SC4 | T004 | AC3 |
| SC4 | T004 | AC4 |
| SC4 | T004 | AC5 |
| SC5 | T005 | AC1 |
| SC5 | T005 | AC2 |
| SC5 | T005 | AC3 |

## Held-out checks

| Edge | Task | Test |
|------|------|------|
| E1 | T001 | tests/test_ci_runtime_restore.py |
| E4 | T003 | tests/test_branch_context.py |
| E6 | T004 | tests/test_post_ship_pointers.py |

## Dependency notes

- T001 depends on T002 — data edge: the workflow's shipped-main assertion and T001's wiring test consume the exact observed format `kind=shipped-integrated;` and the archive path fixed in Contract A; without T002 the assertion would pin a state the adapter can never report. A reviewer sees the string in both the workflow step and T002's governor finding.
- T003 depends on T002 — data edge: the shipped-main scenario group imports `WorkflowStateKind.SHIPPED_INTEGRATED` and pins the pass contract from Contract A; same wave, dispatched in the layer after T002 lands. A reviewer sees the import and the pinned kind value.
- T005 depends on T001 — data edge: the walkthrough executes Contract B's restore procedure against the tracked vendored archive and records its idempotent result (E2). A reviewer sees the same command lines in the report's bootstrap section, the workflow restore steps, and the proof.
- T005 depends on T004 — data edge: the walkthrough follows Contract D's "Fresh-session bootstrap" section and records recognition of the M002 continuation that T004's roadmap/report updates establish. A reviewer sees the section heading and the exact commands identical on both sides.
- No other edges: T002 and T004 are independent by the data test — T004 consumes no symbol or file of T002 (its report describes current state in prose; its Verify runs file/roadmap tests only), and T001/T003 consume no file of T004. Narrative order ("pointers before acceptance") is enforced only where it is a real edge: T005 consumes T004's bootstrap section, so the dep is declared there and nowhere else.
- Branch-locked live claims: task Verify commands stay hermetic. The one live-main evidence run available to a coder (governor exit 0 on a fresh named-branch checkout of 4e0cd4db with the restored runtime) is recorded, optional supporting evidence in T002's Log, never a Verify; the binding CI proof of SC1's main contract is the recorded repository-quality run at ship.
