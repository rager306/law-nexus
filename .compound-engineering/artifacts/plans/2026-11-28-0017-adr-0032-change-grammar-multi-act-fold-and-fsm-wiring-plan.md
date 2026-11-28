---
title: "ADR-0032 Wave 2: ChangeGrammar Header-Scope & Sentence-Append, Commutative Multi-Act Fold, Real 2-Act Zero-Drift Proof, and ln-fsm Workflow Wiring"
date: 2026-11-28
status: active
lifecycle: "[proposed]"
plan_id: 2026-11-28-0017
parent_plan: .compound-engineering/artifacts/plans/2026-11-28-0016-adr-0032-ln-fsm-change-grammar-spike-plan.md
authority:
  - doc/adr/0032-temporal-cst-ast-core-and-change-grammar.md
  - prd/architecture/model-crystal.md
  - prd/architecture/crate-dependency-allowlist.json
---

# ADR-0032 Wave 2 Execution Plan

## Goal

Advance the ADR-0032 core model and workspace FSM uniformity across two clean, independently reviewable PRs while preserving zero new external crates in `Cargo.lock` and strict D098 `[proposed]`/`[bounded]` lifecycle honesty.

## PR-A: `feat/adr-0032-change-grammar-and-multi-act-fold`

1. **`crates/ln-decode/src/change_grammar.rs` (Clean-Room Russian Drafting Grammar Expansion — ADR-0032 D3):**
   - **Header-scoped act targets (`ActHeaderParse::HeaderScope.initial_scope` / internal `act_scope`):** extract unambiguous singular structural steps between `Внести [изменение|изменения] в ` and the word-bounded act-kind marker (`федерального закона`, `федерального конституционного закона`, `закона российской федерации`, `закона рсфср`, `*кодекса`, `указа`, `постановления`, `распоряжения`, `приказа`, `основ законодательства`) while stripping Code-Part suffixes (`части первой/второй/третьей/четвертой` before `*кодекс*`), e.g. `333-ФЗ` (`Внести в часть 1 статьи 95 Федерального закона ...:`), `432-ФЗ` (`Внести в статью 112 Федерального закона ...:`), `494-ФЗ` ст. 3 (`Внести в пункт 3 статьи 4 Федерального закона ...:`), initializing `numbered_scope` and `lettered_scope` from `act_scope` instead of resetting to empty.
   - **Inline sentence-append (`дополнить предложением следующего содержания: "..."`):** support both inline single-paragraph quotes (e.g. `484-ФЗ` ст. 1 п. 12 подп. «д») and next-line quoted blocks, emitting `ChangeOpKind::InsertText` + `ChangePositionParam::EndOfComponent`.
   - **Compound inline conjunction (`и ` / `а `):** allow optional Russian conjunctions between chained inline operations in Case 4 while preserving fail-closed `INV-10` refusals on any unparsed remainder, sentence-indexed targets, or plural/range targets.
   - **Tests (`crates/ln-decode/tests/change_grammar_contracts.rs`):** offline unit tests for header-scoped headers, inline `дополнить предложением следующего содержания: "..."`, chained `и` inline ops, and `[smoke]` real corpus checks covering `138-ФЗ`, `124-ФЗ` (`0` refusals), `333-ФЗ` (`4/4` `statya-95/chast-1/...`), `432-ФЗ` (`2/2` `statya-112/chast-{66,67}`), `484-ФЗ`, and `494-ФЗ` (multi-act law).

2. **`crates/ln-temporal/src/amendment_compiler.rs` (Commutativity-Verified Same-Day Multi-Act Composition — `INV-03` precision):**
   - Refine same-day multi-act bucket handling `(legal_effective_day, target_locator)` when `distinct_acts > 1`:
     - Verify whether ALL ops in the bucket are pure anchored text edits (`ReplaceText(ExactAnchor)`, `InsertText(AfterAnchor|BeforeAnchor)`, `DeleteText(ExactAnchor)`), the target component is currently `Active`, every anchor matches uniquely (`count == 1`), all matched byte spans are strictly separated (`prev_end < next_start`), AND no op's replacement/insertion text can create a duplicate match for any other op's anchor.
     - When provably commutative, apply deterministically in canonical `(amending_act_id, op_id)` order (`INV-02` permutation-invariant!).
     - Otherwise (any `WholeComponent`, `EndOfComponent`, `Repeal`, `Attach`, missing/ambiguous anchor, overlapping/touching byte spans, or cross-anchor interference), fail closed with `ApplyOutcome::OrderingConflict` (`INV-03`).
   - **Tests (`crates/ln-temporal/tests/amendment_compiler_contracts.rs`):** test both commuting same-day multi-act edits (strictly disjoint anchors, permutation invariance `A+B == B+A`) and non-commuting same-day multi-act conflicts (touching spans, overlapping spans, replacement creating duplicate anchor, `WholeComponent` / `Repeal` contention -> `OrderingConflict`).

3. **`crates/ln-testkit/tests/adr0032_vertical_proving_spike.rs` (Real 2-Act Zero-Drift Proof on `consru_export`):**
   - Add `[smoke]` real `consru_export` 2-act proof: `44-ФЗ edition-0112 + 484-ФЗ + 124-ФЗ -> edition-0113` (`as_of = 2025-01-01`), proving **7/7 real components with `drift = 0`** across `InsertText(AfterAnchor)`, commuting same-day `InsertText + ReplaceText(ExactAnchor)` on `punkt-8.1`, `ReplaceText(WholeComponent)` on `punkt-7` and `statya-15/chast-4`, `Attach` on `statya-15/chast-4.4`, and 4-axis `MC-REPEAL` `Tombstone` on `statya-15/chast-4.1` and `statya-15/chast-5`, plus real `INV-02` permutation invariance (`[484-ФЗ, 124-ФЗ]` vs `[124-ФЗ, 484-ФЗ]` -> identical SHA-256 `root_hash`).

## PR-B: `feat/ln-fsm-workflow-gate-promote-wiring`

Wire three core lifecycle/workflow crates identified via `codebase-memory-mcp` onto `crates/ln-fsm` with `GraphSpec` validation, `ALL_STATES × ALL_EVENTS` bijection tests, and deterministic model checking (`0` new external crates):
1. **`crates/ln-promote`** (`PromotionAttemptState`: `InProgress -> Cancelled | Committed`, `Committed` absorbing, `PublicationAuthority` never minted).
2. **`crates/ln-gate`** (`LifecycleType`: `ExtractedCandidate -> VerifiedAssertion`, C10 forbids in-place mutation and confidence-only crossing).
3. **`crates/ln-dispose`** (`DispositionState`: `Pending`, `Quarantined`, `Accepted`, `Rejected`, non-accepted states never reach promotion authorization).
4. Update `prd/architecture/crate-dependency-allowlist.json` (`ln-promote -> ln-fsm`, `ln-gate -> ln-fsm`, `ln-dispose -> ln-fsm`).

## Verification & Governance

- Multi-reviewer `ce-code-review` archived under `.compound-engineering/reviews/YYYY-MM-DD-<slug>.md` for both PRs.
- Local `cargo fmt`, `cargo clippy --all-targets -D warnings`, targeted tests, `cargo deny`, `cargo shear`, `verify-crate-dependency-allowlist.py`, `governor --fail-on-warn`, and 5/5 GitHub Actions CI before each merge.
- Refresh local GitNexus index after final merge and verify clean `main` with `just preflight`.
