# M048 S08 git-lex Proof Contract

## Status

Adopted for `M048-q4x62e / S08 / T02` as the isolated proof contract for future S09 git-lex evaluation.

This artifact does not approve runtime git-lex adoption. It defines the proof scenarios, workspace constraints, diagnostic artifacts, and blocked-runtime semantics that a later S09 proof must satisfy before ACP may classify any git-lex capability as proven.

## Inputs and Authority

This contract refines the capability matrix in `prd/architecture/acp/M048-S08-GIT-LEX-CAPABILITY-MATRIX.md`.

The authority rule remains:

```text
No artifact is authoritative by shape alone.
Authority requires source category + lifecycle state + evidence anchor + proof gate or accepted decision.
```

S09 may use this contract to run an isolated proof, but it must not reinterpret this document as evidence that git-lex runtime is installed, safe, adopted, or requirement-validating.

## Scenario Matrix

| Scenario | Priority | Required capability focus | Minimum passing evidence | Blocked/fail interpretation |
| --- | --- | --- | --- | --- |
| `source-record-lifecycle` | P0 | typed records, schema/frontmatter validation, evidence anchors, lifecycle transitions, transition history | Create a representative ACP source record, mark it `candidate`, attach a repo-relative evidence anchor, validate required fields, transition to `accepted` only after proof/decision evidence, and recover transition history with previous state, new state, rationale, actor/tool/context, and anchor. | Missing fields, shape-only Markdown, missing anchor, invalid transition, or unrecoverable history is `ImitativeArtifact` or `InsufficientEvidence`; do not promote acceptance. |
| `blocked-claim` | P0 | proof gates, health findings, blocked diagnostics, blocked runtime semantics | Create a proof-required claim, make the proof fail or runtime probe unavailable, persist a typed blocked/deferred state, and emit a durable diagnostic tied to the claim and capability. | Failed proof or unavailable runtime is `BlockedCapability` or `UnsupportedGitLexRuntime`; it is not neutral and not adoption evidence. |
| `projection-boundary` | P0 | derived projection boundary, source/projection separation, stale projection handling | Generate a derived projection from source records, mutate or stale the projection, detect derived/stale status, and recover canonical source records as authoritative. | Projection override, projection-only validation, or manual projection edits becoming source truth is `ImitativeArtifact` or `UnsafeMutation`; reject authority inheritance. |
| `recovery-query` | P1 | query/recovery, evidence anchors, proof gates, dependent records, blocked findings | Query a claim and recover source record, lifecycle state, evidence anchor, proof gate, derived projections, dependents, and blocked findings without relying on polished prose. | Missing authority chain or prose-only recovery is `InsufficientEvidence`; keep ACP-native recovery or adapter-only status. |
| `git-semantics` | P2 | record-aware git value beyond ordinary git | Compare ordinary git branch/diff/history/conflict/rebase behavior with candidate git-lex behavior over record changes, and identify concrete record-aware value. | If git-lex is unavailable or adds no record-aware value, runtime adoption remains `blocked`, `adapter later`, or `reject`; ordinary git plus ACP-native records remains sufficient. |
| `isolation-safety` | P0 | isolation and mutation guard, rollback, cleanup, no-main-repo `.lex` | Run all git-lex proof work outside the main `law-nexus` checkout, assert main repo `.lex` absence before and after, record rollback/delete path, and fail closed on unexpected repository-state mutation. | Any blind `git lex init`, main-repo `.lex` creation/mutation, missing rollback, or unapproved durable runtime state is `UnsafeMutation`; runtime adoption is blocked or rejected. |

## Workspace Constraints

S09 proof execution must obey these constraints:

