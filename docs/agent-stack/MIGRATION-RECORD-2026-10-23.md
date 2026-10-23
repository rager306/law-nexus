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
