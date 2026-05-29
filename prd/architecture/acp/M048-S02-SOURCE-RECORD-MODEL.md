# M048 S02 ACP Source-Record Model Contract

**Status:** Accepted S02 source-record model artifact for `M048-q4x62e / S02`.

## Verdict

The ACP source-record model for project knowledge is approved as a **source-backed governance contract**, not a new source of product truth.

ACP may represent requirements, decisions, prompts, proposals, decision candidates, proof gates, evidence anchors, health findings, derived projection references, profile constraints, and blocked actions as tracked records. ACP must preserve the existing project source-of-truth hierarchy and must not promote stale summaries, generated projections, recovery outputs, RDF/SHACL/SPARQL files, dashboard views, current ACP fixtures, or future git-lex stores into authoritative source truth.

This contract consumes `prd/architecture/acp/M048-S01-KNOWLEDGE-BOUNDARY-AUDIT.md` as its immediate input. It also follows the prior ACP boundary contracts in `M041-SOURCE-OWNERSHIP-CONTRACT.md`, `M040-CANONICAL-PROJECTION-CONTRACT.md`, `M044-DEFAULT-INCLUSION-POLICY.md`, and `M046-RDF-PROJECTION-HARDENING-DECISION.md`.

## Scope

This document defines the project-knowledge record model needed by M048 S02/S03/S04/S06:

- source-of-truth hierarchy for ACP project-knowledge records;
- reusable ACP core record categories;
- law-nexus profile constraints that must not leak into generic ACP core;
- allowed and blocked evidence-anchor rules;
- mapping from S01 surface families into ACP categories;
- handoff checklists for S03 lifecycle/health modeling, S04 isolated git-lex proof, and S06 final verification.

## Required Non-Claims

This contract does **not** validate:

- `R035` ontology architecture proof boundaries;
- `R037` FalkorDB graph ingestion or runtime loading;
- `R038` independent review gate satisfaction;
- parser completeness;
- legal correctness;
- FalkorDB capability, ingestion, or production readiness;
- graph-vector retrieval quality;
- generated-Cypher safety;
- RDF engine correctness;
- SHACL engine validation;
- SPARQL runtime behavior;
- git-lex compatibility or adoption readiness;
- currentness of `prd/project-state/*`;
- current ACP fixtures as general lifecycle or product proof.

This task also deliberately does **not** refresh `prd/project-state/*`, initialize git-lex, create `.lex` state, mutate git-lex vendor/reference files, or convert generated JSONL/RDF/recovery/projection outputs into source truth.

## Source-of-Truth Hierarchy

ACP records must preserve this hierarchy when representing project knowledge.

| Rank | Layer | Examples | ACP authority rule |
| --- | --- | --- | --- |
| 1 | Authoritative project source evidence | `.gsd/PROJECT.md`, `.gsd/REQUIREMENTS.md`, `.gsd/DECISIONS.md`, `.gsd/KNOWLEDGE.md`, `.gsd/STATE.md`, tracked milestone context/plans/summaries, accepted PRD/architecture contracts, source code, tests, runtime proof, real-document proof | Source records may bind to these surfaces. If a projection conflicts with them, the projection is stale or faulty. |
| 2 | ACP typed source records | Markdown/frontmatter records for prompts, proposals, candidates, decisions, gates, anchors, findings, constraints, blocked actions | Source evidence for ACP governance mechanics only. Record status and proof state must be explicit. |
| 3 | Checked derived projections | architecture JSONL registry, ACP recovery/projection JSON, RDF/Turtle, SHACL, SPARQL, reports, dashboards | Rebuildable diagnostics. May be referenced by `DerivedProjectionReference`; never authoritative by itself. |
| 4 | Diagnostics and transient execution surfaces | verifier output, dashboard warnings, `.gsd/exec/*`, local command logs | Useful for investigation. Durable proof must be summarized into tracked source artifacts, not cited from transient paths. |
| 5 | External AI/dialogue context | MiniMax/GPT/Grok/other model output, chat transcripts, raw provider payloads | Context only unless converted through policy-filtered records, authority, and proof gates. |

## ACP Core Record Categories

The reusable ACP core should define record categories that are portable across projects. Project-specific proof boundaries belong in profiles, not in these category definitions.

### RequirementBinding

**Purpose:** Bind an ACP concern to a requirement owned by the project requirements system.

