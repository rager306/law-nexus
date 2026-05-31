# M051 S09 Supply Chain and Binary Trust Review

## Scope

This review covers the local vendor snapshots used for the ACP git-lex adoption investigation:

- `/root/vendor-source/git-lex` at source commit `eaa4b24d144a78a8b8e4969404d74cf22267df1f`.
- `/root/vendor-source/subtext-mcp` at source commit `bac5529bb1fdc0ee5c0d9d081a0208f2fefca005`.

The review is evidence-only. It does not assert upstream release integrity beyond files and binaries present in the local snapshots.

## T01: License, dependency, build, workflow, hook, plugin, and MCP surfaces

### License classification

| Component | Evidence | Classification | Notes |
|---|---|---|---|
| `git-lex` | `LICENSE`; `Cargo.toml` `license = "Unlicense"` | Unlicense / public-domain dedication | The LICENSE text permits copy, modification, publishing, use, compiling, selling, and distribution, but carries broad warranty disclaimer. Jurisdictional public-domain uncertainty should be treated as a legal review item before redistribution in strict compliance environments. |
| `subtext-mcp` | No top-level `LICENSE` found; `package.json` has no `license` field; `.claude-plugin/plugin.json` has no license field | Missing explicit license | Adoption or redistribution of the plugin repository and bundled binaries should not proceed without a license grant or a project-local legal decision. |

### Dependency surfaces

#### `git-lex` Rust dependency surface

Evidence reviewed: `Cargo.toml` and `Cargo.lock`.

- `Cargo.lock` is present and contains 395 packages. Build workflow uses `cargo build --release --locked`, so the lockfile is the intended dependency source of truth.
- Major functional dependencies in `Cargo.toml` include:
  - CLI: `clap`.
  - RDF / graph / SHACL: `oxigraph`, `shacl_validation`, `shacl_ir`, `shacl_rdf`, `rudof_rdf`, `sparql_service`, `oxiri`.
  - Git and native crypto: `git2` with `default-features = false` and `vendored-openssl`; lockfile includes `git2@0.20.4`, `libgit2-sys@0.18.3+1.9.2`, and `openssl-sys@0.9.114`.
  - Parsing: `tree-sitter`, `tree-sitter-md`, `regex`, `dateparser`.
  - Server/runtime: `axum@0.8.9`, `tokio@1.52.1`, `tower`, `tokio-stream`, `futures-util`, `reqwest@0.12.28` with `rustls-tls` and default features disabled.
  - Utility/data: `serde`, `serde_json`, `serde_yaml`, `sha2`, `hex`, `open`.
- Supply-chain risk notes:
  - The lockfile is essential because `Cargo.toml` explicitly documents rudof-family sibling-crate API coupling and instructs installation with `cargo install --path . --locked`.
  - Vendored OpenSSL/libgit2 and `oxrocksdb-sys@0.5.7` introduce native build and C/C++ supply-chain surfaces.
  - `reqwest` and server dependencies mean runtime network behavior exists; use must be bounded by command-level policy.

#### `subtext-mcp` TypeScript/Bun dependency surface

Evidence reviewed: `package.json`, `bun.lock`, and `tsconfig.json`.

- `package.json` is private and declares no license. It uses Bun TypeScript entry points.
- Runtime dependency: `@modelcontextprotocol/sdk` `^1.27.1`.
- Peer dependency: `typescript` `^5`.
- Dev dependency: `@types/bun` `latest`.
- `bun.lock` is present and includes `@modelcontextprotocol/sdk`, `@types/bun`, `typescript`, and transitive packages such as `zod`.
- Scripts:
  - `broker`: `bun broker.ts`.
  - `server`: `bun server.ts`.
  - `test`: `bun test`.
- `tsconfig.json` enables strict TypeScript checking, `noEmit`, `moduleResolution = "bundler"`, `allowImportingTsExtensions`, and Bun/ESNext-style module execution.

### Build and workflow surfaces

#### `git-lex` build workflow

Evidence reviewed: `.github/workflows/build.yml`.

- Triggered on pushes to `main`, `v*` tags, pull requests to `main`, and manual dispatch.
- Matrix targets:
  - `aarch64-apple-darwin` on `macos-14`.
  - `x86_64-apple-darwin` on `macos-14`.
  - `x86_64-unknown-linux-gnu` on `ubuntu-latest`.
  - `aarch64-unknown-linux-gnu` is explicitly omitted because the default `cross` image has an old C++ compiler for `oxrocksdb-sys` C++20 requirements.
