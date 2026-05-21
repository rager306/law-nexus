# Reusable Architecture Control Plane Contract — Research Synthesis

**Date:** 2026-05-21

## Status

Source-backed synthesis for `M035-775l5y / S04`.

This artifact defines a reusable Architecture Control Plane (ACP) contract. `law-nexus` is the first profile and proving ground, but the core contract is designed to be externalizable to other repositories.

This is a design contract, not an implementation proof. It does not validate parser completeness, legal correctness, FalkorDB ingestion, graph-vector retrieval quality, production readiness, independent external review, R035, R037, or R038.

## Summary

The ACP is a Git-native governance layer for constructing, recovering, and verifying architecture state. It answers:

- What is the current architectural position?
- Why did the architecture thread start?
- Which proposals, decision candidates, ADRs, proof gates, and health findings exist?
- Which decisions are accepted, rejected, superseded, blocked, or verified?
- Which next actions are allowed or blocked by policy and proof state?
- Which generated views are stale, incomplete, contradictory, or overclaiming?

The ACP combines four source-backed inputs:

1. **git-lex mechanics** — typed Markdown/frontmatter records, ontology/kit discipline, SHACL-style validation, RDF/SPARQL-style projection, and rebuildable derived stores.
2. **spec-kit-plus PHR/ADR mechanics** — prompt provenance, deterministic record creation, stage-aware routing, decision significance tests, ADR clustering, and consent boundary for accepted decisions.
3. **Spec Architect rubric** — proposal quality checklist: scope, dependencies, interfaces, NFRs, data, ops, risks, validation, and ADR candidates. The specific README-referenced prompt file was not present in the cloned source, so this contract uses available source-backed command/protocol analogs rather than treating a missing prompt as evidence.
4. **Understand-Anything visualization mechanics** — derived dashboard/recovery graph, graph validation issue surfaces, path sanitization, local-token dashboard safety, guided tours, search, diff overlays, and copyable diagnostics.

GSD remains the execution/proof adapter: it already provides milestone/slice/task state, requirements, decisions, summaries, verification evidence, reassessment, and gate results. ACP should not duplicate GSD. ACP should define architecture state and governance; GSD should execute and record work against that state.

## Source-backed inputs

| Slice | Artifact | Contribution |
| --- | --- | --- |
| S01 | `prd/research/architecture/git-lex-mechanics-for-architecture-control-plane.md` | Typed Git-native records, ontology/kit model, SHACL-style validation, RDF/query projection, derived stores, validation hooks. |
| S02 | `prd/research/architecture/spec-kit-plus-phr-adr-mechanics-for-architecture-control-plane.md` | PHR as provenance, ADR command workflow, decision clusters, significance gates, safety-filtered prompt capture, deterministic scaffolding. |
| S03 | `prd/research/architecture/understand-anything-visualization-fit-for-architecture-control-plane.md` | Derived visualization/recovery graph, warning model, path-safety patterns, dashboard adapter requirements, non-authoritative view boundary. |
| Existing project architecture | `prd/09_architecture_planning_verification_research.md`, `prd/architecture/README.md`, architecture registry scripts, GSD artifacts | law-nexus source-of-truth hierarchy, verifier contract, proof-level discipline, derived registry/report boundary. |

## Non-goals

ACP does not:

- replace GSD milestone/slice/task execution;
- replace project requirements management;
- replace source code tests or runtime proof;
- replace human/project authority for accepted architecture decisions;
- make LLM output authoritative;
- make visual graphs authoritative;
- validate legal correctness;
- validate parser completeness;
- validate FalkorDB ingestion;
- validate graph-vector retrieval quality;
- validate R035, R037, or R038 from documentation/provenance/visualization alone.

## Source-of-truth hierarchy

The ACP contract preserves a strict source hierarchy:

1. **Authoritative source evidence**
   - human-confirmed ADRs or architecture decisions;
   - PHR/provenance records for intent and origin, not proof;
   - project requirements;
   - GSD milestone/slice/task plans and summaries;
   - source code and tests;
   - runtime smoke/integration/real-document evidence;
   - tracked PRD or design docs.
2. **ACP typed records**
   - Markdown/frontmatter records that represent provenance, proposals, candidates, decisions, proof gates, evidence anchors, and health findings.
