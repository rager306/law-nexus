# M048 S03 ACP Lifecycle and Health Model

**Status:** Accepted S03 lifecycle and health contract for `M048-q4x62e / S03`.

## Verdict

The Architecture Control Plane (ACP) core lifecycle and health model is approved as a reusable governance contract.

This document defines lifecycle states, transition rules, health finding categories, allowed actions, blocked actions, and profile-boundary rules for future ACP validation and isolated git-lex proof work. It is intentionally a source-backed design contract, not runtime telemetry and not product proof.

The reusable ACP core may model generic governance records and actions. The law-nexus profile must retain project-specific proof boundaries for Russian legal evidence, FalkorDB, parser completeness, LLM authority, GSD operational quirks, and requirements `R035`, `R037`, and `R038`.

## Scope

This contract covers:

- core lifecycle states for `ArchitecturePromptRecord`, `ArchitectureProposal`, `DecisionCandidate`, `ArchitectureDecision`, `ProofGate`, `ArchitectureHealthFinding`, `DerivedProjectionReference`, `ProfileConstraint`, and `BlockedAction`;
- transition rules between those states;
- health finding categories, severities, blocked actions, and allowed next actions;
- S01 seed mapping for `HF-M048-S01-001` through `HF-M048-S01-013`;
- generic ACP core action semantics;
- law-nexus profile action semantics;
- reusable core versus profile boundary rules;
- S04 isolated git-lex mechanic checklist;
- S06 verification checklist;
- negative tests for future mechanical assertions;
- observability impact for future agents.

This contract does not implement an ACP runtime, initialize git-lex, create `.lex` state, mutate product architecture, refresh stale project-state outputs, validate legal correctness, validate parser completeness, load FalkorDB, or close any requirement by itself.

## Required Non-Claims

The following are explicit non-claims:

1. This contract does not validate `R035`, `R037`, or `R038`.
2. This contract does not prove FalkorDB ingestion, FalkorDB runtime behavior, FalkorDB production scale, vector search, full-text search, or graph-vector retrieval quality.
3. This contract does not prove Russian legal evidence correctness, legal-answer correctness, citation sufficiency, temporal legal validity, or parser completeness.
4. This contract does not make LLM output authoritative. MiniMax, GPT, Grok, and other external AI outputs remain context or candidate input only unless separately converted through accepted authority and proof evidence.
5. This contract does not prove git-lex compatibility or adoption readiness. It defines what S04 must test in an isolated workspace.
6. This contract does not make derived JSONL, RDF, SHACL, SPARQL, recovery, dashboard, report, or project-state projections authoritative.
7. This contract does not refresh stale `prd/project-state/*` files or treat them as current M048 authority.
8. This contract adds no runtime telemetry. It adds a durable inspection surface for future static and workflow verification.

## Authority and Non-Authority Rules

### Authoritative source evidence

ACP may reference authoritative source evidence when it is repository-relative, durable, and appropriate for the claim:

- accepted PRD and architecture contracts;
- GSD project, requirement, decision, knowledge, state, milestone, slice, and task artifacts;
- accepted ADRs and decision records;
- source code and tests for implemented behavior;
- runtime summaries when runtime behavior is claimed;
- real-document evidence summaries when legal-source behavior is claimed.

### ACP source records

ACP typed records are authoritative only for ACP governance mechanics. They can represent provenance, proposals, candidates, decisions, proof gates, health findings, profile constraints, blocked actions, and derived projection references.

ACP source records do not automatically become product proof, legal proof, runtime proof, parser proof, or requirement-validation proof.

### Non-authoritative records and projections

The following are non-authoritative unless separate authority or proof evidence exists:

- `DecisionCandidate` records;
- `ArchitecturePromptRecord` records;
- external AI output;
- `ProofGate` definitions before evidence has satisfied the gate;
- derived JSONL projections;
- derived RDF, SHACL, SPARQL, recovery, dashboard, report, and project-state projections;
- stale `prd/project-state/*` files.

### Blocked durable proof anchors

The following must not be used as durable ACP proof anchors:

- `.gsd/exec/*` logs;
- absolute local paths;
- ignored paths and local-only scratch paths;
- raw provider payloads;
- raw vectors;
- secrets, credentials, tokens, and auth headers;
- unnecessary raw legal text;
- external URLs as the only proof for an authoritative project claim;
- generated projections as the only proof for an authoritative source claim.

## Lifecycle State Tables

### ArchitecturePromptRecord

Purpose: preserve architecture-relevant prompt or external AI provenance after safety filtering.

