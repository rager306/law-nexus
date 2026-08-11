# law-nexus Product Contract

**Document status:** `[proposed]` Product Contract; document state `ready-for-assessment`
**Planning baseline:** `60fd8245ace999f3f29911844375dd7cc36a2a38` (2026-08-11)
**EA-02 tested revision:** `37f82c4245642f7c1e9104f288db43df762178fe` (`assessment/02-product-contract.md`)
**Authority:** canonical product intent (A3) once accepted; architecture state remains governed by `prd/ARCHITECTURE.md` and `doc/adr/**`
**Requirements projection:** `prd/REQUIREMENTS.md`
**Non-claim:** publication of this contract does not validate product runtime, legal correctness, corpus coverage, or release readiness
**Ontology alias:** this contract uses O1–O7 for ADR-0016–0022; `prd/ARCHITECTURE.md` currently labels the same design sequence L1–L7

## 1. Product purpose

law-nexus is intended to help humans inspect Russian normative acts as immutable, source-anchored evidence and obtain deterministic structural, temporal, retrieval, and citation outcomes at explicitly bounded proof levels.

The product is evidence tooling, not a legal authority. It must abstain rather than invent legal, temporal, applicability, or citation certainty. Rust owns product behavior. The Python repository harness owns process gates only.

## 2. Personas and human authority

| Persona | Primary work | Authority boundary |
|---------|--------------|--------------------|
| Evidence engineer | ingest provider sources, run decode/inspect, review diagnostics | prepares evidence candidates; cannot mint legal authority |
| Corpus curator | select material eligible for promotion | human promotion decision within ADR-0008 controls |
| Publication reviewer | accept complete units for authoritative publication | human publication decision; independent from promotion authority |
| Legal researcher or analyst | ask bounded structural, temporal, retrieval and citation questions | consumes evidence outcomes; retains responsibility for legal interpretation |
| Architecture/process governor | maintain ADR, D098 and repository-control honesty | process authority only; not legal or product acceptance authority |
| Independent assessor | review a frozen documentation packet | document/process disposition only; cannot validate product or law |

LLM output is advisory. It cannot produce authoritative promotion, publication, citation, applicability, requirement-satisfaction, lifecycle-promotion, or release decisions.

## 3. Primary user loops

### UL-01 Source intake and decode `[bounded]`

1. Observe immutable source bytes and provenance.
2. Select a provider-isolated decoder.
3. Emit structural and lexical candidates with spans and diagnostics.
4. Return typed failure or incomplete outcomes for hostile or insufficient input.

Provider isolation is mandatory: Consultant WordML and Garant ODT fixtures and assumptions must not be mixed.

### UL-02 Evidence admission and authority `[bounded]`

1. Assert identity without unsafe cross-family merge.
2. validate relations against a closed registry;
3. promote eligible evidence through a singular promotion authority;
4. publish only complete units through a distinct publication authority;
5. reject dual-writer, incomplete and direct provisional-to-authoritative paths.

### UL-03 Evidence-bounded query and citation `[bounded]`

1. Query admitted evidence with explicit source and temporal constraints.
2. Return candidates with provenance and adapter-true scores.
3. Resolve citations to source spans when available.
4. Return `Unknown`, `Conflict`, `Incomplete` or typed rejection when evidence is insufficient.

This loop does not claim production retrieval quality, real-corpus citation safety, or legal-answer correctness.

### UL-04 Temporal legal applicability `[deferred]`

The intended future chain is:

```text
NormRule
→ ApplicabilityPredicate
→ CaseFacts
→ ApplicabilityDecision
→ ExplainableTrace
```

ADR-0023 decides ownership at `[proposed]` design level: the neutral core owns evaluation/decision/abstention/trace and profiles supply versioned inputs. This executable chain still does not exist in the current product. ADR-0016–0022 provide the O1–O7 `[proposed]` prerequisite design spine.

### UL-05 Industry proving profiles `[proposed]`

