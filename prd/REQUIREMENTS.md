# Published Requirements Projection

**Kind:** requirements projection (A4)
**Document status:** `[proposed]` requirements projection; document state `ready-for-assessment`
**Planning baseline:** `60fd8245ace999f3f29911844375dd7cc36a2a38` (2026-08-11)
**EA-02 tested revision:** `37f82c4245642f7c1e9104f288db43df762178fe` (`assessment/02-product-contract.md`)
**Derives from:** `prd/PRODUCT.md`
**Architecture ceilings:** `prd/ARCHITECTURE.md` + `doc/adr/**`
**Local workflow source:** `.gsd/REQUIREMENTS.md` is non-published seed/state and is not authority for cold readers
**Ontology alias:** O1–O7 here is the ADR-0016–0022 design sequence labelled L1–L7 in `prd/ARCHITECTURE.md`

## 1. Projection contract

This file publishes only obligations required to assess the proposed Product Contract. It is not a dump of local GSD requirements and does not copy historical validation states. It cannot override Product clauses, ADR decisions, architecture non-claims, or evidence ceilings.

Lifecycle rule:

```text
lifecycle(requirement)
≤ lifecycle(owning Product clause)
≤ lifecycle(governing ADR and available proof class)
```

Roadmaps, assessment dispositions, generated registry rows, LLM reports, archive behavior and local `.gsd` paths cannot satisfy a requirement.

## 2. Allowed states and proof classes

Requirement states: `active`, `deferred`, `satisfied-bounded`, `satisfied-smoke`, `validated-scoped`, `withdrawn`.

D098 lifecycle values: `[proposed]`, `[bounded]`, `[smoke]`, `[validated]`, `[deferred]`.

Proof classes used here: `none-design`, `process-gate`, `static-invariant`, `synthetic-hostile`, `port-contract`, `real-fixture-smoke`, `representative-corpus`, `release-class`, `human-acceptance`.

`validated-scoped` requires representative evidence and human acceptance for the exact declared scope. No product requirement in this projection currently has that state.

## 3. Projected requirements

