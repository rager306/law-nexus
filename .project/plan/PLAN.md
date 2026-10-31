# Plan — law-nexus

<!-- Written by the orchestrator (quick mode). Executed wave-by-wave by /gsd-path-build. -->

Project verify: `cargo fmt --all --check && cargo test --workspace --offline && uv run --frozen pytest tests/test_post_ship_pointers.py tests/test_project_state_roadmap_freshness.py tests/test_repository_quality_gate.py -q`
<!-- Run once at ship, in a fresh sidecar worktree at the reviewed commit. -->

## Config

- max_review_cycles: 3
- wave_budget: none
- review_panel: off
- finding_skeptics: off

## Wave 1 — reference-package surface and honest front door

Goal: prove the reference package user scenario end-to-end on the tracked fixture through the product CLI (build/check, exit contract 0/2/3/6, determinism, input immutability, edition-50 applicability) and make the front-door documentation agree with the shipped reality.
Review depth: full

## Surface contract

### terminal CLI — T001

Criteria: SC1, SC2, SC3, SC4, SC5, SC6, SC7
Entry: `law-nexus-inspect reference-package build|check --corpus-dir <dir> --catalog <sqlite> --out-dir <dir>`; `cargo run -q -p ln-product-cli -- health`
States: ok (exit 0), byte drift (exit 6), unreadable/missing input incl. empty corpus dir (exit 3), invalid argv (exit 2), measurements not applicable (exit 0 with explicit marking)
Walkthrough:
1. Run build on the tracked measure-ed50 fixture and catalog; observe exit 0 and the artifact set in the out-dir.
2. Run check on the unmodified package; observe exit 0.
3. Modify one artifact byte; run check; observe exit 6. Restore; observe exit 0.
4. Remove the catalog; run build; observe exit 3. Pass an unknown flag; observe exit 2.
5. Run against a corpus without edition 50; observe the explicit not-applicable report and exit 0.
6. Run `cargo run -q -p ln-product-cli -- health` exactly as README writes it; observe exit 0.

## Intent coverage

| Criterion | Task | Acceptance |
|-----------|------|------------|
| SC1 | T001 | AC1 |
| SC2 | T001 | AC2 |
| SC3 | T001 | AC3 |
| SC4 | T001 | AC4 |
| SC5 | T001 | AC5 |
| SC6 | T001 | AC6 |
| SC7 | T001 | AC7 |
| SC8 | T002 | AC1 |
| SC9 | T002 | AC2 |

## Held-out checks

| Edge | Task | Test |
|------|------|------|
| E1 | T001 | crates/ln-product-cli/tests/reference_package_cli.rs::build_same_dir_twice_is_idempotent |
| E2 | T001 | crates/ln-product-cli/tests/reference_package_cli.rs::truncated_artifact_is_drift_exit_6 |

## Dependency notes

- T002 depends on T001's landed effect: SC9 links the fixture, the named test path `crates/ln-product-cli/tests/reference_package_cli.rs`, and a recorded check result that exists only after T001 lands. A reviewer sees the links resolve to the landed test and its recorded run in the task Log.
