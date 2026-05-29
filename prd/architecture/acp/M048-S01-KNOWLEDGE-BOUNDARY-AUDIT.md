# M048 S01 GSD and Project-State Knowledge Boundary Audit

**Status:** Accepted S01 audit artifact for `M048-q4x62e / S01`.

## Verdict

The current ACP and architecture projection surfaces are technically fresh, but the project knowledge base has an authority-boundary mismatch:

- GSD artifacts identify `M048-q4x62e` as the active milestone and include active requirements `R040`-`R048` for ACP/git-lex work.
- The `prd/project-state/*` package is a derived M047 cold-reader package and still describes M047 as active, recommends ACP Decision Lifecycle Workflow as the next milestone, and lists only `R035`, `R037`, and `R038` as active requirements.

Therefore `prd/project-state/*` must be treated as a stale derived summary until refreshed by an explicit later workflow. The stale state is a health finding, not a reason to silently rewrite project-state files during S01.

## Scope

This audit classifies current project knowledge surfaces as:

- authoritative or source-authoritative;
- derived and non-authoritative;
- stale;
- sparse;
- ACP/git-lex source-record candidates.

It does not initialize git-lex, update generated projections, refresh the M047 project-state package, validate `R035`, `R037`, or `R038`, or bind the full law-nexus architecture into ACP.

## Source-of-truth rule

Authoritative project evidence remains in PRD/GSD/ADR/accepted decision artifacts, source code, tests, runtime proof where runtime behavior is claimed, and real-document evidence where legal-source behavior is claimed.

Generated JSONL, architecture reports, ACP recovery/projection outputs, RDF, SHACL, SPARQL, dashboards, project-state summaries, and future git-lex derived stores are diagnostic/recovery/projection surfaces. They may help find or explain state, but they do not become source truth or requirement-validation proof by themselves.

## Surface classification

### Authoritative or source-authoritative surfaces

| Surface | Classification | Purpose | Audit rule |
| --- | --- | --- | --- |
| `.gsd/PROJECT.md` | Authoritative GSD/project contract | Current project identity, milestone sequence, and project-level guardrails. | May be used as current project-state authority. Do not use generated projections to override it. |
| `.gsd/REQUIREMENTS.md` | Authoritative requirement registry | Active/validated/deferred requirement contract, including `R040`-`R048`. | Requirement status changes must go through GSD requirement tooling, not derived project-state JSON. |
| `.gsd/DECISIONS.md` | Authoritative decision register | Accepted decisions, including `D067`-`D070` for M048 git-lex isolation/proof/integration/binding sequence. | Accepted decisions may seed ACP decision records; decision candidates/projections must not override them. |
| `.gsd/KNOWLEDGE.md` | Authoritative durable project rules | ACP authority boundary, git-lex adoption boundary, law-nexus profile boundary, durable proof-anchor rule. | Treat as project policy input; keep compact and do not inflate it into runtime proof. |
| `.gsd/STATE.md` | Authoritative GSD operational snapshot | Current active milestone and GSD execution state. | Useful for current-state comparison, but do not use `.gsd/exec` as durable proof evidence. |
| `.gsd/milestones/M048-q4x62e/*` | Authoritative M048 execution scope | M048 context, roadmap, research, plans, and summaries. | S01-S06 boundary and acceptance source for this milestone. |
| `prd/architecture/acp/fixtures/minimal-chain/*.md` | ACP source records for governance mechanics | Typed Markdown/frontmatter fixture chain: prompt record, proposal, decision candidate, proof gate, health finding. | Source evidence for ACP governance mechanics only; not product, legal, parser, FalkorDB, retrieval, or R035/R037/R038 proof. |
| `prd/architecture/acp/M041-SOURCE-OWNERSHIP-CONTRACT.md` | ACP source-ownership contract | Precedent for ACP source/projection hierarchy and blocked anchors. | Reuse its ownership and non-claim language for M048 source-record modeling. |
| `prd/architecture/acp/M045-ACP-ADVANCEMENT-ROADMAP.md` | ACP planning contract | Prior ACP advancement phases, including isolated git-lex alignment spike. | Planning evidence only; not implementation proof. |
| `scripts/*acp*.py`, `scripts/export-architecture-rdf-projection.py`, `scripts/verify-architecture-graph.py` | Source code authority for local checker/exporter behavior | Defines current bounded verifier/exporter behavior. | Outputs remain derived. Code changes require normal impact and test verification. |
| `tests/test_acp*.py`, `tests/test_architecture_rdf_projection.py` | Test authority for bounded behavior | Regression coverage for ACP/projection mechanics. | Passing tests prove only the tested bounded behavior, not external git-lex/RDF/SHACL/SPARQL/FalkorDB semantics. |

