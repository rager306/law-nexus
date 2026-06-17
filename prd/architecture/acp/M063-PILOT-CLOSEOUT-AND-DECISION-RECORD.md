# M063/S04: Pilot closeout and decision record

## Status

Pass (bounded evidence). The bounded L2 diagnostic pilot ran successfully under S02 state+rollback contract enforcement. Positive leg produced bounded runtime evidence (10 final pass steps). Negative leg reproduced the M058 underconstrained-shape finding on 5 scalar probes (honest classification, not overclaim). Object-link negative is explicitly blocked per M058/M060. No main-repo residue. No pilot halt triggered. Blocked boundaries preserved.

This decision does not authorize L2 promotion, main `.lex` adoption, source-truth migration, production adoption, R035/R037/R038 validation, hard validation-gate adoption, or native multi-kit inheritance.

## Scope

This record closes M063 and produces the pilot decision that any future L2 promotion milestone must consume.

Inheritance chain:

- S01 (M063) pilot harness with S02 contract enforcement — 15 pytest pass, 7 setup records.
- S02 (M063) positive runtime-smoke — 6 paired fixtures, 10 final pass steps.
- S03 (M063) negative runtime-smoke — 5 scalar probes, 1 object-link blocked.
- M062 S01 evidence category matrix (allowed / caution / blocked / ACP-native-only).
- M062 S02 state+rollback contract (3-layer state, 4-owner boundary, residue, rollback, 8 failure modes).
- M062 S03 limited-pilot decision.
- M062 S04 roadmap synthesis (bounded L2 pilot proposal).
- M055 L1 shadow diagnostic/projection pattern.
- M054 proof-only diagnostic adapter spike.
- M061/S04 reusable profile overlay synthesis.
- M058 validation root cause.

## Evidence summary

Source: `prd/architecture/acp/runtime/M063-qp7ial/diagnostics.jsonl` (63 records).

| Phase | Count | Classification breakdown |
|---|---|---|
| setup | 29 | 28 pass + 1 blocked (initial prefixless SPARQL attempt) |
| positive | 11 | 10 pass + 1 blocked (initial SPARQL recovery) |
| negative | 11 | 10 pass-with-shape-violation + 1 blocked (object-link) |
| cleanup | 12 | 12 pass |
| **Total** | **63** | **51 pass + 10 pass-with-shape-violation + 2 blocked** |

### Positive leg (S02)

8 final pass steps: validate, sync, and 6 class queries (acp:ValidationClaim, acp:ProofGate, acp:EvidenceAnchor, lawNexus:ParserRun, lawNexus:LegalDocument, lawNexus:ACPBoundaryLink). All exit 0 in disposable /tmp workspace. Plus 1 initial blocked (prefixless SPARQL, recovered via PREFIX injection per M061/S04 pattern).

### Negative leg (S03)

5 scalar probes, all classified as `pass-with-shape-violation` (per M058 underconstrained-shape finding):

| case_id | exit_code | classification |
|---|---|---|
| acp-invalid-verdict | 0 | pass-with-shape-violation |
| acp-missing-source-artifact | 0 | pass-with-shape-violation |
| lawNexus-invalid-observedAt | 0 | pass-with-shape-violation |
| lawNexus-missing-synthetic | 0 | pass-with-shape-violation |
| lawNexus-invalid-proof-status | 0 | pass-with-shape-violation |

Object-link negative: 1 record, classification=`blocked`, reason="Deferred per M058/M060: frontmatter object values may normalize to IRIs and produce false negatives".

## Halt analysis (S02 8 failure modes)

| # | Failure mode | Triggered? | Detection | Note |
|---|---|---|---|---|
| 1 | State corruption | No | git-lex validate non-zero check | All validate steps exit 0. |
| 2 | Network failure | No | git-lex init exit 127 / connection error | Local-equivalent configured-kit per M060/S02 fallback used. |
| 3 | Hook failure | No | git commit non-zero due to git-lex hook | All commits passed. |
| 4 | Validation overflow | No | validator emits > 100 violation lines | Validators emitted < 100 lines per step. |
| 5 | Workspace retention overrun | No | workspace > 1 GB or > 1000 files | Workspaces under 100 MB and under 100 files. |
| 6 | Main-repo residue | No | 4 main-repo asserts | All pre_residue and post_residue: false. |
| 7 | ACP-native-only overclaim | No | JSONL contains authority claim for ACP-native-only category | No authority claims in JSONL. |
| 8 | User abort | No | user signal received | Pilot completed without abort. |

