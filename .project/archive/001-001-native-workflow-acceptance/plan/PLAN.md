# Plan — law-nexus, milestone 001-native-workflow-acceptance

<!-- Written by the planner role (GSD Path plan, 2026-10-26). Executed
     wave-by-wave by the build orchestrator. Task id, title, deps, and files
     live only in each `.project/tasks/T###-slug.md` frontmatter; `wave: N`
     there assigns the task to a wave here. -->

Project verify: `uv sync --frozen && cargo fmt --all -- --check && cargo clippy --workspace --offline --all-targets -- -D warnings && cargo build --workspace --offline && cargo test --workspace --offline && uv run ruff check src/ && uv run ruff format --check src/ && uv run basedpyright src/ && uv run ty check src/ && uv run pyrefly check src/ && uv run python scripts/verify-crate-dependency-allowlist.py && uv run python scripts/verify-adr-conformance.py && uv run pytest -q tests/test_harness_subprocess_failure_modes.py tests/test_harness_status_tracer.py tests/test_harness_governor.py tests/test_harness_preflight.py tests/test_harness_review_case_cli.py tests/test_review_case_governor.py tests/test_review_case_schema.py tests/test_review_case_delta_fixture.py tests/test_verify_crate_dependency_allowlist.py tests/test_verify_port_contract_coverage.py tests/test_verify_hostile_negative_suite_coverage.py tests/test_verify_multi_adapter_port_coverage.py tests/test_verify_live_adapter_readiness.py tests/test_architecture_views.py tests/test_architecture_analysis_views.py tests/test_architecture_remediation_matrix.py tests/test_architecture_track_split.py tests/test_architecture_closure_roadmap.py tests/test_architecture_registry_schema.py tests/test_verify_adr_conformance.py tests/test_harness_workflow_state.py tests/test_phase_dispatch_adapter.py tests/test_verify_source_snapshot_v2.py tests/test_harness_cli_entrypoints.py tests/test_harness_no_forbidden_imports.py tests/test_documentation_navigation.py tests/test_repository_quality_gate.py tests/test_project_state_roadmap_freshness.py tests/test_path_isolation_recovery.py tests/test_m225_validation_residual.py tests/test_product_model.py tests/test_gitnexus_block_receipt.py tests/test_m001_cutover_readiness.py`

<!-- Run once at ship, in a fresh sidecar worktree at the reviewed commit.
     This is exactly CI's hermetic green surface (repository-quality.yml,
     portable parts of all three jobs) plus this milestone's own tests.
     Corpus-dependent Rust suites skip visibly by design; the advisory M207
     batteries and the strict corpus job are deliberately absent — green here
     never proves corpus scenarios ran. The live-governor and environment-bound
     suites are excluded because a verify sidecar sits on a different branch
     and the governor fails closed there by design. -->

## Config

- max_review_cycles: 3
- wave_budget: none
- review_panel: off
- finding_skeptics: off

## Wave 1 — risk burn-down

Goal: Burn the three plan-invalidating risks SYNTHESIS names. (1) Five-fix landing integrity: the canonical patches from the preserved copies outside the repository apply cleanly to the base and land as real task commits on gsd-path/M001, with SC1's exact command green — tree-vs-patch drift is the assumption to burn first. (2) The de-suppressed m207 schema check runs green as a blocking step, or its unknown failures surface here while fix capacity remains in the wave. (3) Marker sync (SC2): the workflow marker and roadmap data name this Path milestone exactly, so the branch-locked, fail-closed governor gates every later native claim with 0 errors on the bound branch.

Review depth: full

## Wave 2 — independent evidence residuals

