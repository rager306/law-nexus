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