| State | Meaning | Allowed next states | Blocking conditions |
|---|---|---|---|
| `draft` | Prompt record is being prepared. | `captured`, `discarded` | Contains secrets, raw provider payloads, raw legal text, or unsafe anchors. |
| `captured` | Safe provenance was recorded with profile and source context. | `linked`, `redacted`, `discarded` | Missing source reference, profile, or redaction status. |
| `redacted` | Unsafe or unnecessary raw content was removed while preserving bounded metadata. | `linked`, `discarded` | Redaction loses required intent or leaves unsafe content. |
| `linked` | Prompt record is linked to proposal, candidate, proof gate, health finding, or GSD unit. | `superseded`, `archived` | Link implies authority or proof. |
| `superseded` | A later prompt/provenance record replaces this record for recovery context. | `archived` | Supersession is not explicit. |
| `discarded` | Record is rejected as unsafe or irrelevant. | none | Any downstream action still treats it as active. |
| `archived` | Record is retained for history only. | none | Used as current authority or proof. |

Core rule: `ArchitecturePromptRecord` is provenance, not authority.

### ArchitectureProposal

Purpose: represent a proposed architecture direction before authority accepts, rejects, or narrows it.

| State | Meaning | Allowed next states | Blocking conditions |
|---|---|---|---|
| `draft` | Proposal is incomplete. | `proposed`, `discarded` | Missing source context or scope. |
| `proposed` | Proposal is available for review. | `candidate_extracted`, `needs_evidence`, `rejected`, `superseded` | Proposal claims product/runtime/legal validation. |
| `candidate_extracted` | One or more decision candidates were extracted. | `under_review`, `superseded` | Candidate extraction implies acceptance. |
| `under_review` | Human, agent, or verifier review is evaluating the proposal. | `accepted_as_decision`, `rejected`, `needs_evidence`, `superseded` | Review lacks authority or evidence class. |
| `needs_evidence` | Proposal cannot advance without proof gates or source anchors. | `under_review`, `rejected` | Missing proof is hidden instead of surfaced. |
| `accepted_as_decision` | Proposal has been accepted only through an `ArchitectureDecision`. | none | Acceptance bypasses decision authority. |
| `rejected` | Proposal is explicitly rejected. | none | Rejected proposal remains active. |
| `superseded` | Proposal is replaced by another proposal or decision. | none | Successor is not named. |
| `discarded` | Proposal was unsafe, duplicate, or out of scope. | none | Discarded proposal drives actions. |

Core rule: a proposal can produce candidates but cannot itself validate a requirement or satisfy a proof gate.

### DecisionCandidate

Purpose: represent a potential decision that needs authority and possibly proof.

| State | Meaning | Allowed next states | Blocking conditions |
|---|---|---|---|
| `draft` | Candidate is being shaped. | `candidate`, `discarded` | Missing rationale or source context. |
| `candidate` | Candidate is ready for significance and authority checks. | `requires_authority`, `requires_proof`, `accepted`, `rejected`, `superseded` | Candidate is treated as accepted doctrine. |
| `requires_authority` | Candidate needs human, GSD, ADR, or accepted decision authority. | `accepted`, `rejected`, `requires_proof` | Authority source is absent or derived-only. |
| `requires_proof` | Candidate needs one or more proof gates before adoption or validation. | `accepted`, `blocked`, `rejected` | Gate definition is mistaken for satisfied proof. |
| `accepted` | Candidate was promoted to an `ArchitectureDecision` by authority. | none | No accepted decision record exists. |
| `rejected` | Candidate was rejected. | none | Rejected candidate remains actionable. |
| `blocked` | Candidate cannot advance due to health finding, blocked action, or unsatisfied proof. | `requires_proof`, `rejected`, `superseded` | Block reason has no unblock evidence. |
| `superseded` | Candidate is replaced by another candidate or decision. | none | Successor is not named. |
| `discarded` | Candidate is unsafe, duplicate, or irrelevant. | none | Candidate appears in allowed action list. |

Core rule: `DecisionCandidate` is non-authoritative until accepted as `ArchitectureDecision` through an authoritative process.

### ArchitectureDecision

Purpose: represent accepted architecture doctrine and its verification boundaries.

| State | Meaning | Allowed next states | Blocking conditions |
|---|---|---|---|
| `accepted` | Decision is accepted by the appropriate authority. | `active`, `requires_proof`, `superseded`, `retired` | Missing rationale, scope, or source authority. |
| `active` | Decision currently governs actions. | `requires_proof`, `verified`, `superseded`, `retired` | Downstream actions exceed decision scope. |
| `requires_proof` | Decision is accepted but some claim requires evidence before validation. | `verified`, `blocked`, `superseded` | Requirement is marked validated from decision existence alone. |
| `verified` | Required proof gates are satisfied by durable evidence. | `active`, `superseded`, `retired` | Evidence is derived-only, unsafe, stale, or out of scope. |
| `blocked` | Decision cannot be executed safely due to health or profile constraints. | `active`, `requires_proof`, `superseded`, `retired` | Block is ignored. |
| `superseded` | Decision was replaced by another accepted decision. | none | Successor coverage is missing. |
| `retired` | Decision no longer applies. | none | Retired decision is used as current doctrine. |