3. **Validated projections**
   - JSONL registries, RDF/N-Quads, graph reports, dashboard JSON, SPARQL/query indexes, generated recovery views.
4. **Diagnostics and visualizations**
   - verifier output, dashboard warnings, drift reports, issue banners, graph layouts, guided tours.
5. **External AI or dialogue context**
   - context only unless independently converted into an accepted decision with source anchors and proof gates.

Derived stores are rebuildable. If a derived store conflicts with source records, source records win and the derived store is stale or faulty.

## Core record types

### `ArchitecturePromptRecord`

Purpose: capture architecture-relevant prompt/intent provenance.

Required fields:

- `id`
- `record_kind: architecture_prompt_record`
- `title`
- `stage`
- `date`
- `profile`
- `surface`
- `capture_mode`
- `redaction_status`
- `user_intent`
- `response_snapshot`
- `outcome`
- `links`
- `source_refs`
- `policy_checked`

Allowed capture modes:

- `verbatim`
- `redacted-verbatim`
- `summarized-with-quotes`
- `metadata-only`

Core rule: preserve enough intent for recovery, after mandatory profile policy and safety filtering.

PHR does not prove a decision. It explains why an architecture thread entered the system.

### `ArchitectureProposal`

Purpose: structured proposal produced from prompt/research/planning.

Required fields:

- `id`
- `record_kind: architecture_proposal`
- `title`
- `status`
- `scope`
- `non_goals`
- `dependencies`
- `interfaces`
- `nfrs`
- `data_or_state_impacts`
- `operational_impacts`
- `risks`
- `validation_plan`
- `adr_candidates`
- `source_refs`

Spec Architect rubric applies here. A proposal is incomplete unless each rubric field is present or explicitly marked not applicable with rationale.

### `DecisionCandidate`

Purpose: significant architecture decision under review.

Required fields:

- `id`
- `record_kind: decision_candidate`
- `title`
- `status`
- `origin_prompt_record`
- `origin_proposal`
- `cluster`
- `significance`
- `alternatives`
- `consequences_positive`
- `consequences_negative`
- `conflicts`
- `supersession_candidates`
- `required_proof_gates`
- `authority_required`

Decision candidates may be created by agents. They are not accepted decisions.

### `ArchitectureDecision`

Purpose: accepted, rejected, or superseded architecture doctrine.

Required fields:

- `id`
- `record_kind: architecture_decision`
- `title`
- `status`
- `accepted_by` or `rejected_by` when applicable
- `date`
- `decision`
- `rationale`
- `alternatives`
- `consequences`
- `supersedes`
- `superseded_by`
- `source_refs`
- `provenance_refs`
- `proof_gate_refs`
- `revisable`

Accepted decisions require explicit authority or project policy. Verified decisions require matching proof gates.

### `ProofGate`

Purpose: define what evidence is required before claims can be upgraded.

Required fields:

- `id`
- `record_kind: proof_gate`
- `claim`
- `required_evidence_class`
- `accepted_evidence_refs`
- `status`
- `blocks`
- `verifier_command`
- `failure_mode`
- `owner_profile`

Proof gates separate provenance and decision from implementation and verification.

### `EvidenceAnchor`

Purpose: point to bounded proof or source material.

Required fields:

- `id`
- `record_kind: evidence_anchor`
- `path`
- optional `line_range`
- `evidence_class`
- `claim_supported`
- `limitations`
- `source_role`

Durable anchors should be repository-relative and must not point to ignored local-only files or secrets. `.gsd/exec` is not suitable as a long-term registry anchor.

### `ArchitectureHealthFinding`

Purpose: record drift, overclaim, contradiction, missing evidence, unsafe provenance, or blocked action.

Required fields:

- `id`
- `record_kind: architecture_health_finding`
- `severity`
- `category`
- `finding`
- `affected_records`
- `blocked_actions`
- `recommended_fix`
- `detected_by`
- `status`

Health findings are first-class ACP state, not throwaway logs.

## Lifecycle model

### Prompt/provenance lifecycle

```text
captured -> policy_checked -> linked -> superseded_or_archived
```

A prompt record can be policy-checked and linked to proposals or decisions, but it does not become proof.

### Proposal lifecycle

```text
draft -> complete -> candidate_extracted -> closed
```

A proposal is complete only after the Spec Architect rubric is satisfied.

