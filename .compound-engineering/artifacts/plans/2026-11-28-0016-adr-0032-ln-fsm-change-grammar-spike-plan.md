---
title: "ADR-0032 Execution Plan: ln-fsm Core, Typestate DocumentContext, Clean-Room ChangeGrammar, and Compiler Fold Proving Spike"
type: feat
status: active
date: 2026-11-28
plan_id: 2026-11-28-0016
adr: ADR-0032
---

# ADR-0032 Execution Plan: `ln-fsm` Core, Typestate `DocumentContext`, Clean-Room `ChangeGrammar`, and Compiler Fold Proving Spike

## Goal

Prove the core normative-act Temporal CST/AST + `DocumentContext` + `ChangeGrammar` vertical defined in `doc/adr/0032-temporal-cst-ast-core-and-change-grammar.md` `[proposed]` end-to-end while strengthening finite-state-machine engineering across the Rust workspace with zero new runtime dependencies.

## Scope & Sequencing (3 Sequential PRs)

### PR1: Zero-Dependency Deterministic `ln-fsm` Support Crate + Live Migrations
- **Branch:** `feat/ln-fsm-core`
- **Units:**
  - **U1 (`crates/ln-fsm`):** Non-KOF-DA support crate (`unsafe_code = "forbid"` via `[lints] workspace = true`, 0 external dependencies, 0 proc-macros):
    - Fail-closed `DeterministicFsm` trait (`apply(self, event) -> ApplyResult<S, E, R>`, `INV-10`, no silent `Option<State>`).
    - `TransitionTrace<S, E>` for structured audit trails.
    - `GraphSpec` + `validate_graph(&spec)` (BFS reachability from `initial`, zero outgoing edges from `terminal`, dead-end & self-loop trap detection for non-terminal states, duplicate edge/terminal detection, explicit `forbidden_direct_edges` endpoint validation and enforcement closing the `_ => None` exhaustiveness blind spot).
    - `to_mermaid_state_diagram(&spec)` rendering `stateDiagram-v2` directly from code.
    - Deterministic built-in model-based property checker (`run_deterministic_model_check` with seeded SplitMix64 PRNG + 1-minimal sequence shrinking, offline zero-dep) checking determinism (`INV-01`), fail-closed rejections (`INV-10`), and terminal immutability.
  - **U2 (Live Consumers + Workspace Wiring):**
    - `crates/ln-decode`: integrate `ln-fsm` via `ContextPhaseFsm`/`CONTEXT_PHASE_GRAPH_SPEC` (`document_context.rs`) and `EnumerationFsm`/`ENUMERATION_GRAPH_SPEC` (`local_grammar.rs`) with backward-compatible `transition()` preserved + full bijection, graph validation, and model-based checks.
    - `crates/ln-work`: integrate `ln-fsm` via `WorkStateMachine`/`WORK_STATE_GRAPH_SPEC` (`domain.rs`) with full bijection, graph validation, and model-based checks (preserving all HC-10 contracts).
    - Update root `Cargo.toml`, `prd/architecture/crate-dependency-allowlist.json` (`ln-decode -> ln-fsm`, `ln-work -> ln-fsm`; `ln-temporal -> ln-fsm` added in PR3 U5), and `README.md` workspace member count (48; preserving zero `archive/` substrings).

