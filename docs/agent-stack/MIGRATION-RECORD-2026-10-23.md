# Law-Nexus migration inventory and record (C0/C1)

**Date:** 2026-10-23
**Scope:** sanitized, repository-tracked inventory of the actual local
checkout and workflow state at the start of the GSD-Pi → Allspark + GSD Path
+ PDD Kit migration. No secrets, credentials or full environment dumps.
Runbook: `MIGRATION.md` (C0/C1). Private backup receipt: see
`MIGRATION_BACKUP` below.

## Git facts

| Fact | Value |
|---|---|
| Repository root | `/root/law-nexus` |
| HEAD | `12599fd679dd1e5c9bb62f8cc2a4d5d20817c866` (2026-10-18) |
| Branch | `main` (tracks `origin/main`) |
| `origin` | `https://github.com/rager306/law-nexus.git`, default `main` |
| `origin/main` | `f15612b2034ce71c9109326173c5e8a3b8a86b76` (251 commits behind local HEAD) |
| Index / worktree | clean except the untracked starter archive `doc/allspark-path-pdd-starter/` |
| Staged / unstaged diff | none |
| Worktrees | primary only; `/tmp/ln-m223` was a prunable stale entry (gitdir gone), pruned during C1 |
| Git identity | global `rager306 <alexey.podolinniy@gmail.com>`; repo-local identity added during bootstrap; isolated Allspark HOME initially had no identity |
| Signing | no `commit.gpgsign` configured (neither HOME) |
| Hooks | `core.hooksPath` unset → `.git/hooks`; pre-commit framework hook installed (ruff/cargo/allowlist/ADR conformance); no Pi-owned hooks found |

## Workflow state (.gsd, GSD-Pi)

| Fact | Value |
|---|---|
| `.gsd` | symlink → `/root/.gsd/projects/3495c0714df3` (kept) |
| Size | 1.6 GB total (`gsd.db` 646 MB + WAL, `exec/` 289 MB, `gsd.db.backup-v50` 253 MB) |
| Engine | `/usr/bin/gsd` v1.22.0 (GSD-Pi) |
| Active milestone | M225-qrwdfv (Reference knowledge layer in Rust), phase `blocked` |
| Blocker | M225 milestone validation returned `needs-attention` (journal 2026-10-18 11:10, orchestrator stop/pause) |
| Active tasks | none in `active/running` states; 11 rows `blocker-accepted`/`skipped` in historical milestones |
| Queue (paused) | M208, M217, M218, M219, M220 (⏸) + M225 (🔄) |
| Writer processes | none running (no gsd/headless processes, no supervisor pidfile, journal quiet since 2026-10-18 18:10) |
| Freeze | writer was already stopped; supervisor not restarted (C1) |
| Other workflow roots | `.project/`, `.planning/` absent; `/root/.gsd-path/` exists in normal HOME with old experiment runtimes, no `runtime.json` |

## Local instructions, skills, MCP

| Surface | Fact |
|---|---|
| `AGENTS.md` | existed as gitignored local overlay (Pi supervisor + tool contract); superseded by this tracked version |
| `CLAUDE.md` | GitNexus block only; stays gitignored |
| `.agents/skills/` | gitignored; contains `law-nexus-rust`, `law-nexus-subagent` (now tracked), `gitnexus-*`, `pi-skill-creator` (stay local/generated) |
| `~/.gsd/agent/agents/` | 13 Pi role prompts — historical, frozen with the engine |
| `.mcp.json` (gitignored) | servers: `gitnexus` (stdio), `agentmemory` (stdio), `jina-mcp-server` (http, bearer token — secret, not copied to tracked config), `gsd-workflow` + `gsd-browser` (Pi engine, retired with the freeze) |
| Tracked Allspark MCP | `deepwiki` public HTTP endpoint in `.ai/allspark/settings.json` (no auth) |

## Environment

| Tool | Version |
|---|---|
| Platform | Linux x86_64, glibc 2.39 (fork.009-compatible) |
| System Python | 3.12.3 (bootstrap entry) |
| Project Python | 3.13.12 (`.venv`, `uv sync --frozen`) |
| Rust | 1.99.0 pinned (`rust-toolchain.toml`), rustfmt+clippy installed |
| System Node | v24.22.0 (starter pins 22.23.4 locally under `.ai/local/`) |
| System uv | 0.12.13 (starter pins 0.13.5 locally) |
| Installed `allspark` on PATH | fork.008 (0.10.1-beta.35) at `/root/.local/bin/allspark` — **not** the pinned fork.009; the repo wrapper installs and uses the pinned build under `.ai/local/` |
| Disk | ~55 GB free at C1 |

