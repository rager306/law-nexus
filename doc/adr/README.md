# ADRs — law-nexus architectural decisions

## Citation hygiene (RC12-F18)

Active ADRs must not cite missing `prd/research/` paths or gitignored
`AGENTS.md` as durable authority. Archive-only prior art lives under
`prd/archive/research-era/`; living authorities are `prd/ARCHITECTURE.md`
and the ADR corpus itself.

> **Format:** MADR-lite with YAML front matter. Retired Python-specific ADRs
> (M068–M106) are archive-only local archaeology and are intentionally absent
> from active links, default indexing and conformance scans.
>
> **D098 lifecycle tags** are mandatory on every architectural/state claim:
> `[bounded]` / `[smoke]` / `[validated]` / `[proposed]` / `[deferred]`.
>
> **Supersession metadata:** active ADR frontmatter uses canonical `supersedes`
> and `superseded_by` keys. The legacy misspelling `superseds` may be read only
> for historical-input compatibility and is rejected on active ADRs by Governor.

## Current ADRs

### Direction & foundation

- **ADR-0004** — Rust-only product ownership with bounded crate/port/CLI contracts; production storage/retrieval and complete KnowQL remain outside current proof `[bounded]`
- **ADR-0005** — Rust target architecture (crate and port map; **crate map superseded by ADR-0011/D127**) `[bounded]`
- **ADR-0007** — Python repository control-plane harness (process orchestration only) `[validated]`
- **ADR-0008** — Promotion and publication authority ceiling (D116/D120 separate singular authorities) `[bounded]`; D116 ≠ assertion `AuthoritativeInternal` mint; pointer only (`prd/architecture/assertion-lifecycle-contract.yaml`, E.2.7)
- **ADR-0009** — Five-clock event-anchored temporal model; `legal_act_effect` enters the legal order but does not by itself establish `InForce` or case applicability (D118) `[bounded]`; civil-day ordinal is a projection, not a sixth clock (Review 4); Merkle section is not a sixth clock; pointer only (`prd/architecture/merkle-roots-contract.yaml`, E.2.6)
- **ADR-0010** — Evidence kernel gates (D119 C10/C12/C13) `[bounded]`; C10 ≠ assertion FSM; pointer only (`prd/architecture/assertion-lifecycle-contract.yaml`, E.2.7); review-26 P0-7 EvidenceAnchor/EvidenceBundle design YAML (`prd/architecture/evidence-anchor-contract.yaml`) `[proposed]`
- **ADR-0011** — KOF-DA ownership — twenty exclusive capability owners (D123) `[bounded]`
- **ADR-0012** — Consequential evidence protocol (storage/ledger/workspace candidate assessment) `[bounded]`
- **ADR-0013** — Universal multi-source parser architecture (Consultant XML + Garant ODT, bounded morphology, sentence and lexical candidates) `[bounded]`; EditionSnapshot ≠ AST; provider oracles stay isolated (Review 4); parser records ≠ CST; ingest artifact_hash ≠ section root; pointer only (`prd/architecture/merkle-roots-contract.yaml`, E.2.6); parser emits `Proposed`; pointer (`prd/architecture/assertion-lifecycle-contract.yaml`, E.2.7); review-26 P0-7 evidence-anchor design YAML (`prd/architecture/evidence-anchor-contract.yaml`) `[proposed]` — `ln-decode::EvidenceAnchor` stays the decoder homonym, `EvidenceSpan` its crosswalk alias
- **ADR-0014** — RuVector as primary graph+vector infrastructure (RVF + redb dual storage; FalkorDB historical-only) `[proposed]`
- **ADR-0015** — Hexagonal verification architecture (overlapping contours, port contracts, lifecycle honesty) `[bounded]`

### Temporal legal ontology and applicability boundary (all `[proposed]`)

A top-down ontology of what an agent needs to reason legally over time. Each
layer depends on the one below it; all are fail-closed (R068) and follow the
D046 adoption ladder (project-local evidence kernel is canon; Akoma/FRBR/ELI/
LKIF are compatibility references, not canon replacements).