1. **Main checkout is read-only for git-lex runtime state.** Do not run `git lex init`, create `.lex`, or mutate git-lex state in `/root/law-nexus`.
2. **Use an isolated workspace.** Candidate runtime work must happen in a temporary or explicitly disposable workspace outside the main checkout, with only tracked fixture/source inputs copied in.
3. **No hidden acquisition.** Do not clone, install, download, durably build, or cache git-lex unless the proof plan explicitly names provenance, approval, cleanup, and rollback controls.
4. **No gitignored authority.** Diagnostic output may be generated in temporary paths, but accepted evidence anchors must point to tracked repo-relative artifacts, commands, or durable summaries, not `.gsd/exec/*`, `.lex/*`, local caches, provider payloads, raw vectors, or secrets.
5. **Rollback is mandatory.** Every workspace mutation must have a documented cleanup path; failure to clean up keeps the capability blocked.
6. **Profile boundaries remain intact.** Russian legal evidence, parser completeness, FalkorDB behavior, LLM authority, and `R035`/`R037`/`R038` proof obligations remain law-nexus profile constraints, not reusable ACP core proof.

## No-Main-Repo `.lex` Guard

A future executable proof must record all of the following checks:

| Guard check | Required result |
| --- | --- |
| `test ! -e .lex` before proof in main checkout | pass |
| No command equivalent to blind `git lex init` in main checkout | pass |
| Runtime/projection state created only in isolated workspace | pass |
| Isolated workspace rollback/delete path recorded | pass |
| `test ! -e .lex` after proof in main checkout | pass |

If any guard fails, S09 must mark the runtime capability `UnsafeMutation` and stop using the proof as adoption evidence.

## Accepted Diagnostic Artifacts

S09 should prefer structured diagnostics that are durable, typed, and tied to capabilities:

| Artifact type | Accepted use | Authority boundary |
| --- | --- | --- |
| tracked Markdown proof report | human-readable cold-reader summary of commands, results, and blocked findings | summary only; must cite source/proof anchors |
| tracked JSON or fixture projection | deterministic recovery/query evidence over copied source records | derived and non-authoritative |
| pytest output or proof command result | executable verification evidence | proof evidence only when command and artifact are preserved in tracked summary |
| typed health finding | durable record for imitative, unsupported, unsafe, stale, or insufficient evidence state | diagnostic state, not acceptance by itself |
| transition history record | provenance for lifecycle changes | authoritative only when linked to source category, lifecycle state, evidence anchor, and proof/decision |

Rejected as authority: polished prose without anchors, manually edited derived projections, `.gsd/exec/*` paths by themselves, `.lex/*` state in the main checkout, absolute local paths, provider payloads, raw embeddings/vectors, secrets, screenshots without source anchors, and self-asserting generated summaries.

## Blocked-Runtime Semantics

`UnsupportedGitLexRuntime` means the local `git lex` / `git-lex` runtime surface cannot be safely used or representative operations cannot be completed. It has these semantics:

- it is an explicit blocked/deferred result, not a test pass and not an adoption claim;
- deterministic ACP-native checks may still pass, but they prove ACP mechanics only;
- unavailable runtime must not trigger unplanned clone/install/download/build behavior;
- a later successful runtime probe is not enough for full adoption unless acquisition provenance, representative operation, source/projection boundary, mutation guard, rollback, and diagnostic requirements also pass;
- runtime-blocked capabilities may be classified only as `blocked`, `adapter later`, `absorb approach`, `implement ACP-native`, or `reject` according to the matrix.

## Required S09 Proof Steps

A later S09 proof should execute the scenarios in this order:

1. Establish workspace guard: assert main `.lex` absence and prepare disposable isolated workspace.
2. Run safe runtime probes: `git lex --help` and/or `git-lex --help` only if available locally and safe; otherwise record `UnsupportedGitLexRuntime`.
3. Execute deterministic ACP source-record fixtures for lifecycle, validation, anchors, proof gates, projection boundary, recovery query, and blocked diagnostics.
4. Execute runtime git-lex representative operations only if runtime acquisition/use is already approved and isolated.
5. Compare git semantics against ordinary git for branch/diff/history/conflict/rebase behavior.
6. Clean up isolated workspace and re-check main `.lex` absence.
7. Write a tracked proof report summarizing pass/blocked/fail states by scenario and capability.

## Pass, Block, and Fail Rules

