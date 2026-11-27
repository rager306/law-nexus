# Project agent instructions — law-nexus

> **Tracked repository instructions.** Durable authority stays with
> `prd/ARCHITECTURE.md` and `doc/adr/**` (RC12-F18); this file is the agent
> entry point, not a legal or product authority. Historical GSD-Pi, GSD-Path,
> and Allspark delivery records (milestones M001–M012) are preserved under the
> immutable Git tag `archive/gsd-path-final`.

## Language

| Surface | Language |
|---|---|
| Interactive chat | Russian |
| Tracked ADR / PRD / code / comments / git | English |
| Local planning prose (Path/Pi scratch) | Russian |
| Delivery one-liners that become git subjects | English |

User override wins. Do not silently pick.

## Direction

Rust-only product runtime. Python product is archive-only
(`python_archive/product/`). Thin harness `src/law_nexus_harness/` —
Cargo / ADR / docs / parity / CI / workflow-state checks only; no product
logic, no PyO3/FFI. ACP/git-lex and FalkorDB are archive / historical-only
(ADR-0014 → RuVector `[proposed]`). `/root/git-lex-kit-acp/` is separate
historical work.

Read first: `prd/ARCHITECTURE.md` → `doc/adr/README.md` (0004–0031;
0001/0002/0003/0006 retired) → `prd/temporal-legal-model.md` §3 before naming
temporal/parser/evidence types → `prd/architecture/model-crystal.md` (Layer 0/1
projection of Reviews 10–14; cite `INV-`/`AXIS-`/`OP-`/`RES-` IDs instead of
pasting review prose). `deferred-undefined` / `runtime deferred` = stop.

Skills: `law-nexus-rust` first for crates. Vocabulary:
`prd/temporal-legal-model.md` §3 + owning ADR. Vaults
(`python_archive/`, `.lex/`, `Old_project/`, `prd/archive/*`, `archive/*`)
are not product truth. Map: `prd/archive/README.md`. Temporal AST model L0:
`doc/review/review-20-08-2026.md`.

## Compound Engineering

- Active delivery workflow: Compound Engineering (`prd/project-state/workflow-backend.json`
  sets `backend: "compound-engineering"`). Product behavior model stays in
  `product-model/` (PDD Kit, audited read-only with `/skill:pdd-verify report only`).
- Repo config: `.compound-engineering/config.yaml` sets
  `docs_root: .compound-engineering/artifacts`, keeping CE artifact folders
  (`solutions/`, `plans/`, `ideation/`, `explainers/`, `pulse-reports/`,
  `dogfood-reports/`, `feedback-sweep/`, `personas/`) under
  `.compound-engineering/artifacts/` instead of `docs/`. Machine-local overrides
  (`.compound-engineering/*.local.yaml`) and local skill scratch
  (`.context/compound-engineering/`) are gitignored.
- Knowledge store: `.compound-engineering/artifacts/solutions/` holds documented
  solutions to past problems (bugs, best practices, workflow patterns),
  organized by category with YAML frontmatter (`module`, `tags`,
  `problem_type`), relevant when implementing or debugging in a documented area.
- **Review reports:** save every final `ce-code-review` and `ce-doc-review`
  report under `.compound-engineering/reviews/YYYY-MM-DD-<target-slug>.md`
  (create the directory if absent) in addition to summarizing it in chat. Keep
  ephemeral per-run intermediates in `/tmp/compound-engineering-<uid>/...`
  untracked; if `CODING_STANDARDS.md` or `REVIEW.md` are created, they remain at
  the repository root per CE discovery rules.
- Repository control-plane harness: `src/law_nexus_harness/` validates living
  architecture, ADR, dependency allowlist, and Compound Engineering workflow
  boundaries without product logic.

## Testing

Authority: ADR-0015 +
`.agents/skills/law-nexus-rust/references/verification-matrix.md`.
How to write a slice: `.agents/skills/law-nexus-rust/` — the slice-writing
and review guides live under that skill's `workflows/`.
Do not invent a second matrix here.

Overlapping contours, not a pyramid. Smallest contour that can lie, plus one
fail-closed path. TDD. Compilation is never done. Port with >1 adapter →
`crates/ln-testkit/tests/*_port_contracts.rs`. Consultant ≠ Garant.
`consru_export` = `[smoke]`. New change-class row goes in the tracked matrix,
not this overlay.

Typical: `cargo test -p <crate> --offline --test <suite>` then
`cargo fmt --all --check && cargo check --workspace --offline`.

### Rust Build & Verification Standard (host SSOT)

Follow `/root/.config/rust-standard/STANDARD.md` (pinned versions in
`/root/.config/rust-standard/versions.env`, compact checklist in
`/root/.config/rust-standard/AGENTS-snippet.md`):
- **Toolchains:** stable `1.99.1` (edition 2024, `rust-toolchain.toml` includes
  `rustfmt`, `clippy`, `rust-analyzer`, `rust-src`, `llvm-tools`); verification
  nightly `nightly-2026-08-21` (`miri`, `rust-src`, `llvm-tools`, `rust-analyzer`,
  `rustc-codegen-cranelift`).
- **Host vs repo boundary:** `kache 2.3.0`, `mold 3.0.0`, and `ulimit -n 65536`
  are configured globally on the host (`/root/.cargo/config.toml`, `/etc/kache/config.toml`);
  `target` is symlinked to `/srv/rust-build/targets/law-nexus` (zero-copy ZFS hardlinks).
  **Never** set `rustc-wrapper` or `[build] rustflags` in in-repo `.cargo/config.toml`.
  For parallel worktrees, run `/root/.config/rust-standard/scripts/worktree-target-init.sh <worktree>`.