- Uses `actions/checkout@v4`, `dtolnay/rust-toolchain@stable`, `actions/cache@v4`, `actions/upload-artifact@v4`, and `softprops/action-gh-release@v2`.
- Builds with `cargo build --release --locked --target <target>`.
- Packages release tarballs containing `git-lex`, `git-lex-serve`, `LICENSE`, and `README.md`.
- Produces plugin binary layout artifacts under `plugin-bin-layout/bin/<target>/`.

#### Cross-repository binary sync workflow

Evidence reviewed: `.github/workflows/sync-binaries-to-plugin.yml`.

- Triggered after successful `build` workflow completion on `main`, or manually.
- Checks out `repolex-ai/subtext-mcp` using `SUBTEXT_MCP_PAT` and pushes directly to `main`.
- Downloads `plugin-bin-*` artifacts from the selected build run.
- Copies `git-lex` and `git-lex-serve` into `subtext-mcp/bin/.platforms/<target>/` and sets executable permissions.
- Computes the short source SHA from the upstream build run and commits with message shape `binaries: sync git-lex @ <short-sha>`.
- Trust concern: this workflow is a high-impact supply-chain surface because it uses a cross-repository PAT and direct `main` push for binary artifacts. It records the source short SHA in the commit message, but the plugin repository itself does not embed a machine-verifiable manifest that binds each binary hash to a full source commit, build run id, workflow file revision, and target.

### Runtime hooks, plugin, and MCP surfaces

Evidence reviewed: `subtext-mcp/.claude-plugin/plugin.json`, `.mcp.json`, `server.ts`, `broker.ts`, `lib/host-binaries.ts`, and `hooks/hooks.json` presence.

- Plugin metadata: `.claude-plugin/plugin.json` declares plugin name `subtext`, version `0.1.3`, author `repolex-ai`, and `mcpServers` path `./.mcp.json`.
- MCP config: `.mcp.json` launches `bun ${CLAUDE_PLUGIN_ROOT}/server.ts` and sets `NODE_PATH=${CLAUDE_PLUGIN_DATA}/node_modules`.
- MCP server behavior:
  - Starts as a stdio MCP server.
  - Calls `setupHostBinaries(pluginRoot)` on startup to symlink host-platform `git-lex` binaries from `bin/.platforms/<target>/` into top-level `bin/`.
  - Ensures a local broker daemon is running by spawning `bun broker.ts` if needed.
  - Registers tools: `list_peers`, `send_message`, `set_summary`, `check_messages`, and `start_viz`.
  - `start_viz` may run `git lex sync` in the current git root if `.lex/oxigraph` is missing, then spawns `git lex serve viz` and attempts to open a browser with `xdg-open`/`open`/`start`.
- Broker behavior:
  - Starts a local HTTP service on `127.0.0.1:${SUBTEXT_PORT:-7901}`.
  - Uses Bun SQLite at `${SUBTEXT_DB:-$HOME/.subtext.db}` with WAL and creates `peers` and `messages` tables.
  - Periodically cleans stale peers by PID.
- Hook surface:
  - `hooks/hooks.json` exists and must be treated as plugin hook metadata for adoption review even if it is not executed by this task.
- Supply-chain/runtime implication:
  - Installing and enabling the plugin can execute Bun TypeScript, spawn a local daemon, create/modify a user-home SQLite database, symlink bundled binaries, run git-lex commands in the active repository, start localhost HTTP/WebSocket services, and open a browser.
  - These are expected plugin/MCP behaviors, but they require explicit user consent and a trust policy before use in LegalGraph workflows.

## T02: Bundled binary hash and trust inventory

### Bundled `subtext-mcp` platform binaries

Evidence reviewed: `/root/vendor-source/subtext-mcp/bin/.platforms/*/{git-lex,git-lex-serve}`. All bundled files are executable (`0755`).

