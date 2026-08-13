# Temporal Semantic Gap Register

**Lifecycle:** `[bounded]` documentation inventory; capability rows retain their stated `[proposed]` or `[deferred]` ceilings  
**Status:** non-authoritative gap projection  
**Source criticism:** recovered primary review recorded in `assessment/13-current-head-gap-audit.md`  
**Authority:** `prd/ARCHITECTURE.md` and active ADRs; this register cannot satisfy a requirement, promote lifecycle, or establish legal/product correctness.

## 1. Purpose

This register prevents confirmed semantic gaps from disappearing when publication and process defects close. It classifies missing documentation, design, implementation and evidence without turning assessment prose into architecture truth.

Closure requires the governing authority and proof named in the row. A documentation edit alone cannot close an implementation or evidence gap.

## 2. Active gaps

| Gap ID | Capability or term | Class | Governing owner | Current lifecycle | Current non-claim | Closure trigger and required proof | Status |
|---|---|---|---|---|---|---|---|
| TSG-001 | Complete temporal controlled vocabulary, including `edition_date`, projected `effective_from/to`, `EvidenceSpan`, `SourceBlock` and deprecated aliases | documentation | ADR-0009, ADR-0017, ADR-0018, temporal model | mixed `[bounded]` / `[proposed]`; future evidence entities deferred-undefined | glossary consistency is not legal correctness or runtime proof | tracked crosswalk names owner, vocabulary status and fail-closed boundary; deterministic drift checks may follow | active |
| TSG-002 | Typed TextChangeEvent versus NormativeEffectEvent taxonomy | design | ADR-0017 and ADR-0018 | `[proposed]` | lexical or amendment text does not prove legal effect | governing ADR amendment plus typed Rust events, hostile substitution tests and provenance assertions | active |
| TSG-003 | Event-sourced CTV operations, including split, merge, move, renumber and whole-act fail-closed compilation | implementation/evidence | ADR-0017 | `[proposed]` | no executable CTV runtime or real-amendment correctness | Rust resolver/ports, positive and hostile contracts, representative amendment fixtures and human scope acceptance | active |
| TSG-004 | NormativeState dimensional separation and canonical public type | design/implementation | ADR-0018 | `[proposed]` | `NormativeStatus` compatibility wording is not a second validated model | public Rust type and resolver preserve text/status/applicability separation with provenance and hostile joins | active |
| TSG-005 | NormRule intermediate representation and normative rule graph | design | future ADR under ADR-0023 prerequisites | `[deferred]` | parser lexemes, LLM text and derived graphs are not rules or authority | explicit owner/ADR, typed IR, provenance, abstention and hostile candidate-to-rule promotion tests | active |
| TSG-006 | ApplicabilityPredicate/Decision/ExplainableTrace executable protocol | implementation/evidence | ADR-0023 | ownership `[proposed]`; runtime `[deferred]` | CTV, `InForce`, profile code, similarity and LLM cannot decide a case | Rust domain/ports, abstention contracts, representative real cases and human legal-scope acceptance | active |
| TSG-007 | Competence, delegation and normative hierarchy evidence graph | design/implementation | ADR-0019 | `[proposed]` | hierarchy prose does not validate conflict resolution | typed authority/rank provenance, conflict resolver, hostile delegation cases and representative evidence | active |
| TSG-008 | Practice coverage taxonomy distinguishing no practice, incomplete search and conflicting practice | design/evidence | ADR-0020 | `[proposed]` | observed practice does not rewrite kernel state or guarantee legal truth | typed coverage outcomes, PracticeEvidence port/projection, hostile missing/conflict cases and bounded corpus review | active |
| TSG-009 | Transitional resolution separated from advisory risk | design/implementation | ADR-0021 | `[proposed]` | chronology or risk score cannot decide applicability | separate typed outputs/ports, explicit provision provenance, `Unknown` risk and hostile chronology-default tests | active |
| TSG-010 | Versioned profile lists/classifiers and procurement case graph | design/implementation | ADR-0022 and ADR-0023 | `[proposed]`; applicability runtime `[deferred]` | profile inputs do not mutate neutral clocks, ranks, CTV or state | versioned input contracts, profile-isolation tests, representative procurement cases and human scope acceptance | active |
| TSG-011 | Immutable correction ledger and deterministic projection replay | implementation/evidence | ADR-0009 and ADR-0017; TQ-04 | invariant `[proposed]` | current wording does not prove a temporal database or correction runtime | immutable observation/storage port, rebuild equivalence and hostile in-place-rewrite rejection | active |
| TSG-012 | Temporal cross-reference resolution from candidate through identity, CTV and NormativeState | design/implementation | future owner; TQ-05 | `[proposed]` gap | latest text or unresolved parser candidate is not citation authority | governing decision, typed resolver/non-success outcomes and historical-reference fixtures | active |
| TSG-013 | Structural parent/child membership versioning and cardinalities | design/implementation | ADR-0016 and ADR-0017 | `[proposed]` | identity documentation does not prove corpus-wide membership correctness | explicit cardinality/event contract, split/move hostile tests and multi-provider identity fixtures | active |
| TSG-014 | Self-contained temporal API contract and unified typed error taxonomy | documentation/design | temporal model plus future owning ADRs | partial `[proposed]` | paper signatures and golden shapes are not a stable public API | declared request/result/error schemas tied to owning ports and hostile-negative contracts | active |
| TSG-015 | Golden-case catalog breadth and executable promotion | evidence | temporal model TL-G01..TL-G12 | 18 paper cases; mixed ceilings | paper cases are semantic-shape oracles, not legal gold answers | each promoted case has an owner, executable positive/hostile proof, revision-bound fixture and honest non-claim | active |
| TSG-016 | Retrieval scoring and ranking honesty beyond InMemory synthetic contracts | evidence | ADR-0014, ADR-0015, PC/RQ-006 and 019 | InMemory scoring `[bounded]`; live infrastructure `[proposed]` | real cosine values do not establish Russian legal retrieval quality | representative EvidenceSpan/SourceBlock contract, real 1024d corpus, quality metrics, exact citation round-trip and human acceptance | active |

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
