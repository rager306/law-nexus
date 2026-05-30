# M051 S02 Git Lex Code Analysis

Status: partial slice code map for T01 and T02, verified 2026-05-30. This document maps the upstream `git-lex` runtime and `subtext-mcp` wrapper from local vendor checkouts using GitNexus-indexed repositories plus targeted source reads. It does not claim runtime proof; later S02/S03 tasks must execute isolated proof commands before ACP adoption decisions.

## Source and GitNexus anchors

| Subject | GitNexus repo | Local path | Indexed commit | Evidence |
|---|---|---|---|---|
| Main runtime | `git-lex-reference` | `/root/vendor-source/git-lex` | `eaa4b24` | `npx gitnexus query -r git-lex-reference ...`; contexts in `.gsd/exec/8adf69e9-1692-4550-8bff-50054acca534.stdout`; targeted source extraction in `.gsd/exec/453d38ff-7f67-4fb5-b7d9-f521474a4ce4.stdout` |
| MCP wrapper | `subtext-mcp-reference` | `/root/vendor-source/subtext-mcp` | `bac5529` | `npx gitnexus query -r subtext-mcp-reference ...`; source extraction in `.gsd/exec/7f8d33e7-7f67-4fb5-b7d9-f521474a4ce4.stdout` |
| Prior inventory | n/a | `prd/architecture/acp/M051-S01-GIT-LEX-SOURCE-INVENTORY.md` | n/a | S01 confirms both code indexes match local checkout anchors and `/root/law-nexus/.lex` was absent. |

GitNexus warning: the broad natural-language query against `git-lex-reference` reported missing FTS indexes, but symbol-name and vector-backed queries still returned command and process symbols. This analysis therefore uses exact symbol queries plus targeted source reads for high-value functions.

## T01: Main `git lex` runtime map

### Command routing

`src/main.rs` defines the Clap `Commands` enum and dispatches in `main` through a direct `match`:

| Command / surface | Main symbol | File:lines | Observed implementation seam | ACP implication |
|---|---|---:|---|---|
| `git lex init` | `cmd_init` | `src/main.rs:213` | Initializes `.lex/`, installs base kit plus optional kit through `resolve_kit_spec`, writes repo config/scaffold. | Proof must run in an isolated temp repository, never `/root/law-nexus`, because it mutates `.lex/` and can fetch/install kit content. |
| `git lex create` | `cmd_create` | `src/main.rs:829` | Creates markdown documents from installed ontology/classes; uses kit resolution and class metadata. | Useful only after `init`/kit install; ACP proof should capture generated frontmatter shape and file path. |
| `git lex save` | `cmd_save` | `src/main.rs:1021` | Save path crosses harness sync and raw mirror flows, then stages/commits/syncs. GitNexus process hits `sync_skills`, `split_frontmatter`, `find_git_root`, and `raw_mirror::run`. | High mutation surface: it invokes git staging/commit behavior and Raw mirror; ACP proof should avoid it until a temp repo fixture and expected commit policy are explicit. |
| `git lex validate` | `cmd_validate` | `src/main.rs:1216` | Loads kit shapes from `.lex/ontology/<kit>/<kit>-shapes.ttl` and adaptive `_ontology/**-shapes.ttl`; parses SHACL with `rudof`/`shacl_*`; validates frontmatter-derived Turtle for markdown files. | Validation is real code-backed SHACL processing, but parse failures currently return success in some shape-loading branches; proof must include a negative document fixture. |
| `git lex parse` | `cmd_parse` | `src/main.rs:1405` | Debug parser path for markdown syntax tree. | Helpful diagnostic only; not sufficient as ACP semantic proof. |
| `git lex extract` | `cmd_extract` | `src/main.rs:1540` | Cleans staged sidecars, runs `generate_frontmatter_nquads`, extracts markdown links, extracts JSONL sessions, exits non-zero on frontmatter errors. | Good isolated proof target for `.spo` sidecars and extraction errors. It mutates `.lex/extract/`. |
| `git lex sync` | `cmd_sync` | `src/main.rs:1584` | Opens/creates persistent Oxigraph store, computes HEAD, rebuilds adaptive shapes, has fast path for already-synced HEAD, clears virtual graphs, loads git triples, loads current frontmatter N-Quads, and maintains sync/history graphs. | Core runtime proof target. Requires at least one commit and must run in disposable repo because it writes derived store under git/lex state. |
| `git lex query` | `cmd_query`, `run_query` | `src/main.rs:2414`, `2260` | Prefers persistent store; falls back to in-memory store from `generate_git_nquads` and `load_lex_nquads`; prefixes query via `add_prefixes`. | ACP proof can check query behavior before/after `sync`; persistent-vs-in-memory path must be recorded separately. |
| `git lex serve ...` | `Commands::Serve` | `src/main.rs:2486` | Delegates directly to external `git-lex-serve` binary with trailing args. | Runtime proof must verify bundled/install path for `git-lex-serve`; code alone does not prove the binary exists. |
| `git lex kit-update` | `cmd_kit_update` | `src/main.rs:2993` | Re-downloads/reinstalls kit, preserving content/extractions and optionally forcing scaffold overwrite; reuses `resolve_kit_spec`, base kit, and SHACL hints. | Acquisition/update proof must isolate network/cache behavior and distinguish kit content changes from runtime changes. |
| `git lex history-verify` | `cmd_history_verify` | `src/main.rs:2646` | Reconstructs live-at-HEAD triples from history graph and compares against current `.spo` emission through the same emitter. | Strong candidate for ACP invariant proof after sync/extract fixture is established. |
| `git lex raw backfill` | `cmd_raw_backfill` | `src/main.rs:2510` | Calls `raw_mirror::backfill` and reports copied historical harness sessions. | Raw mirror is a separate provenance surface; ACP proof should not enable it unless the harness path fixture is explicit. |

