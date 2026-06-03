# M052 S05 Remaining CLI Command Matrix

## Status

In progress for `M052-idogd6 / S05`.

S05 maps and smoke-tests the remaining git-lex CLI command surface after M051 and M052/S01-S04. It preserves the no-main-`.lex` rule and runs mutating/destructive commands only in disposable `/tmp` repositories.

## Guardrails

- Do not create or mutate `/root/law-nexus/.lex`.
- Do not run destructive commands outside disposable `/tmp` repositories.
- Record before/after filesystem and git status for mutating commands.
- Do not treat local smoke as production adoption.
- Do not push remote state from this repository.

## T01: CLI command handler inventory

### Source trace note

A GitNexus query against `git-lex-reference` warned that FTS indexes were degraded even after the background reindex notification. T01 therefore uses direct source anchors from the indexed vendor checkout plus the already refreshed source tree:

```text
/root/vendor-source/git-lex/src/main.rs
/root/vendor-source/git-lex/src/bin/git-lex-serve.rs
/root/vendor-source/git-lex/src/raw_mirror.rs
```

### Command enum and dispatch anchors

| Surface | Source anchor | Handler / behavior |
|---|---|---|
| CLI enum | `/root/vendor-source/git-lex/src/main.rs:80-195` | Declares `Query`, hidden `Extract`, hidden `Validate`, hidden `Hook`, `Dump`, `Sync`, `List`, `Create`, `Save`, `Join`, `Parse`, `Nuke`, `KitUpdate`, `Display`, `Serve`, `HistoryVerify`, and `Raw`. |
| Raw subcommands | `/root/vendor-source/git-lex/src/main.rs:195-201` | `raw backfill` only. |
| Dispatch | `/root/vendor-source/git-lex/src/main.rs:2450-2507` | Routes each enum variant to handler; `Serve` delegates to `git-lex-serve`; `Raw` dispatches to `cmd_raw_backfill`. |
| Server binary | `/root/vendor-source/git-lex/src/bin/git-lex-serve.rs` | `viz` and `listen` were covered by S04. |

### Remaining command inventory

| Command | Handler source | Mutation profile | Runtime hypothesis for S05 |
|---|---|---|---|
| `create <doctype> [instance] [--json]` | `cmd_create`, `/root/vendor-source/git-lex/src/main.rs:829-1014` | Creates a markdown document under kit folder base/class directory. Fails if type unknown or file exists. Does not commit by itself. | Mutating; run only in `/tmp`. Use `--json` for machine-readable result. |
| `save [message]` | `cmd_save`, `/root/vendor-source/git-lex/src/main.rs:1021-1108` | Syncs harness skills/subagents, mirrors Raw sessions, runs `git add -A`, commits with resolved agent identity, and hooks run extract/validate/sync. | Mutating and commits; run only in `/tmp` with explicit `GIT_AUTHOR_*`/committer env. |
| `join <squad_path>` | `cmd_join`, `/root/vendor-source/git-lex/src/main.rs:1111-1207` | Writes `.lex/tickets/*.ticket` in agent repo and `.lex/members/*.yml` in squad repo. Does not commit; tells user to commit both. | Cross-repo mutating; run only between two disposable `/tmp` git-lex repos. |
| `parse <file>` | `cmd_parse`, `/root/vendor-source/git-lex/src/main.rs:1405-1482` | Reads a markdown file and prints tree-sitter syntax tree/stats. No writes. | Safe read-only smoke in `/tmp` or vendor fixture. |
| `display <query> --port <port>` | `cmd_display`, `/root/vendor-source/git-lex/src/main.rs:1489-1512` | POSTs query to a running local viz server `/api/run-and-push`; no filesystem writes. | Local API client. S04 proved endpoint; S05 should run command against isolated viz server if practical. |
| `nuke` | `cmd_nuke`, `/root/vendor-source/git-lex/src/main.rs:2893-2991` | Destructive: confirmation prompt, removes hook, auto-commits snapshot, `git rm -rf .lex`, deletes `.lex`, deletes `.git/lex`, unregisters repo, commits removal, then attempts `git push`. | Destructive and outward-action-prone. Run only in disposable repo with no remote; feed `nuke` on stdin. Must record push failure/no remote as expected. |
| `kit-update [kit] [--force]` | `cmd_kit_update`, `/root/vendor-source/git-lex/src/main.rs:2993-3210` | Re-fetches base and domain kit from GitHub, reinstalls scaffold, may overwrite with `--force`, refreshes identity, removes legacy `.env`, regenerates shapes/templates, audits folders. | Mutating and network-dependent. Prefer help/source-only unless isolated runtime is needed; if run, use `/tmp` only and no `--force` first. |
| `raw backfill` | `cmd_raw_backfill`, `/root/vendor-source/git-lex/src/main.rs:2510-2535` plus `raw_mirror::backfill` | Copies configured harness session files into `Raw/` based on `.lex/repo.yml` raw-mirror config. | Mutating only if raw-mirror harness paths exist. In default squad repo likely no-op; safe in `/tmp`. |
| hidden `extract` | `cmd_extract`, `/root/vendor-source/git-lex/src/main.rs:1540+` | Writes `.spo` sidecars and extraction logs; exits non-zero on frontmatter extraction errors. | Already indirectly exercised by commits/hooks; can classify as mutating derived extraction surface. |
| hidden `validate` | `cmd_validate`, `/root/vendor-source/git-lex/src/main.rs:1216+` | Reads shapes/files; no intentional writes. | Covered by S01; not primary S05 target. |
| hidden `hook pre-commit` | `hook_pre_commit`, `/root/vendor-source/git-lex/src/main.rs:1527-1537` | Runs extract, stages `.lex/extract`, validates. | Covered indirectly by `git commit` and `save`; direct invocation optional only in `/tmp`. |
| `serve` | dispatch and `git-lex-serve` | Starts local server. | Covered by S04. |
| `history-verify` | `cmd_history_verify`, `/root/vendor-source/git-lex/src/main.rs:2645+` | Read-only comparison over history graph and `.spo`. | Covered by M051/S10 and S03 workspace. |
| `query`, `dump`, `sync`, `list`, `init` | earlier handlers | Already covered by M051/S10/S01-S04. | Not primary remaining matrix except help/status as baseline. |