### Derived and non-authoritative surfaces

| Surface | Classification | Purpose | Audit rule |
| --- | --- | --- | --- |
| `prd/architecture/architecture_items.jsonl`, `prd/architecture/architecture_edges.jsonl` | Derived canonical architecture projection | Machine-readable registry projection for graph checks and generated views. | If wrong or stale, repair source anchors/evidence and regenerate through checked workflows. |
| `prd/architecture/architecture_report.md`, `prd/architecture/architecture_health.md`, `prd/architecture/claims_ledger.md`, and related reports | Derived diagnostics/planning views | Human-readable architecture health and claim-safety diagnostics. | May guide remediation; cannot become source authority. |
| `prd/architecture/acp/derived/*` | Derived ACP recovery/projection outputs | Recovery view, preview projection, custom canonical-shaped outputs, RDF/SHACL/SPARQL projection. | Current by checks, but non-authoritative and not git-lex compatibility proof. |
| `prd/project-state/*.md` | Derived M047 cold-reader summary | Reader-oriented project overview, ACP state, architecture, roadmap, handoff, verification. | Useful orientation package, but stale relative to active M048. Treat current-state claims as diagnostics until refreshed. |
| `prd/project-state/data/*.json` | Derived M047 parseable summary | Machine-readable project-state package. | Stale relative to M048 for active milestone and active requirements. Do not feed ACP as authority without current GSD reconciliation. |
| `.gsd/exec/*` | Transient execution logs | Noisy local command evidence for research/execution. | Never use as durable proof anchor. Summarize results into tracked artifacts instead. |

## Stale surfaces

| ID | Severity | Surface | Finding | Blocked actions | Recommended fix |
| --- | --- | --- | --- | --- | --- |
| HF-M048-S01-001 | high | `prd/project-state/README.md` | Says last completed milestone is M046 and active milestone is M047, while GSD now has M048 active. | Do not use as current active-milestone authority. | Refresh project-state package in a dedicated workflow or annotate it as M047 snapshot. |
| HF-M048-S01-002 | high | `prd/project-state/handoff.md` | Says M047 S05 remains current closeout work and recommends starting ACP Decision Lifecycle Workflow after M047. | Do not use as current handoff for M048 planning. | Create a new handoff after M048 or explicitly mark this as M047 handoff history. |
| HF-M048-S01-003 | high | `prd/project-state/roadmap.md` | Says M047 is active and recommends ACP Decision Lifecycle Workflow as next, while M048 is active and full law-nexus binding is deferred to a later milestone. | Do not use as current roadmap authority. | Refresh after M048 S01-S06 establish ACP/git-lex foundation. |
| HF-M048-S01-004 | high | `prd/project-state/data/project-overview.json` | Reports current phase as M047 and active requirements as only `R035`, `R037`, and `R038`; omits `R040`-`R048`. | Do not feed this JSON into ACP source-record modeling as current requirement truth. | Regenerate from current GSD state only after defining source-record ownership. |
| HF-M048-S01-005 | high | `prd/project-state/data/roadmap.json` | Reports M047 as current and ACP Decision Lifecycle Workflow as next. | Do not use as current milestone sequence authority. | Regenerate or supersede with a tracked M048-aware package. |
| HF-M048-S01-006 | high | `prd/project-state/data/open-requirements.json` | Lists only `R035`, `R037`, and `R038` as active. | Do not use as active requirements authority. | Rebuild from `.gsd/REQUIREMENTS.md` after source-record model is defined. |
| HF-M048-S01-007 | medium | `prd/project-state/data/verification-matrix.json` | Verification recency points to M046/M047 evidence, not current M048 S01 baseline. | Do not claim M048 verification from this matrix. | Refresh after final M048 verification or create a separate M048 verification matrix. |

