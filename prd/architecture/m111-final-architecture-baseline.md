# M111 Final Architecture Baseline

**Status:** `[bounded]` implementation-neutral architecture baseline  
**Milestone:** M111/S10  
**Selection package:** D116, D118, D119, D120, D121 and D123 `KOF-DA`  
**Product direction:** Rust-only product runtime under ADR-0004; subprocess-only Python harness under ADR-0007; ADR-0005 product topology is superseded
**Proof ceiling:** architecture contracts, artifact-static checks, bounded adjacent repository evidence, and post-M111 HC-01 through HC-12 bounded runtime proofs

## Objective and boundary

This document is the final M111 architecture package for future Rust planning. It fixes semantic ownership, authorities, evidence ceilings, hostile-case oracles and invalidation conditions without selecting implementation technology.

The baseline proves architecture-level coherence only. Artifact-static checks pass for all 20 hostile cases, and all 14 cross-slice attack classes have an exclusive owner, fail-closed rule and invalidation condition. Post-M111 evidence now provides bounded product-capability runtime PASS for HC-01 through HC-12 (`S10-HC-01-RT`, `S10-HC-02-RT`, `S10-HC-03-RT`, `S10-HC-04-RT`, `S10-HC-05-RT`, `S10-HC-06-RT`, `S10-HC-07-RT`, `S10-HC-08-RT`, `S10-HC-09-RT`, `S10-HC-10-RT`, `S10-HC-11-RT`, `S10-HC-12-RT`): current runtime results are 12 PASS, 0 FAIL and 8 `unsupported-case`. This does not establish aggregate conformance.

Architecture PASS is not product runtime PASS. Adjacent parser, citation, architecture/ADR and marker checks are partial evidence only.

## Selected contracts and decisions

| Contract | Durable artifact | Baseline role |
|---|---|---|
| Source and authority | `prd/architecture/m111-corpus-source-authority-contract.md` | official-source-first families; access transport is not authority |
| Consultant intake | `prd/architecture/m111-consultant-intake-contract.md` | immutable intake, review and D116 promotion boundary |
| Temporal | `prd/architecture/m111-temporal-contract.md` | D118 five clocks and event-anchored assertions |
| Canonical model | `prd/architecture/m111-canonical-legal-model.md` | D119 evidence kernel, family modules and C10/C12/C13 |
| Pipeline and capacity | `prd/architecture/m111-pipeline-capacity-contract.md` | D120 complete H1 authority, provisional ceiling and unknown E1-E3 |
| System skeleton | `prd/architecture/m111-system-skeleton-contract.md` | D123 ownership, HC-01-HC-20 and 12 rejection oracles |
| Prior-art dispositions | `prd/architecture/m111-prior-art-reconciliation.md` | adopt/adapt/reject boundaries without inheriting Python topology |
| Adversarial closure | `prd/research/m111/whole-system-adversarial-closure.md` | proof modes, evidence IDs, verdicts and 14 attack classes |
| Living truth | `prd/ARCHITECTURE.md` | project-wide current architecture direction |

Selected decisions:

- **D116:** the sole Promotion Authority owns one idempotent curated-corpus commit. Promotion is not legal/evidence publication.
- **D118:** immutable typed evidence assertions/events and observation history are authoritative; intervals and bitemporal views are derived, family/target-scoped projections.
- **D119:** a compositional typed evidence kernel owns cross-family semantics; family modules own bounded vocabularies and evidence contributions. C10, C12 and C13 remain inward.
- **D120:** immutable complete H1 publication units are the sole authoritative, complete and current mode. Optional acceleration is non-authoritative, incomplete and not-current.
- **D121/R071:** consequential choices require primary provenance, positive and negative experience, transferability limits and independent confirmation or a bounded local probe.
- **D123 `KOF-DA`:** an O1-primary deep hexagonal spine; O2 only thin processing-state orchestration; O3 only bounded family vocabularies; one exclusive primary owner per capability.

