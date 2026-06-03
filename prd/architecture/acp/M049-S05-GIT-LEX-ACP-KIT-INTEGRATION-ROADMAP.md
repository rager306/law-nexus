# M049 S05 Git Lex ACP Kit Integration Roadmap

## Status

Created for `M049 / S05 / T01`.

This artifact records the corrected git-lex to ACP integration roadmap after M048-M055 and M049/S01-S04. It positions `ACP-kit` as a semantic-kit implementation track between the M051 static ACP ontology prototype and future L2 operational diagnostics. It does not approve ACP source-truth migration, main `.lex` adoption, or production git-lex use.

## Executive decision

ACP should continue using git-lex within the proven L1 shadow diagnostic/projection boundary, but the next tighter integration step should be an ACP semantic kit, not immediate L2 backend promotion.

Corrected sequence:

```text
M051 S08 static ontology prototype
→ K1 ACP-kit v0 package over git-lex-kit-base
→ K2 isolated ACP-kit runtime proof
→ K3 M049 binding projection through ACP-kit records
→ K4 L2 operational diagnostic integration
→ K5 isolated main `.lex` rehearsal
→ K6 ACP source-truth migration design
→ K7 production/provenance adoption
```

The immediate next implementation target is therefore `ACP-kit v0`, with no main repository `.lex`, `Squad`, or `Raw` state.

## Evidence baseline

| Milestone | Result | Impact on ACP-kit roadmap |
|---|---|---|
| M048 | Closed ACP/git-lex foundation with ACP-native source records, lifecycle, health, evidence, proof gate, and anti-imitation framing. | Establishes the authority rule that ACP-kit shapes/projections cannot be authoritative by themselves. |
| M051 | Completed deep git-lex research; selected semantic vocabulary and proof-boundary patterns can be absorbed ACP-natively. S08 created ACP ontology/static projection prototype. | Provides the direct seed for ACP-kit vocabulary and static verifier concepts. |
| M052 | Hardened capability gaps: JSON-LD runtime rejected, broad SPARQL-star blocked, negative SHACL only bounded, production blocked. | ACP-kit may include static JSON-LD/TTL/SHACL/SPARQL artifacts, but must not claim unsupported git-lex runtime capabilities. |
| M053 | Produced minimal adapter boundary and rejected raw/session logs, broad save/create/raw workflows, and production provenance. | ACP-kit must avoid raw/session payload proof anchors and keep runtime helpers behind adapter gates. |
| M054 | Proved a pinned source-built proof-only diagnostic wrapper in isolation. | Supplies adapter feasibility for future ACP-kit-aware diagnostics, not ACP-kit authority. |
| M055 | Advanced git-lex to L1 shadow diagnostic/projection backend and selected L2 operational diagnostics as follow-up. | ACP-kit should become the semantic contract used before or during L2 integration. |
| M049/S01-S04 | Bound law-nexus architecture into ACP source/proof/profile boundaries and added an executable binding verifier. | ACP-kit must preserve reusable ACP core versus law-nexus profile separation and verifier-backed overclaim checks. |

## Corrected stage model