### PR2: Typestate `DocumentContext` Pipeline, Optional `MorphEvidenceSet` Seam, and Clean-Room `ChangeGrammar` (ADR-0032 D2–D3)
- **Branch:** `feat/adr-0032-change-grammar`
- **Units:**
  - **U3 (Typestate Pipeline & Morphology Seam in `ln-decode`):**
    - Compile-time Typestate phase wrapper (`DocumentPipeline<Raw>` -> `<Indexed>` -> `<Analyzed>` -> `<ContextClosed>`, private fields, sealed `PipelinePhase` trait, no `Clone`/`Copy`, fallible transitions return `Err((self, err))`).
    - Explicit optional `MorphEvidenceProvider` / `MorphEvidenceSet` seam over covering `Word` tokens (ADR-0028 dual-tokenizer discipline) with `NullMorphProvider`.
  - **U4 (Clean-Room `ChangeGrammar` in `crates/ln-decode/src/change_grammar.rs`):**
    - Pure deterministic parser over covering `lex()` + hierarchical container scope stack (`OWNER / KIND / CHILD / VALUE / PARAM / LOCVALUE`, zero Pullenti code/dicts/thresholds per D380).
    - Bounded initial `MC-OPS` subset: `ReplaceText`, `InsertText`, `DeleteText`, `Attach`, `Repeal`.
    - Filters non-normative editorial notes (`КонсультантПлюс: примечание.`), handles multi-operation clauses in one item, emits fail-closed `Proposed` candidates with UTF-8 byte `EvidenceSpan` or typed `ChangeParseRefusal` (`UnsupportedOperation`, `AmbiguousTarget`, `IncompleteSource`).
    - Offline unit/hostile tests + skip-capable `[smoke]` integration test over real `484-ФЗ`, `138-ФЗ`, `333-ФЗ` in `consru_export/`.

### PR3: Fields-Carrying Temporal FSMs, Deterministic Compiler Fold, and `EditionOracle` Vertical Proving Spike (ADR-0032 D4)
- **Branch:** `feat/adr-0032-compiler-fold-spike`
- **Units:**
  - **U5 (Fields-Carrying FSMs in `ln-temporal` over `ln-fsm`):**
    - `PendingEffectState` (`Scheduled` -> `Applied | Cancelled`, `ModifyPendingEffect` only on `Scheduled`, `validate_graph` forbids `Applied`/`Cancelled` mutation).
    - `AssertionLifecycleState` (`Proposed` -> `Validated` -> `AuthoritativeInternal` | `Rejected` | `Superseded`, `validate_graph` forbids direct `Proposed -> AuthoritativeInternal` jump).
  - **U6 (Deterministic Amendment Compiler Fold & `EditionOracle` Verifier in `crates/ln-temporal/src/amendment_compiler.rs`):**
    - Applies bounded `MicroOperation` subset (`ReplaceText`, `InsertText`, `DeleteText`, `Attach`, `Repeal` with four-axis `MC-REPEAL`: `ForceStatus=Repealed`, `StructuralMembership=Absent`, `EditorialPresence=Tombstone`, `TextAvailability=HistoricalOnly`).
    - Deterministic SHA-256 `root_hash` (`INV-01`), future-effect exclusion (`INV-04`), source mention immutability (`INV-06`), closed `MC-RES` typed non-successes (`INV-10`).
    - `verify_against_edition_oracle` reporting scoped `drift = 0` and typed `Discrepancy` without rewriting canon from the oracle.
  - **U7 (Proving Spike Tests):**
    - Always-run offline vertical integration suite proving `AmendingText -> ChangeGrammar -> MicroOperation -> CompilerFold -> EditionOracle (drift = 0)` on both real `44-ФЗ` + `484-ФЗ` clause patterns and a second non-44-ФЗ control act.
    - Skip-capable `[smoke]` real-corpus verification over `consru_export` (`edition-0112` + `484-ФЗ` vs `edition-0113`/`0117`) emitting honest coverage metrics for ADR-0032 D4 kill/pivot review.

## Verification Contract (Every PR)

- `just gate` (Rust `fmt`, `clippy --workspace --offline --all-targets -D warnings`, `nextest --workspace --offline --profile ci`, `cargo deny`, `cargo shear`, `actionlint`, `zizmor`, crate allowlist, ADR conformance)
- `just governor --fail-on-warn` (`error_count=0`, `warn_count=0`)
- `ce-code-review` archived under `.compound-engineering/reviews/YYYY-MM-DD-<target-slug>.md`
- GitHub Actions `repository-quality` 5/5 green before merge.

## Non-Claims (D098)

- All ADR-0032 outputs remain `[proposed]` / `[bounded]`.
- No `RC*` finding, `TSG-*` row, or ADR lifecycle tag is promoted automatically.
- Local `consru_export` tests remain skip-capable `[smoke]` evidence.
