# Project agent instructions — law-nexus

> **Tracked repository instructions.** Durable authority stays with
> `prd/ARCHITECTURE.md` and `doc/adr/**` (RC12-F18); this file is the agent
> entry point, not a legal or product authority. Historical GSD-Pi workflow
> notes live in `doc/gsd-headless-supervisor.md` and the frozen `.gsd`
> snapshot (see `docs/agent-stack/`).

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

## Agent stack (Allspark + GSD Path + PDD Kit)

- Host: Allspark, pinned configuration in `.ai/` (see `docs/agent-stack/INSTALL.md`).
- Delivery workflow: GSD Path; native state in `.project/`, runtime selection
  in `.gsd-path/runtime.json`. Follow the generated root `WORKFLOW.md` and
  installed phase contracts. Use native helpers for state mutations.
- Product behavior: PDD Kit in `product-model/`, orchestration off.
  `/skill:pdd-verify report only` for audits; Path owns implementation.
- Read `docs/agent-stack/ALLSPARK_NOTES.md`, `AGENT_HANDOFF.md`, `MIGRATION.md`
  and `WORKFLOW.md` before workflow work.
- Start Allspark through `scripts/ai/allspark` from the primary root. Linked
  worktrees use the absolute primary launcher and keep their assigned cwd.
- The wrapper selects the official Allspark launcher and the exact
  same-commit runtime/skills supplement. Do not rename PRIME_AGENT/PI
  environment names and do not bypass the launcher by calling
  `libexec/prime-agent` directly.
- Allspark has an isolated HOME (`.ai/local/allspark-home`). Validate both
  exact Path runtime caches, the shared external worktree root, and effective
  Git identity/hooks/signing. Do not copy upstream auth or private SSH
  configuration into the fork HOME.
- Keep versions, public settings and roles in Git (`.ai/`). Keep credentials,
  sessions, tool installations and caches in ignored `.ai/local/`.
- Do not enable an additional Pi/PDD/Allspark autonomous coordinator. The Path
  owner is the sole dispatcher; use fresh role contexts and exact worktrees.
- Shared skill installation does not create an Allspark phase adapter for
  every Path phase. Validate the required dispatch capability
  (`scripts/ai/phase-dispatch.py`, `docs/agent-stack/PHASE-ADAPTER.md`)
  before declaring the full workflow operational.
- MCP endpoints and environment variable names belong in the tracked settings
  template (`.ai/allspark/settings.json`). Secrets stay local. Discover live
  MCP schemas; a legacy `.mcp.json` is not proof of an active connection.
- Use the tracked model settings. After an intended template change, run
  `python3 scripts/ai/allspark-settings.py apply`; do not change a shared
  profile from a task worker.

## Workflow-state boundary (harness)

`src/law_nexus_harness/workflow_state.py` is the only sanctioned adapter
between repository checks and delivery-workflow state. It distinguishes:
bootstrap not-cut-over, operational valid Path state, missing state, invalid
schema, unavailable/mismatched runtime, conflicting ownership, and historical
legacy evidence. Missing or invalid operational state is a blocking
diagnostic, never a silent PASS. Portable bootstrap checks passing does not
mean workflow readiness.

## Legacy GSD-Pi (frozen 2026-10-23)

GSD-Pi is retired as the active coordinator. Its local state (`.gsd` symlink →
`/root/.gsd/projects/3495c0714df3`) is a read-only historical snapshot; the
supervisor runbook (`doc/gsd-headless-supervisor.md`) and the Pi tool-contract
notes in git history are process archaeology, not operative instructions.
Do not restart the Pi supervisor, do not mirror `.gsd` into `.project`, and do
not fabricate attempts/approvals from it. Active obligations were carried over
through `docs/agent-stack/history/LEGACY_CROSSWALK.md` only. Source-integrity
hashes recorded by the Pi engine stay historical evidence; the live successor
is `scripts/verify-source-snapshot-v2.py`.

## Testing

Authority: ADR-0015 +
`.agents/skills/law-nexus-rust/references/verification-matrix.md`.
How to write a slice: `workflows/implement-rust-slice.md`.
Do not invent a second matrix here.

Overlapping contours, not a pyramid. Smallest contour that can lie, plus one
fail-closed path. TDD. Compilation is never done. Port with >1 adapter →
`crates/ln-testkit/tests/*_port_contracts.rs`. Consultant ≠ Garant.
`consru_export` = `[smoke]`. New change-class row goes in the tracked matrix,
not this overlay.

Typical: `cargo test -p <crate> --offline --test <suite>` then
`cargo fmt --all --check && cargo check --workspace --offline`.

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

This project is indexed by GitNexus as **law-nexus** (23577 symbols, 50919 relationships, 568 execution flows).

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
<!-- BEGIN: data-sources-map (2026-09-01, health session; .gsd row updated 2026-10-23) -->
## Data Sources Map (IMPORTANT — read before any corpus analysis)

| Directory | What it is | Scale |
|---|---|---|
| `consru_export/consru_export/exports/` | **FULL consru corpus** — all parsed XML documents (43,785 files, 3.7 GB) | THE corpus |
| `law-source/consultant/` | Fragment of the corpus (122 XML files) — NOT the full set | partial |
| `law-source/garant/` | Garant-format documents | separate format |
| `.gsd/projects/*/gsd.db` | Frozen legacy GSD-Pi SQLite DB (read-only archive since 2026-10-23) | historical |

**RULE:** Before any corpus-wide analysis, scan `consru_export/exports/`,
NOT `law-source/`. The latter is a subset. Also: `/root/law-nexus/.gsd`
is a symlink to `/root/.gsd/projects/3495c0714df3` — always `realpathSync`
both paths before `path.relative()` to avoid `../../../`-style poisoned
paths (2,478 artifact rows in the DB contain such paths).

**Known issue:** 2,478 artifact rows in the DB contain `../`-style paths.
Compat-marker write-guard and heal-drop patches prevent them from
poisoning the marker. Do NOT delete these DB rows without a sanctioned
migration. The DB is frozen; new workflow state lives under `.project/`.
<!-- END: data-sources-map -->