| Result | Meaning | Allowed next action |
| --- | --- | --- |
| `pass` | Scenario produced executable or tracked evidence satisfying source, lifecycle, proof, and safety constraints. | Capability may inform a later explicit adoption/implementation decision. |
| `blocked` | Scenario could not be proven because runtime, evidence, safety, or workspace constraints were unavailable. | Keep runtime adoption blocked/deferred; continue ACP-native or adapter planning only. |
| `fail` | Scenario ran and violated the contract, such as unsafe mutation or source/projection authority confusion. | Fail closed; repair proof design before using any result. |
| `not_applicable` | Scenario is outside the current proof scope and explicitly deferred. | Do not cite as coverage. |

A single `fail` in `isolation-safety` or `projection-boundary` blocks runtime adoption even if other scenarios pass.

## Failure Modes

| Dependency | Failure path | Required handling |
| --- | --- | --- |
| Tracked input matrix and prior ACP artifacts | Missing, stale, unreadable, or contradictory capability matrix / S04-S07 reports | Stop or mark proof incomplete; do not infer missing contract terms from memory or generated prose. |
| Filesystem and workspace isolation | Cannot create disposable workspace, cannot copy tracked fixtures, cleanup fails, or main checkout gains `.lex` | Mark `UnsafeMutation` or blocked; fail closed and do not continue as adoption evidence. |
| Subprocess runtime probes | `git lex` / `git-lex` missing, non-zero, malformed, hangs, or raises `OSError` | Record `UnsupportedGitLexRuntime` with command, exit/status, and bounded stderr/stdout summary; do not auto-install. |
| Git operations | branch/diff/merge/rebase commands fail, conflict output is malformed, or ordinary git comparison cannot be completed | Mark `git-semantics` blocked/fail according to cause; do not claim git-lex adds value. |
| Source/projection validation | Required fields, lifecycle state, anchors, proof gate, freshness, or source/projection markers are absent or inconsistent | Emit `ImitativeArtifact` or `InsufficientEvidence`; keep record candidate/diagnostic only. |
| Diagnostic persistence | Failure details are only transient logs or local ignored files | Mark evidence insufficient; require tracked proof summary or typed health finding before closeout. |

Network acquisition is deliberately excluded unless a future task explicitly adds a provenance and rollback policy.

## Load Profile

This T02 artifact has no production runtime load dimension. It adds a static proof contract and document-level regression test; it does not add a server, API endpoint, database pool, queue, crawler, browser flow, background worker, or telemetry stream.

At 10x the expected scenario count, the first constrained resource is reviewer clarity and local document-test parsing, not a runtime service. The protection is a fixed scenario matrix, explicit pass/block/fail states, table-driven diagnostics, and strict workspace constraints. No rate limiting, pagination, caching, autoscaling, pool sizing, or runtime backpressure is required for this artifact.

A future S09 executable proof must define its own load profile if it introduces bulk repository scans, subprocess fan-out, network acquisition, long-running build steps, or persistent git-lex services.

## Negative Tests

Negative coverage for this contract is provided by `tests/test_m048_s08_git_lex_proof_contract.py`:

- rejects missing proof contract or title drift;
- rejects missing scenario rows for source-record lifecycle, blocked claim, projection boundary, recovery query, git semantics, or isolation safety;
- rejects omission of workspace constraints, no-main-repo `.lex` guard, rollback, and no hidden acquisition language;
- rejects missing accepted/rejected diagnostic artifact boundaries;
- rejects runtime adoption overclaims and `R035`/`R037`/`R038` validation leaks;
- requires explicit failure handling for filesystem/workspace, subprocess runtime probes, git operations, source/projection validation, and diagnostic persistence;
- requires blocked-runtime semantics to say runtime unavailability is not adoption evidence.

The test is intentionally document-level because T02 defines a future proof protocol rather than executing runtime git-lex.

## Observability Impact

This contract requires every failed, blocked, deferred, or unsafe git-lex capability to produce structured diagnostics. Future proof reports must expose scenario id, capability id or name, result state, failure category, command/artifact anchor, source/projection authority status, workspace path class, rollback status, and allowed next action.

The intended observability surface is durable enough for a cold-reader agent to answer: what was attempted, what was proven, what was blocked, why runtime adoption remains blocked/deferred, whether the main checkout stayed free of `.lex`, and which ACP-native or adapter path remains allowed.