Rejected structures include pure pipeline ownership of legal policy, pure kernel ownership without a process owner, unconstrained hybrid/composite ownership, mega-ports, adapter-owned clocks/gates/authority, pure H2 authoritative incremental publication, mutable baselines, direct provisional promotion and multiple D116 or D120 writers.

## Authority model

1. Every capability has exactly one primary owner. An invoker, contributor or adapter is not an owner.
2. D116 Promotion Authority and D120 Publication Authority are separate and singular.
3. Promotion success never grants publication authority.
4. Only a committed complete H1 unit may carry authoritative, complete or current labels.
5. Provisional output cannot transition directly to authoritative; authority requires a new complete H1 unit.
6. Families cannot override shared clocks, identity, relation, promotion, publication, closure, citation or diagnostic policy.
7. Application orchestration owns processing progress only, never legal state or evidence truth.

| Authority | Owns | Does not own |
|---|---|---|
| D116 sole Promotion Authority | accepted immutable inputs, disposition evidence, operation identity, hashes and one curated-corpus commit | legal applicability, H1 completeness or D120 labels |
| D120 sole Publication Authority | decision that a complete H1 unit is authoritative for declared source scope, rule set and knowledge cutoff | intake promotion or partial/provisional authority |

## Twenty exclusive capabilities

| # | Capability | Exact primary owner | Typed non-success summary |
|---|---|---|---|
| 1 | Observe Source | outward source boundary | unavailable, timeout, cancelled, transport-or-TLS-failure, access-restricted |
| 2 | Inventory Immutable Intake | intake application policy | integrity-failed, metadata-mismatch, review-required, ambiguous-identity |
| 3 | Dispose Review | intake disposition policy | unresolved, conflicting-review, unauthorized |
| 4 | Commit Curated Promotion | sole Promotion Authority | incomplete, conflict, unauthorized, cancelled, already-committed, rollback |
| 5 | Decode and Anchor | outward decode boundary | malformed, unsupported, incomplete, restricted |
| 6 | Gate Lifecycle | evidence kernel C10 policy | insufficient-evidence, invalid-transition, conflict, unknown |
| 7 | Assert Identity | evidence kernel C12 policy | one-sided-evidence, ambiguous, conflict |
| 8 | Validate Relation | evidence kernel C13 registry policy | unknown-predicate, wrong-owner, insufficient-evidence |
| 9 | Resolve Five-Clock State | domain temporal policy | missing-anchor, substitute-rejected, unknown, conflict, scope-unsupported |
| 10 | Transition Work State | application processing policy | invalid-transition, retry-exhausted, cancelled, stale |
| 11 | Compute Dependency Closure | inward dependency policy | incomplete, unbounded, unknown, rule-version-mismatch |
| 12 | Rebuild Disposable Projection | outward projection boundary | failed, partial, stale-input, cancelled |
| 13 | Decide Admission | application admission policy | bound-unknown, saturated, retry-amplification |
| 14 | Coordinate Checkpoint and Replay | application replay policy | mismatch, corrupt, incompatible-rule, incomplete |
| 15 | Publish Authoritative H1 Unit | sole Publication Authority | incomplete, conflict, cancelled, duplicate, failed |
| 16 | Publish Provisional Acceleration | application acceleration policy | closure-unknown, failed, stale, cancelled |
| 17 | Query Evidence-Bounded State | inward query policy | no-answer, incomplete, conflict, restricted |
| 18 | Resolve Citation | domain citation policy | unresolved-anchor, unavailable-source, visibility-restricted |
| 19 | Emit Safe Diagnostics | inward diagnostic policy | sink-unavailable, redaction-failed, schema-invalid |
| 20 | Evaluate Conformance | architecture conformance contract | mismatch, leak, bypass, unsupported-case |

The full conceptual inputs, outputs, non-responsibilities and evidence are normative in the system skeleton. This table cannot be used to infer co-ownership.

## Five clocks and inward gates

D118 preserves five distinct clocks:

| Clock | Meaning and ceiling |
|---|---|
| `factual_event` | conduct, condition or transaction that anchors the legal question |
| `proceeding` | complaint, hearing, decision, appeal, remand, enforcement or other procedural event |
| `legal_act_effect` | adoption, amendment, commencement, scoped applicability, suspension, invalidity, repeal or finality supported by evidence |
| `source_publication` | official/public manifestation publication, correction, replacement, redaction or removal |
| `system_observation` | fetch, ingestion, timeout, retry, review, quarantine or promotion observation |

The clocks cannot be collapsed into universal `valid_time`/`system_time`. Missing legal anchors yield a typed `unknown`, `conflict`, `missing-anchor` or `substitute-rejected`; observation, processing, publication, latest-edition or current wall-clock values cannot silently substitute.

- **C10 lifecycle:** transitions create immutable typed outcomes or new identities. Confidence ranks evidence within one lifecycle and cannot cross a boundary. No in-place or workflow/storage bypass promotion.
- **C12 identity:** evidence yields same, different, candidate, conflict or not-resolvable assertions. Assertions do not merge objects. Families and similarity contribute evidence but cannot authorize identity.
- **C13 relations:** kernel and family registries are closed and revisioned. Unknown or wrong-owner predicates are rejected; runtime, users, LLMs and adapters cannot mint predicates.

## Publication, acceleration and capacity

An authoritative H1 unit is immutable and complete for its declared source scope, rule set and knowledge cutoff. Readers may treat only committed complete units as authoritative, complete or current. Partial, conflicted, cancelled, duplicate or failed candidates remain typed non-success.

Optional acceleration may publish only explicitly:

- `non-authoritative`;
- `incomplete`;
- `not-current`;
- accompanied by stale/gap/trace metadata.

`published-provisional → published-authoritative` is forbidden. D116 promotion, projection rebuild or label mutation cannot create D120 authority. `incomplete`, `unbounded` or `unknown` closure cannot become authoritative completeness.

E1-E3 are scenario envelopes, not measurements. Unknown bounds, saturation or retry amplification cause pause or rejection. External/vendor measurements cannot become local throughput, latency, storage, SLA or architecture-selection proof.

## Query, citation and diagnostics

Query and citation consume evidence; they cannot create it. Query policy cannot invent facts, clocks, identities, relations, legal state, completeness or authority. Citation policy cannot invent an anchor, hide unresolved source access or relabel a mirror as official.

Diagnostics may expose only bounded identifiers, hashes, phases, categories, rule versions, retryability and bounded measurements. Raw legal text, full payloads, embeddings/vectors, credentials, secrets and unrestricted sensitive data are forbidden. Redaction failure is typed diagnostic failure, not permission to emit original content. Positive controls are mandatory when runtime diagnostic privacy is tested.

## Hostile-case verdicts

| Evidence class | Result | Exact meaning |
|---|---|---|
| Artifact-static subchecks | PASS 20/20 | contract fields, owner bindings, vocabularies and oracles are present |
| Repository-adjacent checks | available checks PASS after corrected invocation | partial parser/citation/repository evidence only |
| Architecture attack protections | PASS 14/14 | each attack class has exact owner, fail-closed protection and invalidation condition |
| Milestone-invalidating architecture failures | 0 | no current cross-contract contradiction found |
| Runtime aggregate | PASS 12/20; FAIL 0/20; `unsupported-case` 8/20 | HC-01 through HC-12 have bounded runtime proofs; mandatory surfaces for HC-13-HC-20 remain absent |