## Sparse surfaces

| ID | Severity | Surface | Finding | Blocked actions | Recommended fix |
| --- | --- | --- | --- | --- | --- |
| HF-M048-S01-008 | high | git-lex acquisition/runtime path | The exact git-lex source/binary path for M048 proof is not confirmed in current tracked project-state. | Do not claim git-lex viability or initialize git-lex in the main repository. | S04 must run isolated proof or record blocked diagnostics. |
| HF-M048-S01-009 | medium | ACP fixture chain | Existing ACP source record chain has five records and one safe governance decision. This is enough for mechanics proof, but sparse for general lifecycle/health governance. | Do not generalize full ACP lifecycle coverage from the minimal chain. | S02/S03 should define source-record and lifecycle/health categories before broader adoption. |
| HF-M048-S01-010 | medium | project-state M048 representation | The M047 project-state package has no current M048/R040-R048 representation. | Do not treat the package as current ACP/git-lex planning state. | Refresh project-state only after M048 boundaries and adoption decision are stable. |

## Unsafe or blocked surfaces

| ID | Severity | Surface | Finding | Blocked actions | Recommended fix |
| --- | --- | --- | --- | --- | --- |
| HF-M048-S01-011 | critical | main repository git-lex state | No main-repo `.lex` adoption state is present, and that absence is correct until isolated proof and explicit adoption decision. | Do not run blind `git lex init`; do not create `.lex` state in the main checkout. | S04 must use an isolated workspace; S05 must record evidence-backed full/partial/deferred adoption. |
| HF-M048-S01-012 | critical | derived ACP/RDF/JSONL/recovery views | Derived outputs are current but non-authoritative. | Do not validate `R035`, `R037`, or `R038` from ACP/git-lex/projection evidence alone. | Keep non-claims in every downstream source-record/projection contract. |
| HF-M048-S01-013 | high | durable proof anchors | `.gsd/exec`, absolute paths, ignored paths, raw provider payloads, raw vectors, secrets, and unnecessary raw legal text are unsafe durable proof anchors. | Do not cite them as durable ACP evidence. | Use tracked repository-relative anchors and summarize transient command results in tracked artifacts. |

## ACP/git-lex source-record candidates

| Candidate | Candidate ACP category | Source value | Boundary |
| --- | --- | --- | --- |
| `.gsd/REQUIREMENTS.md` entries `R040`-`R048` | Requirement/evidence-anchor source records | Defines the M048 capability contract. | Requirement status remains owned by GSD tooling. |
| `.gsd/DECISIONS.md` entries `D067`-`D070` | Accepted architecture/process decisions | Defines isolated git-lex proof, semantic proof threshold, evidence-backed integration, and deferred law-nexus binding. | ACP may model decisions, but must not invent acceptance. |
| `prd/architecture/acp/fixtures/minimal-chain/APR-0001.md` | Architecture prompt/provenance record | Existing typed ACP prompt fixture. | Provenance only; no implementation proof. |
| `prd/architecture/acp/fixtures/minimal-chain/AP-0001.md` | Architecture proposal | Existing ACP proposal fixture. | Proposal only; not accepted architecture. |
| `prd/architecture/acp/fixtures/minimal-chain/DC-0001.md` | Decision candidate | Existing ACP decision-candidate fixture. | Requires authority; not an accepted decision. |
| `prd/architecture/acp/fixtures/minimal-chain/PG-0001.md` | Proof gate | Existing ACP proof-gate fixture. | Gate definition does not satisfy the gate. |
| `prd/architecture/acp/fixtures/minimal-chain/AHF-0001.md` | Architecture health finding | Existing ACP health finding fixture. | Diagnostic/blocker only; not proof of readiness. |
| `prd/architecture/acp/M041-SOURCE-OWNERSHIP-CONTRACT.md` | ACP source ownership contract | Defines allowed/blocked anchors and source/projection rules. | Contract evidence, not runtime proof. |
| `prd/research/architecture/architecture-control-plane-contract.md` | ACP core design input | Defines reusable ACP record/lifecycle model. | Research/design input; requires implementation proof. |
| `prd/research/architecture/git-lex-mechanics-for-architecture-control-plane.md` | git-lex mechanics design input | Maps git-lex mechanics to ACP goals. | Research input; S04 must verify in isolation. |
| `prd/research/architecture/law-nexus-acp-profile-and-first-proof-plan.md` | law-nexus profile design input | Defines profile boundaries for legal/FalkorDB/parser claims. | Profile guidance; must not pollute reusable ACP core. |

