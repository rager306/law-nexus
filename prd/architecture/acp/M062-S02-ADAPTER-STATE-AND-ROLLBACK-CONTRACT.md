# M062/S02: Adapter state and rollback contract

## Status

Pass (contract draft). S02 produces a static contract that any future git-lex L2 diagnostic adapter pilot must satisfy. It is not adapter implementation, not main `.lex` adoption, not source-truth migration, not production adoption, and not validation evidence for R035, R037, or R038.

## Scope

This contract governs where adapter state lives, who owns it, what residue checks run, how rollback works, what diagnostics are emitted, and what failure modes the adapter must classify. The contract is consumed by M062/S03 (fitness decision) and M062/S04 (roadmap synthesis).

Inheritance:

- S01 evidence category matrix defines which evidence categories the adapter may touch (`allowed`, `caution`, `blocked`, `ACP-native-only`).
- M055 L1 shadow diagnostic/projection pattern is the prior reference for adapter scope.
- M054 proof-only diagnostic adapter spike is the prior reference for isolation pattern.
- M061/S05 blocked boundaries remain authoritative.

## State location

State lives in three layers; each layer has explicit ownership and lifetime.

| Layer | Location | Lifetime | Owner | Notes |
|---|---|---|---|---|
| Disposable workspace | `/tmp/git-lex-l2-<uuid>` | Per probe / per pilot step | Adapter instance | Removed at probe end or pilot end. No persistent data. |
| Persistent cache (optional) | Project-local config dir (e.g. `prd/architecture/acp/runtime/<milestone>/`) | Per milestone | Project / GSD slice | Holds JSONL diagnostics, no raw payloads, no git-lex state. |
| Main repo | `/root/law-nexus` | Persistent | Project (law-nexus) | Must never contain `.lex`, `Squad`, `Raw`, `.artifacts`, or any git-lex runtime state. |

Hard rule: adapter state MUST NOT be created in the main repo. The adapter must fail closed if the main-repo state invariant is violated.

## State ownership boundary

| Owner | Owns | Does not own |
|---|---|---|
| Adapter instance | Workspace lifecycle, JSONL emission, residue checks. | Persistent project state, project decisions, source-of-truth records. |
| Project (law-nexus) | Persistent diagnostics, evidence category matrix application, blocked-boundary policy. | Adapter implementation, git-lex state, runtime invocation. |
| ACP core | Authority class, validation claim framing, profile boundary semantics. | Adapter behavior, git-lex state, raw payload handling. |
| User (human) | Final go/no-go/limited-pilot decision; explicit adoption promotion; production authorization. | Per-step adapter execution; per-step residue. |

The adapter must surface ownership conflicts to JSONL diagnostics with explicit owner labels, not silently override them.

## Residue checks

Residue checks run before and after every adapter action, and at pilot boundaries.

### Per-step residue check (mandatory)

```text
pre-step:
  assert /root/law-nexus/.lex does not exist
  assert /root/law-nexus/Squad does not exist
  assert /root/law-nexus/Raw does not exist
  assert /root/law-nexus/.artifacts does not exist
  assert workspace exists and is under /tmp
post-step:
  re-run the same four asserts
  capture diff in JSONL {pre_residue, post_residue}
on-violation:
  fail closed
  log to JSONL with classification=residue-violation
  do not auto-clean main-repo state
```

### Per-pilot residue check (mandatory at pilot end)

```text
cleanup-workspace:
  rm -rf <disposable-workspace>
verify-cleanup:
  assert workspace does not exist
verify-main-state:
  re-run four asserts on /root/law-nexus
  log to JSONL with classification=pilot-residue
on-violation:
  log classification=pilot-residue-failed
  halt pilot, raise to user
```

### Residue check contract

- The four main-repo asserts are non-negotiable.
- A violation in any of the four is `residue-violation` and fails the pilot.
- Per-step residue check is a hard precondition; no adapter step may run without it.

## Rollback policy

The adapter must support three rollback modes.

| Mode | Trigger | Recovery | Limit |
|---|---|---|---|
| Step rollback | Per-step residue violation, validation overflow, hook failure. | Re-run step from last known-good snapshot within workspace. | Within pilot only. |
| Pilot rollback | Persistent residue violation, state corruption, user abort. | Remove workspace, halt pilot, emit JSONL classification=pilot-aborted. | Pilot scope only. |
| Adoption rollback (not in scope) | Promotion to source-truth / production / R035/R037/R038 validation. | Not applicable — adoption is blocked. | Outside M062 scope. |

Hard rule: there is no "main-repo rollback" because there is no main-repo state. The adapter cannot mutate main repo, so there is nothing to roll back there. The contract enforces this by residue check, not by rollback.

