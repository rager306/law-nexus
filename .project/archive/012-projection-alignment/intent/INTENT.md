# Intent — law-nexus

<!-- Written by /gsd-path-define (brownfield, standard mode). Every downstream agent reads this first.
     Constraints and vetoes here override everything downstream. -->

Lane: quick   <!-- quick: two deliverable-sized docs-alignment tasks in one wave,
                      no RESEARCH or NEEDS-USER items (rulings delegated and
                      recorded), no cross-wave risk. Quick skips research and decide. -->

Review panel: off   <!-- off; quick lane stays off. -->

Finding skeptics: off   <!-- off; quick lane stays off. -->

Surfaces: none   <!-- docs/projection alignment pass; no new human-facing
                      surface. Success criteria are observable by running the
                      tracked suites and reading files at HEAD. -->

## Summary

M011 shipped honestly but skipped the pinned ship-time projection refresh, so
`prd/project-state/roadmap.md|json` still front M010, the current-state
document claims a green `main` that is red (CI run 41198873586 at the M011
integration `ef17106b` failed on the projection suites), and 21 stale claims
accumulated across README/AGENTS/PRD/ADR docs. M012 is the alignment pass:
run the missed projection refresh per the pinned procedure, re-record the
live CI state with dated history, clear the DOCS-AUDIT remediation queue
(rows #25-#50, rulings #25-#50 recorded), and re-pin the m221 binding.
Owner and coding agents get a repository whose front-door docs and CI state
agree again.

## Problem

The repository's own pinned rule (AGENTS.md ship-time projection refresh)
was violated by the M011 ship: the pointer suites are red locally and in CI
on `main`, while `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` tells the
reader the live state is green (runs 40805352394/40822037565) and its
bootstrap section says to expect all tests to pass when 2 fail. Beyond that,
20 stale doc claims (counts, ranges, anchors, ADR inventory, subcommand
list) and one stale hash-pinned m221 binding mislead every agent that reads
them as ground truth. Evidence: `.project/research/DOCS-AUDIT.md` rows
#25-#50 (21 non-verified claims), CI run 41198873586.

## Users

The repository owner and coding agents (technical, terminal-first). They
read README/AGENTS/POST-SHIP-STATE as the entry contract and run the tracked
pointer/freshness suites as bootstrap checks.

## Success criteria

1. The ship-time projection refresh (per `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md`) names the shipped M011 record — milestone `reference-front-door`, ship `38abe687`, integration `ef17106b`, archive `011-reference-front-door` — in `prd/project-state/roadmap.md` and `roadmap.json`, and `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py tests/test_post_ship_pointers.py -q` reports 0 failures at HEAD.
2. `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` appends the M011 delivered record (ship `38abe687`, integration `ef17106b`, tag `milestone/011-reference-front-door`, archive `.project/archive/011-reference-front-door`) and records the newest main run 41198873586 at `ef17106b` as a FAILURE on the projection suites with prior green runs kept as dated history; the fresh-session bootstrap step 4 again tells the reader to expect all tests to pass.
3. Audit rows #25-#28, #30-#31, #36-#37, and #44-#49 are re-verified against the live tree: ARCHITECTURE parser counts or their removal, one-page oracle within the 325-line budget, ADR index table header, cross-matrix through ADR-0031, legacy-ledger line date-bound, law-source README checkout wording, PHASE-ADAPTER header aligned with its section 9, interface.md listing five subcommands, README status band and assessments range, AGENTS.md DB count and fixture counts, README ADR range 0004-0031 — the audit claim check passes for each.
4. `prd/architecture/m221-s05-docs-reconciliation.yaml` pins path+sha256 equal to the tracked `prd/architecture/npa-analysis-jsonl-contract.md` at HEAD, and the M221 s05 readiness battery passes with the re-pinned binding.
5. The AGENTS.md GitNexus block is regenerated from a fresh `node .gitnexus/run.cjs analyze --force --name law-nexus` run; its numbers equal that run's recorded meta.json (nodes/edges/processes) and the note that the index is local-excluded stays.

## Edge coverage

| Edge | Criterion | Category | Disposition | Detail |
|------|-----------|----------|-------------|--------|
| E1 | SC1 | idempotency | criterion SC1 | Re-running the refresh procedure yields identical front content (the procedure is deterministic from the recorded milestone fields). |
| E2 | SC3 | empty | criterion SC3 | A refreshed count claim whose target set is empty (zero matches) is recorded as zero with evidence, not as verified-by-omission. |
| E3 | SC4 | boundary | criterion SC4 | A digest mismatch between the binding and the tracked file fails the check fail-closed. |
| E4 | SC2 | ordering | criterion SC2 | The appended M011 record lands after the existing dated records (append-only order) and the newest-run claim names the actual newest main run at edit time. |
| E5 | SC5 | adjacency | criterion SC5 | The regenerated GitNexus block occupies exactly the delimited block span in AGENTS.md — markers preserved, no neighboring content touched. |

## Prohibitions

| Prohibition | Criterion | Must not | Disposition | Detail |
|-------------|-----------|----------|-------------|--------|
| N1 | SC2 | dated history rows must not be rewritten or deleted; the M011 record and the red-state note are appended | criterion SC2 | Stated in SC2; reviewer checks prior run rows survive. |
| N2 | SC5 | the GitNexus analyze run must not modify product code or any tracked file other than the AGENTS.md tool block | criterion SC5 | Stated in SC5. |
| N3 | SC3 | refreshed docs must not raise lifecycle tags or present fixture-level results as corpus-wide parity | judgment | Final reviewer reads refreshed rows against the D098 tag ladder. |
| N4 | SC1 | the refresh must not modify archived milestone artifacts (archives are read-only) | criterion SC1 | Stated in SC1; reviewer checks the archive is untouched. |
| N5 | SC4 | the re-pinned binding must not pin any path outside the declared companion file, and the battery must not be weakened to pass | criterion SC4 | Stated in SC4; reviewer reads the binding yaml diff and the battery invocation. |

## Scope: in

- T001 (projection + current-state honesty, `prd/project-state/`, `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md`, `docs:` commit procedure): the missed M011 projection refresh per the pinned procedure (#39), the M011 record and red-state CI rows in POST-SHIP-STATE (#40-#43), delivering SC1 and SC2.
- T002 (long-tail doc alignment + tool index, README/AGENTS/PRD/ADR/product-model + `.gitnexus`): rows #25-#28, #29 re-pin, #30-#31, #36-#37, #44-#49, and the GitNexus reindex (#50), delivering SC3-SC5.

## Scope: out (vetoes)

- No product behavior changes: docs, the AGENTS.md tool block, and the m221 binding yaml only; product admission stays fail-closed; no new crates; no workspace member changes.
- Full-corpus runs or any corpus-wide D5/D4 execution claim — user: "не запускать горизонт автоматически".
- Modifying or deleting archived milestone artifacts (`.project/archive/**` is read-only) or rewriting dated history rows (N1).
- Allspark repair or pin movement — separate stream; pin stays fork.009.
- Unparking M208-wrz6fg / M217-M220 — requires owner re-verification of their input evidence.

## Constraints

- Ship-time projection refresh is a pinned procedure: M012's own ship must run it for M012 (this milestone fixes the missed M011 refresh and its fallout).
- Verification authority: `.agents/skills/law-nexus-rust/references/verification-matrix.md`; docs claims cite file:line or command evidence; the fix-doc verify re-runs the audit's claim check.
- Lifecycle tags `[proposed]/[bounded]/[smoke]/[validated]/[deferred]` are mandatory on claims (D098; Governor-enforced).
- Language: tracked docs and commit subjects in English; chat in Russian.
- The green offline workspace suite must not break (`cargo fmt --all --check && cargo check --workspace --offline`).

## Current state (brownfield only)

- **What exists**: Rust-only product runtime — 47-crate workspace (edition 2024, toolchain 1.99.0, ~6 external deps), hexagonal per-capability crates with 20 hostile-case runners, product CLI `law-nexus-inspect` (health/inspect/replay/subordinates/reference-package), thin Python repository-control harness; reference-package surface shipped in M011 (T001/T002) with the honest exit contract 0/2/3/6.
- **Delivery state**: M011 `reference-front-door` shipped and integrated (`38abe687` ship, `ef17106b` merge, tag `milestone/011-reference-front-door`, archive `011-reference-front-door`) but without the ship-time projection refresh; CI on `main` is red on the projection suites (run 41198873586); 21 stale doc claims queued.
- **Must not break**: green offline workspace suite; existing CLI commands and typed failures; governor/preflight honest classification; dated history rows; archives.
- **Ground truth**: `.project/research/evidence-codebase.md`, `.project/research/DOCS-AUDIT.md` (132 verified / 21 stale / 0 aspirational; queue #25-#50; rulings #25-#50 recorded 2026-10-31).

## Open questions

<!-- none: quick lane; rulings on #25-#50 recorded from the delegated owner directive -->

## Corrections

- 2026-10-31: «действуй проактивно, принимай решения оптимально/элегантно в соотвествии с требованиями архитектуры и репозитория - используй gsd» — owner delegated the queue rulings; auditor classes adopted for #25-#50 with three judgment calls: #26 trim the oracle to the tracked budget (do not raise it), #29 re-pin the binding to the current tracked digest (current revision canonical), #30 date-bound the legacy-ledger line (roadmap.json stays the live product front).