Procurement and other domains may specialize neutral core inputs and rules. Procurement is a proving profile, not a second core ontology and not evidence of legal completeness.

## 4. Typed input contract

| Input | Required content | Failure boundary |
|-------|------------------|------------------|
| `SourceBytes` | immutable bytes, hash, source/provider identifier | missing or mutable provenance rejects authority-bearing processing |
| `ObservationContext` | observation identity and available clock anchors | missing anchor remains `Unknown`; clocks are not substituted silently |
| `DecodeRequest` | source format and explicit provider adapter | unsupported/ambiguous provider returns typed rejection |
| `QueryRequest` | scope, source constraints, temporal constraints, citation requirement | underspecified request yields diagnostic/abstention, not inferred legal intent |
| `HumanDecision` | actor role, decision kind, evidence reference | cannot be inferred from model prose or tool success |
| `ProfileFacts` | versioned domain facts with provenance | profile facts cannot mutate neutral core semantics |

## 5. Typed output and abstention contract

| Outcome | Meaning | Authority effect |
|---------|---------|------------------|
| `WorkflowAccepted` | deterministic success in a declared bounded scope | advances only the named workflow transition; distinct from human/document acceptance |
| `Unknown` | missing provenance, anchor, state or evidence | no positive legal/temporal/applicability assertion |
| `Conflict` | irreconcilable competing evidence or authority state | expose conflict and reason; do not choose silently |
| `Incomplete` | completeness gate not satisfied | remains non-authoritative |
| `Rejected` | hostile or policy-invalid input/transition | preserve typed reason and unchanged prior state |
| `Provisional` | acceleration or candidate output | cannot be directly promoted to authoritative state |
| `DiagnosticOnly` | process/operator information | never treated as legal or publication authority |

Infrastructure failures and invalid input shapes are errors. `Unknown`, `Conflict` and `Incomplete` are successful fail-closed product outcomes when evidence is insufficient.

## 6. Product clauses

The lifecycle shown is the current maximum honest ceiling, not an implementation target. Requirement links are canonical in §11 rather than duplicated in the clause tables; every PC row must resolve there to at least one RQ row.

### Capability clauses

| ID | Obligation | Lifecycle | Proof class | Governing ADRs | Acceptance | Hostile acceptance | Non-claim |
|----|------------|-----------|-------------|----------------|------------|--------------------|-----------|
| PC-001 | Product behavior is owned by the Rust `ln-*` runtime; Python remains repository control-plane only | `[bounded]` product / `[validated]` harness boundary | `static-invariant` + `process-gate` | ADR-0004, 0005, 0007, 0011 | active product composition is Rust; harness contains no domain logic | forbidden Python product imports and PyO3/FFI fail repository gates | does not prove product completeness |
| PC-002 | Decode supported Russian legal-source formats through provider-isolated adapters | `[bounded]` | `port-contract` + limited fixture tests | ADR-0013, 0015 | each provider has independent positive and hostile tests with valid spans | Consultant assumptions cannot satisfy Garant tests and vice versa | no parser completeness, parity or corpus coverage |
| PC-003 | Evidence identity, lifecycle and relation gates fail closed | `[bounded]` | `synthetic-hostile` | ADR-0010, 0011, 0015 | identity overwrite, unsafe merge and unregistered relation are rejected with typed outcomes | prior accepted state remains unchanged after hostile input | no legal correctness or production-storage claim |
| PC-004 | Promotion and publication use distinct singular human authorities | `[bounded]` | `synthetic-hostile` | ADR-0008, 0011 | complete units alone can follow accepted promotion/publication transitions | dual writer, incomplete unit and direct provisional promotion are rejected | acceptance does not prove legal correctness |
| PC-005 | Citation resolution is source-anchored and fail closed | `[bounded]` | `port-contract` + `synthetic-hostile` | ADR-0010, 0011, 0015 | resolved citation identifies tracked source/span provenance | missing or invalid span never becomes an exact citation | no real-corpus citation-safe answer claim |
| PC-006 | Query outcomes remain bounded by admitted evidence and provenance | `[bounded]` | `port-contract` + `synthetic-hostile` | ADR-0011, 0015 | result carries source/provenance and real adapter score semantics | missing admission/provenance produces non-authoritative outcome | no production retrieval or RuVector runtime claim |
| PC-007 | Five-clock anchors prevent silent temporal substitution | `[bounded]` | `synthetic-hostile` | ADR-0009, 0011 | available anchors are preserved by role | missing/competing anchors yield `Unknown`/`Conflict`, never a silently substituted positive temporal outcome | no computed legal applicability or CTV runtime claim |
| PC-008 | O1–O7 temporal legal ontology remains an explicit design spine | `[proposed]` | `none-design` | ADR-0016, ADR-0017, ADR-0018, ADR-0019, ADR-0020, ADR-0021, ADR-0022 | each layer has scope, invariants and future graduation criteria | no layer is represented as implemented from documentation alone | no ontology runtime or R035 validation |
| PC-009 | Applicability uses a future typed `NormRule → … → ExplainableTrace` protocol | `[deferred]` | `none-design` | ADR-0023 + ADR-0017–0022 prerequisites | ownership is decided; neutral core decision/abstention/trace consumes versioned profile inputs; runtime absence and abstention remain explicit | no current surface may claim case applicability from temporal phrases, CTV, `InForce`, profile code, derived graph or LLM | executable applicability is absent |
| PC-010 | Procurement remains a proving profile over a neutral core | `[proposed]` | `none-design` | ADR-0022, 0023, 0015 | profile facts/predicate declarations are versioned/provenanced and do not redefine core outcomes | provider/profile assumptions cannot leak into neutral kernel or emit final decisions outside core protocol | no implemented procurement profile or legal completeness |

