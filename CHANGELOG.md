# Changelog

All notable changes to law-nexus are documented in this file.

## Unreleased — current architecture landing and repository map

### Composition decode lift (KBO-R029)
- `law-nexus-inspect` lifts extracted HierarchyNode through YAML aliases.
- Empty registry reports `hierarchy_lifts_unknown`; no ComponentConcept mint.
- Allowlist gained `ln-product-cli -> ln-kb-ontology`; tests use `len(allowlist)`.

### YAML closed-vocabulary coverage (KBO-R028)
- `HierarchyLevel::as_str` emits decode tokens that YAML aliases cover.
- Governor compares named Rust enums to YAML `closed_vocabularies`.
- FSM current is `O2_catalog_coverage`.

### YAML catalog kinds (KBO-R027)
- Graph node/edge/presence kinds are catalog tokens, not Rust enums.
- Unknown kinds fail closed; Manifestation is accepted because YAML lists it.
- Governor compares the projection contract to YAML instead of a hardcoded tuple.

### YAML decode-level aliases (KBO-R026)
- Catalog now owns presence/membership/industrial/force vocabularies and
  `decode_level_aliases` (Statya→statya).
- `marker_from_decode_token` lifts decode tokens through YAML only.

### YAML ontology FSM catalog (KBO-R025)
- Added `prd/architecture/kb-ontology.yaml` as the meta-prompt FSM and
  vocabulary source (states, transitions, hierarchy levels, forbidden kinds).
- `ln-kb-ontology` loads the catalog; unknown levels/transitions fail closed.
- Governor `kb-ontology-draft` requires the YAML catalog.

### HierarchyMarker to CC lift (KBO-R024 / R3-02)
- Explicit `HierarchyMap`; unmapped → Unknown; same key + different CC → Conflict.
- Levels come from YAML, not a Rust enum. No `ln-decode` dependency.

### HierarchyMarker to CC lift (KBO-R024 / R3-02)
- Added `HierarchyMap` / `map_hierarchy_marker` in `ln-kb-ontology`:
  explicit registry only; unmapped → Unknown; same key + different CC → Conflict.
- No `ln-decode` dependency. Number+level is not a ComponentConcept.

### Component-in-Expression presence (KBO-R023)
- Added include/exclude events and `fold_expression_presence` in `ln-kb-ontology`.
- Later Expression does not inherit silently; same-day include+exclude conflicts.
- `filter_ast_to_expression` keeps only present CC nodes. Not CTV text or decode lift.

### Versioned membership fold (TSG-013 / KBO-R022)
- Added `VersionedMembershipLog` and `fold_membership_at` → `StructuralAst`
  in `ln-temporal` (projection at effect_day; same-day two-parent → Conflict).
- `project_structural_ast` in `ln-kb-ontology` emits membership edges only.
- Not CTV text, not Expression bind, not corpus reconstruction.

### KB ontology write-set projection (`ln-kb-ontology`)
- New crate `ln-kb-ontology`: pure `project_work` / `project_expression` /
  `project_membership` / `project_force_event` / `project_join` (no store I/O).
- Forbidden L4–L7 kinds rejected; Unknown force is not a writable node.
- KBO-R021 accepted-draft; FSM O2 + write-set. Not O3 fixtures or RuVector.

### FRBR Work/Expression identity spine (KBO-R011 S2)
- Added `mint_work`, `mint_expression`, and `compare_work_identities` in
  `ln-identity`: authority+date+number required; same number + divergent
  authority/date → Conflict. Distinct from C12 digest identity.
- KB ontology FSM → O2; KBO-R011 partial. Not Manifestation store or corpus.

### Force↔membership join offline (KBO-R012 / O2 partial)
- Added `join_force_with_membership` in `ln-temporal`: force status + structural
  membership context by `ComponentConceptId`; membership never implies InForce.
- KB ontology FSM → O2 partial; KBO-R012 partial; R011/R013 still open.

### KB ontology draft O1 (requirements + L1–L3 projection)
- Added `kb-ontology-requirements.md` (KBO-R001..R020), L1–L3 draft, and
  `kb-ontology-projection-contract.json` (authoritative=false).
- Governor advisory check `kb-ontology-draft` (structural only).
- Not production graph schema, not RuVector validation, not Applicable.

### NormativeState force-status bounded resolver (TSG-004 S2–S3)
- Added `NormativeState`, `ForceStatusTimeline`, and `resolve_force_status_at` in
  `ln-temporal` (force dimension only; missing/conflict → `Unknown`).
- Promotion board: TSG-004 → S2–S3. Not CTV join, not applicability, not corpus proof.

### CTV structural apply bounded runtime (TSG-003/013 S3)
- Added `apply_industrial_op` + `StructuralEventLog` in `ln-temporal`: offline
  membership mutation for renumber/move/split/merge with plan-match and
  duplicate-op fail-closed guards.
- Promotion board: TSG-003 → S3; TSG-013 → S2–S3. Not legal CTV product or corpus.

### Capability promotion board (L_capability / P3)
- Added `prd/architecture/capability-promotion-board.md`: ladder S0–S6, promotion
  packet rules, current TSG progress after RC11/RC12 spine wave.
- Governor advisory check `capability-promotion-board` requires every gap-register
  TSG id to be named on the board (structural only; not TSG closure).

### M167 GSD closeout (DT-lag resolved)
- Completed GSD milestone M167-odlgt8 (NormRule IR design spine) via authorized
  skip-slice waivers after out-of-band product evidence, validation pass, and
  engine residual gate omit — not fabricated Attempts (D154 option C).
- Project-state roadmap current marker advanced to M167; dual-truth note resolved.

### Governor dual-truth visibility and fail-on-warn test fix
- Added advisory Governor check `gsd-review-dual-truth` (D154): warns when the
  GSD↔Review bridge register declares DT-lag for an active/hard-open milestone.
- Made `fail-on-warn` CLI test use a deterministic tmp fixture instead of live
  residual inventory (live registry may be clean).

### GSD↔Review bridge policy (P2)
- Documented B1/B2 delivery intents, dual-truth classes, and M167/RC11-F04a
  DT-lag register (`prd/architecture/review-cases/gsd-review-bridge.md`).
- Forbids fake GSD completion; L_review closed ≠ L_delivery complete.

### Review continuity contract (three lifecycles)
- Adopted docs-first continuity contract separating L_review, L_delivery, and
  L_capability with closure ceilings and B1–B5 bridges (ADR-0024 §9a,
  `prd/architecture/review-cases/continuity-contract.md`).
- RC residual closed ≠ TSG closed; spine ceilings keep gap-register rows active.