| Stage | Name | Status now | Purpose | Promotion gate | Must not claim |
|---|---|---|---|---|---|
| K0 | Static ACP ontology prototype | Done in M051/S08. | Proposed non-authoritative ACP classes, sample records, JSON-LD sample, SPARQL audit pack, and structural verifier. | None; already a planning artifact. | Runtime git-lex adoption, JSON-LD runtime support, requirement validation. |
| K1 | ACP-kit v0 package | Next recommended milestone. | Package ACP core vocabulary as a git-lex-compatible kit derived from `git-lex-kit-base` and M051/S08. | Tracked kit files, ontology review, skill guidance, no unsafe anchors. | Source truth, main `.lex`, production, law-nexus profile validation. |
| K2 | Isolated ACP-kit runtime proof | After K1. | Prove `git-lex init/sync/list/query/validate` can operate with ACP-kit in a disposable workspace. | Source-built pinned binary, isolated workspace, bounded diagnostics, no main residue, positive and negative fixtures. | Production readiness, main checkout adoption, broad runtime capability. |
| K3 | M049 binding projection through ACP-kit | After K2 or static-first after K1. | Represent M049 binding records through ACP-kit classes while preserving ACP-native authority. | Projection verifier catches authority inversion, unsafe anchors, missing proof gates, forbidden git-lex promotion, profile/core drift. | Generated registry freshness, R035/R037/R038 validation, legal/parser/FalkorDB proof. |
| K4 | L2 operational diagnostic integration | Future follow-up. | Invoke ACP-kit-aware git-lex diagnostics regularly in ACP workflows. | Workflow invocation tests, retention policy, failure-state persistence, observability, fail-closed behavior. | ACP source-truth backend, main `.lex`, production. |
| K5 | Isolated main `.lex` rehearsal | Blocked until explicit future decision. | Rehearse repository-like `.lex` state in a disposable clone, including cleanup and rollback. | Explicit human decision, isolated main-repo rehearsal, tracked/ignored state policy, rollback proof. | Direct main checkout mutation. |
| K6 | ACP source-truth migration design | Blocked. | Decide whether any ACP source truth can move into git-lex-managed state. | Authority migration design, conflict resolution, proof-gate policy, accepted decision, rollback. | Projection as source truth. |
| K7 | Production/provenance adoption | Blocked. | Make git-lex/ACP-kit runtime production-grade if ever needed. | Source/build/release/license/SBOM/signature/attestation, security review, rollback, observability. | Current production readiness. |

## ACP-kit v0 shape

Use `git-lex-kit-base` as the base vocabulary package, but create an ACP domain kit rather than mutating base.

Observed kit pattern:

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

Recommended ACP-kit v0 pattern:

```yaml
name: acp
install folders: true
folder base: ACP
folder ontology: acp.ttl
```

Do not use `adaptive: true` in v0. AutoKnow-style adaptive ontology mutation is useful prior art, but ACP authority needs deterministic ontology and proof-gate control before runtime ontology mutation is considered.

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

## ACP-kit v0 core vocabulary

ACP-kit should absorb M051/S08 concepts into reusable ACP core:

| ACP-kit concept | Source seed | Boundary |
|---|---|---|
| `acp:SourceRecord` | M048/M051 source-record model. | Authority only when lifecycle, evidence anchor, and proof gate/decision exist. |
| `acp:Requirement` | ACP requirement contract. | Cannot be validated from projection shape alone. |
| `acp:Decision` | ACP/GSD/ADR decision records and selected `lex:Decision` prior art. | Accepted decision must have tracked anchor and scope. |
| `acp:EvidenceAnchor` | M048/M049 durable anchor rules. | Repository-relative tracked paths only; no local ignored/raw/secret anchors. |
| `acp:ProofGate` | M048/M055 proof-gate matrix. | Executable or checkable gate; placeholder gate is not proof. |
| `acp:HealthFinding` | M048 lifecycle/health model; M055 diagnostics. | Diagnostic only; cannot close requirements alone. |
| `acp:Projection` | RDF/TTL/SHACL/SPARQL/JSON-LD outputs. | Derived unless tied back to accepted source/proof machinery. |
| `acp:LifecycleState` | active, validated, deferred, blocked, rejected, superseded. | State transition requires evidence/proof policy. |
| `acp:AuthorityClass` | Source/projection/runtime-smoke/diagnostic classes. | Prevents shape/prose/projection authority imitation. |
| `acp:ValidationClaim` | Explicit validation records. | Must link requirement + proof gate + accepted evidence. |
| `acp:ProfileConstraint` | M049 reusable core/profile boundary. | law-nexus profile owns legal/parser/FalkorDB/retrieval claims. |
| `acp:RuntimeAdapter` | M053-M055 adapter boundary. | Optional diagnostic process, not ACP core runtime by default. |

