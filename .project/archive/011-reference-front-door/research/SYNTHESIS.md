# Synthesis — M011 (quick lane)

<!-- Settled-only synthesis per the quick-mode plan contract. No invented decisions or runner-ups. -->

## Settled

- Lane quick, scope and vetoes as approved in `.project/intent/INTENT.md` (Surfaces: terminal CLI; exit contract 0/2/3/6 with 5 reserved; measurement edition-50 applicability honesty; admission stays fail-closed).
- Brownfield facts are settled by `.project/research/evidence-codebase.md`: `ln_consultant_parser::reference_layer` already provides `try_derive`, `references_document`, `pageindex_document`, `run_check`, `measurement_applicable`, `MEASUREMENT_EDITION` and the exit constants; the standalone binary `crates/ln-consultant-parser/src/bin/reference_layer.rs` shows the composition; `law-nexus-inspect` parses args manually and has no `default-run`.
- Doc-vs-code rulings #20-#24 (DOCS-AUDIT.md `## User rulings`) are settled: fix-code default-run; fix-doc README 47 members; fix-doc AGENTS.md slice-guide pointer; fix-doc POST-SHIP-STATE current/history separation; fix-doc ARCHITECTURE.md ADR-0031 honest wording.
- Determinism and input immutability are settled constraints (INTENT SC1/SC3, N2): byte-identical rebuilds, write only inside `--out-dir`, inputs read-only.

## For the planner

Walking skeleton, one wave: compose the proven reference_layer functions into two new `law-nexus-inspect` subcommands with fixture acceptance on measure-ed50 (T001), then align the four front-door documents and add the PDD capability documentation linking fixture, test, and recorded check result (T002, depends on T001's landed test and recorded result).