### Applicability capability inventory (RC12-F05)
- Added `ApplicabilityCapability` landed-vs-deferred inventory in
  `ln-applicability`; algebra Satisfied still cannot mint product Applicable;
  TSG-006 remains open for real-case evidence.

### ADR citation hygiene (RC12-F18)
- Relocated active ADR references from missing `prd/research/` and gitignored
  `AGENTS.md` rule anchors to tracked archive-only prior art and living
  architecture authorities (`prd/ARCHITECTURE.md`, ADR-0015).

### CTV structural membership + industrial ops spine (RC11-F08)
- Added fail-closed `MembershipGraph` and industrial op planner
  (`renumber`/`move`/`split`/`merge`) in `ln-temporal` with provenance-required
  plans and whole-act compile fail-closed on incomplete membership.
- Structural only: not full CTV temporal resolution, not legal amendment
  correctness; TSG-003/013 remain open for runtime/corpus proof.

### NormativeState dimensional separation design (RC11-F09)
- Added `NormativeDimension` design inventory in `ln-temporal`: force/status,
  version relation, applicability, and epistemic outcome are orthogonal.
- Fail-closed helpers reject force→applicability and version/text→force collapse;
  design inventory is not a NormativeState resolver (TSG-004 remains open).

### TextChange vs NormativeEffect design taxonomy (RC11-F07)
- Added `LegislativeEventKind` design inventory in `ln-temporal` separating
  text/structure change from normative effect as design-only kinds.
- Fail-closed helper rejects treating text change as legal effect; taxonomy
  presence is not CTV runtime (TSG-002 remains open for executable events).

### Five-clock safety vs temporal algebra boundary (RC11-F06)
- Added `TemporalAlgebraCapability` design inventory in `ln-temporal` that
  classifies interval/bitemporal/legal-date capabilities as deferred algebra.
- Hard non-claim: five-clock HC-09 safety is not a complete temporal algebra;
  derived intervals remain projections, not source truth.

### NormRule IR fail-closed design spine (M167 / RC11-F04a)
- Added pure predicate algebra over NormRule IR + synthetic `CaseFactSet`
  (conditions/exceptions/defeaters composition) with explainable steps.
- Top-level evaluator still only Abstains under ADR-0023 `[proposed]`;
  algebra outcomes never mint Applicable/NotApplicable.

- Review-case graph: split-parent `blocked_by` no longer freezes child residual
  work (breaks RC11-F04↔F04a/b mutual deadlock for stage continuity).
- Human design ceremony closed RC11-F04a (`execution_linked` + design
  `verification_recorded`); parent F04 remains blocked on open F04b.

- Added pure `NormRule` IR in `ln-applicability` (conditions, exceptions,
  defeaters, temporal scope) with closed kind vocabularies and fail-closed
  validation.
- IR-aware `evaluate_with_norm_rule` records structural IR observation in the
  explainable trace and still only abstains under ADR-0023 `[proposed]`.
- Non-claims: IR is design-only; no Applicable/NotApplicable; F04b runtime
  algebra remains deferred.

### Review Case multi-axis FSM residual inventory
- RC11-F03 process-closeable residual advanced via human ledger ceremony:
  `execution_linked` + class-matched `verification_recorded` (process proof) →
  derived closed. Product residuals F04–F09 unchanged.

- Added pure `review_case/fsm.py` observer over ledger-rematerialized packets:
  residual class, operator stages S0-S6, `next_admissible_events`, and
  `missing_for_next` (event-sourced multi-axis FSM projection, not a writable
  status field).
- Application use case `review_case_inventory` + CLI
  `law-nexus-harness review-case inventory` emit schema
  `review-case-fsm-inventory/v1` with non-claims; no disposition/GSD writes.
- Dogfood on `RC-2026-08-11-001`: terminal F01, process_closeable F03,
  blocked_graph F04/F04a/F04b, product_open F06-F09, deferred F13.
- Tests: pure FSM unit coverage + live RC11 residual board + CLI inventory path.

### README current-state snapshot
- Expanded the root README from an architecture pointer into a detailed
  cold-reader landing page while preserving `prd/ARCHITECTURE.md` + active ADRs
  as canonical authority.
- Clarified the exact Rust workspace shape: 44 members consisting of 20
  exclusive ADR-0011 capability owners, 20 HC runners, `ln-product-cli`,
  `ln-testkit`, shared-infrastructure `ln-storage`, and repository-tracer
  `ln-status`; the latter four are not KOF-DA primary owners.
- Added architecture explanations for exclusive ownership, per-capability
  hexagonal boundaries, evidence-before-authority, five-clock/event-derived
  state, provider-isolated parsing, infrastructure ports, the Rust/Python
  control-plane split, and lifecycle anti-drift.
- Added a tracked repository map covering active product, contracts,
  governance, fixtures, tests, generated views, and assessment surfaces with
  their authority boundaries. Local-only and historical paths are deliberately
  excluded from cold-reader navigation.
- Added a short evidence-gated roadmap linked to
  `prd/project-state/roadmap.md` and `prd/migration/`, without silently choosing
  the human-owned parser-G2/CTV/infrastructure ordering.
- Recorded the clean post-remediation `f09416f` process snapshot: 435 Python
  tests passed with 4 skipped; Governor 54 PASS / 1 advisory WARN / 0 ERROR / 0
  TOOL ERROR; preflight 7 PASS / 1 advisory WARN / 0 ERROR. These are process
  checks, not product readiness proof.
- Published the corrected `repository-quality` badge, then repaired the two
  fresh-runner failures it exposed: `ty`-compatible ADR expectation fallback
  typing and a locked online Cargo fetch before offline Rust check/build/test
  gates. Offline verification semantics remain unchanged after bootstrap.
- Removed local-only and historical repository navigation from the root README
  and added a tracked-Markdown regression test that rejects links to those
  surfaces; decommission facts remain prose boundaries rather than destinations.
- Removed fresh-clone CI dependence on unpublished local GSD state: tracked
  roadmap inputs remain required, while absent local GSD projections are
  reported as not-applicable and present malformed/inconsistent projections
  still fail closed.
- Returned installed pre-commit-hook verification to local execution instead of
  hosted CI, where `actions/checkout` intentionally provides no installed hook;
  synthetic hostile hook tests remain in the repository.

## Unreleased — process debt triage

### GSD registry reconcile M161–M166
- Reconciled code-complete M161–M166 into GSD hierarchy via supported engine
  APIs: task summary repair, lifecycle shadow repair, STATE/QUEUE projection
  rebuild. Last completed milestone is M166-iyy4ak; phase complete.
- Project-state roadmap `current_milestone` advanced to M166 complete with
  explicit non-claims (process/registry truth only).
