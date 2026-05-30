# M048 S10 ACP-native Implementation Delta

## Status

Adopted for `M048-q4x62e / S10 / T02` as the ACP-native implementation delta and adapter-boundary record required by `R057` before future law-nexus architecture binding can proceed.

This artifact translates the S10 git-lex adoption decision into implementation boundaries. It is not a code implementation and not a runtime git-lex adoption approval.

## Executive decision

ACP should close M048 with this implementation direction:

```text
Implement required governance mechanics in ACP core, keep ordinary git as the repository baseline, and reserve git-lex for a future isolated adapter proof.
```

Runtime git-lex remains blocked/deferred because S09 did not prove executable availability or record-aware value beyond ordinary git. ACP closure should therefore proceed by making the required authority chain ACP-native:

```text
claim -> typed source record -> lifecycle state -> evidence anchor -> proof gate or accepted decision -> derived projection -> recovery view
```

## Inputs

- `.gsd/milestones/M048-q4x62e/M048-q4x62e-RESEARCH.md`
- `.gsd/milestones/M048-q4x62e/M048-q4x62e-ASSESSMENT.md`
- `prd/architecture/acp/M048-S08-GIT-LEX-CAPABILITY-MATRIX.md`
- `prd/architecture/acp/M048-S08-GIT-LEX-PROOF-CONTRACT.md`
- `prd/architecture/acp/M048-S09-GIT-LEX-FUNCTIONAL-FIT-REPORT.md`
- `prd/architecture/acp/M048-S09-GIT-LEX-RUNTIME-DIAGNOSTICS.md`
- `prd/architecture/acp/M048-S09-INDEPENDENT-PROOF-REVIEW.md`
- `prd/architecture/acp/M048-S10-GIT-LEX-ADOPTION-DECISION.md`

## What ACP already has from M048 evidence

M048 provides bounded, reusable ACP foundations:

1. Source/projection boundary: projections and recovery views are derived and non-authoritative unless backed by source records and proof/decision evidence.
2. Source-record category direction: project knowledge needs typed source-record and evidence-anchor categories.
3. Lifecycle and health model direction: candidate, accepted, blocked, deferred, rejected, stale, and derived states matter for allowed actions.
4. Deterministic fixture evidence: S04/S05/S09 show ACP-native typed records, validation, blocked diagnostics, lifecycle/proof-gate checks, projection boundary checks, and recovery chains can be represented without runtime git-lex.
5. Mutation safety rule: no blind `git lex init`, no main-repository `.lex` state, and no hidden clone/install/download/build path.
6. Core/profile separation: reusable ACP core must not absorb law-nexus-specific Russian legal, parser, FalkorDB, LLM-authority, or `R035`/`R037`/`R038` proof obligations.

## Concepts to absorb from git-lex work

These are useful concepts from the git-lex investigation, but they should be implemented as ACP-native policy/mechanics rather than as a runtime git-lex dependency:

| Concept to absorb | ACP-native interpretation | Why not runtime git-lex now |
|---|---|---|
| Record-oriented repository thinking | Treat architecture knowledge as typed records with stable IDs, schemas, lifecycle states, anchors, and transitions. | S09 did not prove runtime git-lex availability or record-aware operations. |
| Isolation-first runtime experimentation | Any backend that creates repository state must run in an isolated workspace with rollback and cleanup evidence. | The main checkout must remain free of `.lex`; runtime acquisition is blocked. |
| Blocked diagnostics as first-class results | Unsupported runtime and failed proof paths become durable health findings, not hidden logs or optimistic passes. | `UnsupportedGitLexRuntime` is evidence for blocking/deferment, not adoption. |
| Derived views as navigational aids | Projections, dashboards, RDF/JSONL, recovery views, and git-lex outputs may aid inspection but cannot become source truth. | Runtime/projection shape does not satisfy authority by itself. |
| Adapter-friendly backend seam | ACP can leave a future integration seam for record-aware repository backends. | The seam must not block ACP core closure or mutate the main repo. |

## ACP-native implementation delta

### Core P0 mechanics to implement

| Delta | Required behavior | Acceptance signal | Source requirement/decision |
|---|---|---|---|
| Typed source-record schema | Records have kind, stable ID, schema version, source category, lifecycle state, owner/profile boundary, evidence anchors, and proof/decision links. | A record missing authority fields is invalid or candidate-only, not accepted. | `R041`, `R055`, `R056`, `D072` |
| Validation engine | Validate required fields, lifecycle values, anchor shape/resolution, proof-gate references, projection markers, and blocked-action rules. | Invalid or shape-only artifacts produce deterministic diagnostics. | `R055`, `R056` |
| Lifecycle state machine | Enforce allowed transitions among candidate, accepted, blocked, deferred, rejected, stale, and derived states. | State changes require rationale and evidence/proof/decision references. | `R042`, `R055` |
| Proof-gate model | Separate proof-gate definition from proof execution and accepted decision. | A requirement or architecture claim cannot be promoted by a gate definition or projection alone. | `R055`, `R057` |
| Evidence-anchor resolver | Resolve repo-relative anchors and classify unsupported/transient/unsafe anchors. | Cold-reader recovery can locate durable proof surfaces. | `R041`, `R056` |
| Derived projection controls | Mark generated outputs as derived, track source records, detect stale/manual-edited projection drift, and prevent projection-as-source promotion. | Projection mutation or staleness is a health finding, not authority. | `R046`, `D072` |
| Health findings | Persist `ImitativeArtifact`, `BlockedCapability`, `UnsupportedGitLexRuntime`, `UnsafeMutation`, and `InsufficientEvidence` findings. | Blocked/unsafe states appear in durable recovery output. | `R042`, `R055`, `R056` |
| Recovery queries | Recover source record, lifecycle state, evidence anchor, proof gate, accepted decision, derived projections, dependents, and blocked findings. | A future agent can explain why a claim is accepted, blocked, deferred, or rejected without transient logs. | `R056`, `R057` |