### N-Quads, SHACL/OWL subset, and frontmatter flow

GitNexus exact-symbol query returned `generate_frontmatter_nquads` in `src/nquad.rs:416-616` with process links to `parse_kit_shapes` and `parse_shape_file` in `src/ontology.rs`. Targeted source reads show the generator:

- builds the canonical `/<base>/now` graph;
- walks `.md` and `.txt` files while skipping dot-prefixed paths such as `.lex/` and `.git/`;
- parses YAML frontmatter with `serde_yaml` into flattened SPO-style lines;
- extracts `[[wikilinks]]` from body text;
- creates `.lex/extract` as a side-effect;
- uses kit object-property and datatype lookups derived from ontology shape parsing.

`src/shacl.rs:25` exposes `parse_shacl_hints`; `cmd_validate` loads kit-owned SHACL shapes and adaptive `_ontology` shapes. The current code map supports a bounded claim: git-lex contains SHACL-oriented parsing/validation and Turtle/N-Quads emission paths. It does not support an unqualified OWL reasoner claim. Any ACP wording should say “kit ontology / Turtle / SHACL shape subset used by git-lex” unless later runtime evidence proves more.

### Raw mirror behavior

`src/raw_mirror.rs:308` implements `run(root: &Path) -> MirrorReport`; `cmd_save` invokes this before staging so mirrored files can land in the same commit. The mirror reads `raw-mirror` config from `.lex/repo.yml`, expands harness watch paths, copies matching files into `Raw/<harness>/`, records first-seen dates in mirror state, and treats per-file failures as best-effort rather than fatal. `cmd_raw_backfill` calls the backfill variant to rescue pre-existing sessions using mtime as first-seen date.

ACP implication: Raw is byte-faithful acquisition/provenance support, not graph semantics by itself. Proof should verify it only in a fixture with synthetic harness files and should separately assert that Raw is disabled/no-op by default in the ACP temp repo unless configured.

### Main runtime risks and proof seams

1. `save`, `extract`, `sync`, `kit-update`, and `raw backfill` all mutate repository-local state. Run only inside a disposable fixture.
2. `sync` depends on a real Git HEAD; an empty repository path is not enough.
3. `serve` is an external binary delegation (`git-lex-serve`), not implemented inside `src/main.rs` beyond process execution.
4. `validate` contains real SHACL processing, but some setup failures are logged and skipped rather than failing hard; negative validation proof is required before treating it as an enforcement boundary.
5. The code map supports deterministic runtime/proof work, but not production ACP adoption without later isolated runtime evidence.

## T02: `subtext-mcp` wrapper map

### MCP server and broker topology

GitNexus query on `subtext-mcp-reference` identified the dominant process as `server.ts:main -> setupHostBinaries / ensureBroker`, with `server.ts`, `broker.ts`, `cli.ts`, `lib/host-binaries.ts`, `hooks/hooks.json`, `shared/types.ts`, and `package.json` as relevant files.