### Safety classification hypothesis before runtime

| Command | Pre-runtime S05 class | Reason |
|---|---|---|
| `parse` | safe-smoke | Read-only file parse. |
| `display` | safe-smoke with local server | API POST to local viz server; no file writes. Requires server lifecycle cleanup. |
| `raw backfill` | conditional mutating/no-op | Mutates only if raw-mirror config/harness paths exist. |
| `create` | disposable mutating | Creates new content file. |
| `save` | disposable mutating/committing | Commits all changes and runs hooks. |
| `join` | disposable cross-repo mutating | Writes membership/ticket files in two repos. |
| `kit-update` | disposable/network mutating or source-only | Fetches from GitHub, rewrites kit/scaffold-derived files; `--force` can clobber. |
| `nuke` | destructive disposable only | Deletes `.lex`/`.git/lex`, commits removal, attempts push. |
| hidden `extract`/`hook` | disposable mutating | Writes/stages extraction artifacts. |

### T01 conclusion

S05 runtime execution should proceed in two groups:

1. Safe/help/read-only checks: command help, `parse`, `display` against a local isolated viz server if started, default no-op `raw backfill` if no raw-mirror config exists.
2. Disposable mutating matrix: `create`, `save`, `join`, `kit-update`, `raw backfill` with controlled config, `extract`/`hook`, and `nuke` in isolated repos with before/after filesystem and git status evidence.

No result from this matrix can approve production adoption or main-repo `.lex` use. The output is command-by-command adapter relevance and risk classification.

## T02: Safe CLI help and smoke checks

### Evidence anchor

```text
.gsd/exec/a0dc6473-7094-463e-a698-cb94d57d9604.stdout
```

### Workspace and server lifecycle

Safe smoke checks ran in the existing isolated workspace:

```text
/tmp/m052-s04-serve-co1uhmmh
```

For `display`, S05 started an isolated local `viz` server:

```text
cd /tmp/m052-s04-serve-co1uhmmh && \
PATH=/root/vendor-source/git-lex/target/debug:$PATH \
/root/vendor-source/git-lex/target/debug/git-lex-serve viz --port 8894
```