- No fabricated Attempts; no product readiness claim.

### Fail-closed applicability kernel (`ln-applicability` v0)
- New workspace crate `ln-applicability` implements ADR-0023 hexagonal domain/
  ports/application/adapters with **abstention-only** evaluation.
- Prerequisite gates (CTV, NormativeState, transitional, provenance) fail closed
  in stable order; complete prerequisites still abstain with
  `ProtocolUnimplemented` — no Applicable/NotApplicable product claim.
- Mandatory `ExplainableTrace` + non-claims on every outcome. Not a KOF-DA owner
  (ADR-0011 remains 20 exclusive owners).
- Project-state roadmap records M166 review-governance process band and
  applicability downstream blocker honestly; GSD Attempt lag remains advisory.

### Review Case derived-status honesty for already_satisfied
- `already_satisfied` is now a terminal residual disposition (`terminal_without_implementation`)
  with `execution_status=not_required`, not residual-open work.
- Status CLI / derive_finding_status no longer report satisfied docs/process findings as
  `derived_status=open`. Accepting dispositions that still need execution remain open/blocked.
- `deferred` stays residual-open inventory until later human reopen/accept/reject.

### Human Review Case ledger dispositions (session)
- Seeded live packets store from the two-review fixture (cross-packet finding
  endpoints filtered for policy) and recorded human `disposition_recorded`
  events for all 16 findings as actor `rager306`.
- Governor open inventory now rematerializes packets store through the event
  ledger so fixture snapshots no longer double-count residual opens; live
  `open_count=0` after session dispositions (still non-authoritative).

### Governor GSD registry visibility and residual-debt honesty
- Registry parser now accepts planned marker `⬜` (white large square) in addition
  to legacy `⚪`, so M162+ planned rows are no longer silently invisible.
- Hard residual debt uses only in-flight markers (`🔄`/`⏸`/`🟡`). Planned-only
  rows emit advisory `gsd-planned-inventory-visibility`.
- Advisory `gsd-code-complete-lag` when a milestone SUMMARY exists while the
  registry marker is not complete, **or** when a SUMMARY directory is orphaned
  from the STATE registry entirely (e.g. M165 SUMMARY without a registry row).
- Direct `.gsd/STATE.md` mutation remains engine-owned; this wave surfaces lag
  instead of rewriting GSD projections or fabricating Attempts.
- Session triage sheet + human ledger dispositions recorded under review-cases.

### Governor historical-test-debt precision
- Narrowed `historical-test-debt-visibility` so CI process-suite tests and pure
  anti-era control language are not treated as residual hard-dependency debt.
  Residual debt now requires hard-dependency signals (archived imports/clients).
- Live inventory dropped from 7 false-positive process tests to 0 residual
  non-CI hard dependencies.
- Process note: M166-iyy4ak Review Governance Lifecycle is code/docs complete on
  `main` through S01–S06 with green suite, but GSD DB/STATE still show planned/
  pending because manual execution did not create canonical Task Attempts. Do not
  invent completion receipts; reconcile through supported GSD Attempt workflow.

## M166 review governance lifecycle (2026-08-12)

### S06 two-review delta map and hardening
- Added pure `build_review_delta_map` projection and multi-packet `load_packets`
  codec path for cross-review fixtures.
- Tracked non-authoritative `review-11-12-delta-map.md` with empty confirmed
  closures/accepted promotions, residual open inventory of 16 findings, and
  explicit non-claims. No human disposition was invented; real findings remain
  `open / unplanned / unverified`.
- Process proof only: Review Case suites, Governor structural integrity, and
  clean-clone process coverage remain green. Review-proposed roadmap sequences
  stay proposals, not adopted authority.

### S05 Governor and clean-clone integration
- CLI `validate`/`status` rematerialize base packets through the append-only
  event ledger and fail closed on chain breaks; `register` remains base-only and
  still does not invent human disposition.
- Added Governor check `review-case-integrity` for authority laundering,
  source-hash mismatch, orphan promotion, class-mismatched closure, and ledger
  defects as hard structural findings; open findings stay advisory inventory.
- Wired Review Case CLI, Governor, schema, and delta-fixture tests into the
  repository-quality process suite and CI workflow for clean-clone coverage.
  Real review findings remain open pending S06 human acceptance.

### S04 append-only disposition ledger
- Added pure `apply_event` / `replay_events` so a clean base packet plus ordered
  consequential events deterministically materialize current status, including
  opaque `execution_linked` transitions.
- Added `EventLedgerEnvelope`, `EventLedger` port, event/envelope codec helpers,
  and a root-confined filesystem ledger under
  `prd/architecture/review-cases/packets/<id>/events/` with sequence and hash
  chaining. Gaps, forks, hash tamper, duplicates, partial temps, and path escape
  fail closed.
- Added application commands for human disposition, relation, execution-link,
  verification, and reopen that pure-apply first, append receipts, then rematerialize.
  No unauthenticated CLI disposition surface; no GSD/Product/Requirements/ADR
  mutation. Real review findings remain open pending S06 human acceptance.

### S03 persistence codec and CLI vertical slice
- Added outer Pydantic v2 codec adapter with strict/extra-forbid wire models,
  payload-only `tested_revision`, exact JSON authority booleans, deterministic
  canonical bytes, and honest generated-schema diagnostics resolved via `$ref`.
- Added root-confined filesystem source reader and atomic packet store adapters
  (symlink/path-escape/forbidden-prefix/duplicate/corrupt fail-closed) plus a
  stdlib hashlib ContentHasher.
- Wired `law-nexus-harness review-case register|validate|status` with
  deterministic JSON reports and exit classes 0/1/2. Commands do not disposition,
  promote authority, or create GSD work. Adaptix remains deferred with measured
  non-need on the v1 path.
- Process proof only: codec/filesystem/CLI suites and typing gates pass. No
  Governor check, hosted CI gate, or semantic acceptance claim is made.

### S02 pure Review Case core
- Added pure stdlib domain values, disposition/relation policy, proof/rollup
  derivation, and application ports/use cases under
  `src/law_nexus_harness/review_case/` with a recursive inner-module vendor ban.
- Kept derived status non-persisted, verification audit reconstructable, and
  human disposition / promotion firewalls fail-closed in pure policy.

### S01 authority and Review Case contract
- Added ADR-0024 `[proposed]` to define immutable review sources, a
  non-authoritative Review Case projection, append-only human disposition,
  canonical promotion through existing authority, reference-only GSD execution
  links, and class-matched revision-bound closure.