| Surface | Symbol / file | Lines | Behavior | ACP implication |
|---|---|---:|---|---|
| MCP server | `server.ts`, `main` | `570-679` | On startup, optionally activates host binaries from `CLAUDE_PLUGIN_ROOT`, starts broker, gets cwd/git root/tty, registers peer, starts polling/heartbeat, and connects MCP stdio transport. | Practical acquisition/runtime wrapper for Claude Code plugin context, but startup depends on Bun, plugin env, and bundled binaries. |
| Broker startup | `ensureBroker` | `server.ts:67-92` | Checks localhost broker health, spawns `bun broker.ts` detached if absent, waits up to 6 seconds. | Proof should check broker lifecycle and failure modes; detached process is a cleanup concern. |
| MCP tools | `TOOLS`, request handlers | `server.ts:145-522` | Provides `list_peers`, `send_message`, `set_summary`, `check_messages`, and `start_viz`. | The wrapper is mostly peer messaging plus a git-lex visualization launcher; it is not a general git-lex command API. |
| Visualization launcher | `start_viz` handler | `server.ts:431`, `452` | Runs `git lex sync` if the graph store is absent, then spawns `git lex serve viz`, returning `http://localhost:<port>/`. | Useful proof shortcut for packaged `git lex` + `git-lex-serve`, but it triggers runtime mutation through `sync`. |
| Broker daemon | `broker.ts` | key handlers `138-223` | Singleton HTTP server on `127.0.0.1:7901`, backed by SQLite; tracks peers and routes queued messages. | Local-only coordination surface; not ACP evidence except for wrapper operational viability. |
| CLI | `cli.ts` | command cases | Provides `status`, `send`, and `kill-broker` around broker HTTP endpoints. | Operational helper for cleanup/diagnostics during proof. |
| Host binaries | `setupHostBinaries` | `lib/host-binaries.ts:30-70` | Detects target triple, symlinks `bin/.platforms/<target>/*` into plugin top-level `bin/`, logs unsupported/missing binaries without crashing. | This is the strongest acquisition path: packaged platform binaries can expose `git-lex` to Claude Code’s plugin PATH, but proof must inspect available platform dirs and executable names. |
| Package scripts | `package.json` | `scripts.broker`, `scripts.server` | Uses `bun broker.ts` and `bun server.ts`. | Runtime proof requires Bun availability or a plugin host that supplies it. |
| Hooks | `hooks/hooks.json` | hook config | Indexed as plugin hook configuration. | Needs separate review before claiming automated lifecycle integration. |

### Practical acquisition/runtime assessment

`subtext-mcp` can likely provide a practical path for ACP proof when the goal is to test the same packaged experience a Claude Code plugin user would get: host binary activation, MCP startup, broker, and `start_viz` driving `git lex sync` + `git lex serve viz`.

It is not sufficient as the primary semantic proof mechanism because:

- `start_viz` hides important runtime details behind MCP handler logic; ACP proof still needs direct CLI evidence for `init`, `create`, `extract`, `validate`, `sync`, `query`, `history-verify`, and Raw behavior.
- `setupHostBinaries` logs and continues when binaries are missing or platform is unsupported, so MCP startup success does not prove `git-lex` is available.
- broker state is local SQLite on `127.0.0.1:7901`; detached processes must be cleaned up between proof runs.
- the wrapper is designed around Claude Code peer messaging, not legal-domain graph correctness.

### Unsafe or unclear until runtime proof

1. Whether current package contents include `git-lex` and `git-lex-serve` binaries for the proof host target.
2. Whether Claude/plugin PATH setup exposes those symlinks to subprocesses exactly as expected.
3. Whether `start_viz` reliably detects existing graph store and avoids redundant `sync` in all fixture states.
4. Whether broker SQLite location and cleanup behavior are acceptable for repeatable CI-style proof.
5. Whether hook configuration is desirable for ACP proof or should be disabled to avoid ambient side effects.

## Runtime proof checklist for downstream task input

This is the S04 runtime proof checklist derived from the T01/T02 code map. It is not runtime evidence by itself; every command below must run in an isolated disposable fixture and record stdout/stderr, exit code, mutated files, and cleanup results.

