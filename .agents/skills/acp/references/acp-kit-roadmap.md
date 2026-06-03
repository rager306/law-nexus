# ACP-kit roadmap

## Position in the git-lex to ACP plan

ACP-kit is the corrected next semantic integration step after M048-M055 and M049/S01-S04.

It sits here:

```text
M051 S08 static ACP ontology prototype
→ K1 ACP-kit v0 package over git-lex-kit-base
→ K2 isolated ACP-kit runtime proof
→ K3 M049 binding projection through ACP-kit records
→ K4 L2 operational diagnostic integration
→ K5 isolated main `.lex` rehearsal
→ K6 ACP source-truth migration design
→ K7 production/provenance adoption
```

ACP-kit is not immediate backend promotion. It packages ACP core semantics so future diagnostics can speak ACP vocabulary without turning git-lex output into source truth.

## Current evidence

| Evidence | What it supports | What it does not support |
|---|---|---|
| M051/S08 ontology prototype | Static ACP classes, sample records, JSON-LD sample, SPARQL audit pack, structural verifier. | Runtime git-lex adoption or JSON-LD runtime support. |
| M055 L1 decision | git-lex may continue as non-authoritative L1 shadow diagnostics over ACP-shaped synthetic records. | L2 readiness, main `.lex`, production, source-truth migration. |
| M049/S04 verifier | Executable checks catch binding artifact overclaiming. | Canonical registry freshness or profile claim validation. |
| M049/S05 roadmap | ACP-kit should precede L2 operational diagnostics. | ACP-kit implementation or runtime proof by itself. |

## ACP-kit v0 design defaults

Use `git-lex-kit-base` as the base vocabulary package and create a separate ACP domain kit.

Observed kit patterns:

```yaml
# base
name: base
install folders: false

# squad-style domain kit
name: squad
install folders: true
folder base: Squad
folder ontology: squad.ttl
```

Recommended ACP-kit v0:

```yaml
name: acp
install folders: true
folder base: ACP
folder ontology: acp.ttl
```

Do not use `adaptive: true` in v0. Runtime ontology mutation requires a separate authority, rollback, and verifier policy.

Recommended initial structure:

```text
git-lex-kit-acp/
  kit.yml
  ontology/acp/acp.ttl
  content/AGENTS.md
  content/ACP/
    SourceRecord/
    Requirement/
    Decision/
    EvidenceAnchor/
    ProofGate/
    HealthFinding/
    Projection/
    ValidationClaim/
    ProfileConstraint/
    RuntimeAdapter/
```

## ACP-kit core vocabulary

ACP-kit v0 should include reusable ACP core concepts:

```text
acp:SourceRecord
acp:Requirement
acp:Decision
acp:EvidenceAnchor
acp:ProofGate
acp:HealthFinding
acp:Projection
acp:LifecycleState
acp:AuthorityClass
acp:ValidationClaim
acp:ProfileConstraint
acp:RuntimeAdapter
```

Each class must preserve the authority rule:

```text
source category + lifecycle state + evidence anchor + proof gate or accepted decision
```

## Stage gates

### K1: ACP-kit v0 package

Minimum proof:

- kit files exist and are tracked;
- ontology derives from M051/S08 without M051-specific prototype authority claims;
- static verifier confirms required classes/folders;
- no unsafe durable anchors;
- no main `.lex`, `Squad`, or `Raw`.

### K2: Isolated ACP-kit runtime proof

Minimum proof:

- source-built pinned git-lex binary identity recorded;
- disposable workspace outside the main checkout;
- ACP-kit init/sync/list/query/validate operations run;
- positive and negative fixtures exist;
- diagnostics are bounded and non-authoritative;
- pre/post no-main-state residue checks pass.

### K3: M049 binding projection

Minimum proof:

- M049 binding records represented through ACP-kit examples;
- verifier catches authority inversion, unsafe anchors, missing proof gates, forbidden git-lex promotion, profile/core drift, and R035/R037/R038 overclaim;
- no generated registry freshness claim.

### K4 L2 operational diagnostics

Minimum proof:

- regular ACP workflow invocation;
- retention/compaction/indexing policy;
- failure-state persistence;
- retry behavior;
- fail-closed operational tests;
- no main-state residue;
- non-authoritative diagnostic classification.

### K5-K7: blocked future stages

K5 main `.lex` rehearsal, K6 source-truth migration, and K7 production/provenance adoption remain blocked until explicit decisions and proof gates exist.

## Safe and unsafe claims

Safe:

```text
ACP-kit is a semantic integration layer that packages ACP core source/proof/projection vocabulary over git-lex-kit-base while preserving ACP-native authority.
```

Safe:

```text
ACP-kit v0 can prepare better L1/L2 diagnostics without approving main `.lex` or source-truth migration.
```

Unsafe:

```text
ACP-kit makes git-lex ACP source truth.
```

Unsafe:

```text
ACP-kit validates R035, R037, or R038.
```

Unsafe:

```text
ACP-kit existence approves main `.lex` in law-nexus.
```

## Routing rule

Use this ACP skill for ACP-kit design, ontology extraction, proof gates, and ACP/law-nexus profile boundary work.

Use the `git-lex` skill for executable git-lex behavior, `.lex` state, runtime proof, JSON-LD runtime support claims, SPARQL-star runtime claims, binary provenance, and production/adoption gates.