- Fixed the onion boundary before implementation: pure standard-library
  contracts point inward; filesystem, CLI, Governor and codecs remain outer
  adapters. Pydantic v2 is an adapter-only candidate for later bounded probes;
  Adaptix remains deferred pending measured mapping complexity.
- Added the explicit `review-case/v1` JSON Schema and hostile contract tests for
  authority laundering, source/hash drift, invalid status/relationship kinds,
  non-human promotion, class-mismatched proof and blocked-parent closure. These
  are process contracts, not a runtime or semantic-acceptance claim.
- Added a two-packet, 16-finding review-11/review-12 delta fixture with exact
  tracked source hashes and span hashes. All 21 relations are candidates and all
  real findings remain `open / unplanned / unverified` until human disposition;
  the review-proposed M166–M176 sequence remains a roadmap proposal only.
- Added a document-freshness trigger for Review Case schema/packet changes and
  synchronized ADR truth, index, cross-matrix and cold-reader surfaces. No
  Product, Requirements, temporal-ontology, parser, applicability or legal
  lifecycle was promoted.

## Post-M165 architecture assessment and semantic-control remediation (2026-08-11–12)

### M165 temporal legal ontology design
- Added ADR-0016 through ADR-0022 as the `[proposed]` L1–L7 temporal legal
  ontology spine: FRBR/LRMoo identity, component temporal versioning,
  NormativeState, hierarchy/conflict, practice overlay, transitional/risk, and
  industry profiles.
- Integrated the ontology into the living truth oracle and root README while
  keeping external LRMoo/AKML/ELI/LKIF models as D046 compatibility references,
  not replacements for the project-local evidence kernel.
- Kept all ontology layers design-only: no event-sourced CTV runtime, NormRule
  graph, applicability evaluator, correction ledger, or legal validation was
  promoted.

### Rust-only active-plane and archive cleanup
- Reaffirmed Rust-only product ownership and the thin ADR-0007 Python
  repository-harness boundary; removed local probes/noise and kept
  `.agents/skills/**` local-only and gitignored.
- Removed or archived residual FalkorDB, ACP/git-lex, PyO3, pre-Rust PRD,
  research, parser-dump, and retrieval-era surfaces from the active plane.
- Added Governor entrypoint checks for retired ADR IDs and unqualified
  historical-era vocabulary. Historical ACP/git-lex and FalkorDB remain
  archive-only and cannot regain runtime, CI, hook, or authority status.
- Reworked the root README and active PRD surfaces around the post-cleanup tree;
  historical local vaults remain prior art rather than clean-clone proof.

### Product/requirements and temporal assessment packet
- Published `prd/PRODUCT.md` and `prd/REQUIREMENTS.md` as `[proposed]`
  cold-reader contract/projection surfaces and reconciled their requirement
  inventory and trace chains. Document readiness did not validate product
  behavior.
- Added `prd/temporal-legal-model.md` with controlled glossary, fail-closed
  invariants, TL-G01–12 proof gates, paper semantic-shape cases, and the
  ontology crosswalk.
- Added ADR-0023 for `[proposed]` applicability decision/trace ownership while
  explicitly deferring the runtime DSL/AST, field schema, evaluator, and API.
- Completed D0/EA-10 documentation/process assessment stages. Independent EA-09
  assessed revision `120d44b`; human D150 accepted that exact packet with
  findings. Later remediation commits have no successor acceptance and do not
  inherit D150.

### Governor, ADR, trace, and freshness hardening
- Added selectable Governor explain/inventory controls and exact tracked
  evidence anchors for semantic, ADR, hostile-proof, and roadmap findings.
- Distinguished policy findings from tool failures and made unreadable scans,
  malformed catalogs, and failed inventory producers fail closed as structured
  tool errors instead of false passes.
- Added deterministic validation of ADR links, supersession graph, index/matrix
  coverage, lifecycle synchronization, published authority trace chains, and
  retired-ID boundaries.
- Added the non-authoritative generated ADR cross-matrix and redacted source
  snippets from ADR conformance diagnostics to avoid leaking unnecessary
  content.
- Added `prd/architecture/document-freshness-triggers.json`, companion-surface
  policy, review dates, and exact evidence locations for consequential-document
  changes.
- Closed discovered Governor audit false passes while retaining semantic/free-
  text checks as advisory where deterministic legal interpretation is unsafe.

### Project-document reconciliation
- Reconciled the living oracle, root README, product/requirements projections,
  roadmap, ADR matrix, assessment packet, and published trace controls.
- Added post-D150 assessments 13–18 to distinguish current-head facts,
  deterministic remediation, parser evidence gaps, glossary control, and
  remaining human/Rust-owned work.
- Kept architecture registries, claims ledgers, roadmaps, assessments,
  Governor output, `.gsd/**`, and GitNexus as process/derived evidence only;
  none can satisfy product requirements or promote lifecycle.

### Parser protocol and historical workflow quarantine
- Added `prd/parser/representative_golden_corpus_acceptance_protocol.md` with
  explicit G0–G3 evidence levels, provider isolation, manifest/provenance
  requirements, hostile cases, metric/threshold ownership, and lifecycle
  ceilings.
- Classified current parser evidence as G1 `[bounded]`: one tracked real
  Consultant fixture and one tracked real Garant fixture plus structural and
  hostile contracts. G2 multi-fixture independent annotation and G3 human
  source-bound acceptance remain open.
- Quarantined removed M006–M009 Python generator/probe workflows as historical
  references rather than runnable current verification, and added tests that
  preserve active Cargo verification routes and non-claims.
- Added assessments 15–16 to record that protocols specify proof but do not
  create representative fixtures, independent annotations, thresholds, legal
  correctness, or readiness.

### Temporal glossary and coding-injection governance
- Expanded the temporal glossary from 29 to 42 controlled rows and catalogued
  the complete row inventory plus TSG-001..TSG-016 continuity in
  `temporal-vocabulary-contract.json`.
- Added critique vocabulary including TextChangeEvent, NormativeEffectEvent,
  ComponentMembershipVersion, NormRule/Condition/LegalEffect/Defeater,
  ApplicabilitySelector, legal lists/classifiers, procurement resolution,
  practice coverage, and bitemporal correction ledger as
  `deferred-undefined` where no human-owned semantics exists.
- Added `glossary-governance.md` with required read order, ownership/update
  protocol, stop-signals, lifecycle boundaries, deterministic versus heuristic
  controls, and explicit non-claims.
- Hardened `temporal-vocabulary-contract` checks with glossary-local parsing,
  bidirectional glossary/catalog set equality, exact TSG set equality, required
  governance fragments, malformed-schema tool errors, and hostile regressions
  for decoys, omissions, stale IDs, and authority promotion.
