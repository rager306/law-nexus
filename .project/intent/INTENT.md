# Intent — law-nexus

<!-- Written by /gsd-path-define (brownfield, standard mode). Every downstream agent reads this first.
     Constraints and vetoes here override everything downstream. -->

Lane: quick   <!-- quick: at most two deliverable-sized tasks in one wave,
                      no RESEARCH or NEEDS-USER items, no cross-wave risk.
                      Quick skips research and decide. -->

Review panel: off   <!-- off; quick lane stays off. -->

Finding skeptics: off   <!-- off; quick lane stays off. -->

Surfaces: terminal CLI   <!-- law-nexus-inspect gains reference-package
                      build/check; README quick-start command must work as
                      written. Every surface has criteria observable at the
                      terminal (SC1-SC8). -->

## Summary

The reference knowledge layer (ADR-0031) exists as a proven Rust API with a
standalone binary, but is unreachable through the product CLI, and the
repository's front-door documentation contradicts the code (broken quick-start,
stale member count, stale agent pointers, a current-state report that calls
green CI red). M011 composes the existing `reference_layer` functions into
`law-nexus-inspect reference-package build|check`, proves the composition on
the tracked measure-ed50 fixture with the honest exit-code contract
(0/2/3/6), aligns the four load-bearing docs, and links the new capability
into the PDD product model. No new algorithm, no corpus-wide claims.

## Problem

