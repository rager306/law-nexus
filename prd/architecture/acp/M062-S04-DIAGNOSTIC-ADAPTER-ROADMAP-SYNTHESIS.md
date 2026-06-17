# M062/S04: Diagnostic adapter roadmap synthesis

## Status

Pass (roadmap synthesis). The recommended next milestone is a **bounded L2 diagnostic pilot** that mirrors the S03 limited-pilot decision under the S01 evidence matrix and S02 state+rollback contract. This synthesis does not authorize L2 promotion, main `.lex` adoption, source-truth migration, production adoption, or R035/R037/R038 validation.

## Scope

This synthesis records the recommended next-implementation milestone for any future git-lex L2 diagnostic integration. It is consumed by M062 closeout and any future L2 pilot implementation milestone (subject to explicit user approval at planning time).

Inheritance chain:

- S01 evidence matrix — 4-tier classification (allowed / caution / blocked / ACP-native-only).
- S02 state+rollback contract — state location, residue checks, rollback modes, 8 failure modes.
- S03 fitness decision — limited-pilot (bounded disposable workspace pilot).
- M055 L1 shadow diagnostic/projection — proven.
- M054 proof-only diagnostic adapter spike — proven.
- M061/S05 reusable profile overlay synthesis — bounded scope preserved.
- M058 validation root cause — hard validation gate blocked.

## Decision

**Plan a bounded L2 diagnostic pilot implementation milestone.** The pilot is disposable, diagnostic-only, and does not promote to L2 operational integration. The pilot mirrors M055 L1 shadow discipline and M054 proof-only adapter precedent.

```text
next-milestone: bounded L2 diagnostic pilot (subject to user approval at planning time)
scope: disposable /tmp workspace, S01 evidence matrix, S02 state+rollback contract
durable state: not approved
authority: diagnostic only
promotion: not approved; any promotion requires separate milestone and human approval
blocked boundaries: preserved (main .lex, source-truth, production, R035/R037/R038, hard validation gate, native multi-kit)
```

## Proposed next milestone (subject to user approval)

A future milestone `M063-...` — bounded L2 diagnostic pilot implementation. The proposed scope:

```text
milestone: M063 (or next available ID, subject to user approval)
vision: Prove the S02 state+rollback contract is enforceable in practice; produce bounded L2 diagnostic
        evidence under S01 evidence matrix; demonstrate pilot halt on residue violation or
        ACP-native-only overclaim.
```

### Pilot scope (allowed)

- Disposable /tmp workspace per probe / per pilot step.
- Explicit `git-lex init --kit rager306/git-lex-kit-acp <workspace>` (M057 decision).
- Local-equivalent law-nexus-kit configured-kit setup (M060/S02).
- Positive runtime-smoke on paired ACP + law-nexus profile fixtures.
- Negative probes on selected scalar constraints (per M058 honest blocker).
- JSONL diagnostics to `prd/architecture/acp/runtime/m063-<id>/`.
- Per-step and per-pilot residue checks (4 main-repo asserts).
- Classification vocabulary: pass / pass-with-shape-violation / fail-closed / blocked.
- Pilot halt on any of the 8 failure modes from S02 contract.
- Reuse of M061/S04 harness pattern (disposable workspace, JSONL shape, residue check protocol).

### Pilot scope (forbidden)

- Main `.lex` adoption.
- Source-truth migration.
- Production adoption.
- External publishing of law-nexus-kit.
- L2 operational diagnostic integration.
- R035 / R037 / R038 validation from git-lex projection.
- Native ACP-kit → law-nexus-kit runtime inheritance.
- Hard validation-gate adoption.
- Object-link validation as primary proof.
- General validation correctness.
- Raw legal text / raw payload anchors in JSONL.
- Main repo state mutation.

### Pilot prerequisites

