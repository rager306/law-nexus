# Temporal Semantic Gap Register

**Lifecycle:** `[bounded]` documentation inventory; capability rows retain their stated `[proposed]` or `[deferred]` ceilings  
**Status:** non-authoritative gap projection  
**Source criticism:** recovered primary review recorded in `assessment/13-current-head-gap-audit.md`  
**Authority:** `prd/ARCHITECTURE.md` and active ADRs; this register cannot satisfy a requirement, promote lifecycle, or establish legal/product correctness.

## 1. Purpose

This register prevents confirmed semantic gaps from disappearing when publication and process defects close. It classifies missing documentation, design, implementation and evidence without turning assessment prose into architecture truth.

Closure requires the governing authority and proof named in the row. A documentation edit alone cannot close an implementation or evidence gap.

**G0 note (2026-08-20, D216):** the ADR-0017/0018/0016 G0 amendments
(`doc/review/review-25-08-2026.md`) sharpen the closure triggers of
TSG-002/003/012/013 toward the ledger/compiler/CST design. This is a trigger
refinement, not a closure: every row below stays `active` until its named
executable proof lands.

## 2. Active gaps

| Gap ID | Capability or term | Class | Governing owner | Current lifecycle | Current non-claim | Closure trigger and required proof | Status |
|---|---|---|---|---|---|---|---|
| TSG-001 | Complete temporal controlled vocabulary, including `edition_date`, projected `effective_from/to`, `EvidenceSpan`, `SourceBlock` and deprecated aliases | documentation | ADR-0009, ADR-0017, ADR-0018, temporal model | mixed `[bounded]` / `[proposed]`; future evidence entities deferred-undefined | glossary consistency is not legal correctness or runtime proof | tracked crosswalk names owner, vocabulary status and fail-closed boundary; deterministic drift checks may follow | active |
| TSG-002 | Typed TextChangeEvent versus NormativeEffectEvent taxonomy | design | ADR-0017 and ADR-0018 | `[proposed]` | lexical or amendment text does not prove legal effect | design canon now the G0 ledger/amendment algebra (ADR-0017 G0(a)-(g)); closure requires typed Rust events over accepted assertions with provenance assertions and hostile substitution tests | active |
| TSG-003 | Event-sourced CTV operations, including split, merge, move, renumber and whole-act fail-closed compilation | implementation/evidence | ADR-0017 | `[proposed]` | no executable CTV runtime or real-amendment correctness | deterministic amendment compiler fold over accepted assertions with fail-closed whole-act compilation (ADR-0017 G0); Rust resolver/ports, positive and hostile contracts, representative amendment fixtures and human scope acceptance | active |
| TSG-004 | NormativeState dimensional separation and canonical public type | design/implementation | ADR-0018 | `[proposed]` | `NormativeStatus` compatibility wording is not a second validated model | public Rust type and resolver preserve text/status/applicability separation with provenance and hostile joins | active |
| TSG-005 | NormRule intermediate representation and normative rule graph | design | future ADR under ADR-0023 prerequisites | `[deferred]` | parser lexemes, LLM text and derived graphs are not rules or authority | explicit owner/ADR, typed IR, provenance, abstention and hostile candidate-to-rule promotion tests | active |
| TSG-006 | ApplicabilityPredicate/Decision/ExplainableTrace executable protocol | implementation/evidence | ADR-0023 | ownership `[proposed]`; runtime `[deferred]` | CTV, `InForce`, profile code, similarity and LLM cannot decide a case | Rust domain/ports, abstention contracts, representative real cases and human legal-scope acceptance | active |
| TSG-007 | Competence, delegation and normative hierarchy evidence graph | design/implementation | ADR-0019 | `[proposed]` | hierarchy prose does not validate conflict resolution | typed authority/rank provenance, conflict resolver, hostile delegation cases and representative evidence | active |
| TSG-008 | Practice coverage taxonomy distinguishing no practice, incomplete search and conflicting practice | design/evidence | ADR-0020 | `[proposed]` | observed practice does not rewrite kernel state or guarantee legal truth | typed coverage outcomes, PracticeEvidence port/projection, hostile missing/conflict cases and bounded corpus review | active |
| TSG-009 | Transitional resolution separated from advisory risk | design/implementation | ADR-0021 | `[proposed]` | chronology or risk score cannot decide applicability | separate typed outputs/ports, explicit provision provenance, `Unknown` risk and hostile chronology-default tests | active |
| TSG-010 | Versioned profile lists/classifiers and procurement case graph | design/implementation | ADR-0022 and ADR-0023 | `[proposed]`; applicability runtime `[deferred]` | profile inputs do not mutate neutral clocks, ranks, CTV or state | versioned input contracts, profile-isolation tests, representative procurement cases and human scope acceptance | active |
| TSG-011 | Immutable correction ledger and deterministic projection replay | implementation/evidence | ADR-0009 and ADR-0017; TQ-04 | invariant `[proposed]` | current wording does not prove a temporal database or correction runtime | immutable observation/storage port, rebuild equivalence and hostile in-place-rewrite rejection | active |
| TSG-012 | Temporal cross-reference resolution from candidate through identity, CTV and NormativeState | design/implementation | ADR-0017 and ADR-0019 (TQ-05 G0 disposition, D216) | `[proposed]` gap | latest text or unresolved parser candidate is not citation authority | ReferenceMention/Binding/Semantics typed resolver with Unclassified default (ADR-0019 G0 note), typed non-success outcomes and historical-reference fixtures | active |
| TSG-013 | Structural parent/child membership versioning and cardinalities | design/implementation | ADR-0016 and ADR-0017 | `[proposed]` | identity documentation does not prove corpus-wide membership correctness | OrderedMembershipVersion/AddressableTextUnit event contract (ADR-0017 G0(e)), explicit cardinality contract, split/move hostile tests and multi-provider identity fixtures | active |
| TSG-014 | Self-contained temporal API contract and unified typed error taxonomy | documentation/design | temporal model plus future owning ADRs | partial `[proposed]` | paper signatures and golden shapes are not a stable public API | declared request/result/error schemas tied to owning ports and hostile-negative contracts | active |
| TSG-015 | Golden-case catalog breadth and executable promotion | evidence | temporal model TL-G01..TL-G12 | 18 paper cases; mixed ceilings | paper cases are semantic-shape oracles, not legal gold answers | each promoted case has an owner, executable positive/hostile proof, revision-bound fixture and honest non-claim | active |
| TSG-016 | Retrieval scoring and ranking honesty beyond InMemory synthetic contracts | evidence | ADR-0014, ADR-0015, PC/RQ-006 and 019 | InMemory scoring `[bounded]`; live infrastructure `[proposed]` | real cosine values do not establish Russian legal retrieval quality | representative EvidenceSpan/SourceBlock contract, real 1024d corpus, quality metrics, exact citation round-trip and human acceptance | active |
| TSG-017 | EditionOracle-versus-AmendmentEvent assembly of a temporal AST from provider XML (corpus roles, evidence classes, checksum fold) | design | ADR-0013, ADR-0016, ADR-0017 | Review 4 inventory is historical; oracle diff (KBO-R047) and `edition_ast_at` (KBO-R045) are `[bounded]`; single Consultant-act assembly is `[bounded]` at `S_ready_bounded` (402-ФЗ fixture full pipeline, 44-ФЗ edition-0118 drift=0, replay 0080→0081); corpus-wide assembly and resolve_CTV (KBO-R046) remain open | one consolidated XML or a change-overview is not legislative history; fold projection is not CTV text | owning ADR amendments landed as design; executable classify/propose/admit/fold/oracle-diff plus representative C0/C1 or second C2 fixture | active |