Core rule: accepted doctrine and proof satisfaction are separate states.

### ProofGate

Purpose: define evidence required to validate a claim, action, or requirement.

| State | Meaning | Allowed next states | Blocking conditions |
|---|---|---|---|
| `defined` | Gate exists with claim, required evidence, commands, and acceptance criteria. | `pending_evidence`, `waived`, `retired` | Gate definition is treated as proof. |
| `pending_evidence` | Required evidence has not been produced or anchored. | `running`, `blocked`, `satisfied`, `failed`, `waived` | Missing evidence is hidden. |
| `running` | Verification is in progress. | `satisfied`, `failed`, `blocked` | Runtime output is not summarized into durable tracked evidence when needed. |
| `satisfied` | Evidence meets acceptance criteria. | `retired`, `regressed` | Evidence uses unsafe anchors or wrong proof class. |
| `failed` | Evidence exists but does not meet criteria. | `pending_evidence`, `blocked`, `retired` | Failure is normalized away. |
| `blocked` | Gate cannot run due to missing dependency, unsafe environment, or profile constraint. | `pending_evidence`, `waived`, `retired` | Block lacks owner or unblock criteria. |
| `waived` | Explicit authority waived the gate for a bounded reason. | `retired` | Waiver validates runtime/legal/parser proof that does not exist. |
| `regressed` | Previously satisfied gate is no longer trustworthy. | `pending_evidence`, `blocked`, `retired` | Regression is ignored. |
| `retired` | Gate no longer applies. | none | Retired gate used as active proof. |

Core rule: `ProofGate` definitions are never proof by themselves.

### ArchitectureHealthFinding

Purpose: preserve visible health, drift, overclaim, and blocked-action diagnostics.

| State | Meaning | Allowed next states | Blocking conditions |
|---|---|---|---|
| `open` | Finding is active. | `triaged`, `blocked`, `mitigated`, `resolved`, `accepted_risk` | Finding has no severity, blocked actions, or next actions. |
| `triaged` | Owner/category/next action are known. | `blocked`, `mitigated`, `resolved`, `accepted_risk` | Triage downgrades severity without evidence. |
| `blocked` | Finding blocks one or more actions. | `mitigated`, `resolved`, `accepted_risk` | Blocked actions are not enforced. |
| `mitigated` | A bounded mitigation reduces risk but does not fully resolve it. | `resolved`, `accepted_risk`, `reopened` | Mitigation is mistaken for validation. |
| `resolved` | Durable evidence or source update closes the finding. | `reopened` | Resolution lacks source reference. |
| `accepted_risk` | Explicit authority accepts bounded residual risk. | `reopened` | Acceptance is implicit or hides blocked claims. |
| `reopened` | A resolved or mitigated finding is active again. | `triaged`, `blocked`, `resolved` | Reopen reason is missing. |

Core rule: health findings are first-class ACP state, not disposable logs.

### DerivedProjectionReference

Purpose: reference rebuildable generated outputs without promoting them to authority.

| State | Meaning | Allowed next states | Blocking conditions |
|---|---|---|---|
| `registered` | Projection is known with kind, path, source inputs, and authority status. | `fresh`, `stale`, `invalid`, `retired` | `authority_status` is missing or not `non_authoritative`. |
| `fresh` | Projection was generated from current known inputs within its verifier contract. | `stale`, `invalid`, `retired` | Freshness is used as source authority. |
| `stale` | Projection does not reflect current source state. | `fresh`, `retired` | Stale data is fed into ACP as current source truth. |
| `invalid` | Projection shape, source mapping, or verifier check failed. | `fresh`, `stale`, `retired` | Invalid projection drives actions. |
| `retired` | Projection is no longer used. | none | Retired projection remains active. |

Core rule: derived projections are diagnostics and recovery views only.

### ProfileConstraint

Purpose: encode project-specific rules outside the reusable ACP core.

