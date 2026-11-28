# Code Review Report — ADR-0032 Wave 2 PR-A: Header-Scoped ChangeGrammar, Commutative Multi-Act Fold & Real 2-Act Zero-Drift Proof

- **Date:** 2026-11-28
- **Branch:** `feat/adr-0032-change-grammar-and-multi-act-fold`
- **Plan:** `.compound-engineering/artifacts/plans/2026-11-28-0017-adr-0032-change-grammar-multi-act-fold-and-fsm-wiring-plan.md` (`PR-A`)
- **Review depth:** `full` (`change_grammar.rs`, `amendment_compiler.rs`, and all contract + proving spike tests)
- **Reviewers:** 2 independent subagents (`PR-A Correctness Reviewer`, `PR-A Testing & Standards Reviewer`)
- **Verdict:** **Ready to merge** (all 4 P1, 3 P2, and P3 findings resolved and verified before push)

## Summary of Findings Resolved Locally

| # | Severity | Reviewer | Area | Fix Applied |
|---|---|---|---|---|
| 1 | P1 | Correctness & Testing | `amendment_compiler.rs` | Replaced 2-order simulation with exhaustive Heap's-algorithm verification across all `n! <= 24` op-level permutations for `bucket.len() <= 4` (and fail-closed `OrderingConflict` for `> 4` ops), closing 3-act cross-boundary anchor synthesis, `DeleteText` anchor synthesis, and multi-op intra/cross-act interleavings. |
| 2 | P1 | Correctness & Testing | `change_grammar.rs` | Added even quote-parity tracking (`seen_quotes.is_multiple_of(2)`) in `find_next_quote`, required `;`/`.` closes to check remainder boundaries like `,`, and restricted non-boundary fallback strictly to unnested 2-quote pairs (`seen_quotes == 2`), preventing odd/unclosed nested quotes from emitting corrupted candidates. |
| 3 | P1 | Correctness & Testing | `change_grammar.rs` | Hardened `extract_header_initial_scope`: added `ФКЗ`/`РСФСР`, word-bounded matching (`find_word_bounded_ci_span`), hard cap before `" от "`/`(`/quotes so СЗ РФ citations never leak into `act_scope`, and stripped Code-Part suffixes (`части первой/второй/третьей/четвертой`) before `*кодекс*` markers; moved `.filter` inside `.find_map`. |
| 4 | P1 | Correctness & Testing | `change_grammar.rs` | Changed `numbered_scope` and `lettered_scope` to `Option<StructuralLocator>` so refused container headers poison child scope (`None` -> `AmbiguousTarget`) instead of falling back onto non-empty `act_scope`/`numbered_scope`. |
| 5 | P2 | Correctness & Testing | `change_grammar.rs` | Guarded Case 3 (`дополнить ... следующего содержания:`) with `body[prefix_end..].starts_with("дополнить ")` so compound colon-terminated clauses never silently drop leading inline operations. |
| 6 | P2 | Correctness & Testing | `change_grammar.rs` | Normalized quote-merged `Punct` separators (`",`, `"-"`) and extended `is_second_id` with Russian ordinals and single-letter `Podpunkt` markers (`«а» и «б»`, `в абзаце первом и втором`) in `extract_structural_steps_checked`. |
| 7 | P2/P3 | Testing & Standards | Tests & Plan | Added deterministic offline tests for nested/unclosed ASCII quotes, Code Parts, ФКЗ, poisoned scopes, 3-act commutativity & traps, multi-op interleavings, `DeleteText` synthesis traps, and `>4`-op buckets; aligned plan `2026-11-28-0017` and `non_claims`/skip-log assertions. |

## Verification Evidence (Post-Fix)

- `cargo fmt --all -- --check`: PASS
- `cargo clippy -p ln-decode -p ln-temporal -p ln-testkit --offline --all-targets -- -D warnings`: PASS
- `cargo test -p ln-decode --offline --test change_grammar_contracts`: PASS (`7/7`, incl. real `138-ФЗ` 2/0, `333-ФЗ` 4/0, `432-ФЗ` 2/0, `124-ФЗ` 9/0, `484-ФЗ` 51/4, `494-ФЗ` 102/4)
- `cargo test -p ln-temporal --offline --test amendment_compiler_contracts`: PASS (`4/4`)
- `cargo test -p ln-testkit --offline --test adr0032_vertical_proving_spike`: PASS (`4/4`, incl. real 2-act `44-ФЗ ed-0112 + 484-ФЗ + 124-ФЗ -> ed-0113` `7/7 matched`, `drift = 0`)
- `law_nexus_harness.governor --fail-on-warn`: PASS

## Non-Claims (D098)

- All ADR-0032 outputs remain `[proposed]` / `[bounded]`; zero new external crates added to `Cargo.lock`.