| Platform | Binary | Size bytes | Mode | sha256 |
|---|---:|---:|---:|---|
| `aarch64-apple-darwin` | `git-lex` | 24,961,936 | `0755` | `ba00bc508c42675a48393ea07b2d91f7a7f4ca17931fdfe117360b2c117253aa` |
| `aarch64-apple-darwin` | `git-lex-serve` | 17,612,816 | `0755` | `6e4fa543306609d6e417b6543bcd52ec5556fad11e423d88bc965543865f37ff` |
| `x86_64-apple-darwin` | `git-lex` | 26,909,516 | `0755` | `143069a5083e6410db0d75f06997a27d6055dec24e00ee87208099870737d612` |
| `x86_64-apple-darwin` | `git-lex-serve` | 19,222,688 | `0755` | `38b512adb907ae22e0da7f9da5370c02d432713f54df289391d1db81f7101e57` |
| `x86_64-unknown-linux-gnu` | `git-lex` | 31,082,360 | `0755` | `24817f908ca4f30ef13424783fc790dd6502b294fb6e5843d91ce99941b9d9c5` |
| `x86_64-unknown-linux-gnu` | `git-lex-serve` | 22,416,432 | `0755` | `97c8c7f2a207de7af1bbaec10506d8b42b2be4b17c1122f72722a82fd018b53e` |

### Safe native help/version checks

Only the native Linux x86_64 bundled binaries were executed, and only with `--version` / `--help` style arguments from `/tmp`.

| Binary | Command | Exit | Observed behavior |
|---|---|---:|---|
| `bin/.platforms/x86_64-unknown-linux-gnu/git-lex` | `--version` | 2 | No version flag is implemented; output reports `error: unexpected argument '--version' found` and usage `git-lex <COMMAND>`. |
| `bin/.platforms/x86_64-unknown-linux-gnu/git-lex` | `--help` | 0 | Identifies as `Git extensions for knowledge graphs`; lists commands including `init`, `query`, `dump`, `sync`, and `list`. |
| `bin/.platforms/x86_64-unknown-linux-gnu/git-lex-serve` | `--version` | 2 | No version flag is implemented; output reports `error: unexpected argument '--version' found` and usage `git-lex-serve <COMMAND>`. |
| `bin/.platforms/x86_64-unknown-linux-gnu/git-lex-serve` | `--help` | 0 | Identifies as `Servers for git-lex knowledge graphs`; lists `viz` and `listen` server commands. |

### `git-lex` local build outputs

The `/root/vendor-source/git-lex/target/` tree contains debug build artifacts and many Cargo build-script/proc-macro/native dependency outputs, but no top-level `target/debug/git-lex`, `target/debug/git-lex-serve`, `target/release/git-lex`, or `target/release/git-lex-serve` executable was present in the focused search. Therefore, there is no local source-tree application binary to compare byte-for-byte against the `subtext-mcp` prebuilt platform binaries.

### Binary provenance and trust gaps

- The plugin repository contains prebuilt `git-lex` and `git-lex-serve` binaries for three target triples, but no checked-in manifest was found that binds each `sha256` to:
  - full `git-lex` source commit,
  - exact GitHub Actions run id,
  - workflow file revision,
  - build environment image,
  - Rust compiler version,
  - Cargo.lock hash,
  - artifact digest, and
  - signer/attestation identity.
- The local `subtext-mcp` snapshot commit is `bac5529bb1fdc0ee5c0d9d081a0208f2fefca005`; the local `git-lex` source snapshot commit is `eaa4b24d144a78a8b8e4969404d74cf22267df1f`. The binaries may correspond to that or another `git-lex` commit, but this review cannot prove it from local evidence alone.
- `--version` is unavailable for both native binaries, so runtime output does not expose a version or source commit.
- macOS binaries were not executed on this Linux host; their hashes and metadata were recorded only.
- The cross-repository sync workflow's commit message includes a short git-lex SHA, but short SHA in a commit message is not sufficient binary provenance for LegalGraph adoption.

## T03: `subtext-mcp` interaction model, failure modes, and non-proof boundary

### Interaction model overview

Evidence reviewed: `/root/vendor-source/subtext-mcp/server.ts`, `broker.ts`, `cli.ts`, `lib/host-binaries.ts`, `hooks/hooks.json`, `.mcp.json`, `.claude-plugin/plugin.json`, `shared/summarize.ts`, and `shared/types.ts`.

`subtext-mcp` is best understood as an MCP wrapper and peer-messaging coordinator around locally installed `git-lex` tooling, not as direct evidence that `git-lex` is safe or fit for LegalGraph ACP integration. The main runtime path is:

1. Claude Code/plugin metadata starts `bun ${CLAUDE_PLUGIN_ROOT}/server.ts` over MCP stdio with `NODE_PATH=${CLAUDE_PLUGIN_DATA}/node_modules`.
2. The `SessionStart` hook in `hooks/hooks.json` compares plugin `bun.lock` with `${CLAUDE_PLUGIN_DATA}/bun.lock`; if they differ, it copies `package.json` and `bun.lock` into plugin data and runs `bun install --silent` there.
3. `server.ts` startup calls `setupHostBinaries(pluginRoot)` when `CLAUDE_PLUGIN_ROOT` is present.
4. `setupHostBinaries` maps `process.platform/process.arch` to a Rust target triple, then symlinks `bin/.platforms/<target>/*` into top-level `bin/*` so Claude Code's top-level plugin `bin/` PATH augmentation can expose `git-lex` and `git-lex-serve`.
5. `server.ts` checks broker health at `http://127.0.0.1:${SUBTEXT_PORT:-7901}/health`; if absent, it spawns `bun broker.ts`, unreferences it, and waits up to about 6 seconds.
6. `server.ts` discovers context from `process.cwd()`, `git rev-parse --show-toplevel`, parent-process TTY via `ps -o tty= -p <ppid>`, optional git branch/recent files, and optional OpenAI-generated summary.
7. The MCP server registers with the broker and exposes tools over stdio: `list_peers`, `send_message`, `set_summary`, `check_messages`, and `start_viz`.
8. A polling loop calls `/poll-messages` every second and forwards messages as `notifications/claude/channel`; a heartbeat loop updates `/heartbeat` every 15 seconds; signal handlers attempt `/unregister` before exit.

### Broker behavior

`broker.ts` is a singleton localhost HTTP daemon on `127.0.0.1:${SUBTEXT_PORT:-7901}` backed by Bun SQLite at `${SUBTEXT_DB:-$HOME/.subtext.db}`. It enables WAL mode and a 3000ms busy timeout, creates `peers` and `messages`, and supports these endpoints:

- `GET /health`: returns status and peer count.
- `POST /register`: generates an 8-character peer id, removes prior registration for the same PID, and inserts cwd/git root/TTY/summary metadata.
- `POST /heartbeat`: updates `last_seen`.
- `POST /set-summary`: updates the peer summary.
- `POST /list-peers`: filters by `machine`, exact `directory`, or `repo` git root, with directory fallback when no git root exists.
- `POST /send-message`: verifies the target peer id exists, then inserts an undelivered message.
- `POST /poll-messages`: returns undelivered messages for a peer and marks them delivered.
- `POST /unregister`: removes the peer row.

The broker cleans stale peers on startup and every 30 seconds by checking `process.kill(pid, 0)`, and removes undelivered messages addressed to dead peers during startup cleanup. This creates a local peer registry and message queue, not a distributed or authenticated network.

### `server.ts` tools and git-lex invocation

The exposed MCP tools mostly interact with the broker, but `start_viz` invokes git-lex-family commands in the current git root:

- If `myGitRoot` is absent, `start_viz` returns an MCP `isError` response explaining that git-lex visualization needs a repo with `.lex/` initialized.
- If `${gitRoot}/.lex/oxigraph` is absent, it runs `git lex sync` in `myGitRoot` before serving visualization.
- It then spawns `git lex serve viz`, waits up to 5 seconds for stdout containing `127.0.0.1:<port>`, and returns `http://localhost:<port>/`.
- It attempts to open the URL via `open`, `start`, or `xdg-open`, but browser-open failure is logged and does not fail the MCP tool.

This shows the interaction model expected by the plugin: `git lex` and `git lex serve` are expected to be available on PATH via host-binary symlinks or another installation, and `git lex sync` may create/update repository-local `.lex/oxigraph` state. It does not prove the correctness, safety, or ACP suitability of the underlying `git-lex` indexing, RDF/SHACL model, visualization server, or generated graph content.

### `cli.ts` helper commands

`cli.ts` is an operator/debug helper, not the MCP integration path. It talks to the same broker URL with a 3000ms fetch timeout and provides:

- `status`: read `/health`, then list machine peers.
- `peers`: list machine peers.
- `send <peer-id> <message>`: send from synthetic `from_id: "cli"`.
- `kill-broker`: run `lsof -ti :${SUBTEXT_PORT}` and send `SIGTERM` to matching PIDs.

The CLI reinforces that the subtext model is localhost process coordination plus message passing. It is not an ACP runtime contract and should not be used as integration proof for git-lex behavior.

### Hooks, logging, and error behavior

