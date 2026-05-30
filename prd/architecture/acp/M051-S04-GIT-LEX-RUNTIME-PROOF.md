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

## Semantic web runtime checks

T03 attempted to determine whether semantic-web behavior could be exercised through a real `git-lex` or bundled `subtext` runtime. No executable runtime was available, so no ACP-native simulation was substituted and no claim is upgraded from S03 source understanding to S04 runtime proof.

| Claim area | Intended runtime check | Exit code | Result | S03 upgrade status |
|---|---|---:|---|---|
| RDF graph generation | Create/extract a sample record and inspect generated RDF graph output. | not run | blocked: no runnable `git-lex` or `subtext` executable candidate. | not upgraded |
| N-Quads shape | Export or inspect extracted N-Quads and verify subject/predicate/object/graph shape. | not run | blocked: runtime unavailable. | not upgraded |
| SPARQL query behavior | Run a positive query and at least one empty-result query over the extracted store. | not run | blocked: runtime unavailable, query command support could not be probed. | not upgraded |
| frontmatter extraction | Create a markdown/sidecar sample with frontmatter and verify extracted triples/properties. | not run | blocked: runtime unavailable. | not upgraded |
| quoted triples / RDF 1.2 / SPARQL-star | Probe quoted-triple parse/query support only if exposed by runtime help or query engine. | not run | blocked: runtime unavailable and help/version support could not be inspected. | not upgraded |
| JSON-LD export/import | Probe JSON-LD export/import commands if present in runtime help. | not run | blocked: runtime unavailable and command surface could not be inspected. | not upgraded |
| history graph behavior | Save two revisions and query/inspect temporal or provenance graph behavior. | not run | blocked: runtime unavailable; no history graph was produced. | not upgraded |

Diagnostic command evidence:

| Command | Exit code | Result |
|---|---:|---|
| `gsd_exec` purpose `T03 semantic runtime availability and blocker diagnostics for git-lex/subtext` | `0` | Confirmed all checked `git-lex` / `git-lex-serve` candidate paths were non-executable or missing, `subtext_platform_executable_count=0`, isolated workspace still present, and `/root/law-nexus/.lex` still absent. |

Persisted diagnostics:

- `.gsd/exec/0e80065b-dff4-4aff-a3c6-315f8b525fe5.stdout` — semantic runtime availability and blocked diagnostics for RDF, N-Quads, SPARQL, frontmatter, quoted triples, JSON-LD, and history behavior.

## Failure Modes

External dependencies for this task were local filesystem paths, local subprocess/runtime availability, and the previously attempted Cargo/native toolchain build path. No network or external API dependency was used.

| Dependency | Failure mode | Observed path | Handling / diagnostic |
|---|---|---|---|
| `/root/vendor-source/git-lex/target/*` runtime candidates | Missing or non-executable binary. | Observed for `target/debug/git-lex`, `target/release/git-lex`, `target/debug/git-lex-serve`, and `target/release/git-lex-serve`. | Bubbled as blocked diagnostics; no semantic command was run or simulated. |
| `/root/vendor-source/subtext-mcp/platforms/*` bundled runtime candidates | Missing directory or no executable platform binary. | Observed `subtext_platform_executable_count=0`. | Bubbled as blocked diagnostics; JSON-LD/SPARQL/RDF behavior not upgraded. |
| Local Cargo/native build path | Native dependency compilation failure. | Prior T01 locked build failed in `oxrocksdb-sys` because `stdbool.h` was missing. | Preserved as binary provenance blocker; T03 did not rerun a known failing build without new evidence. |
| Main repo filesystem safety | Accidental mutation of `/root/law-nexus/.lex`. | T03 diagnostic reported `main_lex_exists=no`. | Confirmed no main repo `.lex` was created. |
| Isolated workspace availability | Workspace missing before semantic proof. | T03 diagnostic reported workspace state `present`. | Kept available for future reruns once a runtime exists. |

## Load Profile

T03 has no executable runtime load profile because no semantic runtime could be started. The first saturating resource remains binary/toolchain availability, not RDF store size, SPARQL complexity, JSON-LD import volume, or history depth. A 10x semantic load breakpoint cannot be claimed until a runnable binary exists and can generate/query a store in the isolated workspace.