## Corpus / evidence availability

- Full consru corpus present: `consru_export/consru_export/exports/` (43,785 files, ~4.6 GB on disk).
- `law-source/consultant/` subset (122 XML) and `law-source/garant/` present.
- `prd/migration/rust-evidence/` durable batteries present through M225 (2026-10-18).
- Historical CI on the studied public HEAD was failing (ledger parsing assertion, 51 basedpyright
  errors in `governor.py`, M207 battery missing corpus inputs offline) — baseline debt, not a
  waiver and not today's results.

## Unknown / not available from this machine

- Origin-side state beyond `origin/main` SHA (no fetch of other refs performed).
- Whether the 251 unpushed local commits exist on any other remote (owner decision required before push).
- Owner model choice and Allspark login for the pinned fork profile (auth is deliberately not copied).

## MIGRATION_BACKUP

Private backup directory (outside the repository, mode 0700):
`/root/law-nexus-migration-backup-2026-10-23`. Contents: git bundle (all refs,
verified), worktree/index patches, status/untracked/ignored path lists, a
consistent `gsd.db` snapshot (`sqlite3 .backup`, integrity-checked), full
project-state tarball, agent-home essentials, and copies of the ignored local
overlay (`AGENTS.md`, `CLAUDE.md`, `.mcp.json`, hooks, skills). Manifest:
`MANIFEST.sha256`; backup id: see `MANIFEST.id` in that directory.

**Backup manifest id (sha256 of MANIFEST.sha256):** `3a691ee67857bf153ceaa0cf93d23757ee2330cfcd70b4444247a6800a433d50`

## Decisions recorded during bootstrap

- `AGENTS.md` un-ignored and tracked (per INSTALL §5 and the owner directive to
  keep portable instructions in the repository); `CLAUDE.md` stays ignored.
- `.agents/skills/law-nexus-rust/` and `.agents/skills/law-nexus-subagent/`
  tracked; generated Pi-era and tool-installed skill dirs stay ignored.
- The untracked starter archive `doc/allspark-path-pdd-starter/` was merged
  into the tracked layout (`repo/` → root, `validation/TESTED.md` →
  `docs/agent-stack/TESTED.md`) and then removed from the working tree.
- Pi-era hooks were not found in `.git/hooks`; the pre-commit chain is kept
  as-is. Path guards are installed only by `bootstrap hooks` per INSTALL §8.

## Bootstrap validation receipts (2026-10-23, local branch `chore/allspark-path-pdd-bootstrap`)

- `python3 scripts/ai/bootstrap tools` — pinned Node 22.23.4, uv 0.13.5,
  Allspark fork.009 (`allspark 0.10.1-beta.38 (fork build fork.009; upstream
  prime-agent 0.10.1-beta.38)`, commit `91ef62927...`), PDD 0.37.1, kernel
  ready (`kernel-venv`, Python 3.11). Sources: pins in `.ai/versions.json`.
- `python3 scripts/ai/bootstrap skills` — 16 Path skills + 3 PDD skills,
  runtime 1.6.2 digest `6f95a31e…` verified in two caches
  (`/root/.allspark-home/.gsd-path/runtimes/…` for this shell HOME and
  `.ai/local/allspark-home/.gsd-path/…` for the isolated fork HOME; plus a
  host-HOME restore under `/root/.gsd-path/runtimes/…`).
- `python3 scripts/ai/bootstrap hooks` — Git guards with chained
  `pre-commit.gsd-path-chained` (pre-commit framework hook preserved).
- `python3 scripts/ai/doctor.py` — all component checks OK; PENDING:
  model selection (owner `/login` + `/model`) and Path initialization
  (bootstrap PR merge first, per MIGRATION.md C3/C4).
- Harness: governor `status ok, errors 0, warns 1` (workflow-state-surface
  bootstrap warn); preflight `status ok, errors 0, warns 3`
  (gitnexus-index-freshness, workflow-state-surface, trajectory-governor).
- `ruff check`/`ruff format --check` clean for all new/edited files;
  `basedpyright`/`ty`/`pyrefly` clean for the new modules; the 51
  basedpyright + 57 ty diagnostics in `governor.py` are pre-existing
  baseline debt (MIGRATION.md L9), untouched.
- Live source snapshot: `verify-source-snapshot-v2.py` on the working tree —
  2,286 files, aggregate `4cd946bf…`, `--check` matches (exit 0).
