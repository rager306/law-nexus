# M056 S01 Base and Domain Kit Inspection

## Status

Completed for `M056-wjtuag / S01` inspection closure.

This artifact records source-inspected git-lex kit mechanics before ACP-kit v0 files are created. S01 is inspection only: it does not initialize main `.lex`, does not run runtime proof, and does not approve ACP source-truth migration.

## Scope boundaries

- ACP-kit v0 is a deterministic semantic-kit scaffold, not source truth.
- Runtime git-lex proof begins only in later isolated proof work.
- Main checkout `.lex`, `Squad`, `Raw`, and `.artifacts` must remain absent.
- R035/R037/R038 are not validated by kit shape, ontology, projection, or inspection evidence.
- law-nexus legal/parser/FalkorDB/retrieval proof remains profile-owned.

## T01 Base kit inspection

### Source inspected

Local reference checkout inspected outside this repository:

```text
git-lex-kit-base
```

This vendor checkout is inspection input only, not a durable ACP proof anchor. The durable tracked anchor for this inspection is this repository artifact.

Files inspected:

```text
kit.yml
ontology/lex/lex.ttl
ontology/git/git.ttl
ontology/fm/fm.ttl
content/.claude/CLAUDE.md
content/.gitkeep
harness/.gitkeep
www/css/main.css
www/index.html
www/js/main.js
```

The local checkout also contains normal `.git/` files. Those are repository metadata, not kit content.

### kit.yml mechanics

`git-lex-kit-base/kit.yml` contains:

```yaml
name: base
install folders: false
```

Interpretation for ACP-kit:

- `name` identifies the kit as `base`.
- `install folders: false` means the base kit ships shared ontologies and UI assets but does not create domain content folders.
- ACP-kit should not mutate base; ACP-kit should be a separate domain kit that depends on base vocabulary concepts.

### Base ontology files

Base ships three system ontology files:

| File | Namespace | Evidence from source | ACP-kit implication |
|---|---|---|---|
| `ontology/lex/lex.ttl` | `lex:` | Describes git-lex built-in ontology: upper ontology types, extraction features, generic relationships, and provenance properties. Comments state it is loaded into every repo regardless of kit. | ACP-kit can subclass or align to `lex:Document`, `lex:Decision`, `lex:Reference`, `lex:Process`, `lex:Information`, `lex:Concept`, and relationship properties. This is vocabulary evidence, not ACP authority. |
| `ontology/git/git.ttl` | `git:` | Defines git object classes/properties such as `git:Commit`, `git:Actor`, `git:Blob`, `git:Reference`, `git:Branch`, `git:Tag`, `git:Changeset`, and commit/file properties. | ACP-kit can use git provenance vocabulary for observed commits or source anchors where appropriate. Git vocabulary does not validate ACP records by itself. |
| `ontology/fm/fm.ttl` | `fm:` | Defines common frontmatter predicates such as `fm:path`, `fm:title`, `fm:tags`, `fm:status`, `fm:author`, `fm:date`, `fm:project`, and `fm:technologies`; comments say unknown frontmatter keys still work as predicates. | ACP-kit may use frontmatter fields for lightweight metadata, but validation still needs ACP proof gates and tracked anchors. |

### Base content and web assets

The base kit contains:

```text
content/.claude/CLAUDE.md
content/.gitkeep
harness/.gitkeep
www/css/main.css
www/index.html
www/js/main.js
```

Interpretation:

- Base includes optional content/harness/web surfaces even though it does not install domain folders.
- Web/UI assets are diagnostic or user-facing support surfaces only; they are not ACP source truth.
- ACP-kit v0 may include content guidance such as `content/AGENTS.md`, but should avoid raw/session payload folders and should not claim UI/browser surfaces as authority.

### What base proves

Base proves these source-level facts for ACP-kit planning:

- A kit can be configured with `name` and `install folders` fields.
- The base kit is ontology/UI oriented and does not install domain folders.
- `lex:`, `git:`, and `fm:` are available vocabulary inputs for ACP-kit design.
- ACP-kit should be a domain kit over base rather than a mutation of base.