| ID | Obligation | Product clauses | State / lifecycle | Proof class | Governing ADRs | Evidence / validation route | Mandatory non-claim |
|----|------------|-----------------|-------------------|-------------|----------------|-----------------------------|---------------------|
| RQ-001 | Keep all active product/domain behavior in Rust; Python remains repository harness only | PC-001 | `satisfied-bounded` / `[bounded]` product; harness boundary separately `[validated]` | static-invariant + process-gate | 0004, 0005, 0007, 0011 | forbidden-import tests, Cargo architecture, governor/preflight | harness validation does not validate product capability |
| RQ-002 | Decode provider sources through isolated positive and hostile contracts with valid spans | PC-002 | `satisfied-bounded` / `[bounded]` | port-contract + limited fixtures | 0013, 0015 | `crates/ln-decode/tests/`; provider-specific fixtures remain independent | no completeness, parity or corpus coverage |
| RQ-003 | Reject unsafe evidence identity, lifecycle and relation mutations fail closed | PC-003 | `satisfied-bounded` / `[bounded]` | synthetic-hostile | 0010, 0011, 0015 | identity/relation hostile suites; assert typed rejection and unchanged state | no legal correctness or production storage |
| RQ-004 | Separate singular promotion and publication authorities and forbid direct provisional authority | PC-004, PC-015 | `satisfied-bounded` / `[bounded]` | synthetic-hostile | 0008, 0011 | promote/publish/accelerate hostile suites | workflow authority is not legal correctness |
| RQ-005 | Resolve citations only from source-anchored spans and reject missing/invalid mirrors | PC-005 | `satisfied-bounded` / `[bounded]` | port-contract + synthetic-hostile | 0010, 0011, 0015 | citation contract and HC-18 tests | no real-corpus citation-safe answer claim |
| RQ-006 | Return query candidates with admitted provenance and honest adapter score semantics | PC-006 | `satisfied-bounded` / `[bounded]` | port-contract + synthetic-hostile | 0011, 0015 | `crates/ln-query/tests/hc17_query.rs` + query port contracts; missing evidence and invention attempts return typed non-success | no production retrieval/RuVector quality |
| RQ-007 | Preserve five clock roles and return typed uncertainty instead of substitution | PC-007 | `satisfied-bounded` / `[bounded]` | synthetic-hostile | 0009, 0011, 0015 | temporal hostile and port-contract tests | no CTV/applicability runtime or legal-time validation |
| RQ-008 | Keep O1–O7 temporal ontology as explicit proof-gated design | PC-008 | `active` / `[proposed]` | none-design | 0016–0022 | ADR design review; future layer-specific TDD + hostile cases | no implemented ontology runtime or R035 validation |
| RQ-009 | Define and later implement typed applicability from NormRule through ExplainableTrace | PC-009 | `deferred` / `[deferred]` | none-design | 0023 + 0017–0022 prerequisites | ownership decided; future Rust domain/ports, hostile cases and representative real-case evidence still required | executable applicability is absent |
| RQ-010 | Keep procurement/industry semantics in versioned profiles over neutral core | PC-010 | `active` / `[proposed]` | none-design | 0022, 0023, 0015 | versioned profile-input contract and future provider-independent hostile tests | no procurement legal completeness or runtime |
| RQ-011 | Preserve D098 lifecycle and proof classes on consequential state | PC-011 | `satisfied-bounded` / `[bounded]` process | process-gate | 0012, 0015 + ARCHITECTURE | ADR conformance, governor/preflight, human review | process PASS is not product validation |
| RQ-012 | Require positive semantic assertions and one relevant fail/diagnostic path for changed behavior | PC-012 | `satisfied-bounded` / `[bounded]` | port-contract + synthetic-hostile | 0011, 0015 | shared port contracts and HC suites | compilation/mock choreography is insufficient |
| RQ-013 | Abstain fail closed on missing legal, temporal, citation or applicability evidence | PC-013 | `active` / `[bounded]` kernel, `[proposed]` ontology | synthetic-hostile + none-design | 0009, 0010, 0015, 0017–0021 | kernel hostile tests; future applicability hostile cases | no production legal-safety validation |
| RQ-014 | Prevent LLM, semantic similarity, derived registry and roadmap status from becoming authority/proof | PC-014 | `active` / `[bounded]` policy | static-invariant + human review | 0012, 0015 + ARCHITECTURE | publication/process review; deterministic controls where available | assistive use is allowed outside authority paths |
| RQ-015 | Preserve explicit human authority for promotion, publication, architecture acceptance and legal interpretation | PC-015 | `active` / `[bounded]` | synthetic-hostile + human-boundary review | 0008, 0011 | dual-authority tests and documented role separation | does not automate legal judgment |
| RQ-016 | Keep legal/product readiness non-claims in Product and assessment surfaces | PC-016 | `active` / `[proposed]` contract constraint | none-design + process review | ARCHITECTURE | cold-reader review and exact non-claim checks | documentation acceptance is not product/legal validation |
| RQ-017 | Emit safe, useful, typed diagnostics without secrets or authority leakage | PC-017 | `satisfied-bounded` / `[bounded]` | synthetic-hostile | 0011, 0015 | HC-19 diagnostic tests | no observability-platform maturity claim |
| RQ-018 | Expose deterministic CLI health/inspect behavior with visible failure surfaces | PC-018 | `satisfied-bounded` / `[bounded]` | port-contract + limited smoke | 0005, 0013, 0015 | product CLI contract tests; future provider-specific real-fixture smoke | no release/end-user UX readiness |
| RQ-019 | Keep RuVector/TEI infrastructure proposed until representative runtime/corpus proof | PC-019 | `active` / `[proposed]` | none-design; synthetic insufficient | 0014, 0015 | future real TEI/RVF ingestion, query, citation and hostile proof | no live RuVector/TEI product runtime |
| RQ-020 | Require revision-bound release binary, declared scope, release smoke and human acceptance for release claims | PC-020 | `deferred` / `[deferred]` | release-class + human-acceptance | 0015 | future release packet | no current production release claim |

## 4. Inverse trace and hostile-acceptance rules

For multi-parent rows, the first listed Product clause is the `primary_owner`; later clauses are supporting. Lifecycle is recomputed against every parent, and no supporting parent may be ignored when it lowers the ceiling.