- Phase-dispatch adapter on deterministic stubs: ready path exit 0, timeout
  path exit 5 with full child reaping, dry-run prints without spawning.
- `cargo fmt --check` clean; `cargo check --workspace --offline` green after
  `cargo fetch --locked`. Pilot-shaped probe (read-only, not the C6 pilot):
  `amendment_provenance::…::argument_parsing_is_closed_and_requires_one_action`
  matches exactly 1 test and passes — 1 passed, 0 failed.
- Path router on this branch: `path-run.py status/route` correctly report
  `project directory must be real` (no `.project` before merge); `--dry-run
  round` resolves the plan without spawning. Not-workflow-ready is the
  expected honest outcome here — it is not hidden behind any PASS.

## Owner gates required to proceed

| # | Gate | Exact command / action |
|---|---|---|
| 1 | Push the branch | `git push -u origin chore/allspark-path-pdd-bootstrap` (note: `main` is 251 commits ahead of `origin/main`; pushing this branch publishes nothing beyond it, but the bootstrap PR cannot merge to `origin/main` until those 251 commits are also pushed — owner decision) |
| 2 | Review and accept the bootstrap PR | 4 commits (overlay+instructions, native Path contracts, hook-chain verifier, migration control plane) |
| 3 | Allspark login + model selection | In Allspark: `/login`, then `/model`; afterwards `python3 scripts/ai/allspark-settings.py export-model` on this branch |
| 4 | Clean baseline + native Path init | After PR merge: fetch, checkout `origin/main`, run `/skill:path` initialize/bind-initial per INSTALL.md §12 |
| 5 | Carry M225 over | First Path milestone re-plans the frozen M225 attention from `docs/agent-stack/history/LEGACY_CROSSWALK.md`; M210 `not-adopted` stays `hold` |

Bootstrap commits on this branch (reviewable unit, 67 files):

- `e7bed926` starter overlay + tracked agent instructions + C0/C1 records;
- `446e20be` native GSD Path contracts (installer-generated);
- `19561041` pre-commit hook guard-chain verifier;
- `c4c45c8a` typed adapter + source snapshot + phase dispatch + CI inventory.

Recovery: private backup `/root/law-nexus-migration-backup-2026-10-23`
(manifest id `3a691ee67857bf153ceaa0cf93d23757ee2330cfcd70b4444247a6800a433d50`);
git revert for tracked changes; ignored/local state restored from the backup
(separate recovery checkout, read-only first).


## Final gate (2026-10-23, head `ddbe7784`)

- Targeted suites `test_harness_governor.py + test_harness_preflight.py +
  test_project_state_roadmap_freshness.py`: **242 passed, 0 failed**.
- Tracked-tree hygiene confirmed: no `.project/` contents, no
  `m210/temporal-legal-model/crates/product-model` mutations, M210
  `not-adopted` pin untouched; credentials/runtime state only in ignored
  local dirs (backup holds the private copies, mode 0700).
- Working tree clean; 5 migration commits on
  `chore/allspark-path-pdd-bootstrap`, nothing pushed.


## Rust battery (2026-10-23, head `c4c45c8a` + docs)

- `cargo clippy --workspace --offline --all-targets -- -D warnings`: exit 0.
- `cargo test --workspace --offline` (full log `/tmp/mig-rust-full.log` on the
  build machine; not a tracked artifact): exit 0, **465 suites, 3264 passed,
  0 failed** — includes the earlier read-only pilot probe
  (`argument_parsing_is_closed_and_requires_one_action`, exactly 1 test, PASS).
- `cargo fmt --all -- --check` and `cargo check --workspace --offline`: exit 0
  (after `cargo fetch --locked`).


## Disposable-clone restore proof (2026-10-23)

A fresh `git clone` of the branch head into `/tmp/mig-restore2` and checkout
`chore/allspark-path-pdd-bootstrap` (head `ee49f458`) shows exactly what Git
carries and what a new machine must restore:

- Tracked and present: `.ai/` pins and settings (6 files), `scripts/ai/`
  launchers (10 files), native Path contracts, runbooks, the cutover marker
  (`cutover: false`), the typed adapter and successor checks.
- Absent by design: `.ai/local/` (pinned tool payloads), generated skill
  bundles (Path/PDD), `.project/` (created only by native initialization),
  credentials/sessions. A new machine runs `bootstrap tools → skills →
  hooks` then `allspark-settings.py apply` + `/login` (see INSTALL.md §14),
  and no auth material ever travels through Git.