### Fixture and binary preflight

1. Create a disposable git repository outside `/root/law-nexus` and before/after assert the project working tree still has no runtime state at `/root/law-nexus/.lex`.
2. Record binary paths and versions before mutation:
   - `command -v git` and `git --version`.
   - `command -v git-lex || command -v git` plus `git lex --help`.
   - `git lex --version` if supported; if it exits non-zero, record the exact unsupported-version behavior rather than treating it as fatal.
   - `command -v git-lex-serve` before any `git lex serve viz` proof.
   - For the MCP wrapper path, record `command -v bun`, `node --version`, `bun --version`, and any plugin-provided binary path under `subtext-mcp/bin/` or `bin/.platforms/<target>/`.
3. Stop immediately if the command under test resolves to a binary outside the intended fixture/package path and that path cannot be explained in the proof log.

### Direct `git lex` command proof

| Proof target | Exact command surface | Expected files or state | Required checks |
|---|---|---|---|
| Help surface | `git lex --help` | No `.lex` mutation in either fixture or `/root/law-nexus`. | Output lists at least `init`, `sync`, `query`, `extract`, `validate`, and `kit-update` or the equivalent current command names. |
| Version surface | `git lex --version` | No repo mutation. | Capture version if available; otherwise capture stable non-zero behavior as a packaging gap. |
| Init | `git lex init --kit <known-local-or-network-safe-kit>` from the temp repo | `.lex/`, `.lex/repo.yml`, ontology/kit files, scaffold files if generated. | Assert `.lex` exists only in the fixture; inspect kit/source fields in `.lex/repo.yml`; record any network/cache access. |
| Create/frontmatter | `git lex create <class-or-template> ...` or the narrowest available create command discovered from `--help` | A markdown document with YAML frontmatter. | Confirm required frontmatter keys, deterministic IDs/subjects if present, and no malformed YAML. |
| Extract/RDF sidecars | `git lex extract` | `.lex/extract/` plus emitted `.spo`, Turtle, N-Quads, or equivalent RDF sidecars documented by the current binary. | Inspect generated triples for the document subject, frontmatter predicates, datatype/object predicate handling, and wikilink triples. |
| Sync/Oxigraph store | `git add . && git commit -m fixture && git lex sync` | Persistent graph/store state under the fixture-local git/lex location and sync metadata for current `HEAD`. | Re-run `git lex sync` once to prove already-synced idempotence; record created store path and graph names if printed. |
| Query/SPARQL | `git lex query --json '<SPARQL>'` and the same query without `--json` if supported | Query reads either persistent store after `sync` or in-memory fallback before sync. | Use a minimal SPARQL query for the created document subject and at least one frontmatter predicate; validate JSON is parseable when `--json` is requested. |
| Validate/SHACL | `git lex validate` against one valid and one invalid fixture document | Validation output and exit codes for both cases. | Prove whether invalid shape/frontmatter constraints fail hard; if setup errors are logged but skipped, record this as a blocker for enforcement claims. |
| History invariant | Make a second commit, run `git lex sync`, then `git lex history-verify` | History graph and symmetric-difference report. | Expect clean verification for unchanged current state; record exact diff output for an intentional mismatch if one is feasible without corrupting fixture state. |
| Serve/viz | `git lex serve viz --port <free-port>` or current help-approved equivalent | Running `git-lex-serve` child process and HTTP listener. | Only run after `command -v git-lex-serve`; capture URL/port, then kill the child process and prove the port is closed. |
| Kit update | `git lex kit-update --help`, then a safe pinned/local `git lex kit-update ...` only if fixture kit source is controlled | Updated kit files or explicit no-op. | Distinguish runtime update behavior from network acquisition; stop if it would fetch unpinned remote content. |
| Raw mirror | Configure synthetic harness input path in fixture `.lex/repo.yml`, then run the narrowest safe `git lex raw backfill` or `git lex save` proof | `Raw/<harness>/...` copies and mirror state in `.lex`. | Verify byte-for-byte copy, first-seen metadata, and no reads from real harness paths. |

### `subtext-mcp` wrapper proof