### What base does not prove

Base inspection does not prove:

- ACP-kit runtime behavior;
- `git-lex init/sync/list/query/validate` success with ACP-kit;
- JSON-LD git-lex runtime support;
- broad SPARQL-star support;
- main `.lex` safety;
- ACP source-truth migration;
- production readiness;
- R035/R037/R038 validation;
- law-nexus legal/parser/FalkorDB/retrieval/citation/generated-Cypher proof.

## T01 conclusion

Base kit evidence supports the M049/S05 decision that ACP-kit v0 should be a separate deterministic domain kit over `git-lex-kit-base`. The base kit itself should remain vocabulary prior art and shared system ontology input, not ACP authority or runtime adoption proof.

## T01 handoff

T02 should inspect `git-lex-kit-squad`, `git-lex-kit-soul`, and `git-lex-kit-autoknow` to verify domain kit mechanics: `install folders`, `folder base`, `folder ontology`, ontology location, content conventions, generated shapes, and adaptive mutation behavior.

## T02 Domain kit inspection

### Source inspected

Local reference checkouts inspected outside this repository:

```text
git-lex-kit-squad
git-lex-kit-soul
git-lex-kit-autoknow
```

These vendor checkouts are inspection inputs only, not durable ACP proof anchors. The durable tracked anchor for this inspection is this repository artifact.

### Package mechanics summary

| Kit | `kit.yml` mechanics | Ontology file | Content and harness mechanics | ACP-kit implication |
|---|---|---|---|---|
| `squad` | `name: squad`; `install folders: true`; `folder base: Squad`; `folder ontology: squad.ttl` | `ontology/squad/squad.ttl` | `content/AGENTS.md`; seeded `content/Squad/Squaddie/squadling.md`; Claude harness guidance and `squadling-check` skill; `www/.gitkeep`. | Domain kits can install class folders from ontology and ship agent guidance plus optional harness support. ACP-kit can use the domain-kit pattern but must not import Squad identity, peer messaging, or ontology-janitor authority. |
| `soul` | `name: soul`; `install folders: true`; `folder base: Soul`; `folder ontology: soul.ttl`; `init_prompts: agent_name` | `ontology/soul/soul.ttl` | `content/AGENTS.md`; `content/Raw/README.md`; raw mirror folders; soul skills; Claude session-start hook and listener prior art. | Domain kits can ask initialization prompts and ship harness-specific workflows. ACP-kit v0 should not inherit `Raw/` or byte-faithful session mirroring because raw payloads are unsafe ACP anchors. |
| `autoknow` | `name: autoknow`; `adaptive: true`; `install folders: true`; `folder base: AutoKnow`; `folder ontology: autoknow.ttl` | `ontology/autoknow/autoknow.ttl` | `content/AGENTS.md`; `content/AutoKnow/Source/`; `content/AutoKnow/Entity/`; `_autoknow` subagent prompts for extractor, ontologist, and entity writer. | AutoKnow proves an adaptive-kit pattern exists, but ACP-kit v0 should reject `adaptive: true` as default because ACP ontology mutation needs a separate authority, review, rollback, and proof-gate policy. |

### Squad kit details

`squad` is a shared multi-agent coordination kit. Its ontology defines 12 document classes in the inspected source summary:

```text
Squaddie, Message, Decision, Discovery, Brief, Task, Project, Pod, Proclamation, Situation, Freeform, Bug
```

It also defines many object/datatype properties and enum datatypes for statuses, priorities, outcomes, confidence, bug severity, and related coordination metadata. The source comments state that constraints are encoded in the ontology and that SHACL shapes are generated from the ontology rather than hand-edited.

Safe ACP-kit lessons:

- Use `install folders: true` when a domain kit needs content folders generated from ontology classes.
- Use `folder base` to choose the installed content root.
- Use `folder ontology` to name the domain ontology file consumed for class-folder generation.
- Ship model-agnostic agent guidance in `content/AGENTS.md` when future agents need boundary instructions.
- Treat generated SHACL shapes as derivative verifier surfaces, not ACP source truth.

Rejected for ACP-kit v0:

- Do not create `Squad` folders or squad identities in the main law-nexus checkout.
- Do not import peer messaging or squad ontology-janitor authority into ACP core.
- Do not treat squad generated shapes as proof that ACP source records are valid.

### Soul kit details

`soul` is a personal/agent memory kit. Its ontology defines 17 document classes in the inspected source summary:

```text
Soul, Memory, Decision, Task, Exploration, Friend, Journal, Note, Skill, Subagent, Mantra, Habit, Resource, Creation, Interest, Texture, Dream
```

`soul` extends the domain-kit package pattern with `init_prompts`, currently `agent_name`, and ships rehydration guidance, skills, a listener, and raw mirror documentation. The raw mirror docs explicitly describe byte-faithful `Raw/` copies of session files, machine-local state, and harness session JSONL mirroring.

Safe ACP-kit lessons:

- `init_prompts` can parameterize generated content during initialization.
- A domain kit can ship agent-facing operational instructions and optional harness helpers.
- Memory/decision/task classes provide structural prior art for durable record categories, but they do not define ACP authority.

Rejected for ACP-kit v0:

- Do not include `Raw/` folders, byte-faithful session payload copies, or machine-local mirror state in ACP-kit.
- Do not use raw harness logs, provider payloads, local paths, or session JSONL as ACP proof anchors.
- Do not use soul rehydration or identity mechanics as law-nexus ACP governance authority.

### AutoKnow kit details

`autoknow` is an automated knowledge-organization kit. Its inspected `kit.yml` is explicitly adaptive:

```yaml
adaptive: true
```

The kit comments state that ontology seeds to `_ontology/`, is owned and edited by AutoKnow subagents at runtime, and that SHACL shapes regenerate from `_ontology/` on every `git lex save`. Its ontology defines only two initial classes:

```text
Source, Entity
```

The source and agent prompts describe a pipeline:

1. Wrap raw input documents as `AutoKnow/Source/*.md`.
2. Extract candidate entities and typed relationships with a subagent.
3. Let an Ontologist subagent canonicalize classes/properties and edit `_ontology/autoknow/autoknow.ttl`.
4. Let an EntityWriter subagent create entity pages under class folders.
5. Save and query the resulting graph.

The AutoKnow docs label output as best-effort and subagent-produced. They also state that classes emerge from extraction rather than being predefined.

Safe ACP-kit lessons:

- Adaptive ontology mutation is a real git-lex kit pattern, but it is a separate runtime governance model.
- Provenance-per-line and source/entity separation are useful concepts for future ACP diagnostics, if bounded by ACP source/proof rules.
- Subagent-generated extraction output must be classified as diagnostic/proposed until reviewed.

Rejected for ACP-kit v0:

- Do not set `adaptive: true` for ACP-kit v0.
- Do not let subagents own or edit ACP core ontology at runtime.
- Do not treat generated entities, SPO sidecars, or adaptive SHACL regeneration as ACP authority.
- Do not use raw input documents, unreviewed extraction, or generated entity descriptions as validation evidence for R035/R037/R038.

### Cross-kit mechanics learned

The inspected domain kits show these package mechanics:

- `name` is the kit identifier.
- `install folders: true` is used by domain kits that create content folders.
- `folder base` names the installed root folder for generated class folders.
- `folder ontology` names the ontology TTL file used for folder/shape generation.
- `init_prompts` can collect initialization variables, as shown by `soul`.
- `adaptive: true` changes ontology ownership: the ontology is copied into a runtime `_ontology/` area and edited by agents, with shapes regenerated from that mutable copy.
- Domain ontologies encode document classes, properties, enum datatypes, and restrictions; generated shapes are derived from ontology source.
- The inspected domain ontologies use `lex-o:` as their upper-ontology prefix, while the inspected base `lex.ttl` describes `lex-o` as a historical/open-world naming area. ACP-kit v0 should not silently normalize this; S03/S05 must either follow proven current kit conventions or verify runtime compatibility in isolation.
- `content/AGENTS.md` is the common model-agnostic instruction surface.
- Harness-specific guidance can exist, but ACP-kit v0 should keep harness behavior out of ACP core.