`bg_shell` readiness detected `http://127.0.0.1:8894`. After `display` smoke, the server was killed and `bg_shell list` returned:

```text
No background processes.
```

### Help matrix

All targeted help commands exited `0`:

| Command | Exit | Result |
|---|---:|---|
| `git-lex --help` | 0 | Listed top-level commands. |
| `git-lex create --help` | 0 | Syntax: `git-lex create [OPTIONS] <DOCTYPE> [INSTANCE_ID]`; supports `--json`. |
| `git-lex save --help` | 0 | Syntax: `git-lex save [MESSAGE]`; default message `git lex save`. |
| `git-lex join --help` | 0 | Syntax: `git-lex join <SQUAD_PATH>`. |
| `git-lex parse --help` | 0 | Syntax: `git-lex parse <FILE>`. |
| `git-lex nuke --help` | 0 | Syntax: `git-lex nuke`. |
| `git-lex kit-update --help` | 0 | Syntax: `git-lex kit-update [OPTIONS] [KIT]`; supports `--force`. |
| `git-lex display --help` | 0 | Syntax: `git-lex display [OPTIONS] <QUERY>`; supports `--port`. |
| `git-lex serve --help` | 0 | Pass-through syntax: `git-lex serve [ARGS]...`. |
| `git-lex history-verify --help` | 0 | Shows `--show` mismatch output option. |
| `git-lex raw --help` | 0 | Shows Raw harness mirror purpose. |
| `git-lex raw backfill --help` | 0 | Syntax: `git-lex raw backfill`. |

### Read-only / safe smoke checks

| Command | Exit | Evidence | Classification |
|---|---:|---|---|
| `git-lex parse README.md` | 0 | Output contained `Tree-sitter parse: README.md` and `Total nodes:`. | safe-smoke read-only |
| `git-lex raw backfill` in default squad workspace | 0 | `No raw-mirror harness paths configured (or none exist on disk). Add a raw-mirror block...` | safe no-op in default squad workspace |
| `git-lex display 'CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 2' --port 8894` | 0 | `Pushed scene to http://127.0.0.1:8894/api/run-and-push` | local API client smoke; depends on running viz server |

### T02 classification

```text
help surfaces: runtime-backed
parse: runtime-backed read-only debug command
raw backfill default/no-config behavior: runtime-backed no-op
display local API client: runtime-backed against isolated viz server
main repository safety: `/root/law-nexus/.lex` absent
server cleanup: no background processes remain
```

The mutating and destructive commands remain for T03.

## T03: Disposable mutating CLI matrix

### Evidence anchors

```text
.gsd/exec/f4a34fdf-8fd8-400a-8f3e-85ee0b612cb3.stdout
.gsd/exec/2df18944-60b6-4731-ba18-7efaf9e3bb5d.stdout
```

### Matrix summary

All T03 commands ran only in disposable `/tmp` repositories. `/root/law-nexus/.lex` remained absent.

