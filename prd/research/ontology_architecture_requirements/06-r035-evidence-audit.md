---
requirement: R035
status: verifier-safe evidence audit
date: 2026-05-17
primary_source: prd/research/ontology_architecture_requirements/05-registry-integration-plan.md
current_registry:
  - prd/architecture/architecture_items.jsonl
  - prd/architecture/architecture_edges.jsonl
  - prd/architecture/claims_ledger.md
non_authoritative: true
---

# R035 Evidence Audit

## Audit Verdict

R035 remains **Active / not runtime-validated**.

S03 synchronization update: R035 owner: M019-v10cgp/S03 for the active bounded-evidence and requirement-sync work. This owner marker resolves the lifecycle ownership drift signal; it does not validate ontology runtime behavior, ontology benchmark success, Legal KnowQL product behavior, legal-answer correctness, parser completeness, or pilot-scale readiness.

M020 lifecycle update: R035 owner: M020-ujbffl/S05 for the active bounded-evidence lifecycle update after the ontology GraphRAG proof spine. M020 produced bounded fixture-backed integration evidence for only the `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` subset: ontology and temporal filters over proof-local source-backed cases, citation/evidence ID preservation, scoped no-answer behavior, fail-closed diagnostics, redaction safety, generated-query execution avoided, and overclaim guardrails. R035 remains Active; this does not validate R035 broadly, satisfy the full gate, prove product retrieval quality, legal-answer correctness, parser completeness, FalkorDB production behavior, graph-vector/HNSW behavior, formal ontology conformance, or pilot-scale readiness.

M017 and M018 provide bounded planning, proof-gate, verifier-policy, and claims-ledger evidence for ontology architecture proof boundaries. M019-v10cgp/S03 converted the planned M017 ontology candidate layer into current generated architecture registry source mappings and views using conservative statuses, source anchors, proof ceilings, and canonical verifier-policy gate IDs where planning aliases were reconciled.

Current derived-state evidence now shows:

- `prd/research/ontology_architecture_requirements/05-registry-integration-plan.md` defines the source mapping surface: 12 candidate item mappings and 9 candidate edge mapping classes.
- `scripts/extract-prd-architecture-items.py` emits the R035 ontology candidate records from curated source mappings, not by hand-editing JSONL.
- `prd/architecture/architecture_items.jsonl` contains the canonicalized M017 ontology candidate items and gates, including `GATE-AKOMA-FRBR-NORMALIZATION`.
- Planning aliases are reconciled conservatively: `GATE-DEONTIC-MAPPING-PROOF` is represented by canonical verifier-policy gate `GATE-LKIF-DEONTIC-BENCHMARK`, and `GATE-1000-DOC-PILOT` is represented by `GATE-PILOT-SCALE-READINESS`.
- `prd/architecture/claims_ledger.md` contains an `R035 Gate Status` view that enumerates the planned ontology candidate set using canonical IDs where aliases are explicitly reconciled.
- `scripts/check-gsd-sync-drift.py --strict-exit-code` reports `status=OK diagnostics=8 failed=0` for the R035 active/unmapped contradiction class.

Completion of M017/M018 and S03 registry synchronization is still **not** validation evidence for R035. M020's ontology GraphRAG proof spine adds bounded fixture-backed integration evidence for a narrow subset of `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`, but it is still **not** broad validation evidence for R035 and does not satisfy the full gate. R035 is still Active and remains Active until later proof owners produce runtime, benchmark, real-document, legal-answer, parser-completeness, ontology-quality, graph-vector, formal-conformance, or pilot-scale evidence as applicable.

## Requirement Clause Matrix

| R035 clause / implied obligation | Current evidence | What it proves | What remains unproven | Honest status |
|---|---|---|---|---|
| Convert ontology architecture requirements into registry source mappings | `05-registry-integration-plan.md`, `scripts/extract-prd-architecture-items.py`, `architecture_items.jsonl`, `architecture_edges.jsonl` | The planned M017 candidate layer is represented in generated registry artifacts through curated extractor mappings and canonical gate aliases. | Correctness of the ontology model, runtime behavior, legal-answer behavior, and pilot-scale readiness are not proven. | Active / registry mapping synchronized |
| Preserve proof boundaries for ontology standards and research claims | `05-ontology-proof-gates.md`, verifier policy, generated gate rows | Named gate contracts exist as current registry items or canonical verifier-policy aliases. | Gate existence is not gate satisfaction; no ontology benchmark or runtime proof is accepted. | Active / bounded planning evidence |
| Stage adoption rather than replacing the LegalGraph core | `05-ontology-adoption-ladder.md`, candidate registry statuses, claims-ledger non-claims | Adoption remains staged as candidate/bounded evidence rather than promoted product architecture. | No product adoption level above bounded candidate mapping is validated. | Active / planning taxonomy evidence |
| Prevent validated ontology claims without named proof gates | `scripts/verify-architecture-graph.py`, `check-gsd-sync-drift.py` | Verifier and drift checks reject or surface unsafe promotion and stale mapping states. | Policy and static checks do not prove runtime/legal correctness or benchmark quality. | Active / verifier-policy evidence only |
| Provide a current R035 gate-status view | `prd/architecture/claims_ledger.md`, section `R035 Gate Status` | The derived view enumerates the R035 ontology candidate set and missing proof classes. | The view is non-authoritative and cannot validate R035 by itself. | Active / drift reconciled for registry/view coverage |
| Keep derived artifacts non-authoritative | Source hierarchy in M017 docs and claims-ledger scope note | Generated JSONL/report/view artifacts remain derived diagnostics. | Nothing in derived-state evidence can upgrade R035 without separate proof evidence. | Satisfied as guardrail, not validation |