1. M061 closed (S05 synthesis, M061 validation pass, M061 milestone complete).
2. M062 closed (S01 matrix, S02 contract, S03 limited-pilot decision, S04 roadmap synthesis).
3. S01 evidence matrix in effect and consumed by the pilot.
4. S02 state+rollback contract in effect and enforced by the pilot.
5. User explicit approval at planning time for the proposed M063 milestone.

### Pilot success criteria

- All 4 main-repo asserts pass at every per-step and per-pilot residue check.
- Positive paired fixtures pass validate/sync/query in disposable workspace.
- At least one ACP-core negative and one law-nexus profile conformance negative produce output-sensitive evidence or are explicitly blocked per M058.
- JSONL diagnostics include phase / step / exit_code / classification / pre_residue / post_residue / workspace for every step.
- No raw payload bytes in JSONL.
- No authority claim for ACP-native-only categories in JSONL.
- S02 contract 8 failure modes are detectable and recoverable in practice.

### Pilot failure criteria (halt and raise)

- Residue violation in any of the 4 main-repo asserts.
- ACP-native-only overclaim (any authority claim for parser quality, FalkorDB, retrieval/citation, R035/R037/R038).
- Workspace retention overrun (> 1 GB or > 1000 files).
- Persistent state corruption unrecoverable by step rollback.
- User abort.

### Pilot halt and post-pilot decision

- If pilot passes, M063 may record the bounded evidence. A separate future milestone must then decide whether to promote any diagnostic to L2 operational integration. That promotion is **not** approved by M062.
- If pilot fails (residue violation, ACP-native-only overclaim, workspace overrun, or other failure mode), the project remains at M055 L1 shadow diagnostic/projection backend role. L2 promotion is blocked until the failure is diagnosed and resolved.

## Sequence after pilot

| Pilot outcome | Next step | Decision point |
|---|---|---|
| Pilot passes with bounded evidence | M064 (or next available ID) plans the L2 promotion decision | Explicit user approval required; M064 cannot approve L2 promotion. |
| Pilot fails on residue / overclaim / overrun | Project remains at M055 L1 shadow role; failure root-cause documented | New milestone must fix root cause before any retry. |
| Pilot partial (some steps pass, some fail) | Document partial evidence; do not promote | M062/S04 partial pilot is itself a failure outcome. |

## Cross-link to M055 L1 and M054 proof-only

| Pattern | Source | Pilot inherits |
|---|---|---|
| L1 shadow diagnostic/projection | M055 | Pilot diagnostics stay at L1-level granularity; L2 promotion is out of scope. |
| Proof-only adapter discipline | M054 | Pilot reuses the proof-only harness pattern (disposable workspace, JSONL, residue check). |
| Local-equivalent configured-kit | M060/S02 | Law-nexus-kit attachment via local copy, not GitHub publish. |

## Cross-link to M061/S05 and M058

- M061/S05 blocked boundaries (hard validation gate, object-link, native multi-kit, main `.lex`, source-truth, production, R035/R037/R038) are preserved by the pilot.
- M058 root cause (underconstrained generated SHACL shapes) is recorded as a known limitation; pilot reproduces it honestly without overclaim.

## Wording contract

Safe wording preserved:

```text
M062/S04 diagnostic adapter roadmap synthesis recommends a bounded L2 diagnostic pilot implementation milestone (subject to user approval at planning time).
```

```text
The pilot is disposable, diagnostic-only, and does not promote to L2 operational integration.
```

```text
L2 pilot preserves S01 evidence matrix and S02 state+rollback contract.
```

Unsafe wording rejected:

```text
M062/S4 authorizes L2 pilot implementation now.
```

```text
M062/S4 approves main .lex adoption.
```

```text
M062/S4 approves source-truth migration or production adoption.
```

```text
M062/S4 validates R035 / R037 / R038.
```

```text
M062/S4 plans L2 promotion in M063 without separate decision milestone.
```

## Next milestone

M062 closeout (validation + complete). After M062 close, the bounded L2 diagnostic pilot is available as a proposed next milestone subject to explicit user approval at planning time. The project otherwise remains at M055 L1 shadow diagnostic/projection backend role.