- Added advisory deprecated-alias and temporal-vocabulary-presentation-drift
  checks. Product-domain policy tokens live in the non-authoritative JSON
  catalog rather than Python harness source, preserving ADR-0007.
- Corrected active wording around NormativeState, future EvidenceSpan/SourceBlock
  schemas, event-derived intervals, and practice temporality over the five
  clocks without inventing a sixth clock or applicability semantics.

### Historical readiness view and temporal completeness accounting
- Converted generated `product_readiness_blockers.md` from a current-looking
  priority/next-work report into a D7 historical registry archaeology index.
- Preserved all legacy gate/evidence IDs, recorded verification text, and
  non-claims while explicitly denying current readiness, priority, or work-queue
  authority; generator and tests prevent regeneration from restoring the old
  presentation.
- Added a 14-area temporal-contract completeness matrix covering glossary,
  entities, events, clocks, applicability, status, provenance, conflict,
  correction, invariants, API, goldens, errors, and proof gates.
- Marked event taxonomy and applicability DSL `deferred-undefined`, deterministic
  API and error taxonomy absent, and other areas honestly present/partial/paper-
  only. The matrix cannot close a TSG or generate a public Rust contract.

### Remaining explicit gaps
- Human decisions remain required for the ADR-0021 transition/risk split,
  typed event taxonomy, NormRule IR, applicability DSL, correction/reference
  ownership, stable APIs/errors, clean-tree comparison base, Stage D consumer,
  successor acceptance, and post-M165 investment sequence.
- Rust and real-evidence work remains required for parser G2/G3, CTV,
  NormativeState, applicability, conflict/practice/profile/procurement logic,
  correction/reference resolution, live TEI/RuVector, citation-safe retrieval,
  executable legal goldens, operational proof, R035/R038, and release readiness.

## M164 (complete)

### S01: Governor historical-test-debt-visibility probe
- New advisory governor check `historical-test-debt-visibility` (severity warn)
- Inventories tests/test_*.py NOT in CI_PROCESS_SUITE that reference
  decommissioned eras (ACP/git-lex, FalkorDB graph store, PyO3, MiniMax)
- Live repo surfaces `historical_test_count=59` as a visible advisory warn
  (non-blocking); governor overall stays ok
- Serves AGENTS.md "Never silently keep residual scripts/tests that
  hard-depend on archived product code" — non-destructive (nothing deleted)
- Excludes active decommission-policy controls (decommission/no_acp/
  no_forbidden/archive/verify_)
- Complements the M162 product-code honesty probe with test-suite honesty
- TDD: live-inventory + planted-detect + active-control-exclusion
- FalkorDB allowlist extended for the probe's detection-keyword regex

## M163 (complete)

### S01: CLI deterministic retrieval pipeline
- Eliminated the hardcoded constant-vector retrieval cascade in `law-nexus-inspect`
- Replaced 3 hardcoded `vec![0.5; 4]` sites (StubEmbedding, store loop, FindSimilar
  query) with a `deterministic_vector(text, dims)` helper (DefaultHasher-seeded)
- Same text -> identical vector; different text -> different vector; deterministic
- The M161 cosine-ranking retrieval now ranks distinct document vectors instead
  of returning constant cosine 1.0 for all (retrieval_count is no longer just a
  hierarchy-block count)
- TDD: 5 deterministic contract tests (same-text, different-text, deterministic,
  finite+unit-range, dimension-respected)
- Bounded, NOT semantic: hash-derived vectors; real semantic embedding needs TEI
  infrastructure. JSON output now tags retrieval_count as deterministic-non-semantic

## M162 (complete)

### S01: Governor semantic-stub-in-product-code probe
- New advisory governor check `semantic-stub-in-product-code` (severity warn)
- Scans active product Rust (crates/*/src/**/*.rs, excluding tests/ and ln-testkit)
  for stub/fake/dummy/placeholder/hardcoded comment markers and
  todo!()/unimplemented!()/panic!('not implemented') macros
- Closes the process gap (MEM676/D142) that let the M161 fake retrieval cascade
  pass every green process gate while product semantics were fabricated
- Governor now 37/0 (was 36/0); TDD: live-pass + planted-detect + tests/testkit-ignore

## M161 (complete)

### S01: Retrieval ranking semantic honesty
- Replaced the fake retrieval cascade with real cosine-similarity ranking
- `InMemoryVectorStore::query` now ranks by cosine similarity to the query vector (was: truncate-by-BTreeMap-key, ignoring the query vector)
- `RetrievalGate::retrieve` now assigns real per-result cosine scores and sorts results descending (was: constant `score = 1.0`)
- New pure `cosine_similarity` helper in ln-storage (scale-invariant, zero-norm=0, negative-clamped to [0,1] relevance)
- TDD: similarity contract (8), adapter ranking (3 incl. dimension-mismatch fail-closed), gate ranking (4 incl. hostile constant-score regression)
- VectorStorePort contract unchanged; blast radius LOW (RetrievalGate has 0 upstream callers)
- Lifecycle: `[bounded]` InMemory/vector-returning-adapter path; real ANN adapters (RuVector) need future scored-query port evolution

## M160 (complete)

### S01: Verify test CI coverage and governor test-coverage drift
- test_verify_adr_conformance and test_verify_repository_pre_commit_hook in CI
- Governor check `verify-test-coverage-drift` detects drift

### S02: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M159 (complete)

### S01: Architecture generator tests in CI
- 6 test files (159 tests) added to CI process suite and quality-gate inventory
- ci-quality-gate-drift stays green with process_suite=18

### S02: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M158 (complete)

### S01: Governor CI quality-gate drift anti-drift check
- Governor finding `ci-quality-gate-drift`
- Detects pre-commit hook / CI process suite / inventory script drift

### S02: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M157 (complete)

### S01: Live-adapter readiness governor and CI wiring
- Governor finding `live-adapter-readiness`
- CI process suite + inventory scripts include readiness

### S02: Cargo clippy quality-gate landing
- Pre-commit and CI: `cargo clippy --workspace --offline --all-targets -- -D warnings`
- Quality-gate inventory active checks include clippy; removed from future_additions

### S03: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M156 (complete)

### S01: CI process suite expansion and quality-gate honesty
- CI process-only suite includes preflight, quality-gate, inventory verifier tests
- Report-only inventory script steps in CI
- Quality-gate inventory `ci_process_suite` / `ci_inventory_scripts` honesty

### S02: Live adapter readiness report-only process surface
- `verify-live-adapter-readiness.py`: TEI `stub_transport_only`, RuVector `proposed`
- Overclaim scan; no live HTTP

### S03: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M155 (complete)

