# git-lex Mechanics for a Reusable Architecture Control Plane

## Status

Source-backed research for M035-775l5y / S01.

This artifact analyzes `git-lex` as a candidate technical and conceptual backbone for a reusable Architecture Control Plane (ACP). `law-nexus` is treated as the first project profile and proving ground, not as the only target project.

## Source inventory

Local vendor sources were cloned outside this repository and indexed with GitNexus:

| Source | Local reference | Commit | GitNexus repo |
| --- | --- | --- | --- |
| `repolex-ai/git-lex` | vendor source outside this repo | `9606bee` | `git-lex-reference` |
| `repolex-ai/git-lex-kit-squad` | vendor source outside this repo | `3298b9a` | `git-lex-kit-squad-reference` |

Primary source files inspected:

| File | Why it matters |
| --- | --- |
| `README.md` | Declares the public git-lex model: Markdown content, `.lex/` tracked index, `.git/lex/` derived store, kits, save, sync, query. |
| `src/main.rs` | Contains `cmd_save`, `cmd_validate`, `hook_pre_commit`, `cmd_extract`, and command orchestration. |
| `src/extraction.rs` | Contains `frontmatter_to_turtle`, mapping typed frontmatter to Turtle for SHACL validation. |
| `src/nquad.rs` | Contains `generate_frontmatter_nquads`, `.spo` sidecar and current-state graph extraction mechanics. |
| `src/shacl.rs` | Contains `generate_shacl_shapes` and `build_shacl_shapes`. |
| `docs/2026_04_08_KITS_DESIGN.md` | Defines the kit layering model: ontology, use-case assets, harness adapters, agent content. |
| `docs/2026_04_21_SHACL_OWL_LOSSLESS_SUBSET.md` | Defines the SHACL/OWL subset git-lex expects and the boundary between node validation and broader reasoning. |
| `docs/2026_04_04_MARKDOWN_TO_RDF_IDENTITY_SPEC.md` | Defines markdown-as-instance, dot notation, IRI identity, and source-of-truth chain. |
| `ontology/git-lex/lex/lex.ttl` | Built-in upper ontology for cross-kit categories, including `lex:Decision`. |
| `ontology/squad/squad.ttl` from git-lex-kit-squad | Example kit ontology with `squad:Decision`, lifecycle-like outcome values, required fields, and generated SHACL shapes. |

GitNexus context calls used:

| Symbol | Repo | Finding |
| --- | --- | --- |
| `cmd_save` | `git-lex-reference` | Called by `main`; calls `resolve_agent_identity` and `harness::sync`; participates in save flows. |
| `generate_shacl_shapes` | `git-lex-reference` | Called by `build_shacl_shapes`; calls kit resolution and kit TTL loading. |
| `frontmatter_to_turtle` | `git-lex-reference` | Called by `cmd_validate`; maps frontmatter into Turtle using kit namespace, ObjectProperty, and datatype metadata. |
| `generate_frontmatter_nquads` | `git-lex-reference` | Called by `cmd_extract`, `cmd_sync`, and `main`; writes `.spo` and current graph N-Quads from markdown/frontmatter/wikilinks. |

## Executive summary

`git-lex` provides a strong model for the reusable ACP core:

1. **Git-native typed knowledge**: normal Markdown files are source records, not generated blobs.
2. **Frontmatter as machine contract**: dot notation `kit.class.property` provides typed fields without hiding human-readable prose.
3. **Ontology or kit as schema authority**: kits define valid classes and properties for a use case.
4. **Derived graph projection**: `.lex/` extraction artifacts and `.git/lex/` Oxigraph store are projections from tracked source records.
5. **Validation gate**: SHACL validation runs over extracted typed records before accepting a save or commit path.
6. **Query surface**: SPARQL queries make the knowledge state recoverable and navigable.
7. **Separation of kit, harness, and content**: the kit design explicitly separates use-case definition from runtime adapters and agent-created content.

These mechanics align with the target ACP goal: a portable architecture construction system where decisions, prompts, proof gates, health findings, and project profiles are typed Git records that can be validated, queried, visualized, and recovered by agents.

The correct adoption stance is **design commitment, proof-gated implementation**. `git-lex` ideas should be central to the ACP contract, but direct use of the `git lex` binary in the main `law-nexus` repo should remain behind a controlled vertical-slice proof gate.