**Source candidates:** `.gsd/REQUIREMENTS.md` entries such as M048 `R040`-`R048`.

**Minimum fields:** `id`, `record_kind: requirement_binding`, `requirement_id`, `requirement_status`, `source_ref`, `binding_scope`, `allowed_acp_use`, `blocked_acp_use`.

**Allowed ACP use:** expose requirement context, required proof gates, blocked validation paths, and downstream lifecycle status.

**Blocked ACP use:** change requirement status, validate requirements from projection evidence alone, or infer active requirements from stale `prd/project-state/data/*.json`.

### ArchitectureDecision

**Purpose:** Represent accepted, rejected, or superseded architecture/process doctrine.

**Source candidates:** `.gsd/DECISIONS.md` entries and accepted architecture decision artifacts.

**Minimum fields:** `id`, `record_kind: architecture_decision`, `status`, `decision`, `rationale`, `accepted_by_or_source`, `date`, `source_ref`, `proof_gates`, `supersedes`, `non_claims`.

**Allowed ACP use:** recover accepted doctrine, connect decisions to proof gates and health findings, and expose conflict/supersession relationships.

**Blocked ACP use:** invent acceptance, promote decision candidates, or treat an ADR/provenance record as proof-gate satisfaction.

### ArchitecturePromptRecord

**Purpose:** Capture architecture-relevant prompt or intent provenance after safety filtering.

**Source candidates:** typed prompt/provenance records such as `APR-0001.md` and future profile-filtered prompt records.

**Minimum fields:** `id`, `record_kind: architecture_prompt_record`, `stage`, `capture_mode`, `redaction_status`, `user_intent_summary`, `outcome_summary`, `source_refs`, `policy_checked`.

**Allowed ACP use:** explain why a proposal or decision candidate exists.

**Blocked ACP use:** persist secrets/raw provider payloads unnecessarily, make user/model text authoritative, or prove implementation/legal/runtime behavior.

### ArchitectureProposal

**Purpose:** Describe an architecture option or plan before authority is granted.

**Source candidates:** PRD/research/context artifacts, milestone or slice plans, proposal fixture records.

**Minimum fields:** `id`, `record_kind: architecture_proposal`, `status`, `scope`, `non_goals`, `dependencies`, `interfaces`, `nfrs`, `data_or_state_impacts`, `operational_impacts`, `risks`, `validation_plan`, `source_refs`.

**Allowed ACP use:** feed decision candidates and proof gates, show incomplete proposal fields, and recover rationale.

**Blocked ACP use:** become accepted doctrine, satisfy proof gates, or validate product readiness by existence alone.

### DecisionCandidate

**Purpose:** Represent a proposed significant decision that still requires authority and often proof.

**Source candidates:** candidate fixture records, research-derived proposed decisions, unresolved architecture proposals.

**Minimum fields:** `id`, `record_kind: decision_candidate`, `status`, `origin_prompt_record`, `origin_proposal`, `cluster`, `significance`, `alternatives`, `consequences`, `conflicts`, `required_proof_gates`, `authority_required`.

**Allowed ACP use:** organize review, surface conflicts, and show what authority/proof is still required.

**Blocked ACP use:** masquerade as `ArchitectureDecision`, update GSD decisions directly, or override accepted decisions.

### ProofGate

**Purpose:** Define evidence required before a claim, decision, requirement, or adoption path can be considered satisfied.

**Source candidates:** task/slice verification contracts, gate results, architecture verifier commands, proof-gate fixture records.

**Minimum fields:** `id`, `record_kind: proof_gate`, `claim_or_requirement`, `required_evidence`, `verification_commands`, `acceptance_criteria`, `status`, `evidence_anchors`, `blocked_claims`.

**Allowed ACP use:** require and track proof obligations.

**Blocked ACP use:** treat the gate definition as proof satisfaction, claim runtime behavior from static documentation, or satisfy gates from generated projections alone.

### EvidenceAnchor

**Purpose:** Point from an ACP record or proof gate to durable evidence.

**Source candidates:** repository-relative PRD/GSD/source/test/runtime-summary/real-document-summary artifacts.

**Minimum fields:** `id`, `record_kind: evidence_anchor`, `anchor_kind`, `repo_relative_path`, `section_or_line_hint`, `evidence_role`, `claim_scope`, `durability`, `safety_classification`.

