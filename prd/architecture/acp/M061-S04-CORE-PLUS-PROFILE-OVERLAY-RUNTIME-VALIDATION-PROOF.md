# M061/S04: Core plus profile overlay runtime validation proof

## Status

Pass. Positive paired ACP core + law-nexus profile fixtures produced output-sensitive validation/sync/query evidence in an isolated disposable workspace. Negative probes on five scalar constraints confirmed the M058 root-cause finding (underconstrained generated SHACL shapes), so those constraints are explicitly blocked as hard proof-gate evidence until ontology/generator strengthening. Object-link negative is explicitly blocked per M058/M060. No main `.lex` adoption, no source-truth migration, no production adoption, no R035/R037/R038 validation.

## Scope

This artifact records the disposable-workspace runtime proof for paired ACP-kit and law-nexus-kit fixtures, plus the bounded negative validation probe set. It is diagnostic runtime-smoke evidence only. It is not source truth, not production packaging, not a hard proof-gate adoption claim.

Correct mechanics target:

```text
ACP-kit core = reusable governance/proof/source/evidence semantics
law-nexus profile = overlay constraints that map profile records to ACP core semantics
```

Incorrect mechanics target (remains blocked):

```text
law-nexus profile as independent source-truth kit
law-nexus profile bypassing ACP proof gates
law-nexus-specific classes added to ACP core
native ACP-kit -> law-nexus-kit runtime inheritance claim
general validation correctness
object-link negative as primary proof
```

## Source inputs

- `.gsd/milestones/M061-vtvuj0/slices/S04/continue.md` — handoff.
- `prd/architecture/acp/M061-S01-UNIVERSAL-ACP-CORE-CONTRACT.md` — reusable ACP core.
- `prd/architecture/acp/M061-S02-LAW-NEXUS-PROFILE-CONFORMANCE-MAPPING.md` — profile overlay mapping.
- `prd/architecture/acp/M061-S03-ACP-PROFILE-OVERLAY-SHACL-MECHANICS.md` — SHACL strategy and shape subset.
- `prd/architecture/cp/runtime/m061-s04/` — paired fixtures, composed SHACL profile, JSONL diagnostics.
- `.gsd/milestones/M058-dncm69/M058-dncm69-SUMMARY.md` — validation root cause.
- `.gsd/milestones/M060-4n6bg2/M060-4n6bg2-SUMMARY.md` — law-nexus-kit v0 scaffold proof.
- `git-lex-kit-acp/`, `git-lex-kit-law-nexus/` — kit scaffolds (copied into disposable workspace, not main checkout).

## Pre-flight gate (re-confirmed)

```text
uv run python scripts/verify-acp-ci-contract.py → 33 passed
git diff --check → clean
test ! -e .lex && test ! -e Squad && test ! -e Raw && test ! -e .artifacts → ok
git-lex binary at /root/vendor-source/git-lex/target/debug/git-lex → present
```

## Workspace and isolation

All runtime steps ran in disposable `/tmp/s061-s04-<uuid>` git repositories. Per-step pre-residue and post-residue checks confirmed the main checkout never acquired `.lex`, `Squad`, `Raw`, or `.artifacts`. Each negative case used a fresh workspace; on completion the workspace was removed. ACP-kit init used the explicit full spec `git-lex init --kit rager306/git-lex-kit-acp <workspace>` (M057 decision). Law-nexus-kit was attached via local-equivalent configured-kit setup, copying the kit scaffold into the workspace and pointing at the local path, as established in M060/S02.

The proof-shape strategy followed S03 mechanics:

```text
1. provision disposable workspace
2. copy ACP-kit and law-nexus-kit scaffolds into workspace
3. git-lex init --kit rager306/git-lex-kit-acp
4. install composed SHACL profile into workspace
5. author paired ACP + law-nexus fixtures with synthetic / nonAuthoritative / proofStatus = example-only markers
6. commit, sync, validate, query
7. capture exit code + output + classification into diagnostics.jsonl
8. residue check
9. cleanup
```

## Positive evidence (paired fixtures)

The positive probe ran six paired fixture classes and exercised `git-lex validate`, `git-lex sync`, and one `git-lex query` per class. All eight commands exited 0 in the disposable workspace.

| Step | Command | Exit | Output signal |
|---|---|---|---|
| validate | `git-lex validate` | 0 | `Validated 6 files in 84.9ms — all pass ✓` |
| sync | `git-lex sync` | 0 | `Synced in 703.0ms`, `+100 assertions, -0 retracted (600 quads)`, `Total sync graphs: 1` |
| query acp:ValidationClaim | `git-lex query 'SELECT ?s WHERE { ?s a acp:ValidationClaim }' --json` | 0 | rows bound (paired fixture present) |
| query acp:ProofGate | `git-lex query 'SELECT ?s WHERE { ?s a acp:ProofGate }' --json` | 0 | rows bound |
| query acp:EvidenceAnchor | `git-lex query 'SELECT ?s WHERE { ?s a acp:EvidenceAnchor }' --json` | 0 | rows bound |
| query lawNexus:ParserRun | `git-lex query 'SELECT ?s WHERE { ?s a lawNexus:ParserRun }' --json` | 0 | rows bound |
| query lawNexus:LegalDocument | `git-lex query 'SELECT ?s WHERE { ?s a lawNexus:LegalDocument }' --json` | 0 | rows bound |
| query lawNexus:ACPBoundaryLink | `git-lex query 'SELECT ?s WHERE { ?s a lawNexus:ACPBoundaryLink }' --json` | 0 | rows bound |