| HC | Capability | Aggregate verdict | Missing surface preventing runtime PASS |
|---|---|---|---|
| HC-01 | Observe Source | `PASS` `[bounded]` | `S10-HC-01-RT`: four interrupted outcomes, partial-byte canary and safe diagnostic observations |
| HC-02 | Inventory Immutable Intake | `PASS` `[bounded]` | `S10-HC-02-RT`: re-inventory stable digest, append-only attempts and staging/review visibility only |
| HC-03 | Dispose Review | `PASS` `[bounded]` | `S10-HC-03-RT`: pending/quarantined reject promotion without curated commit |
| HC-04 | Commit Curated Promotion | `PASS` `[bounded]` | `S10-HC-04-RT`: cancel/retry/mismatch preserve one D116 effect without publication authority |
| HC-05 | Decode and Anchor | `PASS` `[bounded]` | `S10-HC-05-RT`: honest/malicious differential keeps structural candidates/anchors only; canary absent |
| HC-06 | Gate Lifecycle | `PASS` `[bounded]` | `S10-HC-06-RT`: confidence-only and in-place rejected; accepted path mints new immutable outcome |
| HC-07 | Assert Identity | `PASS` `[bounded]`; legal non-claim | `S10-HC-07-RT`: one-sided/similarity-only reject; bilateral same never merges; both identities survive |
| HC-08 | Validate Relation | `PASS` `[bounded]` | `S10-HC-08-RT`: unknown-predicate and wrong-owner rejected; rejected relations not query facts |
| HC-09 | Resolve Five-Clock State | `PASS` `[bounded]`; legal non-claim | `S10-HC-09-RT`: five-clock forbidden-substitution matrix; wall-clock never authorizes |
| HC-10 | Transition Work State | `PASS` `[bounded]` | `S10-HC-10-RT`: cancel/resume freeze domain/publication; stale typed; progress-to-legal rejected |
| HC-11 | Compute Dependency Closure | `PASS` `[bounded]` | `S10-HC-11-RT`: incomplete/unknown/unbounded/version-skew block publication; progress never completeness |
| HC-12 | Rebuild Disposable Projection | `PASS` `[bounded]` | `S10-HC-12-RT`: partial/stale/cancel/failed non-authoritative; hostile labels demoted; publication authority never granted |
| HC-13 | Decide Admission | `unsupported-case` | saturation/retry runtime and local E1-E3 measurements |
| HC-14 | Coordinate Checkpoint and Replay | `unsupported-case` | prior-effect replay, corruption and rule-version skew |
| HC-15 | Publish Authoritative H1 Unit | `unsupported-case` | dual-writer, duplicate and partial H1 fixtures |
| HC-16 | Publish Provisional Acceleration | `unsupported-case` | label mutation and direct-promotion attempts |
| HC-17 | Query Evidence-Bounded State | `unsupported-case` | M111 staging/gap-invention query fixtures |
| HC-18 | Resolve Citation | `unsupported-case`; legal non-claim | restricted-official/mirror and missing-anchor fixtures |
| HC-19 | Emit Safe Diagnostics | `unsupported-case` | declared sinks, multi-canary and redaction-failure runtime |
| HC-20 | Evaluate Conformance | `unsupported-case` | full meta-suite, runtime HC verdicts and differential adapters |

The 14 protected attack classes are source-authority loss, immutable-intake corruption, partial/duplicate promotion, dual H1 writers, provisional promotion, replay side effects, C10 bypass, C12 bypass, C13 bypass, clock substitution, incomplete closure, unbounded work/false capacity precision, query/citation invention and diagnostic leakage. Their exact risk matrix is normative in the adversarial closure artifact.

## Invalidation

This baseline has a milestone-invalidating architecture FAIL if any accepted design permits:

1. uncommitted intake or provisional output to appear complete/current;
2. D116 promotion to grant D120 publication authority;
3. two paths to publish authoritative H1 for one declared unit;
4. application, workflow, storage or adapter paths to set C10/C12/C13 outcomes without inward gates;
5. a missing legal clock to be filled from observation, processing, publication, latest edition or current time;
6. a family to publish authority, invent a shared clock/relation or declare local closure global;
7. a rebuild executor to change authority;
8. query/ranking/citation to invent a fact, identity, relation, clock, legal state or anchor;
9. a selected port to be CRUD-, product-, protocol-, storage- or crate-named;
10. replay to repeat external effects without idempotent policy;
11. diagnostics to emit raw legal text, payloads, vectors, credentials or secrets;
12. external efficiency or vendor benchmarks to select architecture without comparable local measurements.

Composite ownership, mutable intake, direct provisional promotion, fabricated completeness/capacity or a second D116/D120 writer are also immediate invalidation conditions. `unsupported-case` alone does not invalidate D123 and never counts as PASS.

