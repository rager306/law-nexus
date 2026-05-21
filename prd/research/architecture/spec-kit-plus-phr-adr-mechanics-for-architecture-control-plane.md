# spec-kit-plus PHR and ADR Mechanics for a Reusable Architecture Control Plane

## Status

Source-backed research for M035-775l5y / S02.

This artifact analyzes `panaversity/spec-kit-plus` as a source of reusable prompt provenance and ADR discipline for a portable Architecture Control Plane (ACP). `law-nexus` is the first project profile and proving ground, but the reusable ACP core must remain project-independent.

## Source inventory

Local vendor source was cloned outside this repository and indexed with GitNexus:

| Source | Local reference | Commit | GitNexus repo |
| --- | --- | --- | --- |
| `panaversity/spec-kit-plus` | vendor source outside this repo | `3f6fe49` | `spec-kit-plus-reference` |

Primary source files inspected:

| File | Why it matters |
| --- | --- |
| `templates/phr-template.prompt.md` | Defines PHR frontmatter and body fields: prompt, response snapshot, outcome, tests, files, evaluation notes. |
| `templates/adr-template.md` | Defines ADR structure and embedded significance checklist. |
| `scripts/bash/create-phr.sh` | Implements deterministic PHR routing, ID allocation, slugging, template copy, and JSON metadata output. |
| `scripts/bash/create-adr.sh` | Implements deterministic ADR directory, ID allocation, slugging, template copy, and JSON metadata output. |
| `protocol-templates/AGENTS.md` | Defines agent rules for PHR capture, routing, ADR suggestion, consent, and architecture planning discipline. |
| `templates/commands/phr.md` | Defines explicit PHR command workflow and placeholder filling. |
| `templates/commands/adr.md` | Defines ADR review workflow, clustering rules, significance tests, conflict checks, and completion reporting. |
| `CHANGELOG.md` | Documents PHR routing evolution and rationale for predictable prompt locations. |

Search terms used against local source included: `PHR`, `Prompt History`, `ADR`, `Architectural decision`, `decision significance`, `create-phr`, `create-adr`, `history/prompts`, and `history/adr`.

## Executive summary

`spec-kit-plus` contributes a second essential ACP dimension that `git-lex` alone does not fully cover: **decision provenance**.

Where `git-lex` provides typed Git-native knowledge, ontology, validation, and queryable graph mechanics, `spec-kit-plus` provides a disciplined workflow for capturing:

1. what the user asked;
2. what stage the request belonged to;
3. what the assistant did;
4. which files and tests were involved;
5. which evaluation notes or graders mattered;
6. when an architecture decision deserves an ADR rather than remaining a prompt-history note.

The transferable ACP pattern is:

```text
Prompt / intent
  -> Prompt History Record
  -> Architecture Proposal
  -> ADR candidate or Architecture Decision
  -> Proof Gate
  -> Implementation / verification binding
  -> Health and recovery views
```

The key adoption stance is **adapt, do not copy literally**. `spec-kit-plus` is useful because it makes provenance and ADR creation deterministic, but its rule to preserve every user input verbatim must be adapted for ACP safety. A reusable ACP should preserve enough prompt context for audit and recovery while redacting secrets, provider payloads, and other project-prohibited material.

## PHR model

### Template shape

`templates/phr-template.prompt.md` defines YAML frontmatter with:

- `id`
- `title`
- `stage`
- `date`
- `surface`
- `model`
- `feature`
- `branch`
- `user`
- `command`
- `labels`
- links to `spec`, `ticket`, `adr`, and `pr`
- `files`
- `tests`

The body contains:

- `Prompt`
- `Response snapshot`
- `Outcome`
- `Evaluation notes (flywheel)`

ACP transferable mechanics:

- PHRs are first-class provenance records, not chat logs hidden in agent memory.
- PHR frontmatter provides a machine-readable bridge from user intent to later decisions, proof gates, files, and tests.
- `Response snapshot` is intentionally concise and recoverable; it avoids requiring future agents to replay the whole conversation.
- `Evaluation notes` are directly useful for ACP health and prompt-quality feedback loops.