## Diagnostics emission policy

The adapter emits diagnostics as JSONL only. Per the S01 evidence category matrix:

| Channel | Content | Allowed categories |
|---|---|---|
| JSONL file | `phase`, `step`, `command`, `exit_code`, `stdout_truncated`, `stderr_truncated`, `classification`, `pre_residue`, `post_residue`, `workspace`, `timestamp` | allowed + caution |
| stdout (human) | One-line summary per step | n/a |
| stderr (human) | Failure / abort message | n/a |
| Blocked: main-repo state | MUST NOT be created | blocked (legal source / raw text) MUST NOT appear in JSONL even when rejected |
| Blocked: authority claims | MUST NOT be emitted | ACP-native-only (parser / FalkorDB / retrieval / R035/R037/R038) MUST NOT be claimed as authority in JSONL |

### JSONL field contract

- `phase`: `setup | positive | negative | adapter-step | pilot-boundary | residue-violation | pilot-aborted`
- `classification`: `pass | pass-with-shape-violation | fail-closed | blocked | diagnostic-fail | rejected`
- `stdout_truncated`, `stderr_truncated`: max 2 KB per field
- `workspace`: absolute path under `/tmp`
- `pre_residue`, `post_residue`: object with `.lex`, `Squad`, `Raw`, `.artifacts` booleans

## Failure modes

The adapter must classify the following failure modes and either recover or fail closed.

| # | Failure mode | Detection | Recovery | Default action |
|---|---|---|---|---|
| 1 | State corruption in workspace | `git-lex validate` non-zero OR store read error | Snapshot workspace, reset, retry step. | Retry once, then fail closed. |
| 2 | Network failure (GitHub tarball fetch) | `git-lex init` exit 127 / connection error | Use local-equivalent configured-kit per M060/S02. | Fall back to local kit, log classification=network-fallback. |
| 3 | Hook failure during commit | `git commit` non-zero due to git-lex hook | Verify PATH includes git-lex binary, retry. | Fail closed if hook still broken. |
| 4 | Validation overflow | Validator emits > 100 violation lines | Truncate output, log classification=validation-overflow. | Continue, but flag pilot. |
| 5 | Workspace retention overrun | Workspace size > 1 GB OR > 1000 files | Cleanup, rotate to fresh workspace. | Halt pilot, raise to user. |
| 6 | Main-repo residue | Any of the four asserts fails | Halt immediately, log classification=residue-violation. | Do NOT auto-clean main repo. |
| 7 | ACP-native-only overclaim | JSONL contains authority claim for ACP-native-only category | Reject the claim, log classification=overclaim-rejected. | Re-emit without authority claim. |
| 8 | User abort | User signal received | Halt pilot, cleanup workspace, emit classification=pilot-aborted. | Wait for user direction. |

## Cross-link to S01 evidence matrix

| S01 classification | Adapter behavior |
|---|---|
| `allowed` (categories 1-3) | Project to JSONL with explicit authority class. |
| `caution` (if any) | Tag with proof class + bounded context + failure classifier. |
| `blocked` (category 4) | Reject the record before state entry; refuse raw payload bytes. |
| `ACP-native-only` (categories 5-8) | Reject any claim that uses git-lex projection as authority; surface as diagnostic-only. |

## Cross-link to M055 L1 pattern

M055 established the L1 shadow diagnostic/projection pattern. M062 L2 must not silently promote shadow diagnostics to authority. The contract reinforces this by requiring explicit authority class and failure classifier in every JSONL record.

## Cross-link to M054 proof-only adapter

M054 proved a tiny isolated source-built proof-only adapter. M062 L2 inherits the proof-only discipline but adds persistent diagnostics, retry policy, and failure classification. The proof-only "single probe" model becomes "bounded pilot" with the same hard no-main-state rule.

## Wording contract

Safe wording preserved:

```text
M062/S02 adapter state and rollback contract defines state location, ownership, residue checks, rollback modes, diagnostics emission, and failure classification for any future git-lex L2 adapter pilot.
```

```text
The contract is consumed by S03 fitness decision; S03 decides go, no-go, or limited-pilot.
```

Unsafe wording rejected:

```text
M062/S02 authorizes git-lex L2 production adoption.
```

```text
M062/S02 implements the git-lex L2 adapter.
```

```text
git-lex L2 adapter validates R035 / R037 / R038.
```

```text
Main .lex state is acceptable for the L2 adapter.
```

## Next slice

S03 — Adapter fitness decision. It will consume this contract and the S01 evidence matrix, and produce a go, no-go, or limited-pilot decision with conditions. S03 cannot approve main `.lex`, source-truth, production, or R035/R037/R038 validation.