**Allowed ACP use:** bind claims to durable, reviewable, repository-relative evidence.

**Blocked ACP use:** cite `.gsd/exec/*`, absolute local paths, ignored paths, raw provider payloads, raw vectors, secrets, unnecessary raw legal text, or unrefreshed current-state claims as durable proof.

### ArchitectureHealthFinding

**Purpose:** Record a diagnostic finding that blocks, warns, or guides architecture governance.

**Source candidates:** S01 health findings `HF-M048-S01-001` through `HF-M048-S01-013`, verifier findings, validation findings, reassessment results.

**Minimum fields:** `id`, `record_kind: architecture_health_finding`, `severity`, `finding_type`, `surface`, `description`, `blocked_actions`, `allowed_next_actions`, `recommended_fix`, `source_refs`.

**Allowed ACP use:** seed lifecycle/health categories and block unsafe promotion.

**Blocked ACP use:** imply readiness, validate adoption, or hide stale/unsafe surfaces.

### DerivedProjectionReference

**Purpose:** Reference generated outputs without promoting them to source truth.

**Source candidates:** `prd/architecture/architecture_items.jsonl`, `architecture_edges.jsonl`, reports, `prd/architecture/acp/derived/*`, RDF/SHACL/SPARQL outputs, `prd/project-state/*`.

**Minimum fields:** `id`, `record_kind: derived_projection_reference`, `projection_kind`, `repo_relative_path`, `derived_from`, `freshness_status`, `authority_status: non_authoritative`, `allowed_acp_use`, `blocked_acp_use`.

**Allowed ACP use:** diagnose stale or inconsistent views, provide recovery/query/visualization context, and guide regeneration.

**Blocked ACP use:** serve as sole source anchor, validate requirements, override source records, or become canonical architecture rows by copying.

### ProfileConstraint

**Purpose:** Keep reusable ACP core separate from project-specific law-nexus restrictions.

**Source candidates:** law-nexus ACP profile, LegalGraph architecture verification skills, Russian legal evidence guardrails, M048 decisions.

**Minimum fields:** `id`, `record_kind: profile_constraint`, `profile_id`, `constraint_scope`, `rule`, `rationale`, `blocked_claim_patterns`, `required_proof_gates`, `source_refs`.

**Allowed ACP use:** enforce law-nexus-specific legal/FalkorDB/parser/LLM/GSD boundaries at the adapter/profile layer.

**Blocked ACP use:** bake law-nexus legal-source roles, FalkorDB claims, parser constraints, or GSD symlink/ignored-path quirks into generic ACP core.

### BlockedAction

**Purpose:** Make unsafe operations explicit and machine-checkable.

**Source candidates:** S01 blocked actions, M041/M044/M046 blocked-action sections, future health findings.

**Minimum fields:** `id`, `record_kind: blocked_action`, `action`, `surface`, `severity`, `reason`, `blocked_until`, `required_unblock_evidence`, `source_refs`.

**Allowed ACP use:** prevent unsafe source/projection promotion, main-repo git-lex adoption, stale project-state authority, and proof overclaims.

**Blocked ACP use:** silently expire without evidence, suppress a health finding, or replace a human/accepted decision boundary.

## Evidence-Anchor Rules

### Allowed Anchors

An `EvidenceAnchor` may reference:

- tracked PRD, architecture, research, or accepted decision artifacts;
- `.gsd/PROJECT.md`, `.gsd/REQUIREMENTS.md`, `.gsd/DECISIONS.md`, `.gsd/KNOWLEDGE.md`, `.gsd/STATE.md`, and tracked GSD milestone/slice/task summaries when used as source evidence and not as ignored closeout key files;
- source code and tests for bounded implementation behavior;
- runtime smoke/integration evidence summarized in tracked artifacts;
- real-document evidence summarized in tracked artifacts with hashes/counts/source roles when legal-source behavior is claimed;
- generated projections only through `DerivedProjectionReference` with `authority_status: non_authoritative`.

### Blocked Anchors

An `EvidenceAnchor` must not use:

- `.gsd/exec/*` as durable proof;
- absolute local paths;
- ignored or untracked local paths;
- raw provider payloads;
- secrets, tokens, credentials, or raw vectors;
- unnecessary raw legal text;
- ACP derived JSONL/RDF/recovery/projection files as the sole source for an authoritative claim;
- stale `prd/project-state/*` current-state fields as current M048 authority;
- current ACP fixtures as proof of product, parser, FalkorDB, retrieval, legal, or R035/R037/R038 readiness.