A user or agent holding a set of act editions and a catalog has no single
documented command that produces a reproducible reference data package and
verifies it; they must know an internal standalone binary. The README
quick-start fails as written (`cargo run -q -p ln-product-cli -- health`
exits 101: two binaries, no `default-run`), the status band undercounts the
workspace (45 vs 47, omitting both parser crates), AGENTS.md points coders at
a missing file, and POST-SHIP-STATE-2026-10-28.md still claims integrated
`main` is red while live CI is green. Evidence: sidecar runs at
`3a39fd70`, findings in `research/evidence-codebase.md` and
`research/DOCS-AUDIT.md` (queue #20-#24, #25, #26-#38).

## Users

The repository owner and coding agents (technical, terminal-first). They use
`cargo`/`law-nexus-inspect` today. Downstream consumers: corpus-evidence work
that needs a verifiable reference package before any full-corpus claim.

## Success criteria

1. `law-nexus-inspect reference-package build --corpus-dir <measure-ed50 fixture> --catalog <catalog> --out-dir <dir>` exits 0 and creates the expected reference artifact set (edition/digest layer, references document, pageindex document, measurement artifacts) on the tracked measure-ed50 fixture; it writes only inside `--out-dir` and leaves the corpus directory and catalog byte-unchanged.
2. `law-nexus-inspect reference-package check` with the same arguments on the unmodified built package exits 0 and must never exit 0 when any artifact differs from the derivation — any byte drift, including a truncated or zero-byte artifact, exits 6.
3. Two builds into different temporary output directories produce byte-identical artifacts.
4. A missing or unreadable input (corpus dir absent, catalog unreadable, empty corpus directory with zero XML documents) exits 3.
5. Invalid arguments (unknown flag, missing required flag) exit 2.
6. A corpus that carries no edition 50 builds and checks with the measurements explicitly reported not applicable (no drift counted, exit 0); a corpus that carries edition 50 has its measurements compared normally.
7. `cargo run -q -p ln-product-cli -- health` (README quick-start, as written) exits 0 after `default-run` is set.
8. README status band enumerates 47 workspace members naming `ln-consultant-parser` and `ln-kb-ontology`; AGENTS.md names an existing slice-writing guide (`.agents/skills/law-nexus-rust/`); POST-SHIP-STATE-2026-10-28.md separates current state from dated history (M004 chapter superseded, red-CI table dated); the ARCHITECTURE.md ADR-0031 row states the measurement-level module code exists while corpus-wide D5/D4 execution is unproven — each verifiable by reading the file at HEAD or by the tracked doc suites.
9. `product-model/` gains reference-package capability documentation linked to the measure-ed50 fixture, the executable test, and a recorded check result.

## Edge coverage

| Edge | Criterion | Category | Disposition | Detail |
|------|-----------|----------|-------------|--------|
| E1 | SC1 | idempotency | held-out | Re-running build into the same out-dir overwrites its artifacts cleanly and yields byte-identical output; unrelated files in out-dir are left alone. Pinned by a named test (build twice, same dir). |
| E2 | SC2 | boundary | held-out | An artifact truncated to zero bytes is drift (exit 6), not a missing input (3): the file exists but differs from the derivation. Pinned by a named test. |
| E3 | SC4 | empty | criterion SC4 | An empty corpus directory (zero XML documents) is an unreadable/invalid input and exits 3. |
| E4 | SC6 | boundary | criterion SC6 | A corpus carrying edition 50 among others has its measurements compared normally; only the no-edition-50 case is not-applicable. |
| E5 | SC5 | none | dismissed | The flag set is a closed enum parsed by the composed reference_layer helpers; no further edge is reachable beyond the ruled 2/3 cases. |
| E6 | SC3 | idempotency | criterion SC3 | Determinism is the criterion itself: two full builds into different directories must be byte-identical, so every re-derivation path is covered by that statement. |
| E7 | SC7 | none | dismissed | Single fixed command (`-- health`) with no data input; after the default-run fix its behavior is the existing verified health path. |
| E8 | SC8 | none | dismissed | Static documentation content; no runtime data shapes. Verifiability is the evidence rule in SC8 itself. |
| E9 | SC9 | none | dismissed | Documentation linkage (fixture, test, check result); no runtime data shapes. |

## Prohibitions

| Prohibition | Criterion | Must not | Disposition | Detail |
|-------------|-----------|----------|-------------|--------|
| N1 | SC2 | check must never silently pass: no warn-and-pass path may turn drift into exit 0 | criterion SC2 | Stated in SC2; reviewer checks the exit path handles every drift row. |
| N2 | SC1 | build must not write outside `--out-dir` and must not mutate the corpus or catalog | criterion SC1 | Stated in SC1 (write only inside out-dir; input hashes unchanged). Plan schedules the named test that hashes the inputs before/after a build and asserts the non-output tree is untouched. |
| N3 | SC8 | the aligned docs must not claim corpus-wide parity as proven; the ADR-0031 row stays `[proposed]` with D5/D4 execution stated unproven | criterion SC8 | Stated in SC8's required ARCHITECTURE.md wording; reviewer checks the four files carry no proven-parity or raised-band language. |
| N4 | SC9 | new PDD capability docs must not raise lifecycle tags above the recorded `[proposed]`/`[bounded]` bands and must not present fixture-level parity as corpus parity | judgment | Final reviewer reads the new product-model documents against the recorded check result and the lifecycle-tag ladder (D098). |
| N5 | SC3 | — | dismissed | Determinism is an engineering integrity property, not a values/safety/transparency concern; covered by SC3 and E6. |
| N6 | SC4 | — | dismissed | Drift detection is the core function itself (already phrased as never-silent in N1/SC2's contract family); no further value at stake. |
| N7 | SC5 | — | dismissed | Fail-closed exit 3 on unreadable inputs is the safe direction; ordinary engineering, no person affected beyond the operator seeing the error. |
| N8 | SC6 | — | dismissed | Closed argv enum; ordinary argument validation, no person affected. |
| N9 | SC7 | — | dismissed | The not-applicable marking IS the transparency guarantee; nothing further it could silently become. |

## Scope: in

- T001 (Rust, `crates/ln-product-cli/` + crate-local integration test): `reference-package build|check` subcommands composing `ln_consultant_parser::reference_layer` (`try_derive`/`references_document`/`pageindex_document`/`run_check` semantics); exit codes 0/2/3/6 per the ADR-0031 D6 contract (5 stays reserved, not emitted); `default-run = "law-nexus-inspect"`; fixture acceptance on measure-ed50 covering SC1-SC7, E1, E2, N2.
- T002 (docs + PDD, `README.md`, `AGENTS.md`, `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md`, `prd/ARCHITECTURE.md`, `product-model/`): the four ruled doc alignments (SC8) and the reference-package capability documentation linked to fixture, test, and check result (SC9).

## Scope: out (vetoes)

- Full-corpus run or any corpus-wide D5/D4 (pageindex ladder, requisite deep links) execution claim — corpus acceptance is a separate, later milestone; user: "не запускать горизонт автоматически".
- Unparking M208-wrz6fg / M217-M220 — requires owner re-verification of their input evidence; not requested.
- Gate-honesty triage (full `uv run pytest -q` RED classes: m221 pin drift, untracked-file test deps, ln-status build order, live-scenario context pinning) — deliberately deferred to a later milestone.
- Allspark repair or pin movement — separate stream; pin stays fork.009.
- No new external crates; no changes to committed reference artifact byte-formats; no product admission semantics changes (admission stays fail-closed).

## Constraints

- ADR-0031 D6 exit-code contract: 0 ok, 2 argv, 3 unreadable inputs, 6 byte drift; 5 reserved and not emitted by the Rust side.
- Byte-parity discipline with the committed Python-reference artifacts; `--corpus-dir/--catalog/--out-dir` mirror the Python reference flags.
- Measurement semantics: ed-50 measurements compared only where the corpus carries edition 50; otherwise explicitly not applicable, never drift.
- Rust: edition 2024, pinned toolchain 1.99.0, std-only error enums, no new dependencies (crate allowlist pre-commit hook).
- Verification authority: `.agents/skills/law-nexus-rust/references/verification-matrix.md`; typical gates `cargo fmt --all --check && cargo check --workspace --offline`.
- Lifecycle tags `[proposed]/[bounded]/[smoke]/[validated]/[deferred]` are mandatory on claims (D098; Governor-enforced).

## Current state (brownfield only)

- **What exists**: Rust-only product runtime — 47-crate workspace (~226,635 LOC, edition 2024, 6 external deps), hexagonal per-capability crates with 20 hostile-case runners, product CLI `law-nexus-inspect` (health/inspect/replay/subordinates); thin Python repository-control harness (~11,456 LOC, 1023 tests); `reference_layer` API proven with byte-parity and the fail-closed exit contract; admission fail-closed everywhere by design. Product code frozen since ~2026-10-25 while the delivery workflow shipped M001-M010.
- **Must not break**: green offline workspace suite; existing CLI commands and their typed failures; governor/preflight honest classification; green CI on main; the committed reference artifact byte-formats.
- **Doc-vs-code rulings**: README quick-start — fix-code (default-run); README status band — fix-doc (47 members); AGENTS.md slice guide — fix-doc (point to `.agents/skills/law-nexus-rust/`); POST-SHIP-STATE current-vs-history — fix-doc; ARCHITECTURE.md ADR-0031 row — fix-doc (module code exists at measurement level, corpus-wide D5/D4 execution unproven, ADR stays `[proposed]`). Recorded in DOCS-AUDIT.md `## User rulings` #20-#24.
- **Ground truth**: `.project/research/evidence-codebase.md`, `.project/research/DOCS-AUDIT.md`

## Risks

- The measure-ed50 fixture may not exercise every composition path the standalone binary covers; mitigated by byte-parity to the standalone reference_layer outputs and by keeping the composition thin.
- PDD documentation drift; mitigated by the report-only pdd-verify discipline and the recorded check result linkage.

## Open questions

<!-- none: quick lane -->

## Corrections

- 2026-10-30: "да согласен , 3 корректируй согласно архитектурным требованиям репо - выполняй все оптимально и элегантно" (scope confirmed; ruling #24 fix-doc per repository architecture discipline)
- 2026-10-30: "края и запреты — как рекомендовано" (edge/prohibition rulings E1-E5, N1-N3 as recommended)
