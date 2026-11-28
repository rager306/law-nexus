# Code Review Report — PR1: Zero-Dependency Deterministic `ln-fsm` Core & Live Migrations

- **Date:** 2026-11-28
- **Branch:** `feat/ln-fsm-core`
- **Plan:** `.compound-engineering/artifacts/plans/2026-11-28-0016-adr-0032-ln-fsm-change-grammar-spike-plan.md` (`PR1`, units `U1`–`U2`)
- **Review depth:** `full` (`exec_nontest_lines=398` + new `crates/ln-fsm/`, `size_band=large`, `hard_block_full=true`)
- **Reviewers:** 3 independent subagents (`Correctness Code Reviewer`, `Testing Code Reviewer`, `Project Standards Reviewer`)
- **Verdict:** **Ready to merge** (all P1/P2/P3 findings resolved and verified before push)

## Summary of Findings Resolved Locally

| # | Severity | Reviewer | Area | Fix Applied |
|---|---|---|---|---|
| 1 | P1 | Correctness | `crates/ln-fsm/src/model_check.rs` | Passed captured `SequenceError` directly into `shrink_sequence` instead of re-running `.expect_err(...)`, preventing panics when catching non-deterministic (`INV-01`) machines. |
| 2 | P1 | Testing | `crates/ln-decode/tests/fsm_graph_contracts.rs` | Replaced tautological `state.is_terminal()` branch with `SPEC.terminals.contains(&state.as_str())` and asserted `fsm.is_terminal(&state) == declared_terminal` plus `rej.reason` and `policy_version`. |
| 3 | P1 | Testing | `crates/ln-fsm/tests/fsm_contracts.rs` | Added mid-sequence halt, empty-sequence, and all-accepted `replay` tests asserting exact `traces.len()` and `final_state`. |
| 4 | P1 | Testing | `crates/ln-fsm/tests/fsm_contracts.rs` | Added full coverage of all `GraphDefect` variants, `allow_guarded_branching: true`, degenerate `model_check` configs, and built-in `INV-01` / `INV-10` / `TerminalState` safety detectors. |
| 5 | P2 | Correctness | `crates/ln-fsm/src/graph.rs` | Added validation for `UnknownForbiddenEdgeEndpoint`, `DuplicateEdge`, `DuplicateTerminalState`, `InitialStateIsTerminal`, and `NonTerminalSelfLoopTrap`; iterated `&known_states` to avoid duplicate reachability defects. |
| 6 | P2 | Correctness | `crates/ln-fsm/src/model_check.rs` | Added `is_terminal` determinism check and converse check forbidding non-terminal states from returning `RejectionKind::TerminalState`. |
| 7 | P2 | Testing | `crates/ln-decode/tests/fsm_graph_contracts.rs` | Increased `ContextPhaseFsm` model-check `max_len` to `64` and asserted `accepted_steps > 0`, `rejected_steps > 0`, and terminal reachability. |
| 8 | P3 | Correctness & Standards | `ln-fsm`, `Cargo.toml`, plan doc | Used 64-bit portable modulo in `SplitMix64::gen_range`, fixed-point 1-minimal shrinking in `shrink_sequence`, `#[must_use]` on `ReplayOutcome`, exhaustive enum match guards in domain tests, updated `Cargo.toml` comment (`48`), and aligned PR1 plan wording. |

## Verification Evidence (Post-Fix)

- `cargo fmt --all -- --check`: PASS
- `cargo clippy -p ln-fsm -p ln-work -p ln-decode --offline --all-targets -- -D warnings`: PASS
- `cargo test -p ln-fsm -p ln-work -p ln-decode --offline` (targeted suites): PASS
- `uv run --frozen python scripts/verify-crate-dependency-allowlist.py`: PASS (`observed_edge_count=57`, `finding_count=0`)
- `uv run --frozen python -m law_nexus_harness.governor --fail-on-warn`: PASS (`73` checks, `0` errors, `0` warnings)
- `cargo deny --offline check -D unsound advisories licenses bans sources` & `cargo shear`: PASS

## Non-Claims

- `ln-fsm` is a domain-neutral support crate, not a KOF-DA owner (ADR-0011).
- No D098 lifecycle tag is promoted to `[validated]`.