### T02 conclusion

Domain kit evidence supports an ACP-kit v0 package with domain-kit mechanics, not base-kit mechanics alone. The safe default is deterministic and non-adaptive:

```yaml
name: acp
install folders: true
folder base: ACP
folder ontology: acp.ttl
```

Rejected default:

```yaml
adaptive: true
```

`adaptive: true` should remain out of ACP-kit v0 until a separate ACP authority policy defines who can mutate ACP ontology, how changes are reviewed, how rollback works, and what proof gate makes adaptive output acceptable.

## T02 handoff

T03 should synthesize final ACP-kit packaging defaults from T01 and T02: deterministic `kit.yml`, `folder base: ACP`, `folder ontology: acp.ttl`, ontology path, content guidance, examples, no `Raw/`, no main `.lex`, no source-truth migration, and no R035/R037/R038 validation claim.

## T03 ACP-kit packaging defaults

### Default package identity

ACP-kit v0 should be a separate deterministic domain kit over `git-lex-kit-base`.

Recommended `kit.yml` contract for S03 scaffold work:

```yaml
# git-lex ACP kit
# Deterministic ACP core semantic kit. Derived/non-authoritative until ACP proof gates accept specific records.

name: acp
install folders: true
folder base: ACP
folder ontology: acp.ttl
```

Required omissions:

```text
adaptive: true
init_prompts
Raw/
Squad/
Soul/
AutoKnow/
.lex/
```

Rationale:

- `name: acp` follows observed kit identifiers (`base`, `squad`, `soul`, `autoknow`).
- `install folders: true` follows domain kits that install class folders from ontology.
- `folder base: ACP` keeps ACP documents in an ACP-specific domain root if runtime proof later installs folders in an isolated workspace.
- `folder ontology: acp.ttl` follows domain kit conventions and keeps the domain ontology name stable.
- No `adaptive: true`: ACP ontology mutation needs a separate authority/review/rollback/proof policy.
- No `init_prompts`: ACP-kit v0 should be static and reusable, not tied to local actor identity or machine prompts.

### Expected scaffold layout for S03

S03 should create tracked package files under an ACP-kit source location chosen during scaffold work. The expected internal shape is:

```text
kit.yml
ontology/acp/acp.ttl
content/AGENTS.md
content/ACP/.gitkeep
www/.gitkeep
```

Optional examples may be added only if they are tracked, synthetic, non-authoritative, and clearly labeled as examples:

```text
content/ACP/SourceRecord/example-source-record.md
content/ACP/Decision/example-decision.md
content/ACP/ProofGate/example-proof-gate.md
```

S03 should avoid:

```text
content/Raw/**
content/Squad/**
content/Soul/**
content/AutoKnow/**
content/_autoknow/**
harness hooks that mutate state
runtime-generated shapes as source records
ignored/local validation bundles
```

### Ontology path and namespace defaults

S02 should extract ACP ontology classes from M051/S08 into a deterministic ontology file for S03:

```text
ontology/acp/acp.ttl
```

Recommended namespace:

```text
@prefix acp: <https://legalgraph.example/ontology/acp/> .
```

The exact IRI may be adjusted in S02/S03 if an existing ACP namespace is found in tracked source artifacts, but the namespace must remain ACP-core reusable and must not encode law-nexus profile proof as ACP core authority.

Upper-ontology alignment rule:

- Prefer following the current proven git-lex domain-kit convention if runtime proof requires it.
- Do not silently rewrite `lex-o:` to `lex:` only because base comments describe historical naming.
- If S03 chooses `lex:` or `lex-o:`, the choice must be recorded and S05 must verify runtime compatibility in isolation before any runtime claim.