- Hooks: `hooks/hooks.json` can run `bun install --silent` during Claude Code `SessionStart` when the plugin data lockfile differs from the plugin root lockfile. This is a dependency-install side effect and must be part of any supply-chain review.
- Logging: `server.ts` logs with `[subtext]` to stderr because MCP stdio stdout is reserved for protocol messages. `broker.ts` logs its listen address and database path to stderr. `setupHostBinaries` logs platform activation/warnings/errors to stderr.
- Error handling: most MCP tool handlers catch broker or subprocess failures and return `isError: true` with text. `brokerFetch` throws on non-2xx broker responses. Polling/heartbeat/autosummary/browser-open failures are treated as non-critical and logged or ignored. `ensureBroker` is fatal if the broker does not become healthy within about 6 seconds. Top-level `main().catch` logs `Fatal` and exits with code 1.
- TTY and git root: `getTty` best-effort reads the parent TTY via `ps`; missing/unknown TTY is tolerated. `getGitRoot` uses `git rev-parse --show-toplevel`; failure produces `null`, with repo-scoped peer listing falling back to directory matching and `start_viz` failing closed.

### Process lifecycle

`server.ts` is per-Claude-instance MCP stdio process. `broker.ts` is a local daemon that may survive MCP server exit because it is spawned with ignored stdin/stdout, inherited stderr, and `unref()`. The MCP process unregisters on `SIGINT`/`SIGTERM`, but unexpected process death is handled later by broker stale-peer cleanup. `start_viz` spawns `git lex serve viz` and unreferences it, so visualization server lifecycle is also detached from the tool call after the port is discovered.

### Failure Modes

External dependency and failure-path evidence from the reviewed files:

| Dependency | Failure path | Observed handling |
|---|---|---|
| Plugin filesystem (`CLAUDE_PLUGIN_ROOT`, `bin/.platforms`, top-level `bin`) | Missing env var, unsupported platform, no platform binaries, symlink/unlink failure | Missing plugin root skips setup with stderr warning; unsupported/missing platform logs warning and continues; individual symlink failures log to stderr. This avoids startup crash but may leave `git lex` unavailable. |
| Bun dependency install hook | `bun.lock` differs, copy/install fails, network/package registry unavailable | Hook command has no explicit recovery in `hooks/hooks.json`; hook failure behavior depends on Claude Code plugin hook execution. This is a supply-chain and availability risk, not ACP proof. |
| Broker HTTP service | Broker down, non-2xx response, malformed/unreachable localhost response, startup timeout | `isBrokerAlive` returns false on fetch errors; `ensureBroker` spawns broker and waits up to about 6 seconds, then throws fatal error; tool handlers catch brokerFetch failures and return MCP `isError`. |
| Broker SQLite database | `${SUBTEXT_DB}` or `$HOME/.subtext.db` unavailable, locked beyond busy timeout, schema/write failure | Broker startup/request handler can throw; request handler returns HTTP 500 JSON. There is no migration/repair logic beyond `CREATE TABLE IF NOT EXISTS`, WAL, and busy timeout. |
| Peer processes | Registered PID exits or becomes inaccessible | Broker cleans stale peers at startup and every 30s; list-peers also filters dead PIDs; undelivered messages to dead peers are deleted during startup cleanup only. |
| OpenAI summary API | `OPENAI_API_KEY` missing, request timeout, non-OK response, malformed response | `generateSummary` returns `null`; server logs auto-summary failure as non-critical and proceeds. |
| Git commands for cwd context | Not a git repo, git missing, command errors | Git root/branch/recent-file helpers catch failures and return `null`/`[]`; `start_viz` fails closed when no git root exists. |
| `git lex sync` | Missing git-lex command, sync failure, malformed repository state | `start_viz` returns MCP `isError` with sync exit code and stderr. |
| `git lex serve viz` | Missing command, server exits early, no port announcement within 5s | `start_viz` returns MCP `isError` saying the viz server did not announce a port, including stderr when available. |
| Browser opener | `open`/`start`/`xdg-open` missing or fails | Failure is logged to stderr and does not fail the tool after the viz URL is known. |

### Load Profile

The reviewed `subtext-mcp` code has a runtime load dimension even though this task did not execute it. Expected load is a small number of local Claude Code peers on one machine. At 10x peer/message volume, the likely first saturation points are:

- Broker SQLite writes/updates: `/heartbeat`, `/send-message`, `/poll-messages`, and peer cleanup all share one local SQLite database with WAL and `busy_timeout = 3000`. There is no connection pool, queue backpressure, pagination, retention policy, or message-size limit in the reviewed code.
- MCP polling cadence: every server polls `/poll-messages` once per second and heartbeats every 15 seconds, so broker request rate grows linearly with number of peers.
- Message listing: `/list-peers` and CLI status return full peer rows without pagination.
- Visualization: each `start_viz` can spawn a detached `git lex serve viz`; the code relies on git-lex choosing a free port and does not apply process caps or cleanup.