### Quality and safety clauses

| ID | Obligation | Lifecycle | Proof class | Governing ADRs | Acceptance | Hostile acceptance | Non-claim |
|----|------------|-----------|-------------|----------------|------------|--------------------|-----------|
| PC-011 | Consequential claims preserve D098 lifecycle and proof ceilings | `[bounded]` process | `process-gate` | ADR-0012, 0015 + `prd/ARCHITECTURE.md` | claims identify lifecycle, proof class and non-claims | bounded/smoke evidence cannot be reported as validated | process conformance is not product validation |
| PC-012 | Changed behavior requires positive semantics and a relevant fail/diagnostic path | `[bounded]` | `port-contract` or `synthetic-hostile` | ADR-0011, 0015 | tests assert outcomes, state and provenance | compilation or mock call order alone cannot satisfy the clause | not release-class proof |
| PC-013 | Legal, temporal and citation uncertainty must abstain fail closed | `[bounded]` kernel / `[proposed]` ontology | `synthetic-hostile` | ADR-0009, 0010, 0015, 0017–0021 | missing evidence returns a typed non-success | no default applicable/in-force/low-risk inference | no production legal-safety validation |
| PC-014 | LLM text, semantic similarity and derived reports are non-authoritative | `[bounded]` policy | `static-invariant` + human review | ADR-0012, 0015 + `prd/ARCHITECTURE.md` | authority-bearing gates require deterministic evidence/human decision | model agreement alone cannot satisfy a clause | assistive tooling is not prohibited outside authority paths |
| PC-015 | Human reviewers retain promotion, publication and legal-interpretation authority | `[bounded]` | `synthetic-hostile` + process contract | ADR-0008, 0011 | system cannot self-mint authority | provisional/incomplete/model output cannot bypass human boundary | not legal advice and not human-judgment automation |
| PC-016 | Product and assessment surfaces preserve explicit legal-readiness non-claims | `[proposed]` contract constraint | `none-design` | `prd/ARCHITECTURE.md` | every readiness/assessment surface states its bounded scope | documentation PASS cannot become product/legal validation | legal correctness and case applicability are not claimed |

### Operability and release clauses