ACP adaptation:

- Rename or generalize PHR to `ArchitecturePromptRecord` in ACP core.
- Preserve links to proposals, decisions, proof gates, health findings, and project work units.
- Add safety metadata such as `redaction_status`, `contains_secret: false`, `contains_raw_provider_payload: false`, and `profile_policy_checked: true`.

### Routing and stages

`create-phr.sh` routes PHRs under `history/prompts/`:

| Stage class | Route | Notes |
| --- | --- | --- |
| `constitution` | `history/prompts/constitution/` | Project principles and standards. |
| Feature stages | `history/prompts/<feature>/` | `spec`, `plan`, `tasks`, `red`, `green`, `refactor`, `explainer`, `misc`. |
| `general` | `history/prompts/general/` | Catch-all non-feature context. |

The changelog explains why this matters: consistent feature directory names across branch, specs, and prompts reduce confusion and make automation simpler.

ACP transferable mechanics:

- Prompt records need deterministic routing.
- Routing should encode work context.
- Names should be predictable and sortable.
- Feature or work-unit names should match the rest of the project.

ACP adaptation:

A reusable ACP should not require the SDD terms `spec`, `plan`, and `tasks`, but it should support comparable architecture stages:

- `constitution`
- `intake`
- `research`
- `proposal`
- `decision`
- `proof`
- `implementation`
- `verification`
- `health`
- `recovery`
- `general`

A GSD adapter can map these to milestone, slice, and task context. A non-GSD project can map them to branches, issues, or plain work units.

### Deterministic creation script

`create-phr.sh` performs only scaffold mechanics:

1. validates title and stage;
2. resolves repository root;
3. locates the template;
4. determines route;
5. creates directory;
6. allocates next local numeric ID;
7. slugifies title and stage;
8. copies template with placeholders intact;
9. returns JSON metadata with ID, path, context, stage, feature, and template.

The script intentionally does **not** fill semantic content. The calling agent fills placeholders.

ACP transferable mechanics:

- Artifact identity and location should be deterministic.
- Creation should be dumb and inspectable.
- Semantic filling and validation should be separate steps.
- JSON metadata return is useful for agent workflows.

ACP adaptation:

- ACP should implement `create-record` or `create-prompt-record` with the same split: scaffold first, fill second, validate third.
- ACP should prefer repo-relative paths in durable outputs, even if scripts internally resolve absolute paths.
- ACP must fail if unresolved placeholders remain after filling.

### PHR command workflow deep dive

`templates/commands/phr.md` is more than a template wrapper. It defines a complete provenance workflow:

1. execute the user request first if it has not already been handled;
2. determine stage and routing;
3. run the creation script with title, stage, optional feature, and JSON output;
4. fill every frontmatter and body placeholder;
5. report the created PHR path, stage, feature, file count, and test count.

The command explicitly states that the complete user input is the prompt to preserve and warns not to truncate it. It also requires outcome fields, response summary, files, tests, failure modes, grader results, and next experiment.

Transferable ACP mechanics:

- A prompt/provenance record should be created **after work is complete enough to summarize outcome**, not before the agent understands the result.
- Provenance is not only the prompt text; it includes files, tests, outcome, failure modes, grader results, and next experiment.
- The command treats PHR as a learning and audit artifact, not only as chat transcript storage.
- Placeholder completion is a validation obligation: unresolved placeholders mean the record is not complete.
- The report format is recovery-friendly: ID, path, stage, feature, modified files, and tests involved.

ACP adaptation:

- ACP should keep the outcome/evaluation model but make prompt capture fidelity profile-controlled.
- ACP should introduce `capture_mode` and `redaction_status` so the same core works in open-source, enterprise, legal, and security-sensitive projects.
- ACP should link prompt records to `ArchitectureProposal`, `DecisionCandidate`, `ArchitectureDecision`, and `ProofGate`, not only to spec/ticket/ADR/PR.
- ACP should treat missing files/tests/evaluation fields as a health warning when the prompt produced architecture state.