## S01 Surface Mapping

| S01 surface family | ACP category | Allowed ACP use | Blocked ACP use | Handoff owner |
| --- | --- | --- | --- | --- |
| `.gsd/PROJECT.md` | EvidenceAnchor / ProfileConstraint input | Project identity and guardrails. | Override from projections. | S03/S06 |
| `.gsd/REQUIREMENTS.md` and M048 `R040`-`R048` | RequirementBinding | Bind ACP work to current requirement contract. | Change status or validate requirements outside GSD tooling. | S03/S06 |
| `.gsd/DECISIONS.md` and M048 `D067`-`D070` | ArchitectureDecision / BlockedAction | Represent accepted isolation/proof/integration/binding decisions. | Invent acceptance or bypass isolated proof. | S03/S04/S06 |
| `.gsd/KNOWLEDGE.md` | ProfileConstraint / EvidenceAnchor | Durable policy input. | Treat as runtime proof. | S03/S06 |
| `.gsd/STATE.md` and M048 milestone files | EvidenceAnchor / ProofGate | Current execution scope and verification contracts. | Use transient `.gsd/exec` logs as durable anchors. | S03/S06 |
| ACP minimal-chain fixtures | ArchitecturePromptRecord / ArchitectureProposal / DecisionCandidate / ProofGate / ArchitectureHealthFinding | Governance mechanics examples and sparse source-record seeds. | Generalize to full lifecycle or product proof. | S03/S04 |
| `M041-SOURCE-OWNERSHIP-CONTRACT.md` | ProfileConstraint / BlockedAction / EvidenceAnchor rules | Reuse ownership and blocked-anchor language. | Treat prior derived outputs as source truth. | S03/S06 |
| `M040-CANONICAL-PROJECTION-CONTRACT.md` | DerivedProjectionReference / BlockedAction | Reuse canonical-shaped projection boundary. | Copy derived ACP JSONL into canonical registry. | S06 |
| `M044-DEFAULT-INCLUSION-POLICY.md` | DerivedProjectionReference / BlockedAction | Allow bounded default inclusion of governance rows. | Promote candidates, gates, or projections to proof-positive semantics. | S06 |
| `M046-RDF-PROJECTION-HARDENING-DECISION.md` | DerivedProjectionReference / BlockedAction | Keep RDF/SHACL/SPARQL custom-only, derived, and non-authoritative. | Claim RDF engine, SHACL engine, SPARQL runtime, ontology correctness, or git-lex runtime proof. | S04/S06 |
| `prd/architecture/architecture_items.jsonl` and `architecture_edges.jsonl` | DerivedProjectionReference | Checked generated registry diagnostics. | Repair by hand-editing derived JSONL or treating as source. | S06 |
| architecture reports and health docs | DerivedProjectionReference / ArchitectureHealthFinding input | Guide remediation and expose diagnostics. | Become source authority. | S03/S06 |
| `prd/architecture/acp/derived/*` | DerivedProjectionReference | Recovery/projection/query/interoperability diagnostics. | Serve as source truth or git-lex compatibility proof. | S04/S06 |
| `prd/project-state/*.md` | DerivedProjectionReference / ArchitectureHealthFinding | Stale M047 orientation package; seed stale-summary findings. | Use as current M048 active milestone, requirement, roadmap, or handoff authority. | S03/S06 |
| `prd/project-state/data/*.json` | DerivedProjectionReference / ArchitectureHealthFinding | Parseable stale-summary diagnostics. | Feed ACP as current requirement truth or active roadmap authority. | S03/S06 |
| `.gsd/exec/*` | BlockedAction / unsafe anchor example | Investigation only before summarized into tracked artifacts. | Durable proof anchor. | S03/S06 |
| git-lex acquisition/runtime path | ArchitectureHealthFinding / BlockedAction / future ProofGate | Sparse evidence seed for isolated S04 proof. | Claim viability or initialize main-repo `.lex`. | S04 |
| main-repo `.lex` absence | BlockedAction | Correct blocked adoption state. | Blind `git lex init` or main-repo `.lex` creation. | S04/S06 |
| durable proof anchor hazards | BlockedAction / EvidenceAnchor rules | Prevent unsafe anchors. | Persist secrets/raw vectors/raw legal text/absolute paths. | S03/S06 |
| law-nexus legal/FalkorDB/parser constraints | ProfileConstraint | Enforce proof-gated profile behavior. | Pollute reusable ACP core or validate R035/R037/R038. | S03/S04/S06 |

