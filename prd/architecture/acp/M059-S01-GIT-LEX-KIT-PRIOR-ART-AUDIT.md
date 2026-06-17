# M059/S01: Git-lex kit prior-art audit

## Status

Prior-art audit complete. This artifact classifies existing git-lex kits before any law-nexus-kit implementation work.

## Scope and authority boundary

This audit uses local kit source inspection as runtime observation. It does not create law-nexus-kit, does not change external repositories, does not initialize or mutate main `.lex`, does not approve ACP-kit or git-lex source-truth migration, does not approve production adoption, and does not validate R035, R037, or R038.

The target layering hypothesis remains:

```text
git-lex -> base-kit -> acp-kit -> law-nexus-kit
```

Interpretation:

```text
engine -> repository/frontmatter substrate -> reusable governance core -> law-nexus profile evidence projection
```

This is a semantic packaging and diagnostic projection hierarchy, not an authority hierarchy.

## Kit inventory

### base-kit

Observed structure:

```text
name: base
install folders: false
ontology: fm, git, lex
content folders: none beyond minimal support content
```

Ontology pattern:

```text
fm: frontmatter datatype properties
lex: generic semantic/document/process concepts
git: commit/blob/file/reference/change concepts with stronger domain/range coverage
```

Important finding:

```text
base-kit is substrate, not domain. It should be treated as required mechanics for repository, file, git, and frontmatter facts.
```

S01 classification:

```text
Reuse for mechanics and substrate conventions.
Do not copy as ACP or law-nexus domain authority.
```

### squad-kit

Observed structure:

```text
name: squad
install folders: true
folder base: Squad
folder ontology: squad.ttl
content includes AGENTS guidance and class folders
```

Ontology pattern:

```text
12 domain classes
object and datatype properties with many rdfs:domain and rdfs:range declarations
several enum-like owl:oneOf values
```

Representative domain shape:

```text
Squaddie, Message, Decision, Discovery, Brief, Task, Project, Pod, Proclamation, Situation, Freeform, Bug
```

Important finding:

```text
squad-kit is the best reusable pattern for a simple deterministic domain kit: class folders, frontmatter examples, guidance, and domain ontology with domains/ranges.
```

S01 classification:

```text
Reuse the deterministic domain scaffold pattern.
Use caution with agent/squad memory semantics because law-nexus evidence must remain profile proof, not agent memory authority.
```

### soul-kit

Observed structure:

```text
name: soul
install folders: true
folder base: Soul
folder ontology: soul.ttl
init prompts exist
content includes AGENTS guidance, Raw folder, Soul class folders, and harness logic
```

Ontology pattern:

```text
17 domain classes
many datatype properties with rdfs:domain and rdfs:range
several enum-like owl:oneOf values
```

Representative domain shape:

```text
Soul, Memory, Decision, Task, Exploration, Friend, Journal, Note, Skill, Subagent, Mantra, Habit, Resource, Creation, Interest, Texture, Dream
```

Important finding:

```text
soul-kit shows how a domain kit can package rich personal/agent memory semantics and initialization prompts, but it also carries Raw/session/harness patterns that are unsafe as ACP proof anchors by default.
```

S01 classification:

```text
Caution. Reuse only narrow domain-folder and rich ontology lessons. Block Raw/session/harness authority assumptions for law-nexus-kit v0.
```

### autoknow-kit

Observed structure:

```text
name: autoknow
adaptive: true
install folders: true
folder base: AutoKnow
folder ontology: autoknow.ttl
content includes AutoKnow folders and internal subagent guidance
```

Ontology pattern:

```text
minimal Source and Entity model
datatype properties with rdfs:domain and rdfs:range
enum-like owl:oneOf values
```

Representative domain shape:

```text
Source, Entity
```

Important finding:

```text
autoknow-kit is valuable prior art for Source/Entity extraction concepts, but its adaptive ontology mutation and subagent-owned schema behavior are not safe defaults for law-nexus ACP proof work.
```

S01 classification:

```text
Reuse conceptual Source/Entity modeling ideas only.
Block adaptive ontology mutation, runtime schema ownership, and extraction-subagent-as-authority patterns for law-nexus-kit v0.
```

### ACP-kit

Tracked project scaffold:

```text
git-lex-kit-acp/kit.yml
git-lex-kit-acp/ontology/acp/acp.ttl
git-lex-kit-acp/content/AGENTS.md
```

Observed structure:

```text
name: acp
install folders: true
folder base: ACP
folder ontology: acp.ttl
deterministic ACP core semantic kit
derived/non-authoritative until ACP proof gates accept specific records
```

Ontology pattern:

```text
12 ACP classes
object properties for proof/evidence/lifecycle/profile/runtime relationships
datatype properties for identifiers, source paths, selectors, non-authoritative flags, proof levels, verdicts, and blocked actions
few rdfs:domain declarations in the current generated-shape-relevant form
```