| Requirement | Hostile acceptance source |
|-------------|---------------------------|
| RQ-001 | forbidden Python product import or PyO3/FFI fails repository-control tests |
| RQ-002 | hostile decoder/provider mismatch returns typed failure with no invented structure |
| RQ-003 | unsafe identity/relation mutation rejects and preserves prior state |
| RQ-004 | dual writer, incomplete publication and direct provisional authority reject |
| RQ-005 | missing/invalid span cannot resolve as exact citation |
| RQ-006 | missing evidence, invention or fabrication returns non-authoritative outcome |
| RQ-007 | missing/competing clock anchors return `Unknown`/`Conflict` |
| RQ-008 | documentation alone cannot promote any ontology layer |
| RQ-009 | temporal phrases cannot produce case applicability without the deferred protocol |
| RQ-010 | procurement/profile facts cannot redefine neutral core semantics |
| RQ-011 | bounded/smoke evidence cannot be labelled validated |
| RQ-012 | compilation or mock choreography alone cannot satisfy changed behavior |
| RQ-013 | missing evidence cannot default to applicable, in-force or low-risk |
| RQ-014 | LLM/registry/roadmap output alone cannot satisfy a requirement |
| RQ-015 | provisional, incomplete or model output cannot bypass human authority |
| RQ-016 | documentation PASS cannot become product/legal readiness |
| RQ-017 | diagnostics must omit secrets and authority claims |
| RQ-018 | unsupported/hostile CLI input fails visibly and deterministically |
| RQ-019 | synthetic/vendor evidence cannot promote RuVector/TEI readiness |
| RQ-020 | docs/process acceptance or InMemory-only success cannot create a release claim |

- Every `RQ-###` links at least one `PC-###`.
- Every Product clause links at least one projected requirement.
- Runtime-bearing requirements cite governing ADRs and tracked evidence.
- Design/deferred requirements may have no executable evidence, but must say so explicitly.
- A requirement lifecycle is recomputed from current governing ADR/evidence; it is never copied blindly from local workflow status.
- Missing links, stronger lifecycle, local-only sole proof or derived evidence promotion block D2/EA-02 assessment readiness.

## 5. Local-workflow publication boundary

Local `.gsd/REQUIREMENTS.md` may contain historical, milestone-specific, superseded or more granular workflow rows. This projection intentionally publishes only obligations linked to `prd/PRODUCT.md` plus explicit standing safety constraints.

### Local-only omitted classes

| Class | Reason not projected as current Product requirement |
|-------|-----------------------------------------------------|
| historical FalkorDB/ACP-era obligations | decommissioned or superseded; must not regain active authority |
| milestone choreography and task-state rows | planning/execution detail, not durable product obligation |
| requirements whose only proof is `.gsd/milestones/**` or `.gsd/exec/**` | local evidence is not portable published proof |
| duplicate clauses already represented by an RQ row | avoid dual canon and contradictory lifecycle |
| archive/parser-dump/research-only candidates | prior art or candidate evidence, not accepted obligation |

This omission table does not assert that every local row has been reconciled. A full local-to-published inventory is future process work and cannot promote lifecycle.

## 6. D2 exit checklist

- [x] `prd/PRODUCT.md` and this projection are tracked at tested revision `37f82c4245642f7c1e9104f288db43df762178fe`.
- [x] Every consequential Product statement has a stable `PC-###`.
- [x] PC/RQ IDs are unique and bidirectionally covered.
- [x] Every runtime-bearing row includes positive and hostile acceptance.
- [x] All evidence paths are tracked, repository-relative and exist at the tested revision.
- [x] No Product/RQ lifecycle exceeds ADR or evidence ceiling.
- [x] No validated product capability is claimed.
- [x] Product Contract is distinct from architecture state and roadmap sequence.
- [x] Independent EA-02 reviewer confirmed typed abstention, human authority and non-claims in `assessment/02-product-contract.md`.
- [x] Document state changed to `ready-for-assessment` after the checklist passed.

These checks establish document readiness only. EA-09 independent assessment completed at packet revision `120d44b`, and EA-10 human decision D150 accepted the documentation/process packet with findings. That process disposition does not promote this `[proposed]` projection or validate product, runtime or legal behavior.

## 7. Non-claims

- This projection is not a replacement for ADRs or `prd/ARCHITECTURE.md`.
- It is not a verbatim or complete publication of local `.gsd` requirements.
- It does not close historical GSD requirements or rewrite their records.
- It does not validate product runtime, legal correctness, parser completeness, retrieval quality, RuVector readiness, ontology execution or release readiness.
- It does not make assessment or derived artifacts into requirement evidence.