Goal: Close the four mutually independent evidence residuals. T004 fills the M225 battery pin with a full 40-hex SHA, re-runs the hermetic validation surface natively, and records the honest verdict with its measurement class (E3, N1). T005 creates the minimal PDD model under product-model/ so the AGENTS.md and docs/agent-stack/WORKFLOW.md claims become true, stubs modeled as stubs (E4, N5). T006 re-indexes GitNexus on the primary worktree and regenerates the AGENTS.md tool block with a tracked receipt, never hand-edited (E5, N6). T010 rewords the law-source/consultant/README.md claim naming the never-built governor probe law-source-corpus-glob-guard so it states only what the existing law-source-fixture-guard covers (audit #16, fix-doc ruling), and marks the alignment-queue row planned. A failure here blocks only its own criterion.

Review depth: full

## Wave 3 — native cycle proof and publication

Goal: Prove the native workflow end to end. The deliberately trivial SC10 junk-file deletion runs the full native cycle — dispatch, worker, native validators, independent review with a different evidence path or model family (E6, N7) — with evidence recorded under .project/ (SC6). The session closes with a handoff and a fresh session resumes from disk alone, its recorded verification output on disk (SC7). The bound branch is published, CI confirmed within the documented policy with at most one rerun for a red run (E8), and the written cutover readiness assessment lands with cutover still false (SC8, N2).

Review depth: full

## Surface contract

### terminal (native Path CLI: path-run.py status, governor, pytest, git) — T008

Criteria: SC7
Entry: a terminal in the primary worktree on the bound branch gsd-path/M001; the commands python3 scripts/ai/path-run.py status, uv run --frozen python -m law_nexus_harness.governor, uv run --frozen pytest, and git log / git status.
States: missing state — status fails closed and says so instead of reporting a silent green; running — status prints the phase and route for milestone 001-native-workflow-acceptance on gsd-path/M001; error — the governor exits non-zero and names the failing check (away from the bound branch the documented fail-closed branch-ownership error is expected behavior, not a defect); success — the governor reports 0 errors on the bound branch, the marker pytest passes, and the fresh resume session's recorded verification output is on disk at .project/build/M001-RESUME-PROOF.md (relocated by the owner-ruled pre-ship relocation commit).
Walkthrough:
1. Open a fresh terminal session with only the repository on disk (no conversation context), run python3 scripts/ai/path-run.py status, and confirm it reports branch gsd-path/M001 and milestone 001-native-workflow-acceptance.
2. Run uv run --frozen python -m law_nexus_harness.governor and confirm it exits 0 with 0 errors.
3. Run uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q and confirm the native marker test passes.
4. Open .project/build/M001-RESUME-PROOF.md and confirm it records exactly these commands with their real outputs, produced by the fresh resume session (SC7, N8).

### GitHub (gsd-path/M001 branch, commit history, CI runs) — T009

Criteria: SC8
Entry: the origin repository rager306/law-nexus — the gsd-path/M001 branch view, its commit history, and its Actions runs.
States: branch absent — not yet published (before T009); CI running or red-once — one rerun is allowed for a red run (E8); persistently red — SC8 is unmet unless the failing job is a documented advisory surface and the assessment records it as such; success — the branch is published, the head run is green within policy (M207 batteries report-only, corpus-integration skipped and documented), and the history shows the M001 task landings followed by the single ship commit at integration.
Walkthrough:
1. Open the branch view for gsd-path/M001 on origin and confirm the M001 task commits (T001 through T008) are present in history.
2. Open the Actions run for the pushed head and confirm the portable jobs are green, the M207 batteries are report-only, and the corpus-integration job is skipped as its own comment documents.
3. Compare the run against the CI evidence table in docs/agent-stack/CUTOVER-READINESS-M001.md — at most one rerun per red run (E8) — and confirm the assessment states that green CI does not prove corpus scenarios ran and that cutover remains false.

## Intent coverage

| Criterion | Task | Acceptance |
|-----------|------|------------|
| SC1 | T001 | AC2 |
| SC1 | T011 | AC3 |
| SC2 | T002 | AC1 |
| SC3 | T004 | AC1 |
| SC4 | T005 | AC2 |
| SC5 | T006 | AC2 |
| SC6 | T007 | AC2 |
| SC7 | T008 | AC2 |
| SC8 | T009 | AC2 |
| SC9 | T003 | AC1 |
| SC10 | T007 | AC1 |

## Held-out checks

| Edge | Task | Test |
|------|------|------|
| E1 | T001 | tests/test_path_isolation_recovery.py |
| E3 | T004 | tests/test_m225_validation_residual.py |
| E5 | T006 | tests/test_gitnexus_block_receipt.py |
| E8 | T009 | tests/test_m001_cutover_readiness.py |
| E9 | T003 | tests/test_harness_workflow_state.py |

## Dependency notes

- T008 depends on T007 — data edge: T007 writes the session handoff at the exact path and with the exact sections fixed in both tasks' Interface contract; T008's fresh session consumes only that file plus the repository on disk. A reviewer sees the handoff in T007's landing commit and the proof file citing it in T008's.
- T009 depends on T007 and T008 — prerequisite effect: the push publishes the bound-branch tip containing every M001 landing, and the readiness assessment records the cycle and resume evidence. A reviewer sees the published history containing the T001–T008 landings and the assessment's evidence section citing them.
- T006 depends on T004 and T005 — prerequisite effect, not narrative order: the GitNexus index is machine-local (the whole excluded .gitnexus tree is absent from every sidecar), so the re-index must run in a serial dispatch round on the bound branch in the primary worktree. Once T004 and T005 have landed, T006 is the only ready task and dispatches serially; a parallel round would strand the index in a retired sidecar. The receipt's indexed head on the bound-branch lineage is the reviewer-visible evidence.
- No other edges: wave-1 tasks (T001, T002, T003) touch disjoint files and exchange nothing; T004 and T005 are independent of wave 1 by the data test — none consumes a symbol, file, or landed effect of another task.
- SC10 placement: SYNTHESIS "For the planner" lists SC10 in its wave-1 shorthand and also names the junk-file deletion "the natural carrier" of the SC6 + SC7 walking skeleton in the final wave. The planner owns the exact split: the deletion is T007, the wave-3 cycle carrier, because its whole value is the recorded native cycle around it (SC6), not the deletion itself; wave 1 carries the three real blockers instead.
- Pre-dispatch neutralization for T001: the five fixed files sit uncommitted in the primary worktree (the guard blocks product-file commits outside build) and task isolation requires a clean primary. Before the first dispatch the orchestrator confirms the five files' diffs are exactly the canonical patches preserved outside the repository (the 2026-10-26 handoff recorded all three patch signatures), records that confirmation, then restores the five files to HEAD so the base is clean; T001 re-applies the patches inside its isolated task. If the diffs do not match the canonical patches, that is the tree-vs-patch drift SYNTHESIS warns about: stop and ask the owner.
- Branch-locked governor: task Verify commands never invoke the live governor, because a verify sidecar sits on a different branch by design and the governor fails closed there. Bound-branch governor claims (SC2's 0 errors, SC7's resume proof) are recorded runs on gsd-path/M001 in the primary worktree, cited from the task Log and the resume proof.

## Wave 4 — verify-sidecar test environment contract

Goal: Close P001 (PATCH-FINDINGS.md): Project Verify is blocked at the reviewed commit f3c55d6d — 14 failures, live-governor ×12 + preflight ×2 — an environment-contract mismatch, not a product defect: the verify sidecar runs on a gsd-path-verify/* branch where the documented fail-closed branch ownership fires, while the live-governor and preflight tests assert error_count == 0 (the identical suites are green on the bound branch). Owner ruling (a) makes tests/test_harness_governor.py and tests/test_harness_preflight.py branch-environment-aware: on gsd-path/M001 the full assertions stay unchanged; on a non-operational branch the tests pin the documented fail-closed contract itself (the workflow-state-surface blocking error, honest error-count semantics) instead of error_count == 0 — no assertion weakened where the governor is operational, no suppression, no unconditional skip (N3). One Verify command covers both sides: the worker's isolate run on a governor-operational branch exercises the full-assertion path, and the orchestrator's gsd-path-verify/* verify sidecar at finish exercises the pinned-contract path — the ship gate's Project Verify passes for honest reasons in both environments without touching the fail-closed behavior it documents.

Review depth: full