Representative governance shape:

```text
SourceRecord, Requirement, Decision, EvidenceAnchor, ProofGate, HealthFinding, Projection, LifecycleState, AuthorityClass, ValidationClaim, ProfileConstraint, RuntimeAdapter
```

Important finding from M058:

```text
ACP-kit currently supports positive runtime/query diagnostic behavior, but generated ACP shapes are underconstrained for hard validation. Strengthening requires domains/restrictions or generator changes plus true negative runtime proof.
```

S01 classification:

```text
Reuse as governance core.
Do not put law-nexus profile terms in ACP core.
Do not use ACP-kit/git-lex validation as a hard proof gate yet.
```

## Reuse caution blocked matrix

| Pattern | Source kit prior art | Classification | law-nexus-kit implication |
|---|---|---|---|
| `kit.yml` with `name`, `install folders`, `folder base`, `folder ontology` | base, squad, soul, autoknow, ACP | Reuse | law-nexus-kit should use a deterministic `kit.yml` with explicit folder base and ontology file. |
| Domain class folders under a kit-specific root | squad, soul, autoknow, ACP | Reuse | Use `LawNexus/...` class folders for examples and future records. |
| Frontmatter-backed examples | squad, soul, autoknow, ACP | Reuse | Provide synthetic non-authoritative examples only. |
| rdfs:domain and rdfs:range on domain properties | squad, soul, autoknow | Reuse | Add domains/ranges from v0 so generated shapes can become useful. |
| Enum-like `owl:oneOf` values | squad, soul, autoknow, ACP | Caution | Useful only if generated shapes and validation behavior are proven. |
| Source/Entity minimal model | autoknow | Caution | Adapt conceptually for legal source/evidence modeling, but keep deterministic and proof-gated. |
| Rich memory/session semantics | soul | Caution | Useful for inspiration only; not proof authority. |
| Init prompts | soul | Caution | Avoid in v0 unless a later proof shows prompts do not create authority or reproducibility ambiguity. |
| Raw folders or raw/session payload mirroring | soul and git-lex harness prior art | Blocked | Do not include raw legal text, provider payloads, session logs, or Raw folders in law-nexus-kit v0. |
| Adaptive ontology mutation | autoknow | Blocked | No adaptive schema changes or runtime-owned ontology in law-nexus-kit v0. |
| Subagent extraction as authority | autoknow | Blocked | Extraction can be prior art, but law-nexus validation requires ACP proof gates and real source/runtime evidence. |
| ACP profile requirement validation from projection | not safe in any kit | Blocked | law-nexus-kit must not validate R035/R037/R038 by itself. |

## Recommended law-nexus-kit v0 pattern

Use a small deterministic profile/domain kit:

```text
name: law-nexus
install folders: true
folder base: LawNexus
folder ontology: law-nexus.ttl
adaptive: absent
init_prompts: absent
Raw/session folders: absent
```

Candidate v0 classes should remain profile-evidence oriented:

```text
LegalDocument
SourceProvider
ParserRun
SourceBlock
EvidenceSpan
Citation
RetrievalQuery
RetrievalAnswer
FalkorDBGraph
CypherSafetyCheck
```

Candidate relationship direction:

```text
law-nexus evidence records may support or observe ACP proof gates,
but ACP proof gates and accepted decisions remain the validation authority.
```

Safe examples:

```text
LawNexus/LegalDocument/example-legal-document.md
LawNexus/ParserRun/example-parser-run.md
LawNexus/EvidenceSpan/example-evidence-span.md
```

Each example must be marked synthetic and non-authoritative.

## Blocked in law-nexus-kit v0

```text
adaptive ontology mutation
Raw folders
session logs
provider payloads
raw legal text blobs
absolute local anchors
source-truth migration
production adoption claims
R035/R037/R038 validation claims
main checkout .lex initialization
```

## Implication for S02 layering mechanics

S01 does not prove native kit dependency behavior. It only shows the desired architecture and prior-art patterns.

S02 must answer:

```text
Does git-lex install or compose kit dependencies natively?
Can law-nexus-kit import or include ACP ontology terms safely?
Will generated shapes include imported or cross-kit properties?
Should law-nexus-kit be a standalone explicit kit with static imports rather than a runtime dependency chain?
```

Until S02 proves mechanics, treat:

```text
git-lex -> base-kit -> acp-kit -> law-nexus-kit
```

as an architectural layering hypothesis, not a proven runtime inheritance chain.

## S01 conclusion

Existing git-lex kits provide useful prior art, but not a template to copy wholesale.

Safe direction:

```text
base mechanics + squad deterministic domain scaffold + autoknow Source/Entity intuition + ACP governance boundary
```

Blocked direction:

```text
soul/autoknow Raw, session, harness, adaptive, or subagent-authority patterns as law-nexus proof machinery
```

The next step is S02 layering mechanics proof before creating law-nexus-kit v0 scaffold.