| State | Meaning | Allowed next states | Blocking conditions |
|---|---|---|---|
| `proposed` | Constraint is suggested for a profile. | `active`, `rejected`, `superseded` | Generic core begins depending on project-specific rule. |
| `active` | Constraint applies to profile validation and action semantics. | `satisfied`, `blocked`, `superseded`, `retired` | Constraint is bypassed by core action. |
| `blocked` | Constraint blocks a claim or action until proof exists. | `satisfied`, `superseded`, `retired` | Block lacks proof-gate linkage. |
| `satisfied` | Required proof or authority exists for the bounded constraint. | `active`, `superseded`, `retired` | Satisfaction is generalized beyond profile scope. |
| `rejected` | Constraint is not adopted. | none | Rejected constraint still enforced. |
| `superseded` | Constraint is replaced by another profile rule. | none | Successor is not named. |
| `retired` | Constraint no longer applies. | none | Retired constraint blocks actions. |

Core rule: profile constraints may restrict core actions but must not pollute the generic core taxonomy.

### BlockedAction

Purpose: record actions that must not happen until explicit unblock evidence exists.

| State | Meaning | Allowed next states | Blocking conditions |
|---|---|---|---|
| `active` | Action is blocked now. | `unblock_pending`, `waived`, `retired` | Blocked action is executed. |
| `unblock_pending` | Required unblock evidence is being prepared. | `unblocked`, `active`, `retired` | Evidence is incomplete, unsafe, or derived-only. |
| `unblocked` | Required evidence and authority allow the action. | `retired`, `active` | Unblock decision lacks source reference. |
| `waived` | Explicit authority permits a bounded exception. | `retired`, `active` | Waiver creates proof overclaim. |
| `retired` | Block no longer applies. | none | Retired block still appears as active. |

Core rule: blocked actions do not silently expire.

## Transition Rules

1. A record may not transition to a more authoritative state without the required authority class.
2. A `DecisionCandidate` may transition to accepted only by creating or linking an accepted `ArchitectureDecision`.
3. An `ArchitectureDecision` may be accepted without being verified, but it may not validate a proof-bound claim until required `ProofGate` records are satisfied.
4. A `ProofGate` may transition to `satisfied` only when durable evidence matches the required evidence class and acceptance criteria.
5. A `ProofGate` definition may never satisfy itself.
6. A derived projection may transition to `fresh` only within its generation or verifier contract, and that transition never changes `authority_status: non_authoritative`.
7. A stale or invalid `DerivedProjectionReference` must create or keep an `ArchitectureHealthFinding` when it could mislead current-state reasoning.
8. A health finding may transition to `resolved` only through durable source evidence, accepted decision evidence, or a checked verification artifact summarized in tracked source form.
9. A health finding may transition to `accepted_risk` only through explicit authority and bounded residual risk language.
10. A profile constraint may block a core action for a project profile, but the generic core must express the block as generic categories and action semantics.
11. A blocked action may transition to `unblocked` only when required unblock evidence and explicit authority both exist.
12. Main-repo `git lex init` and `.lex` state creation remain blocked until S04 isolated proof exists and a later explicit adoption decision accepts the adoption path.
13. ACP must preserve S01 health findings. It may map and categorize them, but it must not normalize them away or hide their original identifiers.
14. ACP must keep `R035`, `R037`, `R038`, Russian legal evidence, FalkorDB, parser, LLM, GSD quirks, and law-nexus-specific proof boundaries in profile constraints rather than generic core rules.

## Health Finding Categories

| Category | Definition | Default severity | Typical surfaces | Blocks |
|---|---|---:|---|---|
| `stale_summary` | A summary or projection describes an older project state as current. | high | project-state docs and JSON | current-state authority, automated ingestion as source truth |
| `sparse_evidence` | Evidence exists but is too small, indirect, or bounded for broader claims. | medium | fixture chains, planning docs, unproven proof paths | broad lifecycle claims, adoption claims, validation claims |
| `blocked_adoption` | A candidate tool, state, or workflow must not be adopted before proof and decision. | critical | git-lex main-repo state, `.lex` creation | direct adoption, blind initialization, mutation of main repo |
| `unsafe_anchor` | A cited anchor is unsafe for durable proof. | high | exec logs, absolute paths, raw payloads, secrets, raw legal text | durable proof, registry source anchoring |
| `derived_authority_overclaim` | A derived projection or report is being treated as source truth or validation proof. | critical | JSONL, RDF, reports, dashboards, recovery views | requirement validation, proof satisfaction, product readiness claims |
| `profile_boundary_risk` | Project-specific law-nexus constraints leak into reusable core or are bypassed. | high | R035/R037/R038, legal, FalkorDB, parser, LLM, GSD rules | generic core changes, profile bypass, proof-boundary upgrades |
| `missing_proof_gate` | A significant claim or action lacks a required gate. | high | decisions, candidates, requirements | acceptance as verified, validation claims |
| `proof_gate_failed` | A gate ran and failed. | high | verifier output summarized into tracked evidence | proof satisfaction, dependent adoption |
| `proof_gate_blocked` | A gate cannot run safely or lacks dependencies. | high | isolated proof setup, external dependency checks | proof satisfaction, adoption |
| `conflict_or_supersession_gap` | Conflicting or superseded records lack clear resolution. | medium | decisions, candidates, proposals | unambiguous next action, automated status projection |