### S01: WordMLStreamingDecoder shared DecoderPort suite
- Fixture-aware honest DecoderPort contract entrypoint
- WordMLStreamingDecoder exercises shared suite on structural fixture

### S02: Multi-adapter real-port inventory and governor advisory
- `verify-multi-adapter-port-coverage.py` + governor `multi-adapter-port-coverage`
- Residual real multi-adapter gaps: 0 after WordML suite

### S03: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M154 (complete)

### S01: ADR-0015 stale non-claims honesty repair
- Critical ceiling and Non-claims no longer deny landed ln-testkit/allowlist
- TEI/RuVector/product non-claims preserved

### S02: BlockDecoderPort shared family-isolation suite
- Consultant WordML + Garant ODT pass shared own-family / foreign-family contract
- No cross-provider golden coupling; synthetic fixtures only

### S03: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M153 (complete)

### S01: Admission and closure residual hostile shared negatives
- BoundObservationPort honest + HostileVendorCapacity negative
- DependencyEvidencePort honest + HostileProgressCompleteness negative
- Allowlist 44 edges; hostile inventory gaps 4→2

### S02: Projection and work residual hostile shared negatives
- RebuildExecutorPort honest + HostileAuthoritativeExecutor negative
- DomainEvidencePort honest + HostileMutatingEvidence negative
- Allowlist 46 edges; hostile inventory 14/14 status ok; governor pass

### S03: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M152 (complete)

### S01: Hostile adapter inventory and governor advisory
- `scripts/verify-hostile-negative-suite-coverage.py` inventory (mention-based)
- Governor finding `hostile-negative-suite-coverage` (debt = non-blocking warn)

### S02: EmbeddingPort shared contract for TEI stub transport
- `assert_embedding_port_contract` + TeiEmbeddingAdapter stub transport suite
- Honest embed + model/dimension/non-finite/transport rejection (not live TEI)

### S03: Publish and relation hostile shared negatives
- HostileDualWriterLedger fails honest publication suite
- OpenRelationHostileRegistry illicit unknown-predicate storage surface
- Hostile inventory gaps shrink 6→4 remaining

## M151 (complete)

### S01: Governor-native port-contract coverage check
- Governor finding `port-contract-coverage` (debt = non-blocking warn; crash = error)
- Full coverage pass includes explicit bounded non-claim (not TEI/RuVector/product readiness)
- Preflight pass message matches the evidence ceiling

### S02: Strict-gate wording and evidence-ceiling docs refresh
- Quality-gate `future_additions` no longer implies remaining uncovered InMemory adapters
- ADR-0015 records governor-native coverage trajectory

### S03: Validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M150 (complete)

### S01: Accelerate and conformance shared contracts
- AccelerationLedgerPort honest + HostileLabelMutator negative
- ConformanceOraclePort honest + HostileVerdictInflator negative
- Allowlist 39 edges

### S02: Dispose disposition and promotion gate shared contracts
- DispositionStorePort and PromotionGatePort suites
- Allowlist 40 edges

### S03: Relation and replay shared contracts
- RelationRegistryPort closed-registry suite
- CheckpointPort and EffectLedgerPort suites + HostileDuplicateEffectLedger negative
- Allowlist 42 edges; coverage inventory 22/22 covered (bounded port suites only)

## M149 (complete)

### S01: Inventory store and visibility shared contracts
- InventoryStorePort append-only history suite
- VisibilityPort inventory/review surface suite
- Allowlist 34 edges (`ln-testkit` → `ln-inventory`)

### S02: Gate and identity store shared contracts
- CandidateStorePort honest + InPlaceMutatingHostile negative
- IdentityStorePort honest + ErasingMergerHostile negative
- Allowlist 36 edges

### S03: Temporal clock evidence shared contract
- ClockEvidencePort present/missing anchor suite
- Allowlist 37 edges; coverage covered 15 / uncovered 7 / discovered 22

## M148 (complete)

### S01: Crate-qualified port-contract coverage identity
- Inventory schema v2 keys adapters as `crate::StructName`
- Same-named `InMemoryDiagnosticSink` across crates counted separately
- Discovered 22 / uncovered 16 after identity fix (was collapsed to 20/14)

### S02: Decode decoder and diagnostic shared contracts
- `ln-testkit`: honest DecoderPort suite + malicious decoder negative
- Decode `InMemoryDiagnosticSink` record/events suite
- Allowlist 31 edges (`ln-testkit` → `ln-decode`)

### S03: Observe and diagnostic sink shared contracts
- WorkStatePort + observe DiagnosticPort suites
- DiagnosticSinkPort honest allowlist + HostileCanary negative
- `DiagnosticCode::new` public for shared fixtures
- Allowlist 33 edges; coverage covered 10 / uncovered 12 / discovered 22

## M147 (complete)

### S01: Advisory preflight for port-contract coverage debt
- Preflight check `port-contract-coverage` runs inventory script
- Remaining InMemory debt yields warn (status ok); script crash fails closed
- Strict gate deferred to `future_additions`

### S02: Query state shared port contract
- `ln-testkit`: honest QueryStatePort suite + HostileGapInventor negative
- Allowlist 29 edges (`ln-testkit` → `ln-query`)
- Coverage covered set 5

### S03: Publication ledger shared port contract
- `ln-testkit`: PublicationLedgerPort store-level suite for InMemory
- Allowlist 30 edges (`ln-testkit` → `ln-publish`)
- Coverage covered 6 / uncovered 14 / discovered 20

### S04: Docs validation and terminal closure
- CHANGELOG and ADR-0015 updated; structured UAT PASS; terminal projections closed

## M146 (complete)

### S01: Citation source shared port contract
- `ln-testkit`: `assert_citation_source_contract` for honest resolve/missing/authority preservation
- Negative suite: HostileMirrorRelabeler fails honest Mirror→Official preservation
- InMemoryCitationSource passes shared suite

### S02: Promotion store shared port contract
- `ln-testkit`: `assert_promotion_store_contract` for commit visibility, idempotent put, cancel clearing
- InMemoryPromotionStore passes shared suite
- Crate allowlist: 28 edges (`ln-testkit` → storage/citation/promote)

### S03: InMemory port-contract coverage inventory
- `scripts/verify-port-contract-coverage.py` report-only inventory
- Covered 4 / uncovered 16 / discovered 20 InMemory adapters
- `--strict` fails while debt remains; default does not block gates

### S04: Docs CHANGELOG and ADR follow-on sync
- CHANGELOG and ADR-0015 follow-ons updated honestly

### S05: Validation and terminal closure
- Structured UAT PASS; M146 formally complete; terminal projections closed

## M145 (complete)