- **LSP & lints:** `.vscode/settings.json` sets `"rust-analyzer.cargo.targetDir": true`.
  Root `Cargo.toml` defines `[workspace.lints]` (`unsafe_code = "forbid"` + Phase-1
  zero-churn BeautifulRust subset; all 47 crates inherit `[lints] workspace = true`).
- **Unified `Justfile` gates (`CARGO_BUILD_JOBS=4`, `NEXTEST_TEST_THREADS=4`, `COLUMNS=120`):**
  - **WF-1 Turbo:** `just test-clif [crate] [filter]` (Cranelift + `mold`, isolated `target/clif` via `LN_CLIF_TARGET_DIR`, `KACHE_DISABLED=1`).
  - **Tier 0 (`just gate-fast`, <10s):** `fmt`, `gitleaks`, `--no-deps` clippy, `verify-crate-dependency-allowlist.py`, `verify-adr-conformance.py`.
  - **Tier 1 (`just gate`, 1–5m):** `fmt`, `clippy --workspace --offline --all-targets -D warnings`, `nextest --workspace --offline --profile ci`, `cargo deny --offline check -D unsound advisories licenses bans sources`, `cargo shear`, `actionlint`, `zizmor`, Python repo guards.
  - **Tier 2 (`rust-heavy-run` — `flock` + cgroups v2):** `just arch-lint` (`deslop-please@0.1.4 --allow .deslop-please.allow` — **NEVER** run `--update-allow` to hide new debt; `just arch-lint-ratchet` enforces this), `just verify`, `just miri [crate]`, `just cov`, `just mutants [crate] [shard]` (`TMPDIR=/srv/rust-build/mutants-tmp`, reports in `target/mutants.out`), `just llvm-lines [crate]`.
  - **Tier 3 (`just release`):** `cargo deny -D unsound`, `cargo auditable build --release` (`ln-status`, `law-nexus-inspect`), `cargo audit --no-fetch bin`, CycloneDX 1.5 SBOMs in `target/sbom/`.

## GitNexus

Always `repo: "law-nexus"`. Never alias `root`. Impact before editing a
symbol; `detect_changes` before commit; graph-aware rename.
Reindex after architecture/process commits:

```bash
node .gitnexus/run.cjs analyze --force --name law-nexus
```

The auto-block below omits `repo` — still pass it.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **law-nexus** (43376 symbols, 102960 relationships, 584 execution flows).

> Index stale? Run `node .gitnexus/run.cjs analyze --index-only` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? Bootstrap with `npx`, `bunx`, or `pnpm dlx` — e.g. `bunx gitnexus@latest analyze` (npm 11 npx crash; #1939).

## Always Do

- **MUST run impact before editing.** Use `impact({target: "symbolName", direction: "upstream"})` or `node .gitnexus/run.cjs impact "symbolName" --direction upstream --repo .`; report callers, processes, and risk. Never substitute grep for graph analysis.
- **MUST analyze graph changes before committing.** Use `detect_changes({scope: "all"})` (MCP) or `node .gitnexus/run.cjs detect-changes --scope all --repo .` (CLI fallback). `partial: true` or `truncated: true` is not a clean check — a zero means unseen, not unaffected; re-run it. For regression review: `detect_changes({scope: "compare", base_ref: "main"})` or `node .gitnexus/run.cjs detect-changes --scope compare --base-ref "main" --repo .`.
- MUST warn on HIGH/CRITICAL `risk` pre-edit; never use `riskSharedAxes` to waive a HIGH/CRITICAL `risk` warning. Compare File/symbol: MCP File omits axes; Graph-RAG expands File.
- **MUST treat `risk: UNKNOWN` as unresolved, not as low.** An empty caller set is not evidence the symbol is unused — it can also mean the callers are not resolvable by the index (plain-object property access, dynamic dispatch, cross-language calls). `impact` pairs `UNKNOWN` with a `riskNote` saying so. Confirm with a text search before treating the symbol as safe to change or delete; do not proceed on the strength of a zero.
- **MUST use `query({search_query: "concept"})` for concepts/flows, `context({name: "symbolName"})` for a named symbol, or `impact` for blast radius, on read-only callers, dependencies, imports, or execution flow.** Graph first; text search only for empty/`UNKNOWN`/literals.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method before MCP/CLI impact analysis.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis, and never read `UNKNOWN` as an all-clear — it means the walk could not answer, which is the one verdict that requires confirming by other means.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit before MCP/CLI graph change analysis.

## Resources

| Resource | Use for |
| --- | --- |
| `gitnexus://repo/law-nexus/context` | Codebase overview, check index freshness |
| `gitnexus://repo/law-nexus/clusters` | All functional areas |
| `gitnexus://repo/law-nexus/processes` | All execution flows |
| `gitnexus://repo/law-nexus/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
| --- | --- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
<!-- BEGIN: data-sources-map (updated 2026-11-28) -->
## Data Sources Map (IMPORTANT — read before any corpus analysis)

| Directory | What it is | Scale |
|---|---|---|
| `consru_export/consru_export/exports/` | **FULL consru corpus** — all parsed XML documents (43,785 files, 3.7 GB) | THE corpus |
| `law-source/consultant/` | Fragment of the corpus (82 tracked XML fixtures; 40 more `.deprecated/` files are gitignored and absent from current checkouts) — NOT the full set | partial |
| `law-source/garant/` | Garant-format documents | separate format |

**RULE:** Before any corpus-wide analysis, scan `consru_export/exports/`,
NOT `law-source/`. The latter is a subset. Historical GSD-Pi and GSD-Path
delivery records (M001–M012) are preserved read-only under Git tag
`archive/gsd-path-final`.
<!-- END: data-sources-map -->
