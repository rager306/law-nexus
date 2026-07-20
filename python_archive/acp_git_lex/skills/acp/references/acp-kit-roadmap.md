# ACP-kit roadmap

## Active direction (D084, post-M063) — supersedes the K1-K7 ladder below as the forward plan

Full diagnosis and evidence: `prd/architecture/acp/ACP-GIT-LEX-ROADMAP-STRAIGHTENING-REVIEW.md`.

The K1-K7 ladder below records what was *done* (M051 S08 -> K1 package -> K2 isolated
runtime). It is no longer the forward plan. The forward plan is adoption-oriented and
foundation-first:

```text
Stage 0  Direction decision [DONE, D084]: git-lex role = foundation/source-truth
Stage 1  Close the M058 root cause [milestone M064]: strengthen acp.ttl SHACL/OWL
         constraints (sh:datatype / sh:in / sh:minCount or OWL restrictions),
         regenerate shapes, true-negative fixtures, prove git-lex validate != 0
Stage 2  Install git-lex for real: pinned version, `git lex` as a real command,
         closed supply-chain/binary trust (M051/S09)
Stage 3  Adopt .lex in one real repository (law-nexus or a dedicated acp repo):
         git-lex init --kit rager306/git-lex-kit-acp, place ACP records,
         use validate/sync/query in real work
Stage 4  Prove reusability with a SECOND, non-law-nexus project
Stage 5  Formalize the authority model (D072); managed (not blanket-blocked)
         source-truth migration
```

Keep (real correctness, not paralysis): the authority model — a record is
authoritative only with source category + lifecycle state + evidence anchor + proof
gate or accepted decision; R035/R037/R038 require real source/runtime evidence, not
projection.

Drop (paralysis that blocks the goal): never-install, never-main-repo,
shadow-forever, disposable-workspace-only proofs, proof-before-foundation inversion,
and the decision -> pilot -> decision loop.

Routing unchanged: ACP-kit semantic design and ACP/law-nexus profile boundary stay in
this (ACP) skill; executable git-lex behavior, `.lex` state, and runtime adoption go to
the `git-lex` skill.

--- Historical ladder (done; no longer the forward plan) ---

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
| M056/S01 inspection | Base/domain kit mechanics support deterministic ACP-kit package defaults. | Runtime compatibility or source-truth migration. |
| M056/S02 extraction | ACP core vocabulary v0 is selected with profile/runtime boundaries. | Actual scaffold files or runtime proof. |
| M056/S03 scaffold | `git-lex-kit-acp` now contains deterministic `kit.yml`, `ontology/acp/acp.ttl`, guidance, and synthetic examples. | Runtime git-lex compatibility, generated shape behavior, main `.lex`, production, or profile validation. |
| M056/S04 verifier | `scripts/verify-m056-acp-kit.py` and tests provide static scaffold guardrails. | RDF parser proof or git-lex runtime proof. |
| M056/S05 isolated attempt (`prd/architecture/acp/M056-S05-ISOLATED-RUNTIME-PROOF.md`) | Source-built git-lex help/init can run in a disposable workspace and base kit install starts; main checkout remains clean. Post-M056 correction: canonical ACP-kit invocation is `git-lex init --kit rager306/git-lex-kit-acp <target-repo>`, and full-spec init succeeds. | Short `--kit acp` is not canonical and may resolve to `repolex-ai/git-lex-kit-acp`; class discovery/sync/query/validate/negative validation remain separate runtime-semantics proof. |
| M056/S06 synthesis | ACP-kit v0 is static-ready; installation by explicit `rager306/git-lex-kit-acp` full spec is proven in isolation. | L2 diagnostics readiness, main `.lex`, source-truth migration, production, class discovery/sync/query/validate semantics, or R035/R037/R038 validation. |

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

Current scaffold structure:

```text
git-lex-kit-acp/kit.yml
git-lex-kit-acp/ontology/acp/acp.ttl
git-lex-kit-acp/content/AGENTS.md
git-lex-kit-acp/
  kit.yml
  ontology/acp/acp.ttl
  content/AGENTS.md
  content/ACP/.gitkeep
  content/ACP/SourceRecord/example-source-record.md
  content/ACP/Decision/example-decision.md
  content/ACP/ProofGate/example-proof-gate.md
  www/.gitkeep
```

This scaffold is deterministic static package evidence only. It is not runtime proof.

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

Current static verifier:

```text
scripts/verify-m056-acp-kit.py
tests/test_verify_m056_acp_kit.py
```

### K2: Isolated ACP-kit runtime proof

Project rule: use the explicit repository spec everywhere:

```bash
git-lex init --kit rager306/git-lex-kit-acp <target-repo>
```

Do not use short `--kit acp` as the ACP-kit proof command; it is not canonical for law-nexus and may resolve through git-lex short-name defaults.

Current status after the post-M056 repository publication: full-spec init succeeds in a disposable workspace and keeps the main checkout clean. Runtime semantics are still not fully upgraded.

Minimum proof before claiming L2/runtime readiness:

- source-built pinned git-lex binary identity recorded;
- explicit `rager306/git-lex-kit-acp` kit source used;
- disposable workspace outside the main checkout;
- ACP-kit init/list/sync/query/validate operations run;
- positive and negative fixtures exist;
- `git-lex list --json` class-discovery behavior is understood;
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
ACP-kit v0 can prepare better L1/L2 diagnostics conceptually, but runtime proof must use `git-lex init --kit rager306/git-lex-kit-acp <target-repo>` and still needs class discovery, sync/query/validate, and negative validation evidence before L2 readiness.
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