## Mechanics map

### 1. Markdown source as RDF instance

`docs/2026_04_04_MARKDOWN_TO_RDF_IDENTITY_SPEC.md` defines the core identity model:

| Markdown concept | RDF concept |
| --- | --- |
| Markdown file | RDF instance |
| Kit | Ontology namespace |
| Class | `rdf:type` |
| YAML frontmatter | Properties |
| Markdown body | Description or prose for the instance |

The design phrase that matters for ACP is: **the file is the thing**. For ACP, this means:

- `ArchitectureDecision` should be a tracked Markdown file.
- `PromptHistoryRecord` should be a tracked Markdown file.
- `ProofGate` should be a tracked Markdown file.
- `ArchitectureHealthFinding` or health report records can be tracked when they represent accepted diagnostic state, while dashboards remain derived.

### 2. Dot notation frontmatter

The same design spec defines flat frontmatter keys:

```yaml
acp.architectureDecision.id: AD-0001
acp.architectureDecision.status: accepted
acp.architectureDecision.supersedes: AD-0000
```

`src/extraction.rs::frontmatter_to_turtle` implements the pattern for git-lex: it looks for keys matching `kit.class.property`, infers document type from the class segment, and emits RDF properties. It uses kit metadata to decide whether values are object references or typed/plain literals.

ACP implication:

- Generic core records should use a stable namespace such as `acp.*`.
- Project profiles should extend core with profile namespaces, for example `ln.*` for law-nexus-specific claim boundaries.
- Profile keys must not be required for generic core validity.

### 3. Save flow

`src/main.rs::cmd_save` performs:

1. find git root;
2. resolve agent identity from environment or `.claude/settings.json`;
3. sync harness assets;
4. `git add -A`;
5. commit with explicit author;
6. rely on hooks for extraction and validation.

ACP transferable mechanics:

- Save is not just file write. It is a controlled transition through staging, extraction, validation, and commit.
- Agent identity is part of provenance.
- Harness sync is an adapter concern, not a core schema concern.

ACP adaptation:

- ACP core should define record lifecycle and validation requirements.
- GSD adapter may call ACP validation during task or slice completion.
- A future `git-lex` adapter may delegate save and query behavior to `git lex save` and `git lex query`.
- A plain CLI adapter can initially implement smaller create/validate/status commands without requiring the whole git-lex binary.

### 4. Pre-commit extraction and validation

`src/main.rs::hook_pre_commit` runs:

1. `cmd_extract()`;
2. stages `.lex/extract/`;
3. runs `cmd_validate()`;
4. exits non-zero on validation failure.

This is the central ACP pattern: architecture state changes must become extractable and valid before they are accepted.

ACP adaptation:

- Architecture record changes should be blocked if extraction or validation fails.
- Health failures should distinguish blocking failures from advisory warnings.
- For law-nexus, the existing `uv run python scripts/verify-architecture-graph.py` remains the canonical current verifier until an ACP validator supersedes it through proof.

### 5. Frontmatter and sidecar extraction

`src/nquad.rs::generate_frontmatter_nquads` walks Markdown and text files, extracts YAML frontmatter and wikilinks, writes `.spo` sidecars under `.lex/extract/`, and emits N-Quads for a current-state graph.

Important mechanics:

- Hidden directories are skipped during content walking.
- The current graph is explicitly distinguished from historical sync graphs.
- File path and git blob hash are included as provenance.
- Wikilinks are captured as relationships.
- Classes come from explicit ontology/frontmatter, not folder guessing.

ACP adaptation:

- A portable ACP should not infer architecture record types from folder names alone.
- Each record should carry explicit type and status.
- Each record should include repo-relative evidence anchors and optional blob/commit provenance.
- Wikilinks or explicit relation fields can power ADR chains and impact navigation.

### 6. Validation flow

`src/main.rs::cmd_validate`:

1. locates configured kit;
2. collects kit SHACL shapes and adaptive `_ontology` shapes;
3. walks Markdown files;
4. converts matching frontmatter to Turtle with `frontmatter_to_turtle`;
5. validates per file using SHACL tooling;
6. reports counts and non-conforming files.

Important boundary:

- If no kit or no shapes are configured, validation can be skipped.
- Shape parse failures are reported but currently may return success in some branches. A reusable ACP should be stricter for architecture governance.

ACP adaptation:

- ACP validation must fail closed for architecture-control records.
- Missing schema or profile config should be a blocker, not a pass.
- Validation output should become a structured health report with categories, not just stderr text.

### 7. SHACL generation from kit ontology

`src/shacl.rs::generate_shacl_shapes` loads kit TTL, discovers prefix and namespace, and generates shapes. `build_shacl_shapes` writes generated shapes next to the source TTL.

`docs/2026_04_21_SHACL_OWL_LOSSLESS_SUBSET.md` states that git-lex uses a limited SHACL subset:

- class identification;
- property declarations;
- IRI versus literal;
- typed literals;
- required fields;
- enum values.

It also states the crucial boundary:

> SHACL is per-node, OWL is per-graph.

ACP adaptation:

- Core ACP validation can use SHACL/schema for per-record shape and required fields.
- Cross-record checks such as supersession cycles, proof-gate coverage, stale references, and active conflicts must be application-layer health rules, not assumed to fall out of SHACL alone.
- Project-specific overclaim rules must live in profile health rules.

### 8. Kit layering

`docs/2026_04_08_KITS_DESIGN.md` defines four layers:

1. **Ontology**: use-case definition, TTL, SHACL, class templates.
2. **Use-case assets**: files prescribed by the kit.
3. **Harness adapters**: runtime-specific glue for Claude or other agents.
4. **Agent content**: records produced by agents while using the kit.

This is directly transferable to reusable ACP:

| git-lex layer | ACP equivalent |
| --- | --- |
| Ontology | ACP core schema/ontology and optional project profile schema. |
| Use-case assets | Templates, docs, command descriptions, status view contracts. |
| Harness adapters | GSD adapter, git-lex adapter, plain CLI adapter, visualization adapter. |
| Agent content | Decisions, proposals, PHRs, proof gates, health findings. |

This layering is the strongest argument for making ACP externalizable. The `law-nexus` profile must live outside core, just as a kit use case is separate from harness adapters and generated content.

### 9. Upper ontology and squad decision model

`ontology/git-lex/lex/lex.ttl` defines stable upper categories including `lex:Decision`, described as a recorded choice with context and rationale.

`git-lex-kit-squad/ontology/squad/squad.ttl` defines `squad:Decision` as a subclass of `lex-o:Decision`, with fields including:

- `decisionId`;
- `decidedBy`;
- `alternatives`;
- `rationale`;
- `outcome` with values `pending`, `implemented`, `reverted`, `superseded`;
- `supersededBy`.

This is close to ACP needs but not sufficient by itself. ACP needs additional architecture-governance semantics:

- proposal versus accepted decision;
- proof gate links;
- requirement bindings;
- allowed and blocked next actions;
- explicit claim boundaries;
- health finding categories;
- project profile rules.

Transferable conclusion:

- ACP can model `ArchitectureDecision` as a specialized decision record inspired by `squad:Decision`.
- ACP should not copy `squad:Decision` unchanged as the only decision model.
- A future `architecture-control-kit` can import or align with `lex:Decision` and optionally reuse squad concepts where appropriate.

## Reusable ACP core implications

The generic ACP core should define domain-independent records and rules:

### Core record types

- `ArchitecturePromptRecord`
- `ArchitectureProposal`
- `ArchitectureDecision`
- `ArchitectureConstraint`
- `ProofGate`
- `EvidenceAnchor`
- `RequirementBinding`
- `ArchitectureHealthFinding`
- `ArchitectureStateSnapshot`
- `ArchitectureView`

### Core relationships

- `derivedFrom`
- `proposes`
- `acceptedAs`
- `supersedes`
- `supersededBy`
- `dependsOn`
- `conflictsWith`
- `validatedBy`
- `blockedBy`
- `implements`
- `affects`
- `requiresProof`
- `allowsAction`
- `blocksAction`

### Core lifecycle states

A portable ACP should define a generic lifecycle that works across projects:

- `captured`
- `researched`
- `proposed`
- `accepted`
- `implemented`
- `verified`
- `superseded`
- `rejected`
- `blocked`
- `deferred`

### Core validation categories

- schema shape failure;
- missing required field;
- invalid source anchor;
- unknown record type;
- invalid status transition;
- broken relationship target;
- supersession cycle;
- accepted decision without proof gate;
- verified decision without validation evidence;
- stale derived projection;
- generated view treated as source.

