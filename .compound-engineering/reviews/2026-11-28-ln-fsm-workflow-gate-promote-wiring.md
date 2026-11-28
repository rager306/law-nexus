# Code Review Report — ADR-0032 Wave 2 PR-B: `ln-fsm` Wiring for `ln-promote`, `ln-gate`, and `ln-dispose`

- **Date:** 2026-11-28
- **Branch:** `feat/ln-fsm-workflow-gate-promote-wiring`
- **Plan:** `.compound-engineering/artifacts/plans/2026-11-28-0017-adr-0032-change-grammar-multi-act-fold-and-fsm-wiring-plan.md` (`PR-B`)
- **Review depth:** `full` (`crates/ln-{promote,gate,dispose}/src/{domain,application}.rs`, `fsm_graph_contracts.rs`, `Cargo.toml`, `Cargo.lock`, `prd/architecture/crate-dependency-allowlist.json`)
- **Reviewers:** 2 independent subagents (`PR-B Correctness Reviewer`, `PR-B Testing & Standards Reviewer`)
- **Verdict:** **Ready to merge** (all P1, P2, and P3 findings resolved and verified before push)

## Summary of Findings Resolved Locally

| # | Severity | Reviewer | Area | Fix Applied |
|---|---|---|---|---|
| 1 | P1 | Correctness | `ln-dispose/src/application.rs` | Added authoritative in-process `dispositions: HashMap<String, Disposition>` ledger to `DisposeReview` (matching `ln-promote` and `ln-gate`) and enforced fail-closed promotion rejection when `!accepted` regardless of hostile/lossy store or gate adapters. |
| 2 | P1 | Correctness | `ln-dispose/src/application.rs` | Guarded `set_pending` and `set_quarantined` against overwriting terminal `Accepted`/`Rejected` dispositions and routed `store_set_accepted` through `transition_disposition(..., DispositionEvent::Accept, ...)`. |
| 3 | P1 | Testing & Standards | `ln-{promote,gate,dispose}/tests/fsm_graph_contracts.rs` | Added full application-level integration tests: `GateLifecycle::request_transition` (demotion, re-promotion of `VerifiedAssertion`, self-demotion, `< 90` `MissingEvidenceChain`), `CommitCuratedPromotion` (repeated `cancel()`, unknown `cancel()`, `cancel()`/`begin()` after `commit()`), and `DisposeReview` (all rejection paths, `attempt_promotion` after every transition, hostile spoofing store + always-commit gate). |
| 4 | P2 | Correctness & Testing | `ln-promote/src/application.rs` | Replaced `if let Ok` / `Err(_)` with exhaustive `PromotionTransitionRefusal` matching in both `cancel()` and `commit()` so `AlreadyCommitted` can never wipe commit fields or return `Cancelled`. |
| 5 | P2 | Correctness | `ln-gate/src/{domain,application}.rs` | Introduced dedicated `GateTransitionRefusal` (`InPlaceMutation`, `ConfidenceOnly`, `MissingEvidenceChain`, `TerminalLifecycleImmutable`, `InvalidLifecycleTransition`) and corresponding `GateReason` variants so `EvidenceChainSatisfied` is unrepresentable as an FSM refusal and non-in-place terminal/demotion refusals never misreport `"in-place-mutation"`. |
| 6 | P2/P3 | Testing & Correctness | `fsm_graph_contracts.rs` & `ln-dispose/src/domain.rs` | Added symmetric `rejected -> pending/quarantined` `ForbiddenEdge`s, strengthened model-check invariants + `committed_reached > 0`, destructured all fields in `assert_exhaustive`, pinned `90`/`89` confidence boundary, and asserted `rej.trace.policy_version` + `rej.trace.to.is_none()` across all 3 suites. |

## Verification Evidence (Post-Fix)

- `cargo fmt --all -- --check`: PASS
- `cargo clippy -p ln-promote -p ln-gate -p ln-dispose -p ln-hc03-runner -p ln-hc04-runner -p ln-hc06-runner --offline --all-targets -- -D warnings`: PASS
- `cargo test -p ln-promote -p ln-gate -p ln-dispose --offline`: PASS
- `cargo deny --offline check -D unsound advisories licenses bans sources` & `cargo shear`: PASS
- `scripts/verify-crate-dependency-allowlist.py`: PASS (`observed_edge_count=61`, `finding_count=0`)
- `law_nexus_harness.governor --fail-on-warn`: PASS

## Non-Claims (D098)

- Zero new external crates added to `Cargo.lock` (local `ln-fsm` edges only); HC-03/HC-04/HC-06 lifecycle honesty unchanged.
