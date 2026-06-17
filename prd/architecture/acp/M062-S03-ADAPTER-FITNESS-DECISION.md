# M062/S03: Adapter fitness decision

## Status

Pass (decision recorded). The recommended decision is **limited-pilot**: a bounded disposable-workspace git-lex L2 diagnostic pilot, scoped per S01 evidence matrix and S02 state+rollback contract, with explicit preconditions and exit criteria. This decision does not authorize L2 promotion, main `.lex` adoption, source-truth migration, production adoption, or R035/R037/R038 validation.

## Scope

This decision answers: should the project pursue a git-lex L2 diagnostic backend integration, and if so, in what form? The decision is consumed by M062/S04 (roadmap synthesis) and any future L2 implementation milestone.

Inheritance chain:

- M055 L1 shadow diagnostic/projection pattern — proven.
- M054 proof-only diagnostic adapter spike — proven.
- M061/S05 reusable profile overlay synthesis — bounded scope preserved.
- M058 validation root cause — hard validation gate adoption blocked.
- S01 evidence category matrix — classification vocabulary defined.
- S02 state and rollback contract — state location, residue, rollback, failure modes defined.

## Decision

**Limited-pilot.** Pursue a bounded disposable-workspace L2 diagnostic pilot that mirrors M054 proof-only discipline and M055 L1 shadow pattern, with explicit preconditions, scope boundaries, and exit criteria. The pilot is diagnostic-only and does not promote to L2 operational integration, main `.lex`, source-truth, or production.

```text
decision: limited-pilot
scope: disposable /tmp workspace, explicit `rager306/git-lex-kit-acp`, local-equivalent law-nexus-kit
promotion: not approved
durable state: not approved
authority: diagnostic only; not authority for ACP-native-only categories
exit criteria: bounded pilot; halt on residue violation, ACP-native-only overclaim, or pilot failure
```

## Decision input summary

| Input | What it contributes |
|---|---|
| S01 evidence matrix | 4-tier classification (allowed / caution / blocked / ACP-native-only) protects the pilot from overclaim. |
| S02 state+rollback contract | State location (3 layers, no main-repo), residue checks (per-step and per-pilot), rollback modes (step / pilot, not adoption), 8 failure modes. |
| M055 L1 shadow pattern | L1 shadow diagnostic/projection is proven; L2 must not silently promote shadow to authority. |
| M054 proof-only adapter | Tiny source-built proof-only adapter discipline; bounded pilot reuses this pattern. |
| M061/S05 blocked boundaries | hard validation gate, object-link, native multi-kit, main `.lex`, source-truth, production, R035/R037/R038 all remain blocked. |
| M058 validation root cause | Generated SHACL shapes are underconstrained; hard validation-gate adoption blocked until ontology/generator strengthening. |

## Selected option: limited-pilot

### What is allowed in the pilot

```text
- read-only git-lex init --kit rager306/git-lex-kit-acp in disposable /tmp workspace
- positive runtime-smoke on paired ACP + law-nexus profile fixtures
- negative probes on selected scalar constraints (with explicit blocker per M058)
- classification vocabulary: pass / pass-with-shape-violation / fail-closed / blocked
- JSONL diagnostics to prd/architecture/acp/runtime/<milestone-id>/
- per-step residue check (4 main-repo asserts)
- per-pilot cleanup of /tmp workspace
- local-equivalent law-nexus-kit configured-kit setup (M060/S02)
```

### What is forbidden in the pilot

```text
- main .lex adoption
- source-truth migration
- production adoption
- external publishing of law-nexus-kit
- L2 operational diagnostic integration
- R035 / R037 / R038 validation from git-lex projection
- native ACP-kit -> law-nexus-kit runtime inheritance
- hard validation-gate adoption for ACP-kit / law-nexus-kit
- object-link validation as primary proof
- general validation correctness
- raw legal text / raw payload anchors in JSONL
- main repo state mutation
```

### Pilot success criteria

- All 4 main-repo asserts (`.lex`, `Squad`, `Raw`, `.artifacts`) pass at every per-step and per-pilot residue check.
- Positive paired fixtures pass validate/sync/query in disposable workspace.
- At least one ACP-core negative and one law-nexus profile conformance negative produce output-sensitive evidence or are explicitly blocked.
- JSONL diagnostics include phase / step / exit_code / classification / pre_residue / post_residue / workspace for every step.
- No raw payload bytes in JSONL.
- No authority claim for ACP-native-only categories in JSONL.

### Pilot failure criteria (halt and raise)

- Residue violation in any of the 4 main-repo asserts.
- ACP-native-only overclaim (any authority claim for parser quality, FalkorDB, retrieval/citation, R035/R037/R038).
- Workspace retention overrun (> 1 GB or > 1000 files).
- Persistent state corruption unrecoverable by step rollback.
- User abort.

## Rejected options

| Option | Why rejected |
|---|---|
| **go** (full L2 promotion) | Overclaim. M058 root cause is not resolved. M055 L1 is the proven backend role; promoting to L2 would require ontology/generator strengthening, true negative runtime proof, and human-approved adoption decision. None of these are present. |
| **no-go** (no L2 work) | Overly conservative. M055 L1 + M054 proof-only + M061 runtime-smoke are already in evidence. A bounded limited-pilot does not overclaim and is the natural next step. Pure no-go would forfeit the diagnostic value of M055/M054/M061 evidence. |

## Conditions (preconditions for pilot start)

1. S01 evidence matrix is in effect and consumed by the pilot.
2. S02 state+rollback contract is in effect and enforced by the pilot.
3. M061 closed (S05 synthesis, M061 validation pass, M061 milestone complete).
4. The pilot runs in a disposable /tmp workspace; main repo state is forbidden.
5. JSONL diagnostics land in `prd/architecture/acp/runtime/<milestone-id>/` with per-step residue checks.
6. Pilot halt on any of the 8 failure modes from S02 contract.
7. No raw payload anchors, no ACP-native-only overclaim, no L2 promotion, no main `.lex`.
8. Pilot is bounded; exit criteria (success / failure) recorded in M062/S04 roadmap synthesis.

## Cross-link to next slice

S04 — Diagnostic adapter roadmap synthesis. It will consume this decision and produce a roadmap that either plans the next L2 pilot implementation milestone (recommended) or records why L2 pilot adoption remains blocked.

## Wording contract

Safe wording preserved:

```text
M062/S03 adapter fitness decision: limited-pilot.
```

```text
The pilot is bounded, disposable, diagnostic-only, and does not promote to L2 operational integration.
```

```text
L2 pilot preserves S01 evidence matrix and S02 state+rollback contract.
```

Unsafe wording rejected:

```text
M062/S3 approves L2 operational integration.
```

```text
M062/S3 approves main .lex adoption.
```

```text
M062/S3 approves source-truth migration or production adoption.
```

```text
M062/S3 validates R035 / R037 / R038.
```

```text
M062/S3 authorizes native multi-kit inheritance.
```

## Next slice

S04 — Diagnostic adapter roadmap synthesis. Consumes this decision and the S01/S02 inputs. Plans the next implementation milestone (recommended: a bounded L2 diagnostic pilot with the conditions above) or records why the pilot remains blocked.