| ID | Obligation | Lifecycle | Proof class | Governing ADRs | Acceptance | Hostile acceptance | Non-claim |
|----|------------|-----------|-------------|----------------|------------|--------------------|-----------|
| PC-017 | Operator diagnostics expose useful failure context without authority leakage | `[bounded]` | `synthetic-hostile` | ADR-0011, 0015 | typed reason and relevant context are observable | secrets, unnecessary raw legal text and authority claims are absent | no full observability-platform maturity |
| PC-018 | CLI composition exposes bounded health/inspect workflows | `[bounded]` | `port-contract` + limited smoke | ADR-0005, 0013, 0015 | user-visible path returns deterministic success/failure structure | unsupported/hostile input fails visibly | no end-user UX or release-readiness claim |
| PC-019 | RuVector/TEI remains a proposed infrastructure direction until representative proof | `[proposed]` | `none-design` / synthetic probes insufficient | ADR-0014, 0015 | contract preserves proof gate and non-claim | synthetic or vendor evidence cannot promote runtime readiness | no live RuVector/TEI product runtime |
| PC-020 | Release claims require declared scope, release-class smoke and preserved non-claims | `[deferred]` | `release-class` + `human-acceptance` | ADR-0015 | future release packet ties binary, revision, scope and evidence | docs/process acceptance or InMemory success cannot create a release claim | no current production release claim |

## 7. Quality attributes

- **Evidence integrity:** immutable source identity and provenance accompany authority-bearing outcomes.
- **Fail-closed semantics:** missing or conflicting evidence produces typed non-success.
- **Provider isolation:** Consultant and Garant assumptions, fixtures and acceptance oracles remain independent.
- **Lifecycle honesty:** claims never exceed the weakest governing ADR/evidence ceiling.
- **Reproducibility:** consequential evidence uses tracked repository-relative anchors and a tested revision.
- **Debuggability:** failure outcomes contain stable reason kinds and sufficient context without secrets.
- **Authority separation:** product, process, legal interpretation, promotion and publication roles are not conflated.

## 8. Legal-error threat model

| Threat | Required control |
|--------|------------------|
| invented source structure or citation | source-span validation and typed rejection |
| clock or edition substitution | role-preserving anchors and `Unknown`/`Conflict` |
| treating force as case applicability | PC-009 deferred boundary and explicit abstention |
| incomplete evidence promoted to authority | completeness and dual-authority gates |
| provider assumption leakage | isolated adapters, fixtures and hostile tests |
| model prose treated as proof | PC-014 non-authority rule |
| derived registry or roadmap treated as readiness | A5/A7 boundary and proof-class gate |
| historical ACP/FalkorDB/Python behavior revived | archive qualification and Rust-only boundary |

## 9. Human-review boundary

Human decisions are mandatory for promotion, publication, consequential architecture acceptance, `[validated]` product claims and legal interpretation. Tools may prepare evidence and findings. They may not fabricate assent, infer acceptance from silence, or convert all-green checks into human disposition.

## 10. Readiness and release criteria

This document may become `ready-for-assessment` only when:

- all consequential product statements have stable clause IDs;
- each clause has lifecycle, proof class, governing ADRs, requirement links, positive and hostile acceptance, and non-claims;
- `prd/REQUIREMENTS.md` provides an inverse trace without stronger lifecycle;
- all local Markdown links resolve in a frozen tracked revision;
- no current clause claims a validated product capability;
- an independent reviewer confirms typed abstention and human authority boundaries.

`ready-for-assessment` is document readiness only. EA-10 process acceptance is not product validation. Release readiness remains deferred under PC-020.

## 11. Trace table

