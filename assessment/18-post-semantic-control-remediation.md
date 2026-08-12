# Post-semantic-control remediation assessment

**Assessment date:** 2026-08-12  
**Base before remediation:** `98381623f69107f20b403d7e05503308762d0bdd`  
**Presentation-control commit:** `0cbe21c`  
**Lifecycle:** `[bounded]` repository-document/process assessment  
**Role:** non-authoritative disposition; not successor acceptance or product proof  

## 1. Scope and authority

This assessment follows the glossary audit in assessment 17 and rechecks the
remaining safely remediable findings from the recovered 2026-08-11 criticism.
Canonical authority remains `prd/ARCHITECTURE.md` plus active `doc/adr/**`.
Governor, vocabulary catalogs, this assessment and generated architecture views
remain process evidence only.

D150 remains bound to packet revision
`120d44be610b20ee537f402140eb3828e8e9a0f4`. Nothing here accepts later HEADs,
closes TSG rows or promotes product lifecycle.

## 2. Completed bounded remediation

### 2.1 Temporal vocabulary presentation control

`temporal-vocabulary-presentation-drift` now warns on a bounded tracked-path
allowlist when:

- a deferred term appears with implementation/publication cues and lacks a
  future/deferred/historical qualifier;
- a static effective/valid interval field is described with a strong
  source-truth cue and lacks projection/event-sourced qualification;
- practice or another projection is described with sixth-clock-like wording
  without a five-clock/projection qualifier.

The token/cue/qualifier/path policy lives in
`prd/architecture/temporal-vocabulary-contract.json`, not Python source. This
preserves ADR-0007: the Python harness evaluates repository-control data and
contains no product-domain vocabulary rules.

Malformed policy is a tool error. Findings are heuristic `warn` only and require
human disposition. A green result is not semantic or legal validation.

### 2.2 Corrected active wording

| Surface | Corrected drift |
|---------|-----------------|
| ADR-0005 | historical/superseded `SourceBlock` names are explicitly legacy planning, not the future evidence type or parser `SourceBlockRecord` |
| ADR-0013 | future `EvidenceSpan` use is explicitly future-schema and `deferred-undefined` |
| ADR-0020 | practice uses first-class temporality over the five clocks; residual “own clock” wording no longer trains a sixth core clock |
| Rust migration roadmap | R7 names future-schema `EvidenceSpan` only after an owning evidence contract |
| project-state roadmap | downstream citation row states that no public `EvidenceSpan` type exists and confines current evidence to InMemory retrieval |

### 2.3 Derived readiness view quarantine

The generated `product_readiness_blockers.md` surface no longer presents the
D7-quarantined registry as a current priority queue:

- title and scope classify it as a historical registry archaeology index;
- P0–P3 values are historical metadata, not current triage;
- gate and evidence rows are explicitly historical;
- old verification text is retained for traceability, not “next proof work”;
- current planning is redirected to the living oracle, Product/Requirements,
  TL-G01–12, TSG and the parser protocol.

Legacy IDs and non-claims remain available for old assessment references. The
generator and tests own this classification, so regeneration cannot silently
restore current-looking readiness prose.

### 2.4 Fourteen-area temporal-contract matrix

`prd/temporal-legal-model.md` now explicitly accounts for all fourteen areas in
the primary criticism:

- glossary;
- entity model;
- event taxonomy;
- temporal axes;
- applicability DSL;
- status;
- provenance;
- conflict;
- correction;
- invariants;
- deterministic API;
- golden cases;
- error taxonomy;
- proof gates.

Each row is marked `present`, paper-qualified `present`, `partial`, `absent` or
`deferred-undefined` and routes to an owning ADR/TSG. No concrete event enum, API signature, error enum,
DSL field or legal expected result was invented.

## 3. Still unresolved from the criticism

### 3.1 Human semantic decisions

| Gap | Why not automated |
|-----|-------------------|
| Split ADR-0021 transition versus risk | changes ownership and lifecycle; EA clarification separates behavior but not ADR authority |
| Accept TextChange/NormativeEffect event taxonomy | load-bearing ontology choice; current names are stop-signals only |
| Define NormRule IR and Condition/Effect/Exception/Defeater roles | changes semantic kernel/application boundaries |
| Define ApplicabilitySelector AST/DSL | ADR-0023 owns protocol boundaries only; no accepted field/schema design |
| Define deterministic temporal API and unified errors | would create de-facto public compatibility contract |
| TQ-04 correction owner and TQ-05 reference owner | authority and audit/citation consequences |
| Choose post-M165 sequence | parser-G2-first, CTV-first and infrastructure-first have different investment/dependency effects |
| Choose clean-tree comparison base and Stage D consumer | changes CI semantics and human acceptance flow |
| Successor acceptance of current HEAD | human authority act; cannot be inferred from green checks |

### 3.2 Rust and real-evidence work

Documentation cannot implement or validate:

- event-sourced CTV operations and membership versioning;
- NormativeState runtime;
- NormRule graph;
- applicability ports/evaluator/trace;
- competence and jurisdiction conflict graph;
- practice coverage outcomes;
- transition/risk/profile/procurement runtime;
- immutable correction ledger and temporal reference resolver;
- deterministic API contracts in Rust;
- parser G2 independently reviewed multi-fixture corpus;
- executable temporal legal goldens;
- live RuVector/TEI storage/retrieval and citation-safe evidence;
- KnowQL execution and release-class proof.

### 3.3 Golden-case gap

The project has 18 paper semantic-shape cases. The criticism requested 20–30
cases with complete machine traces. The current cases remain below that range
and are not executable legal gold. Adding legal outcomes, thresholds or
representativeness criteria requires human-reviewed source-bound gold and Rust
execution evidence.

## 4. Further safe advisory backlog

Only two process improvements remain potentially safe without semantic choice:

1. L1–L7/O1–O7 alias-note continuity on a narrow living-surface allowlist;
2. a human disposition ledger for Stage D heuristic findings after a concrete
   consumer and interaction contract are selected.

Commit-range/clean-tree freshness must wait for a human comparison-base policy.
No free-text semantic check should become blocking by default.

## 5. Difficulty assessment

| Work | Difficulty | Primary risk |
|------|------------|--------------|
| alias-note continuity | low | false positives in historical prose |
| Stage D disposition ledger | medium | authority laundering without named human consumer |
| temporal API/event paper decision | high | premature public schema and ontology freeze |
| ADR-0021 split | high | ownership/lifecycle migration |
| parser G2 corpus | high | independent annotation, representativeness and legal review cost |
| CTV/NormRule/applicability runtime | very high | coupled identity, temporal, evidence and legal semantics |
| representative legal validation | very high | corpus rights, expert review, disputed gold and lifecycle acceptance |

## 6. Bounded conclusion

The remaining safely automatable causes of terminology drift and readiness-view
misleading presentation are closed in repository-control scope. The temporal
contract now states its own incompleteness rather than hiding absent sections.

The residual critique is predominantly no longer a documentation-cleanup
problem. It is either a human architecture/legal decision or Rust/real-evidence
implementation work. Further prose without those decisions or proofs would
create false completeness rather than reduce risk.