All 8 failure modes are detectable and recoverable. None triggered.

## Pilot decision

**Pass (bounded evidence).**

The bounded L2 diagnostic pilot ran successfully under S02 state+rollback contract enforcement. Evidence captured in 63 JSONL records across 4 phases. Positive leg produced 10 final pass steps for paired ACP + law-nexus profile fixtures. Negative leg reproduced the M058 underconstrained-shape finding on 5 scalar probes (honest classification, not overclaim). Object-link negative is explicitly blocked per M058/M060. No main-repo residue. No pilot halt triggered. Blocked boundaries preserved.

This is a bounded L2 diagnostic pilot evidence record, not a production adoption. L2 promotion, main `.lex`, source-truth, production, R035/R037/R038, hard validation gate, native multi-kit inheritance remain explicitly blocked.

## Pilot out of scope (preserved)

- Main `.lex` adoption.
- Source-truth migration.
- Production adoption.
- External publishing of law-nexus-kit.
- L2 operational diagnostic integration.
- R035 / R037 / R038 validation from git-lex projection.
- Native ACP-kit → law-nexus-kit runtime inheritance.
- Hard validation-gate adoption for ACP-kit / law-nexus-kit.
- Object-link validation as primary proof.
- General validation correctness.
- Raw legal text / raw payload anchors in JSONL.
- Main repo state mutation.

## Sequence after pilot (per S04 roadmap)

| Pilot outcome | Next step | Decision point |
|---|---|---|
| Pilot passes (current outcome) | M064 (or next available ID) plans the L2 promotion decision | Explicit user approval required; M064 cannot approve L2 promotion. |
| Pilot fails (residue / overclaim / overrun / corruption / abort) | Project remains at M055 L1 shadow role; failure root-cause documented | New milestone must fix root cause before any retry. |
| Pilot partial (some steps pass, some fail) | Document partial evidence; do not promote | Partial pilot is itself a failure outcome. |

## Cross-link to M062/S04 and M055 L1

- M062/S04 proposed a bounded L2 diagnostic pilot (subject to user approval). M063 implemented the proposal. The pilot is a bounded evidence record, not L2 promotion.
- M055 L1 shadow diagnostic/projection pattern is the proven backend role. M063 L2 pilot diagnostics are at L1-level granularity; L2 promotion is out of scope.
- M054 proof-only adapter discipline is preserved: pilot reuses disposable workspace, JSONL shape, residue check protocol.

## Cross-link to M058 and M061

- M058 root cause (underconstrained generated SHACL shapes) is reproduced in S03 negative leg. This is honest classification, not overclaim.
- M061/S04 reusable profile overlay synthesis established the harness pattern. M063 reuses and extends it for L2 pilot scope.

## Wording contract

Safe wording preserved:

```text
M063 bounded L2 diagnostic pilot passed with bounded evidence under S02 state+rollback contract enforcement.
```

```text
Positive leg produced 10 final pass steps for paired ACP + law-nexus profile fixtures in disposable workspace.
```

```text
Negative leg reproduced the M058 underconstrained-shape finding on 5 scalar probes; object-link is explicitly blocked per M058/M060.
```

```text
The pilot is a bounded evidence record; L2 promotion, main .lex, source-truth, production, R035/R037/R038, hard validation gate, and native multi-kit inheritance remain explicitly blocked.
```

Unsafe wording rejected:

```text
M063 approves L2 operational integration.
```

```text
M063 approves main .lex adoption.
```

```text
M063 approves source-truth migration or production adoption.
```

```text
M063 validates R035 / R037 / R038.
```

```text
M063 proves native multi-kit inheritance.
```

```text
Hard validation-gate adoption is approved by M063.
```

```text
git-lex L2 adapter is production-ready.
```

## Next milestone

M063 closeout (validation + complete). After M063 close, the next milestone (subject to user approval at planning time) may plan an L2 promotion decision under explicit human approval. The project otherwise remains at M055 L1 shadow diagnostic/projection backend role. Hard validation-gate adoption remains blocked per M058 until ontology/generator strengthening plus true negative runtime proof.