## Evidence Inventory

### Primary M017 mapping plan

`prd/research/ontology_architecture_requirements/05-registry-integration-plan.md` is the primary source for R035 mapping intent. It names these **12 candidate item mappings** as planning-level extractor inputs:

1. `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`
2. `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR`
3. `DATA-LKIF-DEONTIC-MAPPING`
4. `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY`
5. `DATA-LEGAL-SOURCE-HIERARCHY`
6. `GATE-AKOMA-FRBR-NORMALIZATION`
7. `GATE-DEONTIC-MAPPING-PROOF` (canonicalized in registry as `GATE-LKIF-DEONTIC-BENCHMARK`)
8. `GATE-RUSLEGALCORE-SCOPE`
9. `GATE-BFO-GOST-ALIGNMENT`
10. `GATE-LEGAL-COLLISION-POLICY`
11. `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`
12. `GATE-1000-DOC-PILOT` (canonicalized in registry as `GATE-PILOT-SCALE-READINESS`)

It also names these **9 candidate edge mapping classes**:

1. target ontology candidates `evidenced_by` `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`;
2. `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` `bounded_by` `GATE-AKOMA-FRBR-NORMALIZATION`;
3. `GATE-AKOMA-FRBR-NORMALIZATION` `refines` `EVID-PARSER-RECORD-CONTRACT`;
4. `DATA-LKIF-DEONTIC-MAPPING` `bounded_by` `GATE-DEONTIC-MAPPING-PROOF` / canonical `GATE-LKIF-DEONTIC-BENCHMARK`;
5. `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY` `bounded_by` `GATE-RUSLEGALCORE-SCOPE`;
6. `GATE-LEGAL-COLLISION-POLICY` `depends_on` `DATA-LEGAL-SOURCE-HIERARCHY`;
7. `GATE-LEGAL-COLLISION-POLICY` `refines` `GATE-G005`;
8. `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` `refines` or is `bounded_by` retrieval boundaries such as `REQ-R034`, `GATE-G011`, and `GATE-G008` when endpoints exist;
9. `GATE-1000-DOC-PILOT` / canonical `GATE-PILOT-SCALE-READINESS` is `bounded_by` future parser/retrieval runtime evidence only after evidence endpoints exist.

### Proof-gate and adoption-ladder sources

`prd/research/ontology_architecture_requirements/05-ontology-proof-gates.md` defines the proof-gate contract and initial unsatisfied gates. It is evidence that named gates are required and that unproven ontology claims must remain visible as gates. It is not evidence that any gate is satisfied.

`prd/research/ontology_architecture_requirements/05-ontology-adoption-ladder.md` defines the L0-L6 staging model and source-priority boundary. It supports safe wording such as "candidate layer", "compatibility projection", "reference mapping", and "deferred proof area". It does not validate parser completeness, legal correctness, ontology conformance, FalkorDB behavior, retrieval quality, or LLM authority.

`prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md` supplies the gap analysis that the integration plan uses for source anchors and rationale. It explains why the ontology layer is an additive bounded candidate layer rather than a replacement for existing LegalGraph core evidence.

### Verifier-policy evidence

`scripts/verify-architecture-graph.py` contains `ONTOLOGY_PROMOTION_RULES` for Akoma Ntoso / LegalDocML, FRBR, LKIF/deontic, RusLegalCore, BFO/GOST/OWL/Common Logic, Ontology GraphRAG, graph-vector/HNSW, and pilot-scale readiness triggers. The `validate_ontology_promotion_gates()` function checks validated ontology claims for owner/source mapping, required gate links, and minimum proof level.

This is only **verifier-policy evidence**. It shows what the verifier expects before promotion; it must not be cited as proof that those gates are satisfied. For example, the policy names `GATE-AKOMA-FRBR-NORMALIZATION`, and the current registry now contains that item, but the item remains an unsatisfied proof gate rather than validation evidence.

### Current derived-state evidence

Current local inspection of `prd/architecture/architecture_items.jsonl` shows the M017 planned ontology records are present using canonical verifier-policy aliases where required, including at least:

- `GATE-AKOMA-FRBR-NORMALIZATION`;
- `GATE-LKIF-DEONTIC-BENCHMARK` (canonical for planning alias `GATE-DEONTIC-MAPPING-PROOF`);
- `GATE-RUSLEGALCORE-SCOPE`;
- `GATE-BFO-GOST-ALIGNMENT`;
- `GATE-LEGAL-COLLISION-POLICY`;
- `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`;
- `GATE-PILOT-SCALE-READINESS` (canonical for planning alias `GATE-1000-DOC-PILOT`);
- `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`;
- `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR`;
- `DATA-LKIF-DEONTIC-MAPPING`;
- `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY`;
- `DATA-LEGAL-SOURCE-HIERARCHY`.

Current `prd/architecture/claims_ledger.md` has an `R035 Gate Status` section that lists the canonicalized ontology candidate set. This is a freshness and traceability signal only; it does not prove any gate is satisfied.

## Missing Proof Decisions

The following decisions/proofs are still missing before R035 can be validated or split safely:

1. **Runtime and benchmark proof decision:** produce or defer ontology benchmark evidence, Legal KnowQL product behavior evidence, legal-answer correctness evidence, graph-vector/runtime evidence, and pilot-scale readiness evidence.
2. **Gate satisfaction decision:** decide which current gate items have accepted proof evidence and which remain active blockers.
3. **Alias governance decision:** preserve the documented alias mapping for `GATE-DEONTIC-MAPPING-PROOF` → `GATE-LKIF-DEONTIC-BENCHMARK` and `GATE-1000-DOC-PILOT` → `GATE-PILOT-SCALE-READINESS` in future extractor/verifier updates.
4. **Requirement lifecycle decision:** after proof gates receive evidence, decide whether R035 becomes validated, remains active for further proof, or is split into smaller requirements for mapping, verifier policy, runtime quality, and legal proof.

## S02 Drift Signals

S02 detects the exact drift class that made R035 look complete in milestone state while still active/unmapped in source evidence. The original drift signals and current S03 status are:

1. **Active requirement not owned by an in-progress milestone:** resolved for current state by explicit owner `M019-v10cgp/S03`; R035 still remains Active.
2. **Registry-mapping absence:** resolved for current derived registry coverage; planned candidates are present using canonical aliases where documented.
3. **Missing named proof gate:** resolved for current registry existence of `GATE-AKOMA-FRBR-NORMALIZATION`; gate satisfaction remains unproven.
4. **Stale or empty derived views:** resolved for current claims-ledger R035 gate-status coverage.
5. **Enforced verifier rules with missing registry endpoints:** resolved for current ontology verifier-policy gate endpoints.
6. **Candidate-vs-current mismatch:** resolved for current canonical candidate set.
7. **Gate ID drift:** resolved by explicit alias evidence for the two planning/verifier naming mismatches.
8. **Unsafe lifecycle language:** remains guarded; R035 must not be called validated from registry/view synchronization alone.

## S03 Handoff

S03 implemented the deferred registry integration and synchronized R035/R036 lifecycle metadata without validating R035 by assertion. Current safe handoff to S04:

1. Treat the 58-item / 91-edge architecture registry as the current generated baseline for M019-v10cgp.
2. Keep `scripts/extract-prd-architecture-items.py`, `scripts/check-gsd-sync-drift.py`, generated architecture views, and architecture pytest expectations synchronized in the root checkout after worktree migration.
3. Preserve source anchors to the gap analysis and integration plan; do not anchor positive proof claims to generated JSONL or claims-ledger views.
4. Preserve non-claims for parser completeness, legal correctness, ontology conformance, retrieval quality, FalkorDB production behavior, graph-vector/HNSW behavior, generated-Cypher safety, pilot readiness, and LLM authority.
5. Use canonical verifier-policy gate IDs in generated registry records; keep planning aliases documented as aliases only.
6. Verify root-flow commands after migration: extractor check, graph build check, generated views check, architecture verifier, drift check, and architecture pytest suite.
7. Do not mark all of R035 validated until proof obligations beyond registry mapping are explicitly accepted.

## Non-Claims

This audit does **not** claim any of the following:

- This audit does **not** claim that R035 is validated.
- M017, M018, or S03 completion proves ontology runtime behavior.
- Any ontology gate is satisfied.
- Akoma Ntoso, LegalDocML, FRBR, LKIF, RusLegalCore, BFO, GOST R 59798-2021, OWL 2, or Common Logic is adopted as current core architecture.
- Parser completeness, legal correctness, legal-answer authority, retrieval quality, FalkorDB production behavior, graph-vector/HNSW behavior, generated-Cypher safety, or 1,000-document readiness is proven.
- Derived JSONL, graph reports, claims ledger, or verifier output are authoritative source evidence.
- Manual JSONL/view edits are an acceptable substitute for extractor integration and regeneration.
- Source anchors to the gap analysis and integration plan are valid provenance for positive runtime or legal-proof claims.
- Gate ID aliases are interchangeable outside the documented registry/verifier alias mapping.
- Regenerated derived artifacts validate R035 beyond static registry/view/verifier coverage.