Protection observed: localhost-only bind address, process-alive stale-peer cleanup, SQLite WAL, 3000ms busy timeout, and brokerFetch timeouts in `cli.ts`/health checks. Missing protection: rate limiting, authentication, message size bounds, pagination, queue retention cleanup, broker single-instance locking beyond port binding, and detached viz process lifecycle management.

### Negative Tests

No test files were found or executed for this documentation-only task, and the task did not modify executable code. Negative surfaces identified from source review that should be covered before promoting this to an ACP integration are:

- `setupHostBinaries`: unsupported `process.platform/process.arch`, missing platform directory, stale top-level symlink/file replacement failure, and symlink creation failure.
- `server.ts` broker path: broker unavailable, broker non-2xx response, malformed broker JSON, startup timeout, and not-registered states for `send_message`, `set_summary`, and `check_messages`.
- `server.ts` git-lex path: non-git cwd, missing `.lex/oxigraph`, failing `git lex sync`, missing/failing `git lex serve viz`, no stdout port within 5 seconds, and browser opener failure.
- `broker.ts`: malformed JSON body, unknown endpoint, missing/invalid peer ids, dead PID cleanup, SQLite lock/write errors, and message delivery idempotency.
- `cli.ts`: broker down, missing `send` arguments, unknown peer id, and `lsof`/SIGTERM failure in `kill-broker`.

Because the implementation has no checked-in negative tests for these cases in the reviewed snapshot, these findings are review requirements rather than pass evidence.

### Boundary: interaction model, not integration proof

The `subtext-mcp` repository demonstrates a plausible local interaction model for exposing git-lex commands to Claude Code through MCP: host binary surfacing, peer discovery, message passing, optional visualization startup, and best-effort context summary. It must not be promoted to ACP integration proof because:

- It wraps prebuilt binaries whose provenance is not established by this slice.
- It uses a missing-license plugin repository with runtime hook and dependency-install side effects.
- It exercises `git lex sync` and `git lex serve viz` only indirectly and does not validate git-lex graph correctness, legal-domain semantics, citation safety, parser behavior, or ACP architecture fit.
- It creates local state (`$HOME/.subtext.db`, repo `.lex/oxigraph`, detached viz processes) and localhost services that need explicit operational policy.
- It has no local authentication, rate limits, message-size controls, or documented production hardening.

Therefore, S09 may use `subtext-mcp` as research evidence for how git-lex tools can be surfaced to agents, but not as LegalGraph ACP adoption evidence or binary trust evidence.

## Acquisition and binary trust recommendations for downstream tasks

1. Treat the bundled `subtext-mcp` binaries as untrusted prebuilt artifacts unless an adoption policy explicitly allows them.
2. Prefer source builds from a pinned full `git-lex` commit using `cargo build --release --locked` in a controlled builder.
3. Require a binary manifest for any accepted prebuilt artifacts. Minimum fields: platform, binary name, sha256, size, mode, full source commit, Cargo.lock hash, workflow run id, builder OS image, Rust toolchain, creation timestamp, and signer/attestation reference.
4. Add or require `git-lex --version` and `git-lex-serve --version` to print version and source commit before relying on runtime identity checks.
5. Do not enable the `subtext-mcp` plugin/MCP automatically in LegalGraph workflows. Its startup hooks can spawn a broker, write `${HOME}/.subtext.db`, symlink binaries, and expose peer messaging and visualization tools.
6. Resolve the missing `subtext-mcp` license before redistribution or operational adoption.

## Verification commands

- `test -f prd/architecture/acp/M051-S09-SUPPLY-CHAIN-BINARY-TRUST.md && grep -E 'LICENSE|Cargo.lock|package.json|bun.lock|dependency|workflow|hook|plugin|MCP' prd/architecture/acp/M051-S09-SUPPLY-CHAIN-BINARY-TRUST.md`
- `grep -E 'sha256|platforms|git-lex-serve|git-lex|version|help|trust gap|prebuilt' prd/architecture/acp/M051-S09-SUPPLY-CHAIN-BINARY-TRUST.md`
- `grep -E 'setupHostBinaries|server.ts|broker|cli.ts|hooks|logging|error|TTY|git root|interaction model|not integration proof' prd/architecture/acp/M051-S09-SUPPLY-CHAIN-BINARY-TRUST.md`
