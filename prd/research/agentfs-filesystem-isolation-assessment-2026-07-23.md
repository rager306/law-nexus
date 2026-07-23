# AgentFS filesystem isolation assessment

**Date:** 2026-07-23  
**Lifecycle:** `[bounded]`  
**Disposition:** `defer`, separate non-authoritative workspace role  
**Runtime probe:** not yet executed

## Decision question

Can Turso AgentFS provide a disposable copy-on-write filesystem and audit layer
for rvAgent or GSD subagents without being mistaken for OS sandboxing, legal
evidence authority, product storage or a replacement for Git isolation?

## Current disposition

AgentFS is a promising candidate for a disposable agent workspace. It is not an
authoritative database, legal evidence store, complete process sandbox or
selected product dependency. Any future probe must use a throwaway synthetic
base directory, local-only operation and a CLI subprocess boundary.

## Capability matrix

| Capability | Evidence | Current status | law-nexus boundary |
|---|---|---|---|
| SQLite-backed single-file agent state | Official documentation | `[bounded]` documented | Scratch/session state only |
| Copy-on-write overlay and whiteouts | Official overlay documentation | `[bounded]` documented | Base immutability requires a local probe |
| Filesystem, KV and tool-call records | Official SDK/CLI documentation | `[bounded]` documented | Audit aid, not complete activity proof |
| Named shared sessions and snapshots | Official session documentation | `[bounded]` documented | Shared mutation and race behavior unproven |
| MCP filesystem/KV tools with filtering | Official MCP documentation | `[bounded]` documented | Read-only minimum; no authority paths |
| Linux FUSE/namespace execution | Official installation/sandbox documentation | `[bounded]` documented | Runtime and escape resistance unproven |
| Cloud sync | Official documentation | Available but forbidden | No credentials or remote synchronization |
| OS process/network/resource sandbox | No sufficient proof | `unknown` / not supplied by COW alone | Must be provided by a separate OS isolation layer |
| Symlink/path traversal resistance | No local probe | `unknown` | Kill criterion |
| Complete audit of shell/network side effects | No sufficient proof | `unknown` | Do not make compliance claims |
| Authoritative legal evidence storage | Project authority contract | `reject` | Never store legal authority or source truth |

## Isolation model

AgentFS primarily supplies filesystem-view isolation:

```text
read-only base directory
+ SQLite-backed delta and whiteouts
= merged agent view
```

That is distinct from OS isolation. A process may still have access to network,
other processes, inherited environment, `/proc`, host paths or writable paths
outside the overlay unless a separate container, namespace, seccomp, VM or
similarly proven policy blocks them.

Recommended composition if a later probe succeeds:

```text
OS process sandbox
+ rvAgent tool/path/resource policy
+ AgentFS COW state and audit
+ Git branch/worktree policy where needed
```

None of these layers should be described as replacing the others.

## Threat matrix

| Threat | Failure path | Impact | Required probe or control |
|---|---|---|---|
| Base checkout mutation | Overlay or mount escape | Repository/evidence corruption | Hash base before/after writes and deletes |
| Symlink escape | Workspace link targets a host path | Host read/write exposure | Test outward symlinks; fail on prohibited access |
| Shell/process escape | Agent spawns unrestricted process | Exfiltration or host mutation | Separate OS sandbox; AgentFS is insufficient |
| Secret capture | Files, environment or tool arguments enter session DB | Portable credential leak | Strip environment; synthetic fixtures only |
| Audit gaps | Mutation bypasses AgentFS-recorded surface | False audit completeness | Compare base/delta hashes with timeline records |
| Shared-session races | Multiple agents write one session | Nondeterministic state | Prefer one writer; test isolation and reopen |
| MCP overexposure | Write/delete tools exposed unnecessarily | Workspace destruction | Explicit tool allowlist; read-only first |
| NFS/network exposure | Service bound beyond loopback | Remote filesystem access | No remote bind in the bounded probe |
| Cloud sync | Session leaves host | Evidence/security boundary breach | Hard prohibition; no credentials |
| Resource exhaustion | Delta grows without quota | Host disk exhaustion | Bounded files and pre/post free-space checks |
| Authority laundering | Scratch DB becomes cited source truth | Legal evidence integrity failure | Hard policy rejection independent of runtime result |

## Bounded executable probe contract

The first local probe must not install AgentFS into the product Cargo workspace.
Prefer a pinned CLI subprocess in a disposable directory after an explicit
acquisition step. It must use no cloud account, token, sync, real legal corpus or
law-nexus working tree as the writable base.

Proposed location:

```text
probes/agentfs-isolation/
```

Required synthetic checks:

1. record CLI version, platform, FUSE availability and effective mode;
2. modify and delete a base file in one session; verify base hashes are unchanged;
3. create a new file and verify it exists only in the merged/delta view;
4. open two sessions and prove their deltas do not cross;
5. kill a session process, reopen it and verify the delta and base state;
6. attempt an outward symlink read and write, recording exact allowed/blocked behavior;
7. attempt a write outside the base and explicit allowlist;
8. expose MCP with read-only tools and prove write tools are unavailable;
9. compare intentional operations with diff/timeline/audit records;
10. measure session DB growth under a bounded synthetic write;
11. verify no cloud sync, remote NFS bind or credentials are required;
12. delete the disposable workspace and verify the law-nexus checkout was unchanged.

## Kill criteria

Reject AgentFS for the bounded workspace role if any of these occurs:

- the base tree changes after overlay writes or deletions;
- a prohibited host write succeeds through a path or symlink escape;
- the intended value requires cloud sync, credentials or remote exposure;
- material mutations are absent from both delta/diff and audit surfaces;
- crash/reopen loses the isolation boundary or corrupts the base;
- a hard product-runtime dependency is required;
- the probe cannot bound disk growth;
- any workflow stores authoritative legal evidence or GSD source truth in the
  AgentFS database;
- AgentFS is presented as a complete security sandbox without independent OS
  isolation proof.

## Transferability to rvAgent and GSD

AgentFS can complement rvAgent's tool/path/resource controls by making agent file
deltas portable and reviewable. It can complement Git worktrees by preserving a
COW session without requiring a second checkout. It does not automatically
integrate with either system, enforce law-nexus authority gates, merge changes
safely, or prevent a raw subprocess from reaching host resources.

The preferred initial boundary is therefore:

```text
GSD or rvAgent harness -> pinned AgentFS CLI subprocess -> disposable synthetic workspace
```

No product crate or legal-domain module should depend on AgentFS during the
research phase.

## Evidence anchors

Checked 2026-07-23:

- <https://docs.turso.tech/agentfs/introduction>
- <https://docs.turso.tech/agentfs/guides/overlay>
- <https://docs.turso.tech/agentfs/guides/sessions>
- <https://docs.turso.tech/agentfs/guides/auditing>
- <https://docs.turso.tech/agentfs/guides/mcp>
- <https://docs.turso.tech/agentfs/reference/cli>
- <https://docs.turso.tech/agentfs/sdk/rust>
- <https://github.com/tursodatabase/agentfs>

The upstream beta warning is load-bearing: production data requires caution and
backups. Documentation is primary discovery evidence, not local escape,
recovery, concurrency or audit-completeness proof.

## Proof ceiling and non-claims

This assessment proves only that AgentFS has documented COW, state, audit and MCP
surfaces worth a bounded local probe. It does not prove base immutability on this
host, OS sandboxing, symlink safety, audit completeness, crash recovery,
concurrent session correctness, resource containment, legal evidence integrity
or production readiness.