D123 may be reopened if a thinner ownership model satisfies every supported hostile case while KOF-DA does not, or independent evidence invalidates singular authority, inward gates or provisional ceilings.

## Requirement evidence ceiling

- **R067:** advanced by a complete implementation-neutral contract package, 20 exclusive capability owners, 20 hostile oracles, 12 rejection oracles, static PASS 20/20 and architecture attack PASS 14/14. Product/runtime validation remains outstanding.
- **R068:** advanced by D118 five clocks, event-anchored assertions and HC-09 substitution runtime PASS (`S10-HC-09-RT`). Legal applicability/effective-date correctness remain non-claims.
- **R071:** M111 material decisions have primary/independent evidence, positive/negative lessons, dispositions and transferability limits. This demonstrates M111 process compliance, not permanent completion of an ongoing quality requirement.

## Future Rust planning handoff

The target product runtime remains Rust-only. Python product code is behavioral reference; a thin Python repository harness may remain for subprocess orchestration only, with no product/domain logic and no PyO3/FFI.

Future Rust planning must consume semantic capabilities, exact owners, authorities, clocks, gates, ceilings and oracles from this baseline. It must not infer a crate map or implementation topology. Early product slices must preserve:

- all 20 exclusive owner bindings;
- D116 and D120 singularity and separation;
- five-clock non-substitution;
- C10/C12/C13 fail-closed outcomes;
- complete H1-only authority and provisional ceilings;
- query/citation evidence ceilings;
- diagnostic allow/deny and positive-control requirements;
- `unsupported-case` semantics when an observable surface is absent.

Database, FalkorDB schema, storage, queue, work ledger, Rust crate map, network API, concurrency runtime, deployment topology and test framework remain future decisions requiring their own D121 evidence and local probes. Runtime HC execution requires product surfaces and synthetic fixtures. Capacity decisions require comparable local E1-E3 measurements.

## Non-claims

- No product runtime conformance harness existed or was selected at M111; post-M111 HC-01 has a bounded synthetic runtime harness only.
- No database, FalkorDB schema, storage, queue/ledger, crate map, API, concurrency runtime, deployment topology or test framework is selected.
- No legal correctness, applicability, finality, precedent, retroactivity or official-source legal determination is validated.
- No corpus/source completeness, production acquisition, API stability or lawful bulk-extraction capability is validated.
- No E1-E3 capacity, throughput, latency, storage, performance, redaction-overhead or production-readiness claim is made.
- Adjacent Python/parser/citation tests are not HC runtime PASS.
- Architecture graph and ADR verifier output is derived repository evidence, not source truth or product proof.
- External incident numbers and vendor measurements do not establish law-nexus efficiency.

## Evidence ledger

| Anchor | What it supports at the bounded ceiling |
|---|---|
| `prd/architecture/m111-system-skeleton-contract.md` | D123 owners, HC schema and rejection oracles |
| `prd/research/m111/whole-system-adversarial-closure.md` | proof modes, HC classifications, T02 evidence and T03 risk matrix |
| `prd/architecture/m111-corpus-source-authority-contract.md` | source/authority rules and open acquisition gates |
| `prd/architecture/m111-consultant-intake-contract.md` | immutable intake and D116 boundary |
| `prd/architecture/m111-temporal-contract.md` | D118 five clocks |
| `prd/architecture/m111-canonical-legal-model.md` | D119 C10/C12/C13 and family boundaries |
| `prd/architecture/m111-pipeline-capacity-contract.md` | D120 H1/provisional rules and capacity unknowns |
| `doc/adr/0004-rust-migration-decision.md`; `doc/adr/0007-python-repository-harness.md` | Rust-only product direction and subprocess-only harness boundary |
| `doc/adr/0005-rust-target-architecture.md` | Superseded pre-M111 topology and bounded tracer history only |

Bounded execution IDs are retained in the adversarial closure artifact. They are audit evidence, not durable source-truth anchors and not aggregate product PASS.