## ADR model

### Template shape

`templates/adr-template.md` defines:

- title: `ADR-{{ID}}: {{TITLE}}`
- status: `Proposed | Accepted | Superseded | Rejected`
- date
- feature
- context
- decision
- positive and negative consequences
- alternatives considered
- references to feature spec, implementation plan, related ADRs, and evaluator evidence

It also includes a significance checklist:

1. Impact: long-term consequence for architecture, platform, or security?
2. Alternatives: multiple viable options considered with tradeoffs?
3. Scope: cross-cutting concern, not isolated detail?

If any are false, it recommends capturing the matter as a PHR note instead of an ADR.

ACP transferable mechanics:

- ADRs should be reserved for consequential decisions.
- Alternatives and consequences are required, not optional decoration.
- Evaluator evidence or PHR links should connect the ADR to provenance.
- Related decisions must be linkable.

ACP adaptation:

ACP needs a richer architecture lifecycle than the spec-kit-plus ADR template:

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

The spec-kit-plus ADR statuses map into ACP but do not cover proof and implementation states fully.

### ADR command workflow

`templates/commands/adr.md` defines a six-step workflow:

1. load planning context;
2. extract architectural decisions as clusters;
3. check existing ADRs;
4. apply significance test;
5. create ADRs;
6. report completion.

Important mechanics:

- ADRs should document decision clusters, not individual technology choices.
- Existing ADRs must be checked before creating new ones.
- Conflicts with existing ADRs must be flagged.
- Candidates must pass all three significance checks.
- The command requires alternatives, pros, cons, and references.

ACP transferable mechanics:

- ACP should include a `decision-candidate` state before creating or accepting a decision.
- ACP should check for existing decisions and supersession/conflict before creating a new ADR.
- ACP should prefer clustered decisions over over-granular decisions.
- ACP health checks should flag missing alternatives, missing consequences, and unlinked evidence.

ACP adaptation:

For reusable ACP, the significance test should be expanded:

| Criterion | Meaning |
| --- | --- |
| Impact | Long-term effect on architecture, platform, process, security, or proof boundaries. |
| Alternatives | Multiple viable options or explicit reason no alternative exists. |
| Scope | Cross-cutting or likely to influence future work. |
| Proof burden | Changes what evidence is required before claims can be made. |
| Supersession risk | Replaces or constrains an earlier decision. |
| Agent drift risk | Future agents are likely to diverge if the decision is not explicit. |

An ACP ADR should usually be required when at least Impact, Scope, and one of Proof burden / Supersession risk / Agent drift risk are present. Project profiles may make this stricter.

### ADR command workflow deep dive

`templates/commands/adr.md` defines the ADR command as an architecture review workflow, not a blind file generator. The command starts from planning artifacts and asks the agent to:

1. load planning context and required docs;
2. extract architectural decisions as **decision clusters**;
3. check existing ADRs before creating new records;
4. classify each candidate with significance tests;
5. create and fill ADRs only for qualifying clusters;
6. report created ADRs, referenced existing ADRs, conflicts, and next steps.

The command also includes a lightweight Analyze -> Measure -> Improve flywheel:

- Analyze likely failure modes, especially over-granular ADRs and missing alternatives.
- Measure candidates with a checklist: clustered decision, alternatives, pros/cons, concise but sufficient detail.
- Improve by creating only ADRs that pass the checks and linking back to plan/research/data artifacts.

Transferable ACP mechanics:

- ADR generation should be **review-driven**, not automatic record creation.
- Existing architecture decisions must be scanned before creating new decisions.
- Conflicts are first-class outputs, not hidden editorial notes.
- Decision clustering is a governance rule: avoid one ADR per library or micro-choice when the real decision is a coupled architectural cluster.
- ADR commands should produce structured completion output that future agents can parse into health state.

ACP adaptation:

- Replace feature-only planning context with generic ACP context: prompt records, proposals, proof gates, requirements, source anchors, and existing decisions.
- Convert conflict detection into typed relationships: `conflictsWith`, `supersedes`, `blockedBy`, or `requiresDecision`.
- Add profile-aware significance checks. For law-nexus, decisions touching proof boundaries, legal authority, parser completeness, FalkorDB ingestion, or LLM authority must be treated as high-significance even if they do not change code immediately.
- Add status discipline: the command may create a `DecisionCandidate` or `proposed` decision, but it must not silently create `accepted` or `verified` doctrine.

### Deterministic ADR creation

`create-adr.sh` performs only scaffold mechanics:

1. validates title;
2. resolves repository root;
3. creates `history/adr/`;
4. locates template;
5. computes next four-digit ID;
6. slugifies title;
7. copies template;
8. returns JSON metadata.

ACP transferable mechanics:

- ADR creation should be deterministic and scriptable.
- The script should not decide content or status by itself.
- The agent should fill placeholders, then validation should check completeness.

ACP adaptation:

- ACP should create typed decision records, not just prose ADR files.
- ACP should support `ArchitectureDecision` as both human-readable markdown and machine-readable frontmatter.
- ACP should distinguish `candidate`, `proposed`, `accepted`, and `verified` transitions instead of making creation imply adoption.

## Agent rules and consent boundary

`protocol-templates/AGENTS.md` contains two important governance rules:

1. PHRs are created automatically and accurately for every user prompt.
2. ADR suggestions are made intelligently for significant decisions, but ADRs are never auto-created without user consent.

For ACP, this suggests a useful split:

| Record | Can agent create automatically? | Requires human/project consent for accepted status? |
| --- | --- | --- |
| Prompt provenance | Yes, subject to safety filtering. | No, unless policy says otherwise. |
| Decision candidate | Yes, as a candidate/proposal. | Yes before `accepted`. |
| Accepted architecture decision | No, unless explicit project policy grants authority. | Yes. |
| Verified decision | No. | Requires proof gate evidence. |

This is critical for reusable ACP. A system may let an agent draft records, but it should not silently convert architectural judgment into accepted doctrine.

## Reusable ACP core implications

The generic ACP core should adopt these mechanics:

### Core provenance records

- `ArchitecturePromptRecord`
- `ArchitectureDiscussionRecord`
- `ArchitectureProposal`
- `DecisionCandidate`
- `ArchitectureDecision`
- `ProofGate`
- `EvaluationRecord`

### Core provenance relationships

- `prompted`
- `summarizedBy`
- `producedProposal`
- `suggestedDecision`
- `acceptedAs`
- `linkedToDecision`
- `linkedToProofGate`
- `referencesFile`
- `referencesTest`
- `hasEvaluationNote`

### Core creation workflow

1. scaffold typed record deterministically;
2. fill required fields;
3. validate no placeholders remain;
4. validate source links and safety fields;
5. extract into graph or registry;
6. update status and health reports.

### Core health checks

- prompt record missing stage;
- prompt record missing outcome;
- prompt record missing links to generated decision/proposal when one exists;
- accepted decision missing provenance;
- decision candidate passing significance test but not resolved;
- ADR missing alternatives;
- ADR missing consequences;
- ADR conflicts with existing active decision;
- accepted decision without proof gate;
- verified decision without evidence.

## Adapter implications

| Adapter | Role |
| --- | --- |
| Plain CLI adapter | Create prompt records, decision candidates, ADRs, and proof gates without requiring spec-kit-plus. |
| GSD adapter | Create or update provenance records around milestone/slice/task work. |
| git-lex adapter | Represent provenance and decision records as typed dot-notation Markdown records. |
| CI adapter | Validate unresolved placeholders, broken links, missing alternatives, and unsafe prompt capture. |
| Visualization adapter | Show provenance-to-decision chains without treating them as proof. |

The ACP core should not depend on spec-kit-plus scripts. It should adopt their mechanics and expose compatible adapter behavior.

## law-nexus profile implications