### Content guidance defaults

`content/AGENTS.md` should explain ACP-kit boundaries for future agents:

- ACP-kit is derived semantic packaging, not ACP source truth.
- An ACP validation claim needs source category, lifecycle state, tracked evidence anchor, and proof gate or accepted decision.
- Projections, generated shapes, RDF/OWL/SPARQL/JSON-LD, dashboards, and diagnostics are derived unless tied to accepted ACP proof machinery.
- Main `.lex`, `Squad`, `Raw`, source-truth migration, and production/provenance adoption remain blocked.
- R035/R037/R038 remain profile-owned and cannot be validated by ACP-kit or git-lex projection evidence.
- Durable anchors must be tracked repository-relative paths; no absolute local paths, GSD exec outputs, ignored artifacts, raw payloads, secrets, or raw vectors.

### Example defaults

If S03 creates example ACP records, they should be synthetic and marked as examples. They may demonstrate field shape but must not claim validation.

Required safe example wording:

```text
This example is synthetic ACP-kit shape evidence only. It is not an accepted ACP source record, not validation evidence, and not proof for R035/R037/R038.
```

Example records should include only portable tracked references such as:

```text
prd/architecture/acp/M049-S05-FINAL-BINDING-SYNTHESIS.md
prd/architecture/acp/M049-S05-GIT-LEX-ACP-KIT-INTEGRATION-ROADMAP.md
```

They must not include:

```text
absolute local filesystem paths
GSD exec output paths
ignored local artifact paths
raw/session payload paths
secret or provider payload references
```

### Rejected alternatives

| Alternative | Status | Why rejected for v0 |
|---|---|---|
| Base-only kit with `install folders: false` | Rejected | ACP-kit needs domain ACP folders/examples for package proof; base-only mechanics are insufficient. |
| `adaptive: true` ACP-kit | Rejected | Would delegate ACP ontology mutation to runtime/subagents without accepted authority, review, rollback, or proof gates. |
| Soul-derived ACP kit | Rejected | Soul identity/Raw/session mechanisms are unsafe ACP anchors and not governance authority. |
| Squad-derived ACP kit | Rejected | Squad coordination/peer messaging/ontology janitor mechanics are not ACP source truth. |
| AutoKnow-derived ACP kit | Rejected | AutoKnow is best-effort subagent extraction with adaptive ontology mutation; useful prior art only. |
| Main checkout runtime proof | Rejected for S03 and S04 | Runtime proof must be isolated in S05 and must preserve no main `.lex`, `Squad`, `Raw`, or `.artifacts` residue. |
| ACP-kit as source-truth migration | Rejected | Source-truth migration is K6 and remains blocked until separate design and proof. |

### S02/S03 handoff contract

S02 should extract ACP core ontology content without changing these packaging defaults unless source evidence invalidates them.

S03 should scaffold ACP-kit v0 according to this contract and then run static checks that confirm:

- `kit.yml` has `name: acp`, `install folders: true`, `folder base: ACP`, and `folder ontology: acp.ttl`.
- `kit.yml` does not contain `adaptive: true`.
- No `Raw`, `Squad`, `Soul`, `AutoKnow`, or main `.lex` paths are scaffolded.
- All example anchors are tracked repository-relative paths.
- Every example validation phrase is explicitly non-authoritative.
- R035/R037/R038 remain unvalidated.

## T03 conclusion

The final S01 packaging default is a deterministic non-adaptive ACP domain kit with `folder base: ACP` and `folder ontology: acp.ttl`. ACP-kit v0 should package reusable ACP core semantics only; it must not import law-nexus profile proof, raw/session evidence, adaptive ontology mutation, main checkout runtime state, or source-truth migration claims.

## T03 handoff

T04 should verify S01 closure with focused scans for package fields, rejected alternatives, unsafe anchors, forbidden validation claims, main-state residue, and diff hygiene before closing the slice.