## Negative Tests

Negative runtime tests were not executable, but the negative diagnostic surface was covered:

| Negative scenario | Expected behavior | Evidence |
|---|---|---|
| Missing `git-lex` binary | Mark RDF/N-Quads/SPARQL/frontmatter/quoted/JSON-LD/history checks as blocked, not passed. | `.gsd/exec/0e80065b-dff4-4aff-a3c6-315f8b525fe5.stdout` reports `runtime_found=no` and `semantic_runtime_checks=blocked`. |
| Missing bundled `subtext` executable | Preserve JSON-LD/SPARQL/RDF claims as not upgraded. | Same diagnostic reports `subtext_platform_executable_count=0`. |
| Main repo mutation risk | Do not create or use `/root/law-nexus/.lex`. | Same diagnostic reports `main_lex_exists=no`. |
| Unsupported command surface unknowns | Do not infer quoted triple, RDF 1.2, SPARQL-star, JSON-LD, or history support from source-only understanding. | Semantic web runtime checks table marks each area `not upgraded`. |

## Final cleanup and main repo safety status

Final status: **blocked runtime proof, passed cleanup and no-main-repo safety checks**.

- Main repo safety: `/root/law-nexus/.lex` remains absent (`no-main-repo .lex`).
- Main repo mutation scope: no `git-lex` or `subtext` runtime command was executed against `/root/law-nexus`; this artifact is the only intended main-repo update for S04 runtime proof documentation.
- Isolated workspace cleanup state: `/tmp/law-nexus-git-lex-proof-20260530T081850Z` remains present for follow-up diagnostics, and its `.lex` path remains absent because no runtime command successfully initialized it.
- Cleanup decision: the temp workspace was intentionally retained rather than deleted so future reruns can inspect the exact isolated workspace path recorded by T01-T03; there are no active background processes or generated runtime stores to clean up.
- Final diagnostic evidence: `.gsd/exec/8fc45c01-cc6f-4b67-8082-899e7acbec33.stdout` reports `main_lex_exists=no`, `workspace_state=present`, and `workspace_lex_exists=no`.

### T04 Failure Modes

| Dependency | Failure mode | Observed path | Handling / diagnostic |
|---|---|---|---|
| Main repo filesystem path `/root/law-nexus/.lex` | Accidental runtime initialization or leftover cleanup artifact in the main checkout. | T04 diagnostic reported `main_lex_exists=no`. | Passed safety check; no remediation needed. |
| Isolated workspace `/tmp/law-nexus-git-lex-proof-20260530T081850Z` | Workspace deleted too early, making previous diagnostics harder to reproduce. | T04 diagnostic reported `workspace_state=present`. | Retained intentionally as diagnostic state; no main-repo mutation. |
| Isolated workspace `.lex` path | Runtime initialized partial state despite blocked binary proof. | T04 diagnostic reported `workspace_lex_exists=no`. | Confirms no hidden initialized runtime store exists in the isolated workspace. |
| Artifact evidence grep | Missing final cleanup/no-main-repo status would make audit incomplete. | T04 diagnostic counted cleanup/safety tokens before update; final section added explicit status. | Verification requires final status and cleanup/main repo/no-main-repo evidence. |

### T04 Load Profile

T04 has no runtime load dimension: it performs constant-time filesystem existence checks and a bounded grep over one markdown artifact. The first 10x breakpoint would still be human/audit noise in the proof artifact, not CPU, memory, network, or subprocess saturation; no pooling, rate limiting, pagination, or caching is applicable.

### T04 Negative Tests

| Negative scenario | Expected behavior | Evidence |
|---|---|---|
| Main checkout `.lex` exists | Verification must fail instead of claiming no-main-repo safety. | Final verification uses `test ! -e .lex`. |
| Proof artifact lacks cleanup/final status text | Verification must fail so the audit trail cannot close without documented cleanup state. | Final verification greps for `cleanup|main repo|no-main-repo|final status`. |
| Isolated workspace state is ambiguous | Artifact must explicitly document whether workspace was retained or removed. | Final section records `workspace_state=present` and the retention rationale. |
