# M051 S04 Git Lex Runtime Proof

## Scope

This document records isolated runtime proof and diagnostics for evaluating `git-lex` as a possible ACP backend component. All runtime work was kept outside the main `/root/law-nexus` checkout except for this proof artifact.

## Safety baseline and isolated workspace

- Main repository safety state before runtime work: `/root/law-nexus/.lex` was absent (`no-main-repo .lex`).
- Isolated workspace: `/tmp/law-nexus-git-lex-proof-20260530T081850Z`.
- Workspace creation exit code: `0`.
- Main repository safety state after workspace creation: `/root/law-nexus/.lex` remained absent (`no-main-repo .lex`).
- Workspace `.lex` state after creation: absent.

Evidence commands:

| Step | Command | Exit code | Result |
|---|---|---:|---|
| Safety baseline | `test -e /root/law-nexus/.lex` via diagnostic wrapper | `0` wrapper; reported `main_lex_exists=no` | Confirmed no main repo `.lex` before mutations. |
| Workspace creation | `mkdir -p /tmp/law-nexus-git-lex-proof-20260530T081850Z` | `0` | Created isolated workspace outside `/root/law-nexus`. |
| Safety re-check | `test -e /root/law-nexus/.lex` via diagnostic wrapper | `0` wrapper; reported `main_lex_exists_after_workspace_create=no` | Confirmed no main repo `.lex` after workspace creation. |

Persisted diagnostics:

- `.gsd/exec/e10a4f25-be70-423e-9f5a-0a5ffa966d82.stdout` — initial safety baseline and candidate lookup.
- `.gsd/exec/81a9b16c-f933-49d4-a861-ec807a08258d.stdout` — isolated workspace creation and safety re-check.

## Binary provenance, help, and version proof

Candidate search locations required by the task:

- `/root/vendor-source/git-lex` build outputs.
- `/root/vendor-source/subtext-mcp/platforms/*` bundled binaries.

Observed candidates:

| Source | Candidate path | Executable? | help exit code | version exit code | Version/help result |
|---|---|---:|---:|---:|---|
| `/root/vendor-source/git-lex/target/debug/git-lex` | missing | no | not run | not run | No executable build output was present before build attempt. |
| `/root/vendor-source/git-lex/target/release/git-lex` | missing | no | not run | not run | No executable build output was present before build attempt. |
| `/root/vendor-source/git-lex/target/debug/git-lex-serve` | missing | no | not run | not run | No executable build output was present before build attempt. |
| `/root/vendor-source/git-lex/target/release/git-lex-serve` | missing | no | not run | not run | No executable build output was present before build attempt. |
| `/root/vendor-source/subtext-mcp/platforms/*` | directory missing | no | not run | not run | No bundled platform binary directory exists in this checkout. |

A locked source build was attempted to determine whether a runtime binary could be produced locally:

| Command | Exit code | Result |
|---|---:|---|
| `cd /root/vendor-source/git-lex && cargo build --locked --bins` | `101` | Build failed; no runnable binary was produced. |
| `cd /root/vendor-source/git-lex && cargo build --locked --bins --message-format=short` | `101` | Concise diagnostic captured: `oxrocksdb-sys-0.5.7` build failed because `rocksdb/include/rocksdb/c.h:65:10: fatal error: 'stdbool.h' file not found`. |

Because no executable `git-lex` binary was available, `git-lex --help`, `git-lex --version`, `git-lex-serve --help`, and `git-lex-serve --version` could not be run. This is a blocked binary-runtime diagnostic, not an ACP-native simulation.

Persisted diagnostics:

- `.gsd/exec/2eef9c8a-1c3f-45b7-bffc-a92db9e4020c.stdout` — explicit build-output path checks.
- `.gsd/exec/e08ef9c9-ab4e-40f6-a6d5-226c5a873d9a.stdout` — first locked build attempt summary (`cargo_build_exit=101`).
- `.gsd/exec/cac19e45-3c01-4e3d-af9a-192ce8f82a56.stdout` — concise locked build failure diagnostic.

## Isolated core operation proof

No `git-lex` executable was available after candidate lookup and locked build diagnostics, so isolated core operations were not substituted with an ACP-native simulation. Each operation below is recorded as blocked by the missing runtime binary.

| Operation | Intended command class | Exit code | Runtime result |
|---|---|---:|---|
| init | `git lex init ...` / `git-lex init ...` | not run | blocked: no executable candidate. |
| kit install/update | base/squad kit install or `kit-update` where supported | not run | blocked diagnostic: no executable candidate, and command support could not be probed through `help`. |
| create | create sample typed record | not run | blocked: no executable candidate. |
| save | save sample record | not run | blocked: no executable candidate. |
| sync | rebuild extracted store | not run | blocked: no executable candidate. |
| extract | extract sidecar triples/frontmatter | not run | blocked: no executable candidate. |
| query | run SPARQL query | not run | blocked: no executable candidate. |
| validate | SHACL validation | not run | blocked: no executable candidate. |
| cleanup | `nuke` or removal of temporary runtime outputs | not run | no `git-lex` mutation occurred; isolated workspace remains available for later diagnostics. |

Diagnostic conclusion: S04 has proof that the current local environment cannot yet run real `git-lex` core operations from the specified vendor binary locations. The blocker is runtime binary availability/buildability, specifically the failed locked Cargo build caused by a missing C stdbool header during `oxrocksdb-sys` compilation.

## Main repository safety status

- No `/root/law-nexus/.lex` directory was created by these checks.
- No core operation was run against `/root/law-nexus`.
- All attempted runtime preparation happened either in `/tmp/law-nexus-git-lex-proof-20260530T081850Z` or `/root/vendor-source/git-lex` build diagnostics.