| Command | Workspace | Exit | Before -> after | Side effects | Classification |
|---|---|---:|---|---|---|
| `create Task s05-task --json` | `/tmp/m052-s05-create-xetflefk` | 0 | clean -> `?? Squad/Task/s05-task.md` | Created `Squad/Task/s05-task.md`; JSON contained path, URI, class `squad:Task`, id `s05-task`. | runtime-backed mutating create |
| `save` immediately after incomplete created Task | `/tmp/m052-s05-create-xetflefk` | 1 | `?? Squad/Task/s05-task.md` -> staged `.lex/extract/...` + created task | Commit failed because SHACL validation reported `MinCount(1) not satisfied` for the generated-but-unfilled Task. | important failure mode |
| `save` after README-only change | `/tmp/m052-s05-save-success-*` | 0 | `M README.md` -> clean | Committed with explicit env identity `M052 Save Agent <m052-save@example.test>` and message `m052 save readme change`; hooks extracted/validated. | runtime-backed mutating commit |
| `join <squad_path>` | `/tmp/m052-s05-join-agent-*` + `/tmp/m052-s05-join-squad-*` | 0 | clean/clean -> agent `?? .lex/tickets/`, squad `?? .lex/members/` | Wrote membership ticket in agent repo and member YAML in squad repo; did not commit. | runtime-backed cross-repo mutation |
| `raw backfill` with controlled raw-mirror config | `/tmp/m052-s05-raw-*` | 0 | `M .lex/repo.yml` -> `M .lex/repo.yml | ?? Raw/` | Copied one controlled `*.jsonl` file to `Raw/TestHarness/2026-06-01-session-abc.jsonl`. | runtime-backed conditional mutation |
| hidden `extract` | `/tmp/m052-s05-extract-*` | 0 | `?? notes/` -> `?? .lex/extract/notes/ | ?? notes/` | Generated `.spo` extraction sidecars; stderr included markdown links and extraction timing. | runtime-backed derived artifact mutation |
| `kit-update` without `--force` | `/tmp/m052-s05-kitupdate-*` | 0 | clean -> `M .lex/ontology/squad/squad-shapes.ttl` | Fetched base/domain kits from GitHub, installed 4 scaffold files, preserved 11, regenerated shapes/templates; modified generated shapes. | runtime-backed network mutation, adoption-sensitive |
| `nuke` with confirmation in no-remote disposable repo | `/tmp/m052-s05-nuke-kvf5urr0` | 0 | clean -> clean | Removed `.lex/` and `.git/lex/`; committed `git lex nuke`; no background/main effects. | runtime-backed destructive local removal; outward push attempt remains unsafe in real repos |

### Detailed observations

#### `create`

Observed JSON output:

```json
{"class":"squad:Task","id":"s05-task","ok":true,"path":"Squad/Task/s05-task.md","uri":"https://localhost/local/m052-s05-create-xetflefk/Squad/Task/s05-task.md"}
```

The generated file is not automatically committed. It may also be SHACL-invalid until required fields are filled.

#### `save`

Two behaviors are now proven:

1. If pending content violates SHACL, `save` can stage extraction sidecars but fail commit:

```text
Squad/Task/s05-task.md — 1 violation(s): → MinCount(1) not satisfied
fatal: git commit failed
```

2. With a valid README-only change and explicit agent identity env vars, `save` commits successfully:

```text
Saved: m052 save readme change [as M052 Save Agent <m052-save@example.test>]
Validated 1 files ... all pass ✓
```

This means ACP adapters must not call `save` blindly after `create`; they must fill/validate required frontmatter first or handle staged side effects on validation failure.

#### `join`

`join` mutates two repositories but does not commit either:

```text
agent after: ?? .lex/tickets/
squad after: ?? .lex/members/
```

It is not safe as a hidden side effect in ACP automation unless both repos and commit policy are explicit.

#### `raw backfill`

Default S02 no-op is safe; configured backfill is mutating. T03 controlled config copied one JSONL file into `Raw/TestHarness/` and also uses per-machine raw mirror state under `XDG_STATE_HOME`.

#### `kit-update`

`kit-update` is network and scaffold/shape mutating even without `--force`:

```text
Updating base kit ... from GitHub
Updating kit ... from GitHub
Scaffold: 4 file(s) installed, 11 preserved
SHACL shapes regenerated: squad-shapes.ttl
Kit update complete: 12 class templates regenerated.
```

It must remain adoption-sensitive because it can change generated shapes/templates and fetch remote code/content.

#### `nuke`

`nuke` is confirmed destructive. In a disposable no-remote repo it:

- required stdin confirmation `nuke`;
- removed `.lex/`;
- removed `.git/lex/`;
- committed `git lex nuke`;
- left git status clean.

Source still attempts `git push` after local commit; in real repos this is an outward action and must not be run without explicit user confirmation and remote policy.

### T03 classification

```text
create: runtime-backed mutating template/file creation; requires follow-up validation/fill before save
save: runtime-backed commit flow; can fail after staging extraction artifacts when validation fails
join: runtime-backed cross-repo mutation; commit policy external
raw backfill: runtime-backed no-op by default, mutating with config
extract/hook behavior: runtime-backed derived sidecar mutation
kit-update: runtime-backed network/scaffold mutation; adapter-sensitive
nuke: runtime-backed destructive local removal and commit, with unsafe push attempt in real repos
main repository safety: preserved; no `/root/law-nexus/.lex`
```

## T04: CLI adoption relevance classification

### Final command-by-command classification