Aggregate from `prd/architecture/acp/runtime/m061-s04/diagnostics.jsonl`:

```text
phase=positive: 8 entries
classification=pass: 8
phase=setup: 42 entries (workspace provision, scaffold copy, init, fixture install, git add/commit, list --json)
```

Selected structured evidence (truncated for readability):

```text
step=validate           exit=0  "Validated 6 files in 84.9ms — all pass"
step=sync               exit=0  assertion_count_hint=1503, +100 assertions, 600 quads
step=acp-ValidationClaim-class  list --json returned expected ACP + law-nexus classes
```

## Negative evidence (five scalar constraints)

The negative probe ran five scalar-constraint violations that S03 selected as reliable (per M058 — datatype, enum, required-field constraints are not currently enforced by generated SHACL shapes; only a small number of `sh:nodeKind sh:IRI` constraints are generated).

| Probe | Fixture mutation | validate exit | validate output | classification |
|---|---|---|---|---|
| acp-invalid-verdict | `verdict=bogus` on `acp:ValidationClaim` | 0 | `all pass ✓` | pass-with-shape-violation |
| acp-missing-source-artifact | drop `acp:sourceArtifact` from `acp:ProofGate` | 0 | `all pass ✓` | pass-with-shape-violation |
| lawNexus-invalid-observedAt | `observedAt=not-a-date` on `lawNexus:ParserRun` | 0 | `all pass ✓` | pass-with-shape-violation |
| lawNexus-missing-synthetic | drop `lawNexus:synthetic` from `lawNexus:LegalDocument` | 0 | `all pass ✓` | pass-with-shape-violation |
| lawNexus-invalid-proofStatus | `proofStatus=approved` on `lawNexus:LegalDocument` | 0 | `all pass ✓` | pass-with-shape-violation |

Aggregate from `prd/architecture/acp/runtime/m061-s04/diagnostics.jsonl`:

```text
phase=negative: 21 entries
classification=pass-with-shape-violation: 10 (5 probes × validate+query)
classification=pass: 10 (5 probes × git add + commit for fixture install)
classification=blocked: 1 (object-link negative, deferred per M058/M060)
```

The five `pass-with-shape-violation` results reproduce the M058 root cause: `git-lex validate` reads per-file Turtle generated by `frontmatter_to_turtle`; the generated shape set does not attach the relevant datatype, enum, or minCount constraints to the targeted class shapes, so a fixture that violates the SHACL hand-written in the composed profile still passes the current validator. The composed profile in `prd/architecture/acp/runtime/m061-s04/shapes/composed-profile.ttl` is therefore diagnostic shape evidence, not enforcement. M058 already established this; S04 records the reproduction.

## Object-link negative (explicitly blocked)

```text
step=object-link-negative
classification=blocked
reason=Deferred per M058/M060 because frontmatter object values can normalize to IRIs and produce false negatives.
```

Object-link validation is not a primary success criterion for S04 and remains deferred/blocked unless a future strategy that survives git-lex IRI normalization is proven.

## Blocked claims after S04

These remain blocked after S04 and are not validated by S04 evidence:

```text
Blocked: hard validation gate adoption for ACP-kit / law-nexus-kit
Blocked: object-link validation as primary proof
Blocked: general validation correctness
Blocked: native ACP-kit -> law-nexus-kit runtime inheritance
Blocked: main .lex adoption
Blocked: source-truth migration
Blocked: production adoption
Blocked: external publishing of law-nexus-kit
Blocked: R035 / R037 / R038 validation from ACP-kit / git-lex / projection evidence
```

## Wording contract

Safe wording preserved:

```text
M061/S04 produced disposable-workspace runtime-smoke evidence that paired ACP core plus law-nexus profile fixtures pass validate/sync/query, while five scalar negative probes reproduced the M058 underconstrained-shape finding and are explicitly blocked as hard proof-gate evidence.
```

Unsafe wording rejected:

```text
git-lex validate enforces SHACL constraints for ACP-kit / law-nexus-kit.
```

```text
law-nexus-kit v0 is production-ready.
```

```text
ACP-kit validates R035, R037, or R038.
```

```text
M061/S04 proves native ACP-kit -> law-nexus-kit runtime inheritance.
```

## Verification gates (re-confirmed at closeout)

```bash
test -f prd/architecture/acp/M061-S04-CORE-PLUS-PROFILE-OVERLAY-RUNTIME-VALIDATION-PROOF.md
uv run python scripts/verify-acp-ci-contract.py   # 33 passed
uv run pytest tests/test_verify_m061_s04_overhead_runtime.py   # 7 passed
git diff --check
test ! -e .lex && test ! -e Squad && test ! -e Raw && test ! -e .artifacts
```

## Next slice

S05 — Reusable ACP profile overlay synthesis. It must close M061 with the proven scope, blocked boundary, and S04 evidence trail, and hand off to M062 (git-lex diagnostic adapter decision) without approving main `.lex`, source-truth migration, or production adoption.
