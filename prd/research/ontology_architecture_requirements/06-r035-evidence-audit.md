---
requirement: R035
status: verifier-safe evidence audit
date: 2026-05-17
primary_source: prd/research/ontology_architecture_requirements/05-registry-integration-plan.md
current_registry:
  - prd/architecture/architecture_items.jsonl
  - prd/architecture/claims_ledger.md
non_authoritative: true
---

# R035 Evidence Audit

## Audit Verdict

R035 remains **Active / not validated**.

S03 synchronization update: R035 owner: M019-v10cgp/S03 for the active bounded-evidence and requirement-sync work. This owner marker only resolves the lifecycle ownership drift signal; it does not validate ontology runtime behavior or any product/legal-answer claim.

M017 and M018 provide bounded planning, proof-gate, verifier-policy, and claims-ledger evidence for ontology architecture proof boundaries, but they do **not** prove that R035 has been converted into current architecture registry source mappings. The honest current state is:

- `prd/research/ontology_architecture_requirements/05-registry-integration-plan.md` defines the planned registry integration surface: 12 candidate item mappings and 9 candidate edge mappings.
- `prd/research/ontology_architecture_requirements/05-ontology-proof-gates.md` defines named ontology proof gates and states that the gates are initially unsatisfied.
- `prd/research/ontology_architecture_requirements/05-ontology-adoption-ladder.md` defines adoption levels and anti-overclaim language, not validated product architecture.
- `scripts/verify-architecture-graph.py` contains verifier policy for ontology promotion rules that expect named gates before validated ontology claims are accepted.
- `prd/architecture/architecture_items.jsonl` currently lacks the M017 ontology candidate items and gates, including `GATE-AKOMA-FRBR-NORMALIZATION`.
- `prd/architecture/claims_ledger.md` currently exposes an incomplete R035 gate-status view: it shows only the existing GraphRAG research trigger row and reports the missing `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`; it does not list the planned M017 ontology candidate set.

Therefore R035 must stay Active until extractor integration regenerates the derived registry and verifier/views prove the ontology candidates are present with safe statuses, source anchors, proof ceilings, and required gate relationships. Completion of M017/M018 is evidence that the boundary was researched and guardrails were designed; it is **not** evidence that R035 can be marked validated.

## Requirement Clause Matrix

| R035 clause / implied obligation | Current evidence | What it proves | What remains unproven | Honest status |
|---|---|---|---|---|
| Convert ontology architecture requirements into registry source mappings | `05-registry-integration-plan.md`, section "Candidate registry mapping records" and "Chosen registry integration path" | The candidate mapping plan exists and names intended records, anchors, statuses, proof levels, and follow-up workflow. | The extractor has not emitted these records into `architecture_items.jsonl` / `architecture_edges.jsonl`; derived views are not regenerated from those mappings. | Active / implementation missing |
| Preserve proof boundaries for ontology standards and research claims | `05-ontology-proof-gates.md`, sections 1, 3, 6, 7 | Named gate contracts exist and explicitly say unsatisfied gates are not proof. | The current registry does not contain these M017 gate items as derived records. | Active / bounded planning evidence |
| Stage adoption rather than replacing the LegalGraph core | `05-ontology-adoption-ladder.md`, sections 1-6 | Adoption levels L0-L6 and anti-overclaim language are documented. | No registry-backed candidate rows prove adoption status for the planned M017 candidates. | Active / planning taxonomy evidence |
| Prevent validated ontology claims without named proof gates | `scripts/verify-architecture-graph.py`, `ONTOLOGY_PROMOTION_RULES` and `validate_ontology_promotion_gates()` | The verifier has policy logic to reject validated ontology claims that lack required gate links, source mapping, owner, or minimum proof level. | Policy existence does not create the missing gate items or satisfy any gate. | Active / verifier-policy evidence only |
| Provide a current R035 gate-status view | `prd/architecture/claims_ledger.md`, section "R035 Gate Status" | The claims ledger has a derived view for ontology-like triggers and shows missing gate remediation for current GraphRAG research evidence. | The view is incomplete for M017: it does not enumerate the 12 candidate items or the 7 planned ontology gates because the registry lacks those records. | Active / drift visible |
| Keep derived artifacts non-authoritative | `05-registry-integration-plan.md`, source-of-truth hierarchy; `claims_ledger.md` scope note | The source-of-truth hierarchy is explicit: source docs and GSD/ADR/proof artifacts are authoritative; JSONL and claims ledger are derived. | Nothing in derived-state evidence can upgrade R035 without regenerated source mappings and verification. | Satisfied as guardrail, not validation |

## Evidence Inventory

### Primary M017 mapping plan

`prd/research/ontology_architecture_requirements/05-registry-integration-plan.md` is the primary source for R035 mapping intent. It names these **12 candidate item mappings** as planning-level extractor inputs:

1. `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`
2. `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR`
3. `DATA-LKIF-DEONTIC-MAPPING`
4. `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY`
5. `DATA-LEGAL-SOURCE-HIERARCHY`
6. `GATE-AKOMA-FRBR-NORMALIZATION`
7. `GATE-DEONTIC-MAPPING-PROOF`
8. `GATE-RUSLEGALCORE-SCOPE`
9. `GATE-BFO-GOST-ALIGNMENT`
10. `GATE-LEGAL-COLLISION-POLICY`
11. `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`
12. `GATE-1000-DOC-PILOT`

It also names these **9 candidate edge mapping classes**:

1. target ontology candidates `evidenced_by` `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`;
2. `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` `bounded_by` `GATE-AKOMA-FRBR-NORMALIZATION`;
3. `GATE-AKOMA-FRBR-NORMALIZATION` `refines` `EVID-PARSER-RECORD-CONTRACT`;
4. `DATA-LKIF-DEONTIC-MAPPING` `bounded_by` `GATE-DEONTIC-MAPPING-PROOF`;
5. `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY` `bounded_by` `GATE-RUSLEGALCORE-SCOPE`;
6. `GATE-LEGAL-COLLISION-POLICY` `depends_on` `DATA-LEGAL-SOURCE-HIERARCHY`;
7. `GATE-LEGAL-COLLISION-POLICY` `refines` `GATE-G005`;
8. `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` `refines` or is `bounded_by` retrieval boundaries such as `REQ-R034`, `GATE-G011`, and `GATE-G008` when endpoints exist;
9. `GATE-1000-DOC-PILOT` is `bounded_by` or `validated_by` future parser/retrieval runtime evidence only after evidence endpoints exist.

The same plan explicitly chooses deferral: registry emission must happen in a follow-up extractor implementation, not by hand-editing generated JSONL.

### Proof-gate and adoption-ladder sources

`prd/research/ontology_architecture_requirements/05-ontology-proof-gates.md` defines the proof-gate contract and initial unsatisfied gates. It is evidence that named gates are required and that unproven ontology claims must remain visible as gates. It is not evidence that any gate is satisfied.

`prd/research/ontology_architecture_requirements/05-ontology-adoption-ladder.md` defines the L0-L6 staging model and source-priority boundary. It supports safe wording such as "candidate layer", "compatibility projection", "reference mapping", and "deferred proof area". It does not validate parser completeness, legal correctness, ontology conformance, FalkorDB behavior, retrieval quality, or LLM authority.

`prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md` supplies the gap analysis that the integration plan uses for source anchors and rationale. It says the new requirements mostly extend an ontology layer missing from the registry rather than contradicting current graph evidence.

### Verifier-policy evidence

`scripts/verify-architecture-graph.py` contains `ONTOLOGY_PROMOTION_RULES` for Akoma Ntoso / LegalDocML, FRBR, LKIF/deontic, RusLegalCore, BFO/GOST/OWL/Common Logic, Ontology GraphRAG, graph-vector/HNSW, and pilot-scale readiness triggers. The `validate_ontology_promotion_gates()` function checks validated ontology claims for owner/source mapping, required gate links, and minimum proof level.

This is only **verifier-policy evidence**. It shows what the verifier expects before promotion; it must not be cited as proof that those gates exist in the registry. For example, the policy names `GATE-AKOMA-FRBR-NORMALIZATION`, but the current `architecture_items.jsonl` does not contain that item.

### Current derived-state evidence

Current local inspection of `prd/architecture/architecture_items.jsonl` shows the M017 planned ontology records are absent, including at least:

- `GATE-AKOMA-FRBR-NORMALIZATION`;
- `GATE-DEONTIC-MAPPING-PROOF`;
- `GATE-RUSLEGALCORE-SCOPE`;
- `GATE-BFO-GOST-ALIGNMENT`;
- `GATE-LEGAL-COLLISION-POLICY`;
- `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`;
- `GATE-1000-DOC-PILOT`;
- `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`;
- `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR`;
- `DATA-LKIF-DEONTIC-MAPPING`;
- `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY`;
- `DATA-LEGAL-SOURCE-HIERARCHY`.

Current `prd/architecture/claims_ledger.md` has an `R035 Gate Status` section, but it is incomplete for R035 validation: it contains the existing `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS` trigger row and reports a missing `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION`, while the planned M017 gate and data items are not represented.

## Missing Proof Decisions

The following decisions/proofs are still missing before R035 can be validated or split safely:

1. **Extractor integration decision:** add the M017 ontology candidates to `scripts/extract-prd-architecture-items.py` as curated source mappings, or explicitly defer/split R035 so the current requirement no longer claims conversion into registry mappings.
2. **Endpoint resolution decision:** for each planned edge, decide whether the named endpoint exists in the current registry, should be retargeted to a successor, or should be omitted until the endpoint exists.
3. **Gate ID reconciliation decision:** reconcile naming mismatches between planning docs and verifier policy before emission. Notable examples include `GATE-DEONTIC-MAPPING-PROOF` vs verifier policy `GATE-LKIF-DEONTIC-BENCHMARK`, and `GATE-1000-DOC-PILOT` vs verifier policy `GATE-PILOT-SCALE-READINESS`.
4. **Status/proof-level decision:** keep emitted M017 records at `proposed`, `hypothesis`, or `bounded-evidence` with `source-anchor` proof unless separate tests, runtime smoke, real-document proof, or production observation exists.
5. **View freshness decision:** regenerate derived JSONL, graph report, and claims ledger only through the approved extractor/build/view workflow; do not manually patch generated files.
6. **Requirement lifecycle decision:** after registry regeneration and verification, decide whether R035 becomes validated, remains active for further proof, or is split into smaller requirements for mapping, verifier policy, and runtime/legal proof.