## Adapter implications

ACP should be reusable because adapters are separated from core:

| Adapter | Role | Should be optional? |
| --- | --- | --- |
| Plain CLI adapter | Create, validate, status, health over typed records. | Yes, useful before git-lex adoption. |
| git-lex adapter | Use `git lex` kit, validate, sync, query, and possibly save. | Yes, central target but proof-gated. |
| GSD adapter | Tie ACP lifecycle into milestone, slice, and task completion. | Yes, law-nexus uses it first. |
| Visualization adapter | Export derived graph to dashboard, Mermaid, GraphML, or Understand-Anything. | Yes, non-authoritative. |
| CI adapter | Run validation and health checks in external repositories. | Yes, needed for reuse. |

The core must not require GSD. GSD is one execution harness, not the architecture system itself.

## Project profile implications

The law-nexus profile should extend core with project-specific rules:

- R035 must not be validated from documentation-only evidence.
- R037 must not be treated as validated by graph-context staging.
- R038 must not be treated as validated by internal review packs.
- Legal-answer correctness claims need separate legal evidence proof.
- Parser completeness claims need parser proof over the relevant source family.
- FalkorDB ingestion claims require actual runtime ingestion proof.
- MiniMax remains non-authoritative.
- GPT-5.5 remains external review/control, not runtime judge.
- Consultant XML and Garant ODT evidence must not be conflated.

These rules must not be embedded in the generic ACP core. They belong in `law-nexus` profile policy.

## Risks and gaps

### Risk 1: direct git-lex adoption before profile design

Running `git lex init` in the main law-nexus repository would create `.lex/` and possibly tracked sidecars before the ACP record model is settled. This should be done only in an isolated proof workspace or after a specific adoption decision.

### Risk 2: confusing generated graph with source of truth

`git-lex` explicitly separates source Markdown, `.lex/` tracked extraction artifacts, and `.git/lex/` derived store. ACP must preserve this boundary. Dashboards, JSONL, RDF stores, SPARQL answers, and generated reports are derived views unless explicitly promoted by policy.

### Risk 3: SHACL overclaim

SHACL can validate per-record shape and required fields, but it does not by itself solve lifecycle logic, proof sufficiency, or project-specific overclaim safety. ACP needs application-layer health rules.

### Risk 4: prompt provenance safety

Future ACP prompt records should borrow spec-kit-plus PHR mechanics, but law-nexus and reusable ACP must avoid saving secrets, raw provider payloads, and unnecessary raw legal text.

### Risk 5: identity and harness coupling

`cmd_save` currently has Claude-related identity fallback and harness sync behavior. ACP should keep agent identity as provenance but avoid hard-coding one harness into core.

## First proof recommendations

A first ACP vertical slice should dogfood the model without adopting all of git-lex at once:

1. Define a minimal ACP core schema for `ArchitectureDecision`, `ArchitecturePromptRecord`, and `ProofGate`.
2. Create one typed decision record: adopt a reusable git-lex-inspired ACP as the target architecture-construction model.
3. Create one prompt record linking the user request to the decision candidate.
4. Create one proof gate requiring static validation and state recovery.
5. Build a minimal extractor/status command that outputs current decisions, open proof gates, blocked actions, and profile warnings.
6. In an isolated workspace, test whether the same records can be represented as git-lex-compatible dot-notation frontmatter and queried through `git lex`.

The main repo should only adopt `.lex/` after this proof shows:

- typed records validate;
- query/recovery is useful;
- generated artifacts are safely bounded;
- GSD can consume the state without context drift;
- law-nexus profile rules remain outside generic core.

## Conclusion

`git-lex` supplies the strongest available model for the reusable ACP backbone: Git-native typed Markdown records, kit-defined schemas, SHACL validation, derived queryable graph state, and clean kit versus harness versus content layering.

For this project, the design target should be a reusable `architecture-control-kit` plus adapters and profiles, not law-nexus-only scripts. `law-nexus` should be the first profile and proving ground. Direct `git lex` binary adoption should be proof-gated, but the ACP contract should be git-lex-inspired from the beginning.

## Verification notes

This artifact is research and design evidence only. It does not validate law-nexus parser completeness, legal correctness, FalkorDB ingestion, retrieval quality, R035, R037, or R038. It does not make external AI dialogue or generated graph views authoritative.