### Decision lifecycle

```text
candidate -> proposed -> accepted | rejected | deferred | superseded -> implemented -> verified
```

Important constraints:

- `candidate` can be agent-created.
- `accepted` requires authority.
- `implemented` requires mapped work evidence.
- `verified` requires proof-gate evidence.
- `superseded` requires successor coverage.

### Proof gate lifecycle

```text
defined -> blocking -> evidence_submitted -> passed | failed | waived_with_authority
```

Waivers must be explicit and must not validate unavailable runtime/legal/parser proof.

### Health lifecycle

```text
open -> acknowledged -> remediated -> verified_closed
```

Health findings can block next actions.

## Relationship model

ACP core relationships:

| Relationship | Source | Target | Meaning |
| --- | --- | --- | --- |
| `producedProposal` | `ArchitecturePromptRecord` | `ArchitectureProposal` | Prompt/provenance produced proposal. |
| `suggestedDecision` | `ArchitectureProposal` | `DecisionCandidate` | Proposal contains a decision candidate. |
| `acceptedAs` | `DecisionCandidate` | `ArchitectureDecision` | Candidate promoted by authority. |
| `rejectedAs` | `DecisionCandidate` | `ArchitectureDecision` | Candidate explicitly rejected. |
| `requiresProof` | `ArchitectureDecision` or `DecisionCandidate` | `ProofGate` | Decision cannot be verified without gate. |
| `verifiedBy` | `ProofGate` | `EvidenceAnchor` | Evidence supports gate result. |
| `referencesFile` | any ACP record | `EvidenceAnchor` | Record references source/proof file. |
| `conflictsWith` | decision/proposal/health | decision/proposal | Conflict requires resolution. |
| `supersedes` | `ArchitectureDecision` | `ArchitectureDecision` | New decision replaces older one. |
| `blockedBy` | action/decision/proposal | `ArchitectureHealthFinding` or `ProofGate` | Work cannot proceed safely. |
| `executedBy` | proposal/decision/proof | GSD milestone/slice/task reference | GSD executes or verifies work. |

## Significance gates

A decision candidate should be created when a topic satisfies:

- **Impact** — affects long-term architecture, process, platform, security, proof boundary, or authority model.
- **Alternatives** — has multiple viable approaches or a documented reason alternatives do not exist.
- **Scope** — cross-cutting or likely to affect future work.
- **Proof burden** — changes what evidence is required before a claim can be made.
- **Supersession risk** — replaces, constrains, or conflicts with an earlier decision.
- **Agent drift risk** — future agents are likely to diverge without an explicit record.

For reusable ACP, profiles may tune thresholds. For `law-nexus`, proof-boundary, legal-authority, parser-completeness, FalkorDB-ingestion, LLM-authority, and retrieval-quality decisions are high-significance by default.

## Spec Architect rubric

The Spec Architect role becomes an ACP proposal quality gate, not a standalone authority.

Every architecture proposal should answer:

- scope;
- non-goals;
- dependencies;
- key decisions;
- alternatives;
- interfaces and contracts;
- non-functional requirements;
- data/state impacts;
- operations and observability;
- risks;
- validation and proof gates;
- ADR/decision candidates;
- blocked/allowed next actions.

If the README-referenced Spec Architect prompt path is absent in a source checkout, ACP must mark that reference as stale/absent and use available source-backed command/protocol artifacts instead.

## Adapter contracts

### git-lex adapter

Role: typed Git-native source record and projection backend.

Responsibilities:

- represent ACP records as Markdown/frontmatter;
- validate record shape through schema/kit/SHACL-style rules;
- emit RDF/N-Quads/queryable projections;
- support pre-commit or CI validation;
- preserve rebuildability of derived stores.

Non-responsibilities:

- accepting decisions without authority;
- validating runtime/product/legal claims;
- replacing GSD execution state.

### spec-kit-plus adapter

Role: provenance and ADR workflow inspiration.

Responsibilities:

- create prompt/provenance records deterministically;
- create ADR/decision candidates after significance checks;
- preserve command-style placeholder completion and reporting;
- enforce consent/authority before accepted decision status.

ACP adaptation:

- do not blindly persist every user input verbatim;
- apply profile-controlled `capture_mode` and `redaction_status`;
- store architecture-relevant intent with sufficient fidelity for recovery;
- link PHR-like records to proposals, candidates, decisions, proof gates, and GSD work units.