## S01 Health Seed Mapping

The following S01 findings remain preserved by identifier. The lifecycle model maps them to categories and actions without deleting or renaming them.

| Finding ID | Severity | Category | Surface | Blocked actions | Allowed next actions |
|---|---:|---|---|---|---|
| `HF-M048-S01-001` | high | `stale_summary` | `prd/project-state/README.md` | Use README as current active-milestone authority. | Keep finding visible; refresh project-state in a later explicit workflow; use current GSD state instead. |
| `HF-M048-S01-002` | high | `stale_summary` | `prd/project-state/handoff.md` | Use handoff as current M048 closeout or planning authority. | Preserve as stale diagnostic; use M048 GSD milestone artifacts for current work. |
| `HF-M048-S01-003` | high | `stale_summary` | `prd/project-state/roadmap.md` | Treat M047 roadmap state as current ACP/git-lex plan. | Refresh or supersede deliberately; do not silently rewrite during S03. |
| `HF-M048-S01-004` | high | `stale_summary` | `prd/project-state/data/project-overview.json` | Feed JSON into ACP as current project or active requirements authority. | Rebuild from current source in a later project-state refresh. |
| `HF-M048-S01-005` | high | `stale_summary` | `prd/project-state/data/roadmap.json` | Use JSON as current milestone sequence authority. | Keep as stale derived reference; use current GSD roadmap. |
| `HF-M048-S01-006` | high | `stale_summary` | `prd/project-state/data/open-requirements.json` | Use JSON as active requirements authority. | Rebuild from `.gsd/REQUIREMENTS.md` in a deliberate refresh; use GSD requirement registry now. |
| `HF-M048-S01-007` | medium | `stale_summary` | `prd/project-state/data/verification-matrix.json` | Claim M048 verification from old matrix evidence. | Recompute matrix or cite current task/slice verification evidence. |
| `HF-M048-S01-008` | high | `sparse_evidence` | git-lex acquisition/runtime path | Claim git-lex viability or initialize git-lex from unconfirmed path. | S04 must identify and test git-lex in an isolated workspace. |
| `HF-M048-S01-009` | medium | `sparse_evidence` | ACP fixture chain | Generalize five-record fixture mechanics into full lifecycle readiness. | Use fixtures only as minimal mechanics seeds; expand tests before adoption claims. |
| `HF-M048-S01-010` | medium | `stale_summary` | project-state M048 representation | Treat M047 project-state as current ACP/git-lex planning state. | Preserve stale finding; refresh project-state only through explicit future workflow. |
| `HF-M048-S01-011` | critical | `blocked_adoption` | main repository git-lex state | Run blind `git lex init` or create main-repo `.lex` state. | Keep absence of `.lex` as correct blocked state; use isolated proof only. |
| `HF-M048-S01-012` | critical | `derived_authority_overclaim` | derived ACP/RDF/JSONL/recovery views | Validate `R035`, `R037`, or `R038` from ACP/git-lex/projection evidence alone. | Keep projections non-authoritative; require separate proof gates. |
| `HF-M048-S01-013` | high | `unsafe_anchor` | durable proof anchors | Cite `.gsd/exec`, absolute paths, ignored paths, raw provider payloads, raw vectors, secrets, or unnecessary raw legal text as durable proof. | Summarize safe evidence into tracked source artifacts; use repo-relative anchors. |

## Generic ACP Core Action Matrix

| Action | Allowed when | Blocked when | Required result |
|---|---|---|---|
| Capture prompt provenance | Safety filtering is complete and source context is bounded. | Secrets, raw payloads, raw legal text, or unsafe anchors would be persisted. | `ArchitecturePromptRecord` in `captured` or `redacted` state. |
| Create proposal | Proposal scope and source inputs are explicit. | Proposal claims validation or authority by itself. | `ArchitectureProposal` in `proposed` state. |
| Extract decision candidate | Proposal contains a decision-worthy choice and significance checks pass. | Candidate would be treated as accepted doctrine. | `DecisionCandidate` in `candidate`, `requires_authority`, or `requires_proof` state. |
| Accept decision | Appropriate authority accepts rationale, scope, and consequences. | Authority is absent or derived-only. | `ArchitectureDecision` in `accepted` or `active` state. |
| Verify decision or requirement claim | Matching proof gates are satisfied by durable evidence. | Gate is absent, failed, blocked, or satisfied only by derived projections. | `ProofGate` in `satisfied` state and decision may become `verified`. |
| Register derived projection | Projection kind, source inputs, freshness, and non-authority are explicit. | Projection is used as source truth. | `DerivedProjectionReference` with `authority_status: non_authoritative`. |
| Open health finding | Drift, overclaim, unsafe anchor, missing evidence, or blocked action exists. | Finding hides original source identifier or lacks next action. | `ArchitectureHealthFinding` with severity, category, blocked actions, and allowed next actions. |
| Resolve health finding | Durable source update, verified evidence, accepted decision, or explicit accepted risk exists. | Resolution relies on transient logs or derived-only output. | Finding transitions to `resolved`, `mitigated`, or `accepted_risk`. |
| Block action | Unsafe or premature action has clear unblock criteria. | Block silently expires or lacks evidence criteria. | `BlockedAction` in `active` state. |
| Unblock action | Required proof and authority are both present. | Proof is unsafe, stale, profile-incompatible, or derived-only. | `BlockedAction` in `unblocked` or `retired` state. |