1. From the `subtext-mcp` package checkout or installed plugin root, inspect `bin/.platforms/<target>/` and prove whether both `git-lex` and `git-lex-serve` binaries exist for the current OS/architecture.
2. Run the wrapper startup with `CLAUDE_PLUGIN_ROOT` pointing at a disposable copy if possible; confirm `setupHostBinaries` creates or refreshes only plugin-local symlinks in `bin/`.
3. Start the broker through the package script or CLI, then verify `127.0.0.1:7901` health/status, peer registration, and SQLite state location.
4. Exercise MCP `start_viz` only against the fixture git repo: expected behavior is `git lex sync` if the graph store is absent, then `git lex serve viz` with a returned localhost URL.
5. Cleanup must run `subtext-mcp` CLI `kill-broker` if available; otherwise kill only the recorded broker PID and viz PID, remove the disposable plugin copy, and prove no listener remains on `127.0.0.1:7901` or the viz port.

### Cleanup rules

- Never run `init`, `sync`, `query`, `extract`, `save`, `raw backfill`, `serve`, or MCP `start_viz` from `/root/law-nexus`.
- Remove the temp repository, temp plugin copy, generated `.lex` state, broker SQLite file, and any child processes after each proof attempt.
- After cleanup, assert `/root/law-nexus/.lex` is still absent and no `git-lex-serve`, `bun broker.ts`, or orphaned `subtext-mcp` process remains from the proof.
- Keep proof logs outside ignored local runtime directories if the result must be committed; do not rely on `.gsd/` as the only evidence location for S04.

### Blockers to stop on

- `git lex init` mutates `/root/law-nexus` or any non-fixture repository.
- `git lex --help` does not expose the command surfaces mapped in T01 (`init`, `extract`, `sync`, `query`, `validate`) and the mismatch cannot be explained by version drift.
- `git lex sync` cannot operate after a real fixture commit, or silently drops frontmatter triples needed for the SPARQL proof.
- Invalid frontmatter or invalid SHACL constraints exit successfully without an explicit documented warning that downstream ACP can tolerate.
- `git-lex-serve` is missing, resolves to an unexpected binary path, or leaves an unkillable listener.
- `setupHostBinaries` reports unsupported platform or missing binaries while MCP startup still appears successful.
- Broker startup requires ambient user state, real Claude plugin state, or a global SQLite location that cannot be isolated and cleaned.

### Failure Modes

External dependencies for S04 proof are filesystem mutation, git subprocesses, git-lex/git-lex-serve binaries, optional kit network/cache access, Oxigraph store creation, Bun/Node for `subtext-mcp`, localhost ports, and broker SQLite state. Expected failure paths: missing binary, unsupported `--version`, malformed frontmatter parse errors, invalid SHACL shape handling, no git `HEAD`, remote kit fetch timeout, port collision, detached broker orphaning, and unexpected global state reads. The proof must either show each failure bubbles with non-zero exit/status or record a blocker when the implementation logs-and-continues in a way that would make ACP adoption claims unsafe.

### Load Profile

The runtime proof is single-fixture and not a throughput benchmark, so no 10x production load breakpoint is claimed here. The first likely saturation points at 10x fixture size are recursive markdown/RDF extraction under `.lex/extract`, Oxigraph store rebuild/sync, and broker polling/SQLite queue growth. S04 should keep the fixture intentionally small, record file counts and store size, and defer any caching, pagination, or pool-sizing claims until a dedicated load slice exists.

### Negative Tests

S04 should include at least these negative proof cases: malformed YAML frontmatter during `git lex extract`; missing git `HEAD` before `sync`; invalid SHACL/frontmatter shape during `validate`; unsupported or missing `git-lex-serve` before `serve viz`; occupied broker port `7901`; missing Bun for `subtext-mcp`; unsupported `bin/.platforms/<target>` for `setupHostBinaries`; and Raw mirror config pointing at a nonexistent synthetic path. There are no committed automated test files in T03 because this task only updates the runtime proof plan; the negative cases must become executable proof commands in S04.

## Bottom-line ACP implications

- `git-lex-reference` has a coherent Rust runtime for command routing, extraction, N-Quads generation, SHACL-oriented validation, Oxigraph sync/query, kit update, history verification, and Raw mirror support.
- `subtext-mcp-reference` has a plausible MCP/plugin acquisition wrapper and visualization launcher, but it should be treated as packaging/orchestration evidence rather than semantic correctness evidence.
- The next proof work must be runtime-first and fixture-isolated. Code analysis alone is enough to plan proof commands, not enough to accept ACP production use.