### GSD adapter

Role: execution, planning, verification, and recovery substrate.

Responsibilities:

- map ACP proposals/decisions/proof gates to milestones, slices, and tasks;
- record summaries and verification evidence;
- track requirements, decisions, reassessments, and gate results;
- expose current work status;
- preserve forward intelligence for future agents.

Non-responsibilities:

- acting as the complete architecture ontology;
- replacing PHR/provenance records;
- automatically accepting architecture decisions;
- validating claims outside actual evidence.

Mapping examples:

| ACP | GSD |
| --- | --- |
| `ArchitectureProposal` | milestone/slice context or research artifact |
| `ProofGate` | task/slice verification contract or gate result |
| `ArchitectureHealthFinding` | blocker, reassessment, validation finding, or follow-up |
| `ArchitectureDecision` | GSD decision record plus ACP typed decision metadata |
| `EvidenceAnchor` | task/slice summary evidence, test output, source file, PRD artifact |

### Understand-Anything visualization adapter

Role: derived recovery/dashboard layer.

Responsibilities:

- export source-linked ACP records into visual graph nodes/edges;
- group records into lifecycle layers;
- show prompt-to-decision-to-proof chains;
- display health findings and blocked actions;
- provide copyable diagnostics;
- sanitize paths and avoid local absolute path leaks;
- remain read-only relative to ACP authority.

Non-responsibilities:

- validating architecture correctness;
- accepting, rejecting, or verifying decisions;
- proving parser/legal/FalkorDB/retrieval claims.

## Validation and health checks

ACP validation should include:

### Shape checks

- required fields present;
- no unresolved placeholders;
- valid IDs and record kinds;
- valid lifecycle statuses;
- valid capture modes and redaction statuses;
- repo-relative paths only;
- no ignored local-only anchors;
- no `.gsd/exec` durable anchors.

### Relationship checks

- accepted decisions link to provenance;
- accepted decisions link to proof gates when they make proof-sensitive claims;
- superseded decisions have successor coverage;
- conflicts are explicit and unresolved conflicts block status upgrade;
- proposals that pass significance gates have decision candidates;
- proof gates reference accepted evidence before `passed`.

### Claim-safety checks

Flag or block claims that assert unproven:

- legal correctness;
- parser completeness;
- FalkorDB ingestion;
- graph-vector retrieval quality;
- generated-Cypher safety;
- LLM authority;
- production readiness;
- independent external review.

### Provenance safety checks

- no secrets;
- no provider payloads;
- no unnecessary raw legal text;
- no noisy debug dumps;
- no local absolute paths;
- external AI dialogue marked context-only;
- prompt capture mode matches profile policy.

### Recovery checks

- every active architecture decision appears in recovery view;
- every blocking proof gate appears in recovery view;
- every unresolved high-significance candidate appears in recovery view;
- every health finding has a recommended next action;
- allowed/blocked next actions are computable.

## Blocked and allowed action semantics

The ACP contract includes explicit blocked and allowed action semantics.

ACP should compute next-action guidance from current state:

Allowed examples:

- draft proposal from captured prompt;
- create decision candidate from complete proposal;
- execute GSD task for accepted decision with defined proof gate;
- generate visualization from current source records;
- open health finding for missing evidence.

Blocked examples:

- mark decision `accepted` without authority;
- mark decision `verified` without proof-gate evidence;
- claim R035/R037/R038 validation from docs/provenance/visualization;
- treat external AI dialogue as authority;
- use visualization success as architecture proof;
- mutate source truth from dashboard graph;
- proceed with implementation when a blocking conflict is unresolved.

## Reusable core vs project profile

### ACP core

Project-independent:

- record types;
- lifecycle states;
- relationship model;
- validation rules;
- adapter interfaces;
- health finding model;
- allowed/blocked action semantics;
- source-vs-derived hierarchy.

### Project profile

Project-specific:

- claim-safety vocabulary;
- forbidden evidence classes;
- proof levels;
- accepted source roles;
- prompt capture policy;
- verifier commands;
- requirement mappings;
- external authority rules;
- domain-specific overclaim patterns.

## law-nexus profile constraints

The first `law-nexus` profile must enforce:

- `R035` remains active/not validated unless actual registry extractor integration, regenerated registry outputs, and accepted proof-gate evidence exist.
- `R037` remains not validated unless FalkorDB ingestion/runtime loading proof exists.
- `R038` remains not validated unless independent external review proof exists.
- MiniMax is non-authoritative.
- GPT-5.5 external review/control over CLI outputs is not a runtime judge.
- External AI dialogue, including Grok, is context-only.
- PHRs and ADRs are provenance/decision artifacts, not proof of implementation or legal correctness.
- Consultant XML and Garant ODT evidence must not be conflated.
- `law-source/consultant/44-FZ-2026.xml` and `law-source/consultant/Список документов (5).xml` source roles must remain distinct when referenced.
- No secrets, provider payloads, raw vectors, or unnecessary raw legal text in durable architecture artifacts.
- Generated architecture registry JSONL/report/dashboard outputs are derived, non-authoritative projections.
- Canonical architecture verifier remains:

```bash
uv run python scripts/verify-architecture-graph.py
```

Passing this verifier means static registry/graph/source-anchor/decision-fitness/claim-safety checks passed. It does not validate runtime behavior, parser completeness, retrieval quality, FalkorDB production scale, legal-answer correctness, or LLM authority.

## First implementation proof shape

A first ACP vertical slice should be deliberately tiny:

1. Define JSON schema or Markdown/frontmatter schema for:
   - `ArchitecturePromptRecord`
   - `ArchitectureProposal`
   - `DecisionCandidate`
   - `ProofGate`
   - `ArchitectureHealthFinding`
2. Create one fixture chain:

```text
ArchitecturePromptRecord
  -> ArchitectureProposal
  -> DecisionCandidate
  -> ProofGate
  -> ArchitectureHealthFinding
```

3. Add one `GSDTaskRef` or `GSDSliceRef` link.
4. Validate:
   - no unresolved placeholders;
   - all source refs exist;
   - no absolute paths;
   - no unsafe prompt capture;
   - no false R035/R037/R038 validation.
5. Generate one derived recovery view.
6. Confirm visualization is read-only and cannot change source status.

## Verification approach for this contract

This S04 contract should be verified by:

- focused marker scan for required ACP concepts;
- forbidden marker scan for secrets and overclaims;
- canonical architecture verifier:

```bash
uv run python scripts/verify-architecture-graph.py
```

The verifier output remains derived and non-authoritative; source evidence remains authoritative.

## Risks

### Risk 1: ACP duplicates GSD

Mitigation: ACP defines architecture state and governance; GSD executes and records work. Link rather than duplicate.

### Risk 2: PHR becomes noisy or unsafe

Mitigation: profile-controlled `capture_mode`, redaction, and architecture-relevance thresholds.

### Risk 3: ADRs become too granular

Mitigation: decision clusters and significance gates.

### Risk 4: visualization becomes mistaken for proof

Mitigation: read-only visualization adapter and explicit non-authoritative boundary in every generated view.

### Risk 5: reusable core absorbs law-nexus-only constraints

Mitigation: keep core generic; isolate legal/parser/FalkorDB/R035/R037/R038 rules in `law-nexus` profile.

### Risk 6: proof gates become paperwork

Mitigation: verified status requires actual evidence classes, not prose, PHRs, ADRs, or visual graphs.

## Sources

- git-lex mechanics synthesis: `prd/research/architecture/git-lex-mechanics-for-architecture-control-plane.md`.
- spec-kit-plus PHR/ADR mechanics synthesis: `prd/research/architecture/spec-kit-plus-phr-adr-mechanics-for-architecture-control-plane.md`.
- Understand-Anything visualization synthesis: `prd/research/architecture/understand-anything-visualization-fit-for-architecture-control-plane.md`.
- Existing architecture verification context: `prd/09_architecture_planning_verification_research.md` and `prd/architecture/README.md`.
- Project-local architecture verification router: `.agents/skills/legalgraph-architecture-verification/SKILL.md`.

## Verification notes

This contract is research/design evidence only. It does not validate law-nexus parser completeness, legal correctness, FalkorDB ingestion, graph-vector retrieval quality, R035, R037, or R038. It does not make PHRs, ADRs, external AI dialogue, GSD summaries, generated graphs, dashboards, or verifier reports authoritative proof.