## ACP-kit and law-nexus profile split

ACP-kit v0 should be reusable ACP core. It should not hard-code law-nexus legal proof as ACP core ontology.

Reusable ACP core may define:

```text
source records, lifecycle states, evidence anchors, proof gates, health findings, projections, validation claims, authority classes, runtime adapter boundaries
```

law-nexus profile must own:

```text
Russian legal evidence, Garant parser proof, FalkorDB runtime/ingest proof, retrieval quality, citation safety, generated-Cypher safety, R035/R037/R038 substantive validation
```

ACP-kit may include `ProfileConstraint` as a generic concept and may include sample warnings for R035/R037/R038, but it must not validate those requirements from ACP/git-lex/projection evidence alone.

## Relationship to L2 operational diagnostics

ACP-kit should feed L2, not bypass it.

K4 L2 integration should use ACP-kit-aware diagnostics only after K1-K3 prove the kit shape. Required L2 evidence remains:

- regular ACP workflow invocation;
- retention/compaction/indexing policy for diagnostics;
- failure-state persistence;
- retry behavior;
- fail-closed behavior;
- no main `.lex` residue;
- non-authoritative diagnostic classification;
- bounded query IDs and output schemas.

## Blocked and rejected paths preserved

These remain blocked after the corrected roadmap:

```text
main repository .lex approval
ACP source-truth migration
production runtime readiness
release/plugin-bundled binary trust
JSON-LD git-lex runtime support
broad SPARQL-star/RDF-star parity
raw/session/provider payload proof anchors
R035/R037/R038 validation from ACP-kit/git-lex/projection evidence
Russian legal evidence correctness
Garant ODT parser completeness
FalkorDB runtime behavior
```

These remain rejected by default:

```text
Raw/session logs as ACP proof anchors
unbounded arbitrary SPARQL pass-through
git lex save/create/raw backfill/join/kit-update/nuke as ACP-safe operations without dedicated isolated rehearsal and explicit decision
projection-as-source-truth wording
```

## Future milestone recommendation

After M049 closes, create a dedicated milestone:

```text
ACP-kit v0 over git-lex-kit-base
```

Suggested slices:

1. `K1/S01 Base and domain kit inspection` — inspect base/squad/soul/autoknow kit mechanics and record exact ACP-kit format.
2. `K1/S02 ACP ontology extraction` — convert M051/S08 prototype into `acp.ttl` without M051-specific prototype markers.
3. `K1/S03 ACP-kit package scaffold` — create kit.yml, content/ACP folders, README/AGENTS guidance, and static examples.
4. `K1/S04 Static verifier and skill update` — verify ontology/classes/folders/authority boundaries without runtime claims.
5. `K2/S01 Isolated runtime proof` — in a disposable workspace, prove init/sync/list/query/validate with ACP-kit and no main-state residue.
6. `K3/S01 Binding projection fixture` — represent M049 binding records through ACP-kit examples and verify no overclaiming.
7. `K4 planning slice` — decide whether ACP-kit evidence is enough to start L2 operational diagnostics.

## Safe claim language

Safe:

```text
ACP-kit is the next semantic integration step: a git-lex-compatible kit that packages ACP core source/proof/projection vocabulary while preserving ACP-native authority.
```

Safe:

```text
M055 proves git-lex can continue as L1 shadow diagnostics; ACP-kit v0 should define the semantic contract used before L2 operational diagnostics.
```

Unsafe:

```text
ACP-kit makes git-lex the ACP source of truth.
```

Unsafe:

```text
ACP-kit validates R035/R037/R038 or law-nexus legal/FalkorDB/parser behavior.
```

Unsafe:

```text
Because ACP-kit exists, main `.lex` can be initialized in law-nexus.
```