### S01: Executable crate dependency allowlist
- Added `prd/architecture/crate-dependency-allowlist.json` (26 workspace path edges)
- Added `scripts/verify-crate-dependency-allowlist.py` via `cargo metadata`
- Tests cover undeclared edges, stale edges, capability→HC runner and capability→CLI bans

### S02-S03: ln-testkit shared storage port contracts
- Added `crates/ln-testkit` with VectorStorePort and GraphStorePort contract helpers
- InMemory adapters exercise the shared suite from ln-testkit tests
- One-way dependency only: `ln-testkit -> ln-storage` (no reverse dev-dep)

### S04: Gate wiring and docs
- Preflight check `crate-dependency-allowlist`
- Pre-commit + CI + quality-gate inventory wired to allowlist script

## M144 (complete)

### S01: Write ADR-0015 verification architecture
- Added `doc/adr/0015-hexagonal-verification-architecture.md`
- Overlapping contours, port-contract policy, lifecycle honesty, anti-slop rules
- Explicit non-claims for unbuilt testkit/allowlist/real-adapter infrastructure
- ADR index updated

### S02: Align Rust verification matrix to ADR-0015
- Updated `.agents/skills/law-nexus-rust/references/verification-matrix.md`
- Contours, port-contract rules, lifecycle/non-claims, anti-slop checks

### S03: Bind concrete testing rules in AGENTS.md
- Local `AGENTS.md` testing contract (gitignored overlay by project policy)
- Always/never rules and change-class minimum proof table
- Corrected active architecture note: Python product is archived prior art
- Tracked skill entrypoint binds ADR-0015 in S04

### S04: Docs sync CHANGELOG and decision record
- Decision D140 recorded
- Tracked skill entrypoint cites ADR-0015
- CHANGELOG synchronized; gates clean after reindex

### S05: Validation and terminal closure
- Structured UAT PASS; M144 formally complete; terminal projections closed

## M143 (complete)

### S01: Archive orphan residual scripts
- Archived 19 residual scripts with zero active test or control-plane consumers
- Active scripts: 87; archived product scripts: 56
- Active pytest remains green: 1398 passed, 2 skipped

### S02: Remove dead import-linter dependency
- Removed unused `import-linter` from active dev dependencies after onion gate removal
- Refreshed `uv.lock`

### S03: Release build baseline and CLI smoke
- `cargo build -p ln-product-cli --release --offline` PASS
- Release health ok
- Consultant release inspect avg 11.7ms / 167 blocks; Garant avg 186.5ms / 5124 blocks
- Evidence: `prd/migration/rust-evidence/probes/m143-release-baseline.{json,md}` `[bounded]`
- No production packaging claim

### S04: Docs verification and CHANGELOG
- CHANGELOG synchronized; gates green after reindex

### S05: Validation and terminal closure
- Structured UAT PASS; M143 formally complete; terminal projections closed

## M142 (complete)

### S01: Repair active CI and quality gate contracts
- Removed dead `uv run lint-imports` and missing `verify-m112-adr-sync.py` CI steps
- Aligned pre-commit cargo path filters, gate inventory and quality-gate tests with harness-only control plane
- Rewrote ARCHITECTURE current layer: Rust product runtime + Python harness + `python_archive/product` prior art

### S02: Archive failing historical residual tests
- Archived 25 residual ACP/FalkorDB/retrieval/parser proof tests that failed on the active tree
- Active pytest: 1398 passed, 2 skipped, 0 failures

### S03: Archive orphan residual scripts
- Archived 8 residual scripts only consumed by archived historical tests
- Active scripts: 106; archived product scripts: 37

### S04: Active hygiene verification and docs
- CHANGELOG synchronized; gates green after reindex

### S05: Validation and terminal closure
- Structured UAT PASS; M142 formally complete; terminal projections closed

## M139 (complete)

### S01: Performance baseline and determinism proof
- CLI inspect latency: Consultant 30ms (167 blocks), Garant 657ms avg (5124 blocks)
- Output deterministic across 3 repeat runs (excluding variable duration_ms)
- Evidence: `prd/migration/rust-evidence/probes/m139-performance-baseline.{json,md}`

### S02: CLI security audit and hostile input tests
- Unsupported format (.txt) rejected as Parse/UnsupportedFamily
- Empty XML file produces zero blocks (not failure)
- Non-existent file rejected as Io/ReadFailure
- Directory as path rejected as Io/ReadFailure
- 4 new hostile tests, total 9 CLI integration tests

### S03: End-to-end acceptance evidence
- Both Consultant and Garant fixtures produce deterministic structured JSON
- Consultant: 167 blocks, 22 hierarchy, 69 refs, 1 temporal, 4 deontic, 29 unknown
- Garant: 5124 blocks, 140 hierarchy, 1882 refs, 36 temporal, 228 deontic, 2144 unknown
- KnowQL composition proven over in-memory adapters
- Evidence: `prd/migration/rust-evidence/probes/m139-end-to-end-acceptance.{json,md}`

### S04: Validation and terminal closure
- Structured UAT PASS (3 checks: CLI hostile tests, evidence portability, real CLI execution)
- M139 formally complete

## M141 (complete)

### S01: Harness boundary false positive fix
- CI harness suite failed because governor historical-only FalkorDB direction matched FORBIDDEN_SOURCE_TERMS
- Allow only historical-only FalkorDB vocabulary; keep product-domain bans
- CI process-only harness suite: 39 passed

### S02: Residual product-dependent tests archival
- Archived 32 residual active tests that hard-loaded M140-archived product scripts
- Active pytest collection: 1768 tests, 0 collection errors, 0 hard hits

### S03: Residual product-dependent scripts archival
- Archived hard-import/load dependency closure: 9 residual scripts + 9 cascading tests
- Active tree: 0 hard hits, 1695 tests collect cleanly, harness 39/39, governor 30/0
- Archived totals under python_archive/product: 29 scripts, 67 tests

### S04: Active collection hygiene and docs
- CHANGELOG and residual archival verified
- Governor 30/0, preflight 6/0 after reindex

### S05: Validation and terminal closure
- Structured UAT PASS; M141 formally complete; terminal projections closed

## M140 (complete)

### S01: Post-M139 debt audit
- Governor 30/0, preflight 6/0, dead code 0, unused 0, stale projections 0
- CHANGELOG corrected: M139 marked complete
- 157 test suites pass, 378 tests total, 23495 lines Rust code

### S02: Python product isolation verification
- Harness (src/law_nexus_harness/): zero imports from product — confirmed
- Tests: 26 files import from law_nexus.*
- Scripts: 20 files import from law_nexus.*
- pyproject.toml: import-linter contracts reference law_nexus.* modules