| Clause | Requirement | Governing ADRs | Current evidence anchor | Proof class |
|--------|-------------|----------------|-------------------------|-------------|
| PC-001 | RQ-001 | 0004, 0005, 0007, 0011 | `tests/test_harness_no_forbidden_imports.py` | static/process |
| PC-002 | RQ-002 | 0013, 0015 | `crates/ln-decode/tests/hc05_decode_anchor.rs`, `crates/ln-decode/tests/hc05_hostile_decoder.rs`, provider-specific decoder tests | bounded parser contracts |
| PC-003 | RQ-003 | 0010, 0011, 0015 | `crates/ln-identity/tests/hc07_hostile_identity.rs`, `crates/ln-relation/tests/hc08_hostile_relation.rs` | synthetic-hostile |
| PC-004 | RQ-004 | 0008, 0011 | `crates/ln-promote/tests/hc04_hostile_promotion.rs`, `crates/ln-publish/tests/hc15_hostile_publish.rs`, `crates/ln-accelerate/tests/hc16_accelerate.rs` | synthetic-hostile |
| PC-005 | RQ-005 | 0010, 0011, 0015 | `crates/ln-citation/tests/hc18_citation.rs`, `crates/ln-testkit/tests/citation_port_contracts.rs` | bounded contract |
| PC-006 | RQ-006 | 0011, 0015 | `crates/ln-query/tests/hc17_query.rs`, `crates/ln-testkit/tests/query_port_contracts.rs` | port-contract + synthetic-hostile |
| PC-007 | RQ-007 | 0009, 0011 | `crates/ln-temporal/tests/hc09_five_clock.rs`, `crates/ln-temporal/tests/hc09_hostile_clock.rs`, `crates/ln-testkit/tests/temporal_port_contracts.rs` | synthetic-hostile |
| PC-008 | RQ-008 | 0016–0022 | `doc/adr/0016-*.md` … `0022-*.md` | design only |
| PC-009 | RQ-009 | 0023 + 0017–0022 prerequisites | `doc/adr/0023-applicability-protocol-ownership.md` | ownership design only; runtime deferred |
| PC-010 | RQ-010 | 0022, 0023, 0015 | `doc/adr/0022-industry-profiles-architecture.md`, `doc/adr/0023-applicability-protocol-ownership.md` | design only |
| PC-011 | RQ-011 | 0012, 0015 | `scripts/verify-adr-conformance.py`, harness governor tests | process gate |
| PC-012 | RQ-012 | 0011, 0015 | shared `crates/ln-testkit/tests/*_port_contracts.rs` suites | bounded contracts |
| PC-013 | RQ-013 | 0009, 0010, 0015, 0017–0021 | `crates/ln-temporal/tests/hc09_hostile_clock.rs`; future applicability hostile cases are absent | bounded kernel/design ontology |
| PC-014 | RQ-014 | 0012, 0015 | `prd/ARCHITECTURE.md` | policy/process |
| PC-015 | RQ-015 | 0008, 0011 | `crates/ln-promote/tests/hc04_hostile_promotion.rs`, `crates/ln-publish/tests/hc15_hostile_publish.rs` | bounded |
| PC-016 | RQ-016 | architecture non-claims | `prd/ARCHITECTURE.md`, `assessment/00-charter.md` | design/process |
| PC-017 | RQ-017 | 0011, 0015 | `crates/ln-diagnostic/tests/hc19_diagnostic.rs` | synthetic-hostile |
| PC-018 | RQ-018 | 0005, 0013, 0015 | `crates/ln-product-cli/tests/cli_contract.rs` | bounded contract |
| PC-019 | RQ-019 | 0014, 0015 | `doc/adr/0014-ruvector-primary-infrastructure.md` | design only |
| PC-020 | RQ-020 | 0015 | none | deferred |

## 12. Global non-claims

law-nexus does not currently claim:

- legal correctness, authoritative legal interpretation or case applicability;
- parser completeness, provider parity or representative corpus coverage;
- production retrieval quality or citation-safe legal answers;
- live RuVector/TEI product infrastructure;
- executable O1–O7 temporal ontology or applicability runtime;
- cross-store atomicity, production concurrency, recovery or scale;
- a validated product capability or production release;
- that LLM, similarity, roadmap completion, assessment acceptance, `.gsd` state or derived registry output is product proof.
