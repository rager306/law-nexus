# Code Review Report — PR3: Fields-Carrying Temporal FSMs, Deterministic Compiler Fold & ADR-0032 Vertical Proving Spike

- **Date:** 2026-11-28
- **Branch:** `feat/adr-0032-compiler-fold-spike`
- **Plan:** `.compound-engineering/artifacts/plans/2026-11-28-0016-adr-0032-ln-fsm-change-grammar-spike-plan.md` (`PR3`, units `U5`–`U7`, ADR-0032 D4)
- **Review depth:** `full` (`crates/ln-temporal/src/{lifecycle_fsms,amendment_compiler}.rs` + `ln-temporal` & `ln-testkit` contract/spike tests)
- **Reviewers:** 2 independent subagents (`PR3 Correctness & Invariants Reviewer`, `PR3 Testing & Standards Reviewer`)
- **Verdict:** **Ready to merge** (all P1/P2/P3 findings resolved and verified before push)

## Summary of Findings Resolved Locally

| # | Severity | Reviewer | Area | Fix Applied |
|---|---|---|---|---|
| 1 | P1 | Correctness & Testing | `lifecycle_fsms.rs` | Removed unauthorized `Validated -> Rejected` edge per `prd/architecture/assertion-lifecycle-contract.yaml:160-162`, added explicit `ForbiddenEdge`s (`Validated -> Rejected`, `AuthoritativeInternal -> Rejected`, demotions), mapped `Proposed -> AuthoritativeInternal` to `SkipLifecycle`, aligned `AssertionLifecycleRefusal` to the closed E.2.7 3-token set, removed dead `PendingEffectRefusal::InvalidTransition`, and added non-empty guards for `rationale`/`reason`. |
| 2 | P1 | Testing | `lifecycle_fsm_contracts.rs` | Added compile-time exhaustiveness guards (`assert_exhaustive_*`) and full `ALL_STATES × ALL_EVENTS` `GraphSpec` bijection checks plus guard-rejection and E.2.7 refusal tests for both `PendingEffectFsm` and `AssertionLifecycleFsm`. |
| 3 | P1 | Correctness | `amendment_compiler.rs` | Replaced delimiter-separated `compute_root_hash` with collision-free length-prefixed SHA-256 committing to stable enum byte tags, `preserved_mentions` (`INV-06`), exclusion counts, and `audit` outcomes. |
| 4 | P1 | Correctness & Testing | `amendment_compiler.rs` | Blocked `Attach` onto existing active components OR repealed tombstones (`contains_key` guard preserving `MC-REPEAL`/`INV-06`), rejected empty `target_locator`, rejected duplicate `BaseComponent` seeds (`BaseVersionMismatch`) and duplicate `op_id` (`PreconditionMismatch`), implemented `INV-03` `ApplyOutcome::OrderingConflict` for same-day multi-act contention on the same target, and checked `recorded_day > known_as_of` first (`INV-05`). |
| 5 | P1 | Testing | `amendment_compiler_contracts.rs` | Added comprehensive offline suite covering every `ApplyOutcome`, `TextAnchorMode`, `DiscrepancyKind`, `AssertionFoldStatus`, `INV-02` permutation invariance, `INV-03` `OrderingConflict`, delimiter-collision resistance, and `INV-06` mention hashing. |
| 6 | P2 | Correctness | `amendment_compiler.rs` | Extended `OracleComponentExpectation` with `expected_presence: EditorialPresence` and `expected_text: Option<String>` to verify all four `MC-REPEAL` axes on `Tombstone` and allow missing components on `Absent`; hardened `EndOfComponent` (empty base & double-terminator prevention) and `DeleteText` (local splice space collapse preserving untouched NBSP + `ExactAnchor` validation). |
| 7 | P2/P3 | Testing & Correctness | `adr0032_vertical_proving_spike.rs` | Fixed `clippy::inconsistent-digit-grouping` (`20241226`), updated `[smoke]` doc/name to reflect honest `1 matched (drift=0 on п. 8) + 1 TextMismatch (п. 8.1)`, pinned `non_claims`, and clarified synthetic 402-ФЗ control scoping. |

## Verification Evidence (Post-Fix)

- `cargo fmt --all -- --check`: PASS
- `cargo clippy -p ln-temporal -p ln-testkit --offline --all-targets -- -D warnings`: PASS
- `cargo test -p ln-temporal --offline --test lifecycle_fsm_contracts --test amendment_compiler_contracts`: PASS
- `cargo test -p ln-testkit --offline --test adr0032_vertical_proving_spike`: PASS (offline 44-ФЗ + synthetic 402-ФЗ + `[smoke]` real `ed-0112 + 484-ФЗ -> ed-0113`)
- `scripts/verify-crate-dependency-allowlist.py`: PASS (`observed_edge_count=58`, `finding_count=0`)
- `law_nexus_harness.governor --fail-on-warn`: PASS (`73` checks, `0` errors, `0` warnings)

## Non-Claims

- All ADR-0032 outputs remain `[proposed]`; no `RC28-F13`/`RC28-F17` or `TSG-*` closure is claimed automatically.