## 2.1 Design-boundary inventory (non-closure)

The following is **not** a TSG row closure. It records that RC11-F06 design proof
made the five-clock vs algebra boundary explicit in `ln-temporal`:

- `TemporalAlgebraCapability` + `classify_temporal_capability` inventory deferred
  interval/bitemporal/legal-date/applicable-law capabilities as
  `DeferredAlgebra` with mandatory non-claims.
- Five-clock HC-09 safety remains `[bounded]`; algebra/runtime gaps (including
  TSG-011 and incomplete temporal axes) remain **active** until their own
  proof triggers fire.
- Design boundary inventory ≠ interval algebra implementation and ≠ legal-date
  validation.


### RC11-F07 TextChange vs NormativeEffect (non-closure)

- `LegislativeEventKind` + `classify_legislative_event_kind` name and separate
  TextChangeEvent vs NormativeEffectEvent as **design-only** kinds in `ln-temporal`.
- Lexical text change must not prove legal effect (`reject_text_change_as_normative_effect`).
- TSG-002 remains **active** until executable CTV event types, hostile substitution
  tests at runtime, and provenance-backed micro-events ship. Design taxonomy ≠ runtime.


### RC11-F09 NormativeState dimensional separation (non-closure)

- `NormativeDimension` + `classify_normative_dimension` name force/status,
  version relation, applicability, and epistemic outcome as **orthogonal**
  design dimensions in `ln-temporal`.
- Fail-closed helpers reject force→applicability and version/text→force collapse.
- TSG-004 remains **active** until an executable NormativeState resolver with
  provenance-backed transitions and hostile joins ships. Design inventory ≠ runtime.


- Bounded offline **`resolve_force_status_at`** + `ForceStatusTimeline` in
  `ln-temporal` implement **ForceStatus only** (ladder **S2–S3**): missing/conflicting
  evidence → `Unknown` (never assume `InForce`).