### P1/P2 mechanics to stage after core closure

| Delta | Required behavior | Staging rule |
|---|---|---|
| Transition history ledger | Record previous state, new state, rationale, actor/tool, evidence, decision/proof link, and supersession relationship. | Implement after P0 validation/lifecycle are stable if not included in the first core cut. |
| Record-aware diff/review helpers | Produce ACP-aware summaries over ordinary git diffs and record transitions. | Use ordinary git as baseline; do not require git-lex. |
| Adapter interface | Define a backend-neutral interface for optional record/projection import/export and runtime diagnostics. | Keep interface narrow and fail-closed; no backend may be authoritative by output shape. |
| Profile-specific gates | Bind law-nexus checks for Russian legal evidence, parser completeness, FalkorDB, retrieval, and LLM authority. | Keep in profile layer; never move `R035`/`R037`/`R038` into generic ACP core. |

## Adapter boundaries

### ACP core owns

- Record schema and lifecycle semantics.
- Authority rule and anti-imitation checks.
- Evidence-anchor model.
- Proof-gate definition/execution/decision separation.
- Health finding taxonomy.
- Derived projection boundary and freshness checks.
- Recovery/query semantics over authoritative source records and derived views.
- No-main-repo mutation policy for repository-state backends.

### git-lex adapter may own later

Only after a separate isolated proof, a git-lex adapter may provide:

- import/export between git-lex records or views and ACP source records;
- optional record-aware diff/history/conflict diagnostics;
- optional projection generation;
- runtime capability diagnostics;
- backend-specific health findings.

A git-lex adapter must not own:

- ACP authority decisions;
- requirement validation;
- source truth status;
- law-nexus profile proof gates;
- main-repository `.lex` initialization policy;
- unreviewed clone/install/download/build behavior.

### law-nexus profile owns

- Russian legal evidence constraints.
- Parser/source-corpus proof boundaries.
- FalkorDB ingest/runtime and graph-vector proof gates.
- LLM non-authority and legal-answer safety constraints.
- `R035`, `R037`, and standing `R038` review obligations.

These are not reusable ACP core semantics.

## No-main-repo mutation rule

ACP closure preserves the following hard rule:

```text
Do not run blind git lex init, do not create or mutate .lex state in /root/law-nexus, and do not clone/install/download/durably build git-lex from ACP closure tasks without an explicit future proof plan and adoption decision.
```

Any future runtime backend proof must record:

1. `.lex` absence in the main checkout before proof;
2. isolated workspace path and cleanup/rollback strategy;
3. executable provenance and acquisition approval;
4. representative operation results;
5. source/projection authority preservation;
6. `.lex` absence in the main checkout after proof;
7. durable diagnostics for blocked/fail states.

Failure of any mutation guard is an `UnsafeMutation` health finding and blocks adoption.

## Future law-nexus binding prerequisites

Downstream law-nexus architecture binding remains blocked until all of the following are true:

| Prerequisite | Required evidence |
|---|---|
| Per-capability git-lex disposition recorded | `M048-S10-GIT-LEX-ADOPTION-DECISION.md` exists and preserves no-runtime-adoption, ACP-native, adapter-later, rejected, and blocked classifications. |
| ACP-native delta recorded | This artifact defines core implementation needs, adapter boundaries, mutation rule, and profile separation. |
| Closure package recorded | S10 final package must tie adoption decision and delta to `R055`/`R056`/`R057` and list allowed/blocked next steps. |
| No source/projection overclaim | No closure artifact treats git-lex, JSONL, RDF, dashboard, recovery view, or GSD summary as authority by shape. |
| No main-repo git-lex state | Main checkout remains free of `.lex` unless a future explicit adoption decision changes policy. |
| Profile constraints preserved | `R035`, `R037`, and `R038` remain profile/proof obligations and are not validated by ACP closure. |

## Implementation backlog shape

The next implementation milestone should be a narrow ACP core milestone, not law-nexus binding. Suggested order:

1. Define ACP record schema and authority fields.
2. Implement validation and anti-imitation diagnostics.
3. Implement lifecycle transitions and transition history.
4. Implement proof-gate records and execution evidence links.
5. Implement projection freshness/source-boundary checks.
6. Implement recovery query/report over records, evidence, proofs, decisions, projections, and health findings.
7. Define the adapter interface and a stub git-lex adapter that reports `UnsupportedGitLexRuntime` until a separate proof enables it.
8. Only then plan law-nexus profile binding.

## Non-claims

This delta does not claim:

- runtime git-lex is installed, available, adopted, or safe to initialize;
- git-lex adds proven value beyond ordinary git;
- ACP closure validates `R035`, `R037`, or `R038`;
- generated projections, dashboards, recovery views, JSONL/RDF, git-lex views, or polished summaries are source truth;
- law-nexus architecture binding may start before the S10 closure package.

## Closeout delta

`Implement ACP-native authority, validation, lifecycle, proof, projection-boundary, health, and recovery mechanics; absorb isolation and blocked-diagnostic discipline; keep git-lex behind a future adapter proof; preserve the no-main-repo mutation rule; require ACP closure before law-nexus binding.`