- **ADR-0016 (L1/O1)** — FRBR structural legal identity (Work/Expression/Manifestation/Item; date+authority identity) `[proposed]`; Work/Expression S2 (KBO-R011); Work stays stable across amendments (Review 4; de Martim TV ≠ Work); G0 clarification (D216): opaque ComponentId inside a Work, path/label/eId/wId = DesignationVersion, AKN/ELI stay compatibility projections, IdentityContinuityDecision for split/join/renumber; review-26 §4 opaque WorkId; OfficialIdentityClaim natural key; CC-path living alias ComponentLocator (recursive structural locator, not identity canon); mint_work composed key known-lag `[proposed]`
- **ADR-0017 (L2/O2)** — Component Temporal Versioning (CTV) — component-level provenance & fail-closed resolver (R070); TextChange≠NormativeEffect design taxonomy (RC11-F07) `[proposed]`; structural CTV ops spine (RC11-F08); structural apply S3 (TSG-003); membership fold S3 (TSG-013); three L2 canons + AmendmentEvent/EditionOracle design (Review 4); G0(g) operation registry as design-only YAML (`prd/architecture/operation-registry.yaml`, E.2.1) `[proposed]`; E.2.3 pending-effects contract YAML (`prd/architecture/pending-effects-contract.yaml`) `[proposed]`; OP-F names stay in the registry, interval algebra is ADR-0018 YAML (`prd/architecture/force-interval-set-contract.yaml`) `[proposed]`; E.2.5 scope-aware completeness contract YAML (`prd/architecture/scope-aware-completeness-contract.yaml`) `[proposed]`; review-26 P0-8 CoverageCertificate (closure dimensions + CompleteFor/IncompleteBecause); INV-22 root hash without coverage proof is not a completeness claim `[proposed]`; E.2.6 merkle-roots contract YAML (`prd/architecture/merkle-roots-contract.yaml`) `[proposed]`; E.2.7 assertion-lifecycle contract YAML (`prd/architecture/assertion-lifecycle-contract.yaml`) `[proposed]`; review-26 P0-3 living adjudicative decomposition (ValidationReceipt / AssertionDispositionEvent / AssertionRelation); AcceptedForProjection = living alias AuthoritativeInternal; D216 five-set retained as projection-status surface `[proposed]`; review-26 P0-1 living name `LegislativeEffect` (historical G0(b) `LegalEffect` wording retained) `[proposed]`; review-26 P0-2 living checkout `disposition_as_of` / `causal_close` / `projection_protocol_version` + INV-11 `[proposed]`; review-26 P0-6 INV-09a ArtifactPreservation / INV-09b SourceTextRoundTrip / INV-09c ProjectionAgreement `[proposed]`; review-26 P0-4 ActivationTrigger 6-set ForRelationsAfter extracted to TransitionPredicate RelationsArisingOnOrAfter; OnCondition is a guard, TriggerUnknown not false `[proposed]`; review-26 §3 MC-SEPARATION living names StructuralMembership / EditorialPresence (historical OperativeMembership / DocumentaryPresence retained; merkle excluded-root key stays DocumentaryPresence) `[proposed]`
- **ADR-0018 (L3/O3)** — NormativeState(t) — normative status resolver (text ≠ status) `[proposed]`; dimensional separation design (RC11-F09); force resolver S2–S3 (TSG-004); vacatio prospective-versions pointer `prd/architecture/pending-effects-contract.yaml` (E.2.3; not a force interval set); E.2.4 force interval-set contract YAML (`prd/architecture/force-interval-set-contract.yaml`) `[proposed]`; review-26 P0-5a Superseded is VersionRelation (Replaces / Supersedes / Corrects); written force statuses 6-set `[proposed]`; force Unknown ≠ completeness Unknown — pointer only (`prd/architecture/scope-aware-completeness-contract.yaml`, E.2.5)
- **ADR-0019 (L4/O4)** — Normative hierarchy and conflict resolution (lex superior/specialis/posterior; explainable) `[proposed]`; cross-act edges between ASTs (Review 4); design-only ReferenceMention/Binding/Semantics contract data (E.2.2) in `prd/architecture/reference-binding-contract.yaml` `[proposed]`; maxim Conflict ≠ coverage Conflict — pointer only (`prd/architecture/scope-aware-completeness-contract.yaml`, E.2.5)
- **ADR-0020 (L5/O5)** — Judicial, FAS and control-organ practice overlay (EffectiveInterpretation; non-authoritative) `[proposed]`
- **ADR-0021 (L6/O6)** — Transitional provisions and risk assessment (derived, non-authoritative) `[proposed]`; pending-bookkeeping is not TransitionConstraint — pointer only (`prd/architecture/pending-effects-contract.yaml`); Transitional is not an interval status — pointer only (`prd/architecture/force-interval-set-contract.yaml`); review-26 §3 TransitionConstraint is a data plane with own anchors, not an independent temporal axis; AXIS-6 remains a historical alias `[proposed]`
- **ADR-0022 (L7/O7)** — Industry profiles architecture (budget/construction/medicine/general-control; adapter-isolated) `[proposed]`
- **ADR-0023** — Applicability protocol ownership: neutral core decision/abstention/trace with versioned profile inputs; runtime absent `[proposed]`; capability inventory (RC12-F05)

### Repository governance contours

- **ADR-0024** — Review Case intake and disposition: immutable review evidence, non-authoritative AST, human promotion gate, revision-bound closure, and hexagonal harness boundary `[proposed]`; three-lifecycle continuity (L_review/L_delivery/L_capability); GSD dual-truth bridge policy

## Retired Python-era records

ADR-0001, ADR-0002 and ADR-0003 governed the retired Python product. ADR-0006
was a rejected PyO3 coexistence draft. Their local vault is gitignored,
untracked and excluded from active conformance/indexing. Historical IDs may be
named on living surfaces only with an explicit retired/archive qualifier.

<!-- fold_expression_presence KBO-R023 companion -->

<!-- map_hierarchy_marker KBO-R024 companion -->
| [ADR-0025](0025-consultant-parser-crate.md) | Consultant parser — separate crate for provider-specific extraction | Accepted | [bounded] |
| [ADR-0026](0026-ruvector-agent-memory.md) | RuVector as agent memory layer for the meta-parser | Accepted | [proposed] |
| [ADR-0027](0027-multi-layer-classifier.md) | Multi-layer manifest classifier for document-specific link classification | Accepted | [bounded] |