- Offline **`join_force_with_membership`** joins force resolution with structural
  membership context (KBO-R012 / O2 partial). Membership presence never upgrades
  force to `InForce`; join never claims Applicability. Still not CTV text edition
  store, not corpus status-edge proof. TSG-004 remains **active**.

### RC11-F08 CTV membership + industrial ops spine (non-closure)

- `MembershipGraph` + `plan_industrial_op` + `whole_act_structural_compile` in
  `ln-temporal` provide a **fail-closed structural** spine for renumber/move/split/merge
  and whole-act membership completeness (RC11-F08 / TSG-003/013).
- Bounded-runtime **`apply_industrial_op`** mutates membership and appends
  `StructuralEventLog` events offline with hostile plan-mismatch / duplicate-op
  guards (ladder **S3**). Still not temporal CTV store or legal amendment proof.
- Structural plans/applies require amending-act provenance and never claim legal
  effect, temporal CTV resolution, or real-amendment corpus correctness.
- Offline **`fold_membership_at`** builds a `StructuralAst` projection from
  versioned attach/detach events (TSG-013 S3). Same-day two-parent attach is
  `MembershipConflict`. The AST is not canon, not CTV text, not Expression bind.
- TSG-003 and TSG-013 remain **active** until representative amendment fixtures,
  Expression binding, calendar `legal_act_effect`, and human scope acceptance land.
  Fold S3 ≠ full CTV product.
- Offline **`fold_expression_presence`** binds CC to a dated Expression via
  include/exclude events (KBO-R023). A later Expression does not inherit silently.
  Still not CTV text, not corpus reconstruction.
- Offline **`map_hierarchy_marker`** lifts a decode-facing `HierarchyMarker` to CC
  only through an explicit registry (KBO-R024 / R3-02). Unmapped → `Unknown`;
  number+level never mints a CC. Ontology crate does not depend on `ln-decode`.

### Review 4 assembly process (non-closure)

- Review 4 (`doc/review/review-13-08-2026.md`) names `AmendmentEvent`,
  `EditionOracle`, corpus roles C0–C3, evidence classes and a separate
  `assembly_fsm`. This is **design inventory**, not S4 fixtures and not
  `resolve_CTV`.
- TSG-002/003/013 remain the event/text/membership spines. **TSG-017** is the
  process gap: how XML roles become events and how oracles checksum the fold.
- Current 44-ФЗ disk set (one `ред. от 28.12.2025` + overview) does not close
  TSG-017. C2hint lexical counts are not legislative events.


### RC12-F05 applicability capability inventory (non-closure)

- `ApplicabilityCapability` + `classify_applicability_capability` name landed
  spines (abstention kernel, NormRule IR, predicate algebra) vs deferred product
  capabilities (positive decision, product CaseFacts, profile specials, real-case
  acceptance) in `ln-applicability`.
- Fail-closed helpers reject algebra Satisfied → Applicable and IR presence →
  product runtime completeness.
- TSG-005/006 remain **active** until positive applicability with real-case
  evidence and human acceptance. Inventory ≠ product readiness.

## 2.2 Continuity vs gap closure

Review Case residual closeout (L_review) is not TSG closure (L_capability).
Operator continuity contract:
`prd/architecture/review-cases/continuity-contract.md` and ADR-0024 §9a.

When a review finding closes at ceiling `spine` / `bounded_runtime` / `evidence`,
the related TSG row stays **active** until that row's own closure trigger fires.
Section 2.1 non-closure notes (RC11-F06…F09, RC12-F05) are the current B3
record for those spines.

L_capability ladder, promotion packet rules, and current TSG progress board:
`prd/architecture/capability-promotion-board.md` (Governor check
`capability-promotion-board`).

## 3. Disposition rules

A row may move to `closed-bounded` only when:

1. its governing authority is tracked and current;
2. the stated proof exists at a repository-relative durable anchor;
3. at least one relevant hostile/failure path is demonstrated;
4. lifecycle and non-claims remain explicit;
5. evidence class matches the closure claim;
6. human acceptance is recorded where the row requires legal or semantic judgment.

`deferred` means visible and intentionally not implemented. It does not mean rejected, safe by default, or satisfied by documentation.

## 4. Non-claims

- This register is not a product backlog commitment or source truth.
- It does not revive archived Python, ACP/git-lex or FalkorDB architecture.
- It does not validate Product, Requirements, parser behavior, retrieval quality, temporal legal correctness, case applicability, RuVector/TEI infrastructure or release readiness.
- Governor checks may verify deterministic register structure or orphaned terms, but heuristic semantic findings must remain advisory and human-disposed.

<!-- Review 6 progress audit companion -->