The law-nexus profile should be stricter than spec-kit-plus defaults:

- Do not persist secrets, API keys, raw provider payloads, or irrelevant debug dumps.
- Do not require verbatim persistence of every user input when safety boundaries require redaction or summarization.
- Do not store raw legal text unless it is necessary and intentionally scoped.
- Mark external AI dialogue as context-only, not authoritative evidence.
- Preserve boundaries for R035, R037, and R038.
- Do not treat PHRs or ADRs as proof of parser completeness, legal correctness, graph ingestion, retrieval quality, or production readiness.
- Require proof gates before `verified` status.

This means ACP should adapt the spec-kit-plus PHR rule from:

```text
record every user input verbatim
```

to:

```text
record architecture-relevant user intent with enough fidelity for provenance, after mandatory safety filtering and profile policy checks
```

For projects that need strict audit trails and can satisfy safety requirements, a profile may choose stronger verbatim capture. The reusable ACP core should support both modes through profile policy.

## Relationship to git-lex mechanics

S01 established git-lex mechanics as the target model for typed Git-native ACP records. S02 adds provenance discipline:

| Need | git-lex contribution | spec-kit-plus contribution |
| --- | --- | --- |
| Typed source records | Dot-notation Markdown | PHR and ADR templates |
| Validation | SHACL / kit shapes | Placeholder, routing, significance, and artifact completeness discipline |
| Queryability | SPARQL graph | Links from prompts to ADRs, files, tests, and evaluation notes |
| Governance | save / validate / pre-commit | consent boundary and decision significance test |
| Recovery | queryable graph | prompt-to-decision history |

Together, they support a reusable ACP where architecture state is not just valid, but also explainable.

## Risks and gaps

### Risk 1: prompt history becomes noisy

If ACP records every trivial message, future recovery views may drown in low-value records. The core should support profile rules for architecture-relevant capture thresholds, while still allowing stricter audit profiles.

### Risk 2: unsafe verbatim capture

Spec-kit-plus emphasizes verbatim prompt capture. ACP must not copy this blindly. Profiles need redaction and exclusion rules.

### Risk 3: ADR creation without authority boundary

Spec-kit-plus protects against this by requiring user consent. ACP should preserve the principle: agents may draft candidates, but accepted architectural doctrine requires explicit authority or project policy.

### Risk 4: ADR over-granularity

ACP should adopt the cluster rule: decisions that move together should usually be documented together.

### Risk 5: provenance mistaken for proof

A prompt record can explain why a decision exists, but it does not prove the decision works. ACP must separate provenance, decision, implementation, and verification.

## First proof recommendations

A first ACP vertical slice should include provenance, not only decisions:

1. Define a minimal `ArchitecturePromptRecord` schema.
2. Define a minimal `ArchitectureDecision` or `DecisionCandidate` schema.
3. Create one prompt record for the request to build a reusable ACP.
4. Create one decision candidate or proposed decision linked to that prompt record.
5. Create one proof gate linked to the decision.
6. Validate all placeholders are filled.
7. Generate a recovery view that shows: prompt -> proposal -> decision candidate -> proof gate -> current status.
8. Confirm law-nexus profile can redact or summarize unsafe prompt content while preserving provenance.

## Conclusion

`spec-kit-plus` provides a mature provenance workflow that complements the git-lex mechanics from S01. Its most transferable ideas are deterministic PHR creation, stage-aware routing, metadata-rich prompt records, ADR significance tests, clustered ADRs, and explicit consent before creating accepted architecture decisions.

For reusable ACP, these ideas should become generic provenance and decision-candidate mechanics. For `law-nexus`, they must be adapted through a stricter profile that prevents unsafe prompt capture and preserves proof-boundary discipline.

## Verification notes

This artifact is research and design evidence only. It does not validate law-nexus parser completeness, legal correctness, FalkorDB ingestion, retrieval quality, R035, R037, or R038. It does not make PHRs, ADRs, external AI dialogue, or generated views authoritative proof.