## Required non-claims

This audit does not validate:

- `R035` ontology architecture proof boundaries;
- `R037` FalkorDB graph ingestion/runtime loading path;
- `R038` independent review gate satisfaction;
- parser completeness;
- legal correctness;
- FalkorDB ingestion or production readiness;
- graph-vector retrieval quality;
- generated-Cypher safety;
- RDF engine correctness;
- SHACL engine validation;
- SPARQL runtime behavior;
- git-lex compatibility or adoption readiness.

## Blocked actions

- Do not initialize git-lex or create `.lex` state in the main repository.
- Do not treat generated ACP JSONL, RDF, SHACL, SPARQL, dashboards, or recovery views as source truth.
- Do not validate `R035`, `R037`, or `R038` from ACP/git-lex/projection evidence alone.
- Do not use `prd/project-state/*` current-state fields as authoritative until refreshed from current GSD state.
- Do not use `.gsd/exec`, absolute local paths, ignored paths, raw provider payloads, raw vectors, secrets, or unnecessary raw legal text as durable ACP proof anchors.
- Do not move law-nexus-specific legal/FalkorDB/parser constraints into generic ACP core.

## Allowed actions

- Use this audit as S02 input for ACP source-record/evidence-anchor category design.
- Use health findings in this audit as S03 input for lifecycle/health category design.
- Use the current verifier/projection pass state as bounded operational evidence that existing derived surfaces are fresh within their current scope.
- Keep `prd/project-state/*` stale status visible until a deliberate project-state refresh is planned.
- Run git-lex proof only in an isolated workspace during S04.

## Verification snapshot

S01 research and implementation verified that current bounded ACP and architecture checks pass:

```text
uv run python scripts/verify-architecture-graph.py                   PASS
uv run python scripts/verify-acp-records.py                         PASS
uv run python scripts/export-acp-recovery-view.py --check            PASS
uv run python scripts/export-acp-architecture-projection.py --check  PASS
uv run python scripts/export-architecture-rdf-projection.py --check  PASS
uv run python scripts/export-architecture-rdf-projection.py --diff   PASS
```

These passes mean current derived artifacts are fresh within their existing verifier contracts. They do not promote any derived surface to authority and do not validate git-lex compatibility.

## Handoff to S02

S02 should define ACP source-record and evidence-anchor categories using this audit as input. The source-record model should explicitly represent:

- authoritative requirement records;
- accepted decision records;
- prompt/provenance records;
- proposals;
- decision candidates;
- proof gates;
- evidence anchors;
- health findings;
- derived projection references;
- stale summary findings;
- profile-specific blocked actions.

S02 should preserve the rule that derived project-state summaries and generated projections can be referenced as diagnostics, but cannot become source truth.

## Handoff to S03

S03 should use the health findings above as seeds for lifecycle/health categories. At minimum it should model:

- `stale_summary`;
- `sparse_evidence`;
- `blocked_adoption`;
- `unsafe_anchor`;
- `derived_authority_overclaim`;
- `profile_boundary_risk`.

S03 should define allowed and blocked actions for each category and keep law-nexus-specific constraints in the profile/adapter layer.

## Handoff to S04

S04 must not use this audit as git-lex proof. It should use the source-record candidates and blocked-action list to design an isolated git-lex workspace proof that checks typed records, validation, extraction/projection, query/recovery, lifecycle/proof-gate representation, and profile-boundary compatibility.

## Handoff to S05/S06

S05 should base git-lex adoption on isolated proof evidence only. S06 should rerun the architecture and ACP verifier/projection checks and confirm that no source/projection boundary was weakened during M048.