## Reusable ACP Core vs law-nexus Profile Split

| Concern | Reusable ACP core | law-nexus profile |
| --- | --- | --- |
| Record taxonomy | Generic `RequirementBinding`, `ArchitectureDecision`, `ArchitecturePromptRecord`, `ArchitectureProposal`, `DecisionCandidate`, `ProofGate`, `EvidenceAnchor`, `ArchitectureHealthFinding`, `DerivedProjectionReference`, `ProfileConstraint`, `BlockedAction`. | Which law-nexus requirements, decisions, LegalGraph claims, Russian legal evidence roles, and FalkorDB/parser/retrieval boundaries instantiate the taxonomy. |
| Source hierarchy | Source records outrank derived projections; projections are rebuildable and non-authoritative. | `.gsd`, PRD, architecture registry, real-document evidence, and legal-source summaries are the concrete source families. |
| Prompt provenance | Captured with safety filtering and non-authoritative status. | MiniMax/GPT/Grok outputs remain context-only unless converted through policy, authority, and proof gates. |
| Proof gates | Gates define evidence obligations and status. | R035/R037/R038, FalkorDB runtime loading, parser completeness, legal correctness, independent review, and retrieval quality require project-specific proof gates. |
| Derived projections | Represented as references with freshness and authority metadata. | JSONL/RDF/SHACL/SPARQL/recovery/project-state outputs remain derived; project-state is currently stale relative to M048. |
| Unsafe actions | Modeled as blocked actions with unblock evidence. | Main-repo `git lex init`, `.lex` state creation, stale project-state authority, and derived-output promotion are explicitly blocked. |
| Evidence anchors | Repo-relative, durable, safety-filtered anchors. | Avoid `.gsd/exec`, ignored paths, raw legal text, raw provider payloads, raw vectors, secrets, and `.gsd` keyFiles closeout hazards. |

## Document Assertions for Future Agents

These assertions are intentionally human- and test-readable.

1. `M048-S01-KNOWLEDGE-BOUNDARY-AUDIT.md` is the input audit for this model.
2. `prd/project-state/*` is stale M047 derived orientation until explicitly refreshed; it is not current M048 authority.
3. Generated architecture JSONL, ACP derived JSON, recovery views, RDF, SHACL, SPARQL, reports, and dashboards are derived projections.
4. Derived projections may be referenced only as `DerivedProjectionReference` or diagnostics unless another source-backed workflow promotes source changes.
5. Current ACP fixtures prove only bounded governance mechanics; they do not prove product, parser, FalkorDB, retrieval, legal, R035, R037, or R038 readiness.
6. A `ProofGate` definition does not satisfy the proof gate.
7. A `DecisionCandidate` is not an accepted `ArchitectureDecision`.
8. `ArchitecturePromptRecord` and external AI context are provenance/context, not authority or proof.
9. `EvidenceAnchor` values must be repository-relative and durable; `.gsd/exec`, absolute paths, ignored paths, raw provider payloads, raw vectors, secrets, and unnecessary raw legal text are blocked.
10. Main-repo `git lex init` and `.lex` state creation remain blocked until S04 isolated proof and later accepted adoption evidence allow them.
11. ACP core stays reusable; law-nexus legal/FalkorDB/parser/LLM/GSD constraints stay in `ProfileConstraint` and profile adapters.
12. This contract does not validate `R035`, `R037`, or `R038`.

## Handoff Checklist for S03

S03 should use this contract to define lifecycle/health categories and checks.

- [ ] Create lifecycle/health categories for `stale_summary`, `sparse_evidence`, `blocked_adoption`, `unsafe_anchor`, `derived_authority_overclaim`, and `profile_boundary_risk`.
- [ ] Seed health findings from S01 `HF-M048-S01-001` through `HF-M048-S01-013`.
- [ ] Encode allowed/blocked actions for every health category.
- [ ] Ensure `DecisionCandidate`, `ProofGate`, and `ArchitecturePromptRecord` stay non-authoritative until authority/proof status changes.
- [ ] Keep law-nexus-specific proof boundaries in profile constraints, not generic ACP core.
- [ ] Preserve stale `prd/project-state/*` visibility instead of silently refreshing it.

