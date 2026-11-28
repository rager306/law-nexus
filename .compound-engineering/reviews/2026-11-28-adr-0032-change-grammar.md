# Code Review Report — PR2: Typestate `DocumentPipeline`, Optional `MorphEvidenceProvider` Seam, and Clean-Room `ChangeGrammar`

- **Date:** 2026-11-28
- **Branch:** `feat/adr-0032-change-grammar`
- **Plan:** `.compound-engineering/artifacts/plans/2026-11-28-0016-adr-0032-ln-fsm-change-grammar-spike-plan.md` (`PR2`, units `U3`–`U4`, ADR-0032 D2–D3)
- **Review depth:** `full` (`crates/ln-decode/src/{document_pipeline,change_grammar}.rs` + contract tests)
- **Reviewers:** 2 independent subagents (`PR2 Correctness Code Reviewer`, `PR2 Testing & Standards Reviewer`)
- **Verdict:** **Ready to merge** (all P0/P1/P2 findings resolved and verified before push)

## Summary of Findings Resolved Locally

| # | Severity | Reviewer | Area | Fix Applied |
|---|---|---|---|---|
| 1 | P0 | Correctness | `change_grammar.rs` | Replaced char-count offset math + `+ needle.len()` with exact UTF-8 char-aligned `find_ci_span(orig, needle_lower) -> Option<(usize, usize)>` and `body.get(cursor..)`, eliminating panics on multi-char lowercase expansions (`İ` U+0130). |
| 2 | P1 | Correctness | `change_grammar.rs` | Top-level `Статья <N>` heading now resets `current_act = None` (preventing Act 2 leakage into Act 3 transitional provisions); commencement/transitional matchers strip leading part numbers (`1. `, `8. `). |
| 3 | P1 | Correctness | `change_grammar.rs` | Unrecognized container headers (`steps.is_empty()`) now reset scope and emit `AmbiguousTarget`; `StructuralLocator::with_overlay` prunes inherited descendants `>= min(overlay.level)`; `UnmarkedClause` headers populate `numbered_scope` when empty. |
| 4 | P1 | Correctness & Testing | `change_grammar.rs` | `collect_quoted_blocks` skips editorial notes, matches opening/closing delimiter (`"` parity vs `«...»` nesting depth), rejects empty `";`, and refused `:`-clauses consume following quoted payloads. |
| 5 | P1 | Correctness & Testing | `change_grammar.rs` | Closed all silent-drop `INV-10` paths: added `"перед цифр"` to `action_prefix_end`, refused any non-empty unparsed inline remainder (`IncompleteSource` on unclosed quotes, else `UnsupportedOperation`), refused unhandled clauses inside an active act and inline-amendment headers, guarded editorial note `+1` skip to standalone note headers not followed by legislative blocks. |
| 6 | P1 | Testing | `document_pipeline_typestate.rs`, `change_grammar_contracts.rs` | Added tests for `BeforeAnchor` (`перед слов`/`перед цифр`), `EndOfComponent`, `ExactAnchor`, nested guillemets `«...»`, hostile `İ` UTF-8, empty input, editorial note at EOF, scope pruning, plural targets, and ADR-0028 dual-tokenizer `Abbrev`-exclusion + hostile `MorphEvidenceProvider` rejection. |
| 7 | P2 | Correctness & Testing | `change_grammar.rs`, `document_pipeline.rs` | Dispatched `TokenKind::Abbrev` strictly via `AbbrevId` (ADR-0028 Decision 2), restricted bare single-letter IDs to `Podpunkt`, detected plural/multi-target clauses, rejected sentence-scoped `изложить в следующей редакции`, fixed Cyrillic `"От"` date folding, normalized ordinals `1..=10` (with `ё` doublets), enforced `TokenKind::Word`-only `MorphEvidenceProvider` seam in `DocumentPipeline::into_analyzed`. |

## Verification Evidence (Post-Fix)

- `cargo fmt --all -- --check`: PASS
- `cargo clippy -p ln-decode --offline --all-targets -- -D warnings`: PASS
- `cargo test -p ln-decode --offline --test document_pipeline_typestate --test change_grammar_contracts --test fsm_graph_contracts`: PASS (incl. `[smoke]` real `138-ФЗ` & `484-ФЗ`)
- `uv run --frozen python -m law_nexus_harness.governor --fail-on-warn`: PASS (`73` checks, `0` errors, `0` warnings)

## Non-Claims

- `ChangeGrammar` and `DocumentPipeline` remain `[proposed]` (ADR-0032); no `RC28-F13` closure or corpus-wide recall claim.
- Retirement of duplicated `crates/ln-temporal/src/document_context.rs` stays tracked beside PR3/post-spike cleanup so existing 15+ `ln-temporal` contract suites remain intact during the vertical proving spike.