## law-nexus Profile Action Matrix

| Profile action or claim | Allowed | Blocked | Required proof or authority |
|---|---|---|---|
| Model `R035` proof boundary | Yes, as profile constraint or proof gate. | Marking `R035` validated from ACP research, projections, docs, prompt records, or git-lex mechanics alone. | Separate architecture registry integration proof with accepted gate evidence. |
| Model `R037` proof boundary | Yes, as profile constraint or proof gate. | Marking `R037` validated from graph-context staging, dashboard output, or source-record existence. | FalkorDB ingestion/runtime loading proof with counts, idempotency, and error handling evidence. |
| Model `R038` proof boundary | Yes, as profile constraint or proof gate. | Treating internal review packs, LLM review, or ACP summaries as independent review satisfaction. | Accepted independent review proof process and durable review evidence. |
| Reference Russian legal evidence | Yes, via bounded metadata, source roles, summaries, hashes, counts, and repo-relative anchors. | Persisting unnecessary raw legal text or claiming legal correctness from ACP records. | Real-document evidence and citation-safe proof gates. |
| Reference parser state | Yes, as profile constraint or missing-proof health finding. | Claiming parser completeness from ACP docs, source records, or generated projections. | Parser proof over relevant real source family. |
| Reference FalkorDB | Yes, as profile constraint or proof-gate target. | Claiming runtime loading, production scale, vector/full-text behavior, or graph retrieval quality without runtime proof. | Runtime smoke, integration, or production-observation evidence appropriate to the claim. |
| Reference LLM output | Yes, as non-authoritative prompt/proposal/candidate context after safety filtering. | Treating MiniMax, GPT, Grok, or other AI output as authority, proof, legal judgment, or runtime validation. | Accepted deterministic proof or explicit human/decision authority. |
| Use GSD artifacts | Yes, as execution/proof adapter and source evidence. | Using `.gsd/exec/*` as durable proof anchors or unsafe closeout key files. | Tracked GSD artifacts or summarized evidence in accepted source files. |
| Use project-state package | Yes, as stale diagnostic through `DerivedProjectionReference`. | Treating `prd/project-state/*` as current M048 authority until refreshed. | Explicit project-state refresh from current source. |
| Use git-lex in main repo | Not yet. | Blind `git lex init` or `.lex` creation in the main repository. | S04 isolated proof plus later explicit adoption decision. |

## Reusable Core versus Profile Boundary

| Concern | Reusable ACP core | law-nexus profile |
|---|---|---|
| Record taxonomy | Generic record types and lifecycle states. | Concrete profile constraints for legal, FalkorDB, parser, LLM, GSD, and requirement boundaries. |
| Source truth | Source records outrank derived projections. | Current GSD/PRD/architecture evidence defines the project-specific source hierarchy. |
| Derived projections | Always non-authoritative diagnostics. | Project-state is currently stale; architecture JSONL/RDF/recovery outputs cannot validate `R035`, `R037`, or `R038`. |
| Prompt provenance | Non-authoritative provenance after filtering. | MiniMax/GPT/Grok outputs remain non-authoritative and cannot satisfy proof gates. |
| Proof gates | Generic evidence contract with status and anchors. | Requirements `R035`, `R037`, `R038`, Russian legal evidence, parser, FalkorDB, retrieval, and independent review each need profile-specific gates. |
| Health model | Generic categories for stale, sparse, blocked, unsafe, overclaim, boundary, missing proof, failed proof, and conflict. | S01 findings seed concrete law-nexus health state and blocked actions. |
| Git-lex mechanics | Candidate adapter mechanics for typed records, validation, extraction, query, and projection. | Main-repo adoption remains blocked until isolated proof and explicit adoption decision. |
| Evidence anchors | Repo-relative, durable, safety-filtered anchors. | `.gsd/exec`, absolute paths, ignored paths, raw provider payloads, raw vectors, secrets, and raw legal text are blocked durable anchors. |