## S02 Drift Signals

S02 should detect the exact drift class that made R035 look complete in milestone state while still active/unmapped in source evidence. Required drift signals:

1. **Active requirement not owned by an in-progress milestone:** R035 is still Active even though M017/M018 are complete or summarized as complete, so drift tooling must flag an active requirement not owned by an in-progress milestone.
2. **Registry-mapping absence:** a requirement that says ontology requirements must be converted into registry mappings has no corresponding current registry items for the planned candidate IDs.
3. **Missing named proof gate:** at least `GATE-AKOMA-FRBR-NORMALIZATION` is required by source/verifier policy but absent from `architecture_items.jsonl`.
4. **Stale or empty derived views:** `claims_ledger.md` contains `## R035 Gate Status` but does not enumerate the planned M017 ontology candidate gates/data items, so S02 should treat the R035 view as stale or empty for the M017 candidate set.
5. **Enforced verifier rules with missing registry endpoints:** `scripts/verify-architecture-graph.py` mentions a gate ID in `ONTOLOGY_PROMOTION_RULES`, but that mention is not a registry item and must not count as proof when the required registry endpoints are missing.
6. **Candidate-vs-current mismatch:** `05-registry-integration-plan.md` lists 12 candidate items and 9 edge mappings, while derived JSONL lacks those candidates.
7. **Gate ID drift:** verifier policy and planning docs disagree on one or more gate IDs, such as `GATE-DEONTIC-MAPPING-PROOF` / `GATE-LKIF-DEONTIC-BENCHMARK` or `GATE-1000-DOC-PILOT` / `GATE-PILOT-SCALE-READINESS`.
8. **Unsafe lifecycle language:** S02 must flag any document, requirement update, or view that would say R035 is validated merely because M017/M018 completed, because safe lifecycle wording must not validate R035 without proving regenerated registry presence and verifier/view coverage.

## S03 Handoff

S03 should implement the deferred registry integration, not validate R035 by assertion. Minimum safe path:

1. Update `scripts/extract-prd-architecture-items.py` with curated mappings for the 12 candidate items from `05-registry-integration-plan.md`.
2. Add candidate edges only when both endpoints exist; omit or retarget missing/superseded endpoints rather than producing unresolved endpoint diagnostics.
3. Preserve source anchors to the gap analysis and integration plan; do not anchor positive proof claims to generated JSONL or claims-ledger views.
4. Preserve non-claims for parser completeness, legal correctness, ontology conformance, retrieval quality, FalkorDB production behavior, graph-vector/HNSW behavior, generated-Cypher safety, pilot readiness, and LLM authority.
5. Reconcile gate ID names before emission or document aliases explicitly in source evidence and tests.
6. Regenerate derived artifacts through the normal workflow: extractor, architecture graph build, verifier, and claims-ledger/view generation.
7. Verify that `GATE-AKOMA-FRBR-NORMALIZATION` and the other planned candidates appear in derived registry outputs with safe statuses and proof levels.
8. Only after those checks pass, use GSD requirement tooling to update R035 lifecycle status. If any proof obligation remains outside registry mapping, split or defer that obligation and do not mark all of R035 validated.

## Non-Claims

This audit does **not** claim any of the following:

- This audit does **not** claim that R035 is validated.
- M017 or M018 completion proves registry integration.
- `GATE-AKOMA-FRBR-NORMALIZATION` or any other M017 ontology gate exists in the current registry.
- Any ontology gate is satisfied.
- Akoma Ntoso, LegalDocML, FRBR, LKIF, RusLegalCore, BFO, GOST R 59798-2021, OWL 2, or Common Logic is adopted as current core architecture.
- Parser completeness, legal correctness, legal-answer authority, retrieval quality, FalkorDB production behavior, graph-vector/HNSW behavior, generated-Cypher safety, or 1,000-document readiness is proven.
- Derived JSONL, graph reports, claims ledger, or verifier output are authoritative source evidence.
- Manual JSONL/view edits are an acceptable substitute for extractor integration and regeneration.
- Extractor mappings for the 12 candidate items from `05-registry-integration-plan.md` are complete and correct in the current extractor state.
- Source anchors to the gap analysis and integration plan are valid provenance for positive proof claims.
- Gate ID aliases (e.g. `GATE-DEONTIC-MAPPING-PROOF` / `GATE-LKIF-DEONTIC-BENCHMARK`) are reconciled and documented in the registry emission state.
- Regenerated derived artifacts (JSONL, graph reports, claims ledger, verifier output) reflect the post-extractor-integration state and are not stale.