### S03: Python product archival cutover
- Moved src/law_nexus/ -> python_archive/product/law_nexus/ (62 files)
- Moved 26 dependent test files -> python_archive/product/tests/
- Moved 20 dependent scripts -> python_archive/product/scripts/
- Removed tool.importlinter contracts from pyproject.toml
- Added python_archive to basedpyright exclude
- Added *.egg-info/ to .gitignore
- Excluded python_archive/ from ruff pre-commit hooks
- Removed python-onion-dependencies hook (import-linter config removed)
- Harness (law_nexus_harness) and Rust workspace remain fully functional
- Governor 30/0 after archival

### S04: ADR promotion and docs synchronization
- ADR-0004 promoted to [validated]
- ADR-0005 promoted to [validated]
- Forward roadmap ADR matrix updated

### S05: Validation and terminal closure
- Structured UAT PASS; M140 formally complete; terminal projections closed

### S03: CLI failure state persistence
- Failure JSON now includes `attempt_count`, `fingerprint` (FNV1a64 of error message) and `duration_ms`
- Tests verify all three new fields on truncated-fixture failure path
- Success path contains no failure artifacts

- New crate `ln-product-cli` with binary `law-nexus-inspect`
- Subcommands: `health` (JSON status), `inspect <path>` (decode + extract + KnowQL composition)
- Inspect decodes Consultant XML or Garant ODT through ln-decode adapters
- Runs all four extractors + unknown-form census
- Composes KnowQL FindSimilar over in-memory storage adapters
- Structured JSON output with phase/status/duration_ms/source/result/non_claims
- Exit codes: 0 success, 1 parse failure, 2 usage error
- 5 integration tests

### S01: Tokenizer dedup and dead code audit
- Extracted shared `tokenizer.rs` module in `ln-decode` replacing 4 duplicate copies
- Removed `struct Token` + `fn tokens()` from `morphology.rs` (internal, behavior preserved)
- Removed `struct WordToken` + `fn words()` from `references.rs` (internal, behavior preserved)
- Removed `struct WordToken` + `fn words()` from `temporal.rs` (internal, behavior preserved)
- Removed `struct Token` + `fn tokens()` from `unknown_forms.rs` (internal, behavior preserved)
- All existing tests pass unchanged; zero external dependencies added
- Dead code audit: no warnings found
- Doc consistency: ADR-0014, ARCHITECTURE, roadmap all current

### S02: KnowQL typed AST
- Added `crates/ln-query/src/knowql.rs` with typed KnowQL AST over storage ports
- `KnowQLOp` enum: Embed, FindSimilar, FindByLabel
- `ValidatedOp` with construction-time validation
- `KnowQLResult` typed output
- `execute()` dispatcher over EmbeddingPort + VectorStorePort + GraphStorePort
- 8 hostile tests, ln-query depends on ln-storage for port traits

### S03: KnowQL integration proof
- Integration test decodes tracked Consultant fixture (167 blocks)
- Stores hierarchy annotations through InMemoryVectorStore and InMemoryGraphStore
- Queries back through KnowQL FindSimilar and FindByLabel operations
- Parser-to-storage-to-retrieval composition proven
- ln-query depends on both ln-storage and ln-decode

### S04: Validation and terminal closure
- Structured UAT PASS (3 checks: KnowQL contracts, integration, tokenizer regression)
- M137 formally complete

## M136 (complete)

### S01: Storage port contract boundaries
- D139 authority ceiling: storage ports are law-nexus-owned trait definitions
- ADR-0014 M136 storage port contracts section added
- External dependencies gated on port proof and license verification

### S02: Storage port trait contracts
- New crate `ln-storage` with zero external dependencies
- `EmbeddingPort`, `VectorStorePort`, `GraphStorePort` trait definitions
- Validated request/response types with construction-time validation
- 10 hostile tests

### S03: TEI embedding adapter
- `TeiEmbeddingAdapter` behind `EmbeddingPort` with injectable `EmbeddingTransport`
- Model identity, dimension and finiteness fail-closed boundaries
- 8 hostile tests, zero external dependencies

### S04: In-memory adapters with operation journal
- `InMemoryVectorStore` and `InMemoryGraphStore` implementing storage ports
- `OperationJournal` with deterministic replay after simulated crash
- 7 hostile tests, zero external dependencies

### S05: Retrieval/citation gate composition
- `RetrievalGate` composing all three storage ports
- `Citation` with traceable source spans and tamper detection
- Graph store metadata enrichment via `evidence_labels`
- 6 hostile tests, zero external dependencies

### S06: Validation and terminal closure
- Structured UAT PASS (4 checks, 31 tests total)
- ADR-0014 remains `[proposed]`; real TEI/RVF/redb gates unproven
- M136 formally complete, terminal projections closed

## M135 (complete)

### S01-S06: Rust golden pipeline
- `GoldenFixture`, `GoldenSource`, `GoldenAnnotation` manifest types
- `GoldenEvaluator` with per-layer precision/recall/F1
- `UnknownFormCollector` with bounded near-miss dictionaries
- Tracked real fixture enrichment evidence
- Self-consistent P=R=F1=1.0 pipeline composition proof
- ADR-0013 remains `[bounded]`; human-reviewed golden annotations deferred

## M134 (complete)

### S01-S06: Shared lexical extractors
- `ReferenceMention` extractor (статья/пункт + decimal/dotted numbers)
- `TemporalPhrase` extractor (вступает/утрачивает силу)
- `DeonticLexeme` projection (обязан/вправе/запрещается)
- Cross-provider integration and tracked real census evidence
- D137 lexical candidate authority ceiling
- ADR-0013 promoted to `[bounded]`

## M133 (complete)

### S01-S06: Garant ODT adapter
- Bounded in-memory ODT package intake (`zip = "=8.6.0"`)
- Independent `GarantOdtBlockDecoder` behind `BlockDecoderPort`
- `SourceStreamId` and `SourceLocation` coordinate authority
- Real Garant ODT tracer with deterministic 5124-block census

## M132 (complete)

### S01-S05: Consultant WordML adapter
- `ConsultantWordMlBlockDecoder` behind `BlockDecoderPort`
- Shared bounded hierarchy extraction (Раздел, Глава, §, Статья)
- Real Consultant XML tracer with deterministic 167-block census

## M131 (complete)

### S01-S03: Parser domain foundation
- `ParsedBlock`, `TextSpan`, `SourceSpan`, `SourceLocation` domain types
- `BlockDecoderPort` and `DecodeRequest`/`BlockDecodeError`
- Bounded morphology (`find_legal_markers`) and sentence splitting