| Command | Evidence status | ACP adapter relevance | Final guidance |
|---|---|---|---|
| `init` | Proven in M051/S10 and reused in M052 | Required candidate only for isolated adapter setup | Never run in main repo without explicit adoption decision. |
| `sync` | Proven in M051/S10 and reused in M052 | Required candidate | Safe only after `.lex` policy and derived-store cleanup are defined. |
| `query` | Proven in M051/S10/S03/S04 | Required candidate for graph reads | Use explicit query contracts; SPARQL-star support is narrow per S03. |
| `list --json` | Proven in M051/S10 | Required candidate for class discovery | Prefer over `owl:Class` SPARQL inventory unless ontology triples are loaded. |
| `validate` | Upgraded by S01 | Required candidate only with wrapper gates | Must hard-fail missing shapes/skipped docs/setup errors at adapter level. |
| `parse` | Proven in S05/T02 | Optional diagnostic | Safe read-only debug command. |
| `dump` | Proven in M051/S10 | Optional diagnostic | Derived N-Quads only; not source truth. |
| `history-verify` | Proven in M051/S10/S03 workspaces | Optional diagnostic | Useful for history graph integrity, not ACP authority. |
| `display` | Proven in S05/T02 against S04 viz server | Optional local UI/client | Depends on running local viz; not production proof. |
| `serve` / `git-lex-serve viz` | Proven in S04 | Optional local UI | Browser diagnostics partial due to `/api/store-info`; adapter-later. |
| `git-lex-serve listen` | Partially proven in S04 | Optional/research-only | Standard init blocked by kit-string mismatch; short-kit SSE works. |
| `create` | Proven in S05/T03 | Optional but risky workflow helper | Must be followed by required-field fill and validation before `save`. |
| `save` | Proven success and failure in S05/T03 | Optional but risky workflow helper | Can commit valid changes; can leave staged sidecars after validation failure. |
| `join` | Proven in S05/T03 | Research-only for ACP | Cross-repo mutation; not needed for ACP core. |
| `raw backfill` | Proven no-op and configured mutation in S05 | Research-only / evidence-sensitive | Copies raw harness payloads and touches machine state; not suitable as ACP proof anchor by default. |
| `extract` / `hook pre-commit` | Proven indirectly and direct `extract` in S05 | Adapter-internal if adopted | Derived sidecar mutation; must be cleanup-aware. |
| `kit-update` | Proven in S05/T03 | Adoption-sensitive maintenance only | Network/scaffold mutation; never implicit. |
| `nuke` | Proven destructive in S05/T03 | Unsafe/destructive | Human-confirmed emergency/removal only; source attempts push. |

### Required ACP adapter subset

If ACP ever implements a git-lex adapter, the minimal candidate subset is:

```text
init (isolated only), sync, query, list --json, validate-with-wrapper
```

Optional diagnostics:

```text
parse, dump, history-verify, local viz/display
```

Commands to exclude from unattended ACP automation by default:

```text
nuke, kit-update, join, raw backfill, save, create
```

`create` and `save` can be reconsidered only for an explicitly designed authoring workflow with validation cleanup semantics.

### Runtime adoption gates update

Updated:

```text
.agents/skills/git-lex/references/runtime-adoption-gates.md
```

The gates now record:

- `create` generated-file validation risk;
- `save` staged-sidecar failure mode;
- `join` cross-repo mutation;
- `raw backfill` raw payload and machine-state sensitivity;
- `kit-update` network/scaffold mutation;
- `nuke` destructive removal and push attempt.

### S05 conclusion

S05 converts the remaining CLI surface from mostly untested to command-by-command classified. Several commands are useful as local diagnostics or future adapter primitives, but most workflow/destructive helpers remain unsuitable for unattended ACP automation.

Final disposition:

```text
Required adapter candidates: init/sync/query/list/validate wrapper only
Optional diagnostics: parse/dump/history-verify/display/viz
Workflow helpers: create/save/join/raw backfill are risky and require explicit workflow policy
Maintenance: kit-update is network/scaffold mutating and adoption-sensitive
Destructive: nuke is unsafe outside disposable or human-confirmed removal contexts
ACP adoption: still adapter-later
main repository safety: preserved; no `/root/law-nexus/.lex`
```
