# Code Review: Close Surviving Mutants in `crates/ln-temporal/src/calendar.rs`

- **Date:** 2026-11-28
- **Target:** `test/ln-temporal-calendar-mutants` vs `main` (`22057641`)
- **Depth:** `lite` (`size_band: small`, `hard_block_full: false`, `exec_nontest_lines: 7`, 2 changed files / 109 lines)
- **Verdict:** Ready to merge

## Findings

No actionable findings (0 P0, 0 P1, 0 P2, 0 P3).

## Verification & Coverage

- `crates/ln-temporal/src/calendar.rs:122-132`: Removed redundant hyphen pre-checks (`bytes.get(4)` / `bytes.get(7)`) already enforced by the immediately following byte-by-byte loop (`4 | 7 => *byte == b'-'`), eliminating two equivalent mutants (`|| -> &&`) with identical runtime semantics.
- `crates/ln-temporal/tests/calendar_ordinal.rs`: Added boundary tests for `max_year` (`2100-12-31`), century leap/non-leap rules (`1900-02-29`, `2100-02-29`, `2000-02-29`), single-separator malformed ISO strings (`2014/01-01`, `2014-01/01`), `ordinal_to_legal_act_effect_day` bounds and month-boundary roundtrips (`2014-02-28`, `2024-12-31`, `2024-03-01`, `2024-01-01`), `CalendarError::Display`, and `parse_calendar_bounds` edge cases.
- Local checks passed: `just gate-fast ln-temporal`, `cargo nextest run -p ln-temporal --offline`, `just miri ln-temporal` (6/6 passed), and full `cargo mutants -p ln-temporal -f crates/ln-temporal/src/calendar.rs` confirmed all 4 original surviving mutants are killed.
- Conditional lenses not run on `lite` path: `adversarial`, `learnings`, `security`, `performance`, `api-contract`, `data-migration`, `reliability`, `frontend-races`, `previous-comments`.