## Handoff Checklist for S04

S04 should use this contract to design an isolated git-lex proof without mutating the main repository.

- [ ] Run git-lex proof only in an isolated workspace.
- [ ] Do not run blind `git lex init` in the main checkout.
- [ ] Do not create main-repo `.lex` state.
- [ ] Test whether the core record categories can be represented as typed Markdown/frontmatter and queried/recovered.
- [ ] Verify identity/provenance compatibility separately from product proof.
- [ ] Preserve `DerivedProjectionReference` semantics for git-lex extraction/query stores.
- [ ] Record full, partial, blocked, or deferred adoption evidence without claiming law-nexus binding.

## Handoff Checklist for S06

S06 should verify the milestone did not weaken source/projection boundaries.

- [ ] Confirm no generated JSONL/RDF/recovery/dashboard/project-state output was promoted to source truth.
- [ ] Confirm no `prd/project-state/*` current-state claim was used as M048 authority.
- [ ] Confirm no R035/R037/R038 validation claim was introduced by ACP/git-lex/projection evidence alone.
- [ ] Confirm no main-repo `.lex` state was created by M048 S02-S06 unless later explicitly accepted by proof-backed adoption.
- [ ] Rerun architecture and ACP verifier/projection checks required by the milestone.
- [ ] Confirm evidence anchors are repository-relative, durable, and safety-filtered.
- [ ] Confirm reusable ACP core remains separated from law-nexus profile constraints.

## Failure Modes

| Dependency | Failure path | Expected handling in this contract |
| --- | --- | --- |
| Repository filesystem | Target artifact cannot be created or read. | Bubble the write/read failure; the task is incomplete until `test -s prd/architecture/acp/M048-S02-SOURCE-RECORD-MODEL.md` passes. |
| Source input files | Required S01/prior ACP input is missing or malformed. | Do not invent authority; use only available source-backed content and record missing input as a health finding in a later lifecycle task. |
| Stale derived sources | `prd/project-state/*` or generated projections conflict with GSD/PRD source evidence. | Treat as `DerivedProjectionReference` plus health finding seed; never promote to authority. |
| git-lex runtime/acquisition | Binary/source path is unavailable or unverified. | Keep S04 proof isolated and blocked from main-repo `.lex` adoption until evidence exists. |

## Load Profile


## Negative Tests

| Boundary condition | Document assertion protecting it |
| --- | --- |
| Stale `prd/project-state/*` presented as current M048 authority. | Assertions 2 and 9 plus S01 surface mapping rows for project-state Markdown/JSON. |
| Derived ACP JSONL/RDF/recovery output presented as source truth. | Assertions 3 and 4 plus `DerivedProjectionReference` allowed/blocked rules. |
| ACP fixtures used as product or requirement proof. | Assertion 5 plus fixture mapping row. |
| Proof gate definition confused with proof satisfaction. | Assertion 6 plus `ProofGate` blocked use. |
| Decision candidate promoted without authority. | Assertion 7 plus `DecisionCandidate` blocked use. |
| Prompt/LLM provenance treated as authoritative. | Assertion 8 plus `ArchitecturePromptRecord` blocked use. |
| Unsafe or transient anchors cited as durable proof. | Assertion 9 plus Evidence-Anchor blocked rules. |
| Main-repo git-lex initialized before isolated proof. | Assertion 10 plus S04 checklist. |
| law-nexus profile constraints leaked into reusable ACP core. | Assertion 11 plus core/profile split table. |
| R035/R037/R038 validated by ACP/projection evidence alone. | Assertion 12 plus required non-claims. |

## Observability Impact

This artifact is the durable inspection surface for future agents. It makes project-knowledge authority, evidence-anchor safety, stale/derived surface handling, non-claims, health-finding seeds, and blocked git-lex actions reviewable without requiring runtime logs or metrics changes.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
| --- | --- | --- | --- | --- |
| 1 | `test -s prd/architecture/acp/M048-S02-SOURCE-RECORD-MODEL.md` | 0 | pass | 2ms |
| 2 | `python3 content assertions for required categories, S01 input, non-claims, handoff checklists, and health-finding markers` | 0 | pass | 30ms |