Boundary rule: if a rule names `law-nexus`, Russian legal evidence, FalkorDB, parser completeness, `R035`, `R037`, `R038`, specific GSD symlink/ignored-path behavior, or LLM-provider authority, it belongs in `ProfileConstraint` or a profile adapter, not in the reusable ACP core.

## S04 Isolated Git-Lex Mechanic Checklist

S04 must use this contract as the safety checklist for isolated git-lex proof work.

- [ ] Run git-lex proof only outside main-repo adoption state; do not create main-repo `.lex` state.
- [ ] Confirm exact git-lex source or binary path before any mechanics claim.
- [ ] Represent at least one safe fixture chain using typed records: prompt/provenance, proposal or candidate, proof gate, health finding, and derived projection reference.
- [ ] Verify record shape extraction without leaking law-nexus profile-only fields into generic core validity.
- [ ] Verify lifecycle states can be represented or losslessly mapped.
- [ ] Verify blocked and allowed actions can be queried or generated from source records.
- [ ] Verify health findings preserve source identifiers, including S01 seed IDs when represented.
- [ ] Verify derived stores remain non-authoritative and rebuildable.
- [ ] Verify proof gate definitions do not satisfy themselves.
- [ ] Verify unsafe anchors are rejected or surfaced as health findings.
- [ ] Verify stale project-state references remain stale diagnostics, not current authority.
- [ ] Verify `R035`, `R037`, and `R038` cannot be marked validated by fixture or projection proof.
- [ ] Record blocked diagnostics honestly if git-lex cannot safely represent a required mechanic.

## S06 Verification Checklist

S06 should verify the full M048 boundary before milestone closure.

- [ ] This lifecycle and health contract exists and remains source-of-truth preserving.
- [ ] S01 health findings are still visible by original identifier.
- [ ] S02 source-record categories are not weakened.
- [ ] Derived projections are still non-authoritative.
- [ ] Stale `prd/project-state/*` surfaces are not used as current M048 authority.
- [ ] Main-repo `git lex init` and `.lex` creation did not occur without accepted adoption decision.
- [ ] S04 isolated proof evidence, if produced, is summarized into tracked source artifacts rather than `.gsd/exec` anchors.
- [ ] S04 did not validate `R035`, `R037`, or `R038` unless separate profile-specific proof exists.
- [ ] law-nexus profile constraints did not leak into reusable ACP core definitions.
- [ ] Negative tests or document assertions cover non-authority, unsafe anchors, blocked adoption, stale project-state, and profile boundary rules.
- [ ] Any unresolved health finding has severity, blocked actions, allowed next actions, and owner or next workflow.

## Document Assertions for T02

T02 may mechanically assert these durable statements:

1. `DecisionCandidate` is non-authoritative unless promoted to `ArchitectureDecision` by accepted authority.
2. `ArchitecturePromptRecord` is provenance/context, not authority or proof.
3. External AI output is non-authoritative.
4. `ProofGate` definitions do not satisfy proof gates.
5. Derived JSONL, RDF, SHACL, SPARQL, recovery, dashboard, report, and project-state projections are non-authoritative.
6. Stale `prd/project-state/*` files are not current M048 authority.
7. `.gsd/exec/*`, absolute paths, ignored paths, raw provider payloads, raw vectors, secrets, and unnecessary raw legal text are blocked durable proof anchors.
8. Main-repo `git lex init` and `.lex` state creation remain blocked until isolated proof and explicit adoption decision.
9. `R035`, `R037`, `R038`, Russian legal evidence, FalkorDB, parser, LLM, GSD quirks, and law-nexus-specific proof boundaries remain profile constraints.
10. S01 health findings `HF-M048-S01-001` through `HF-M048-S01-013` are preserved.
11. ACP core can expose lifecycle states, health categories, blocked actions, and allowed actions without runtime telemetry.
12. A fresh derived projection can still be non-authoritative.
13. A mitigated health finding is not automatically resolved or proof-satisfied.
14. A waived proof gate must not validate unavailable runtime, legal, parser, FalkorDB, or independent-review proof.

## Negative Tests

Future executable assertions should include at least the following negative cases:

| Case ID | Scenario | Expected result |
|---|---|---|
| `NEG-S03-001` | A `DecisionCandidate` is queried as if it were an accepted `ArchitectureDecision`. | Reject or flag `derived_authority_overclaim`. |
| `NEG-S03-002` | An `ArchitecturePromptRecord` or external AI output is used as proof. | Reject or flag non-authoritative provenance misuse. |
| `NEG-S03-003` | A `ProofGate` definition is marked `satisfied` with no evidence anchor. | Reject or keep gate `pending_evidence`. |
| `NEG-S03-004` | A derived JSONL/RDF/recovery/project-state projection is the only source for an authoritative claim. | Reject or open `derived_authority_overclaim`. |
| `NEG-S03-005` | Stale `prd/project-state/*` data is used as current M048 active milestone or requirements authority. | Reject or open `stale_summary`. |
| `NEG-S03-006` | `.gsd/exec/*` is cited as durable proof. | Reject or open `unsafe_anchor`. |
| `NEG-S03-007` | An absolute local path, ignored path, raw provider payload, raw vector, secret, or unnecessary raw legal text is cited as durable proof. | Reject or open `unsafe_anchor`. |
| `NEG-S03-008` | `git lex init` or `.lex` state creation is attempted in the main repository before isolated proof and adoption decision. | Reject or keep `blocked_adoption`. |
| `NEG-S03-009` | `R035`, `R037`, or `R038` is marked validated from ACP docs, fixture proof, git-lex mechanics, or projections alone. | Reject or open `profile_boundary_risk` plus `derived_authority_overclaim`. |
| `NEG-S03-010` | Russian legal evidence, FalkorDB, parser, LLM, or GSD-specific rule is required by generic ACP core validity. | Reject or open `profile_boundary_risk`. |
| `NEG-S03-011` | A health finding is resolved with no source reference or accepted risk authority. | Reject or keep finding open. |
| `NEG-S03-012` | A blocked action silently expires. | Reject or keep blocked action active. |
| `NEG-S03-013` | A fresh derived projection changes its `authority_status` to authoritative. | Reject or flag `derived_authority_overclaim`. |
| `NEG-S03-014` | A proof-gate waiver is used to claim parser, legal, FalkorDB, runtime, or independent-review proof. | Reject or open `profile_boundary_risk`. |

## Failure Modes

This task adds a document and has no external API, network, database, runtime service, or subprocess dependency in the produced artifact. The relevant failure paths are filesystem and source-artifact failures:

| Dependency | Failure path | Handling in this task | Future ACP implication |
|---|---|---|---|
| Repository filesystem | Target path missing, parent directory missing, or file not written. | Check target existence before writing; verify with `test -s`. | Missing contract blocks T02 mechanical assertions. |
| Source artifacts | Input document missing or malformed. | Treat missing source as a blocker if required facts cannot be reconstructed; this run confirmed source files exist before drafting. | ACP should open `missing_proof_gate` or `sparse_evidence` rather than inventing facts. |
| Generated/transient evidence | `.gsd/exec` contains useful diagnostics but is unsafe as durable proof. | Use diagnostics for drafting only; do not cite `.gsd/exec` as durable proof anchor in the contract. | ACP must require tracked summaries or source artifacts for durable proof. |
| Human or external review | No human available in auto-mode. | Use existing accepted source artifacts and document assumptions; do not create new adoption decisions. | ACP must distinguish accepted authority from candidate/proposal text. |

## Load Profile

This contract has no runtime load dimension. It introduces no service, queue, database pool, API route, background process, or telemetry stream. The future 10x pressure point is document assertion volume in static verification, not runtime throughput.

If future ACP validators consume this model at 10x record volume, the first likely saturation point is static graph/projection verification over typed records. That future implementation should use bounded file scanning, deterministic schema validation, clear pagination or chunking for reports, and health summaries instead of raw payload dumps. This document itself applies no runtime protection because it does not implement runtime behavior.

## Observability Impact

This task adds a durable inspection surface for future agents:

- lifecycle states make record status observable without reading entire narrative histories;
- health categories make drift, sparse evidence, blocked adoption, unsafe anchors, derived authority overclaims, and profile boundary risks inspectable;
- S01 seed mapping preserves original finding IDs for traceability;
- action matrices expose blocked and allowed next actions;
- S04 and S06 checklists define future verification surfaces;
- negative tests define a mechanically assertable failure surface.

No runtime telemetry is added. Observability is document-level and verification-oriented.

## Reader Test

A future agent should be able to use this document to answer:

1. Is this record authoritative, candidate-only, proof-gated, derived, stale, or blocked?
2. Which transition is allowed next?
3. Which action is blocked and what evidence would unblock it?
4. Does this rule belong in reusable ACP core or in the law-nexus profile?
5. Which S01 health finding preserves the original source of a stale, sparse, blocked, unsafe, or overclaim condition?

If the answer requires law-nexus legal, FalkorDB, parser, LLM, GSD, or `R035`/`R037`/`R038` semantics, the answer must come from profile constraints, not generic ACP core.
