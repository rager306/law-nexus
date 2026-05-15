# M017 S04 Registry Integration Plan

## Purpose

This note records the architecture-registry contract that M017 ontology architecture intake must obey before any M017 research output is mapped into `prd/architecture/architecture_items.jsonl` or `prd/architecture/architecture_edges.jsonl`.

The registry is a derived, machine-readable projection for graph analysis and architecture fitness checks. It is not the source of truth for ontology, LegalGraph, FalkorDB, parser, retrieval, Legal KnowQL, generated-Cypher, legal-answer, or LLM-authority claims.

## Source-of-truth hierarchy

Registry integration must preserve this hierarchy from `prd/architecture/README.md`:

1. Authoritative evidence lives in source documents and artifacts: PRD/research notes under `prd/`, GSD requirements/decisions/plans/summaries/validation artifacts, ADR/source code/tests/runtime smoke artifacts, and real-document proof artifacts where runtime or legal evidence is required.
2. `prd/architecture/architecture_items.jsonl` and `prd/architecture/architecture_edges.jsonl` are derived JSONL projections. If generated records disagree with anchored source evidence, fix the source anchor or extractor mapping and regenerate; do not hand-edit JSONL to make a claim appear current.
3. Graph reports, health dashboards, product-readiness blocker reports, claims ledgers, GraphML/diagrams, and future router/skill guidance are downstream non-authoritative views. They may diagnose gaps or claim-safety boundaries, but they cannot upgrade proof beyond anchored evidence.
4. External references only count when represented as explicit `external-reference` source anchors and do not override local PRD/GSD/ADR decisions.

## Allowed item record shape

`architecture.schema.json` validates one `item` record at a time. Every item must include:

- `schema_version`: exactly `legalgraph-architecture-registry/v1`
- `record_kind`: `item`
- `id`: identifier matching `^[A-Z][A-Z0-9_-]*-[A-Za-z0-9_.:-]+$`
- `type`: one of `requirement`, `decision`, `assumption`, `risk`, `proof_gate`, `component`, `interface`, `data_entity`, `quality_scenario`, `viewpoint`, `evidence`, `workflow_check`
- `title`, `summary`
- `layer`: one of `legal-evidence`, `temporal-model`, `graph-runtime`, `parser-ingestion`, `retrieval-embedding`, `generated-cypher`, `api-product`, `security-safety`, `observability-operability`, `workflow-governance`, `architecture-governance`
- `status`: one of `proposed`, `active`, `hypothesis`, `bounded-evidence`, `validated`, `deferred`, `blocked`, `rejected`, `superseded`, `out-of-scope`
- `proof_level`, `risk_level`, `source_anchors`, `owner`, `verification`, `generated_draft`, and `non_claims`

Decision items carry extra ADR-style obligations: `deciders`, `decision_drivers`, and `considered_options` are schema-required. Active decisions must not be consequence-free under verifier policy, superseded decisions must name/link successors, and high/critical active decisions need `checked_by` or `validated_by` proof-gate/workflow-check coverage.

## Allowed edge record shape

Every `edge` record must include:

- `schema_version`: exactly `legalgraph-architecture-registry/v1`
- `record_kind`: `edge`
- `id`, `from`, `to`
- `type`: one of `satisfies`, `depends_on`, `blocks`, `contradicts`, `refines`, `implements`, `validated_by`, `bounded_by`, `supersedes`, `superseded_by`, `risks`, `owned_by`, `evidenced_by`, `uses_viewpoint`, `checked_by`, `has_option`, `chosen_over`, `has_consequence`, `has_assumption`, `has_constraint`, `implicates`, `reviewed_by`, `governs_artifact`
- `status`: one of `active`, `hypothesis`, `bounded-evidence`, `validated`, `rejected`, `superseded`
- `rationale`, `source_anchors`, and `generated_draft`

Verifier policy requires every edge endpoint to resolve to a current item record. Active/hypothesis/bounded `contradicts` edges are hard failures until resolved, rejected, or superseded.

## Proof-level discipline

Use the lowest accurate proof level. Valid proof levels are:

- `none`: no usable evidence yet; normally only for generated drafts or explicit placeholders.
- `source-anchor`: PRD/GSD/ADR/source anchor supports the statement, but runtime behavior is not proven.
- `static-check`: schema, graph integrity, or another static validation supports the claim.
- `unit-test`: focused tests cover the behavior or invariant.
- `integration-test`: multiple implemented components were exercised together.
- `runtime-smoke`: a concrete runtime smoke test was executed.
- `real-document-proof`: representative legal documents or evidence units were processed successfully.
- `production-observation`: observed production behavior supports the claim.

For M017 ontology research, `source-anchor` is the default ceiling for literature-backed or PRD-backed mapping candidates. Do not use `validated`, `runtime-smoke`, `real-document-proof`, or `production-observation` for ontology, parser, retrieval, generated-Cypher, legal-answer, FalkorDB production-scale, or LLM-authority claims unless the corresponding deterministic/runtime/real-document evidence exists and is anchored.

## Source-anchor requirements

Every non-generated draft record must have at least one `source_anchors` entry. A source anchor must use a repository-relative `path` and `kind`; allowed kinds are `prd`, `gsd-requirement`, `gsd-decision`, `gsd-summary`, `source-code`, `runtime-artifact`, `test-artifact`, `external-reference`, and `manual-note`.

Source anchors must be safe and inspectable:

- No absolute paths.
- No traversal outside the repository.
- No `.gsd/exec` local-only artifacts.
- Anchored files must exist and be readable.
- Line ranges must be bounded and within the file.
- `selector` or `section` text must still appear in the anchored file.
- Do not store raw legal text or secrets; optional `quote_hash` may identify a short supporting quote.

## Generator workflow constraints

Any registry integration for M017 must go through the generator workflow rather than manual JSONL/report edits:

1. Update authoritative source evidence first: M017 research note, GSD requirement/decision/summary, ADR, source, runtime smoke, or proof artifact.
2. Update the curated extractor mapping in `scripts/extract-prd-architecture-items.py` only when the source evidence and anchor are known.
3. Regenerate derived JSONL with `uv run python scripts/extract-prd-architecture-items.py`.
4. Rebuild graph views with `uv run python scripts/build-architecture-graph.py`.
5. Run the canonical verifier with `uv run python scripts/verify-architecture-graph.py` before claiming the registry/graph/report/router guidance is current.

Default-path verifier success means only that derived artifacts satisfy current static registry, graph, source-anchor, decision-fitness, and claim-safety rules. It does not validate product readiness, runtime behavior, parser completeness, retrieval quality, legal-answer correctness, generated-Cypher safety, FalkorDB production scale, or LLM authority.

## M017 integration guardrails

M017 ontology intake can safely prepare registry mapping candidates only if each candidate identifies:

- the authoritative source file and stable source anchor;
- whether the record is an `item` or `edge`;
- the intended item/edge type and architecture layer;
- status and lowest earned proof level;
- explicit `non_claims` for all tempting overclaims; and
- the owner/verification condition for any open proof gate.

Until those fields are available, integration should be deferred as a source-mapping plan rather than emitted into the registry. This is especially important for ontology framework adoption, external standard alignment, Russian legal evidence modeling, GraphRAG/retrieval claims, and any claim that could be mistaken for runtime or legal validation.

## Candidate registry mapping records

These candidates are planning-level extractor inputs only. They identify safe source anchors and graph relationships that a later extractor change may generate. They must not be copied by hand into `architecture_items.jsonl` or `architecture_edges.jsonl`; update source mappings and regenerate instead.

### Candidate item mappings

| Candidate ID | Record kind / type | Layer | Status / proof level | Source anchor | Summary | Non-claims | Planned edge relationships | Owner / verification condition |
|---|---|---|---|---|---|---|---|---|
| `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO` | `item` / `evidence` | `architecture-governance` | `bounded-evidence` / `source-anchor` | `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`, section `6.1 Add a research evidence item`, line 423 | Evidence item for the ontology architecture intake covering Akoma Ntoso, FRBR, LKIF, BFO/GOST, legal collision, ontology GraphRAG, and pilot-scale gates as research-derived planning input. | Does not prove parser completeness, GOST/BFO source correctness, LKIF/deontic extraction correctness, FalkorDB graph-vector/runtime capability, ontology GraphRAG retrieval quality, RusLawOD corpus priority, legal-answer authority, or production readiness. | `evidenced_by` from each new gate/data item below to this evidence item; `bounded_by` from this evidence item to existing claim-safety/runtime boundaries such as `RISK-OVERCLAIM-RUNTIME` if present in the current registry. | Architecture owner; verify source anchor exists and generated record keeps `bounded-evidence` / `source-anchor` until primary/runtime proof exists. |
| `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` | `item` / `data_entity` | `temporal-model` | `hypothesis` / `source-anchor` | `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`, section `Gap A — No formal legal document identity model`, line 362 | Candidate FRBR-like identity model separating legal act/work, edition/expression, source manifestation, and file/item boundaries without replacing current parser records. | Does not prove correct FRBR implementation, real legal-document identity resolution, amendment aggregation, inactive-version filtering, or compatibility with Consultant, Garant, RusLawOD, or Akoma Ntoso sources. | `refines` existing temporal/status semantics such as `DATA-TEMPORAL-PROPERTY-BUNDLE` and `REQ-TEMPORAL-STATUS-SEMANTICS`; `bounded_by` `GATE-AKOMA-FRBR-NORMALIZATION`; `evidenced_by` `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`. | Architecture + parser owners; verify with source-backed identity examples before upgrading beyond hypothesis. |
| `DATA-LKIF-DEONTIC-MAPPING` | `item` / `data_entity` | `legal-evidence` | `hypothesis` / `source-anchor` | `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`, section `Gap B — No explicit ontology/domain layer`, line 372, and section `Gap D — No deontic extraction proof gate`, line 392 | Candidate semantic model for obligation, permission, prohibition, negation, and LKIF-inspired deontic classes. | Does not prove extraction precision/recall, negation handling, modal-verb interpretation, legal validity, or that ML/NER outputs are authoritative assertions. | `bounded_by` `GATE-DEONTIC-MAPPING-PROOF`; `depends_on` source provenance/evidence-span concepts such as `DATA-LEGAL-EVIDENCE-CORE`; `evidenced_by` `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`. | Architecture + legal-evidence owners; verify against source spans and benchmark cases before activation. |
| `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY` | `item` / `data_entity` | `legal-evidence` | `hypothesis` / `source-anchor` | `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`, section `Gap B — No explicit ontology/domain layer`, line 372 | Working-name candidate for a Russian legal domain ontology layer covering legal-force hierarchy, competence, interpretation, and source-backed legal concepts. | Does not define final ontology scope, prove Russian-law completeness, validate judicial interpretation handling, or replace project-local LegalGraph core contracts. | `bounded_by` `GATE-RUSLEGALCORE-SCOPE`; `depends_on` `DATA-LEGAL-SOURCE-HIERARCHY` if generated; `evidenced_by` `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`. | Architecture + legal domain owners; verify scope boundaries and source classes before active status. |
| `DATA-LEGAL-SOURCE-HIERARCHY` | `item` / `data_entity` | `legal-evidence` | `hypothesis` / `source-anchor` | `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`, section `Gap C — Legal collision policy is too narrow`, line 382 | Candidate hierarchy model for legal force, federal competence, supersession, and lex maxim inputs used by collision-policy gates. | Does not decide legal priority, prove collision resolution correctness, or authorize automated legal conclusions. | `supports` should not be used because it is not a valid edge type; use `depends_on` from `GATE-LEGAL-COLLISION-POLICY`, `refines` existing temporal conflict gate `GATE-G005`, and `evidenced_by` `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`. | Architecture + legal domain owners; verify with explicit hierarchy source anchors and examples. |
| `GATE-AKOMA-FRBR-NORMALIZATION` | `item` / `proof_gate` | `parser-ingestion` | `proposed` / `source-anchor` | `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`, section `6.2 Add proof gates rather than immediate implementation claims`, line 446, and section `6.3 Separate source format from canonical legal unit model`, line 458 | Proof gate for source-specific parser records to canonical LegalUnit/ActEdition/EvidenceSpan and optional Akoma Ntoso/FRBR projection. | Does not make Akoma Ntoso canonical, prove export compatibility, or require replacing current parser record contracts. | `bounded_by` or `validated_by` target for `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR`; `refines` parser record evidence such as `EVID-PARSER-RECORD-CONTRACT`; `evidenced_by` `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`. | Parser + architecture owners; verify with generated fixtures/real-document proof before validation. |
| `GATE-DEONTIC-MAPPING-PROOF` | `item` / `proof_gate` | `legal-evidence` | `proposed` / `source-anchor` | `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`, section `Gap D — No deontic extraction proof gate`, line 392 | Proof gate requiring source-span provenance and evaluation for obligation, permission, prohibition, negation, and ambiguous modality. | Does not prove semantic extraction, legal correctness, benchmark quality, or ML model fitness. | `validated_by` future tests/evidence; `bounded_by` for `DATA-LKIF-DEONTIC-MAPPING`; `evidenced_by` `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`. | Legal-evidence + extraction owners; verify with benchmark metrics and negative cases. |
| `GATE-RUSLEGALCORE-SCOPE` | `item` / `proof_gate` | `legal-evidence` | `proposed` / `source-anchor` | `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`, section `Gap B — No explicit ontology/domain layer`, line 372 | Proof gate for defining the minimum and excluded scope of any RusLegalCore/domain-ontology layer. | Does not prove ontology completeness, legal correctness, or implementation readiness. | `bounded_by` for `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY`; `evidenced_by` `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`. | Architecture + legal domain owners; verify with bounded class list, non-goals, and source anchors. |
| `GATE-BFO-GOST-ALIGNMENT` | `item` / `proof_gate` | `architecture-governance` | `proposed` / `source-anchor` | `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`, section `Gap E — No BFO/GOST proof boundary`, line 400 | Proof gate for checking whether BFO/GOST/Common Logic claims are supported by primary or reliable external source evidence before adoption. | Does not assert GOST requirements, BFO conformance, Common Logic necessity, or OWL reasoning support. | `evidenced_by` `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`; may `bounded_by` future external-reference evidence item before activation. | Architecture owner; verify external references and conformance criteria before promoting. |
| `GATE-LEGAL-COLLISION-POLICY` | `item` / `proof_gate` | `legal-evidence` | `proposed` / `source-anchor` | `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`, section `Gap C — Legal collision policy is too narrow`, line 382 | Proof gate for lex superior, lex specialis, lex posterior, supersession, and explainable norm-priority behavior beyond same-date temporal conflict. | Does not prove automated collision resolution, court interpretation correctness, or legally binding answers. | `refines` `GATE-G005`; `depends_on` `DATA-LEGAL-SOURCE-HIERARCHY`; `evidenced_by` `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`. | Architecture + legal domain owners; verify with explicit legal maxims, source hierarchy, and explainability examples. |
| `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` | `item` / `proof_gate` | `retrieval-embedding` | `proposed` / `source-anchor` | `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`, section `6.2 Add proof gates rather than immediate implementation claims`, line 446 | Proof gate for integrating ontology filters with graph/vector retrieval while preserving citation-bound, non-authoritative answer behavior. | Does not prove retrieval quality, vector/full-text/FalkorDB runtime capability, HNSW behavior, single-transaction graph+vector semantics, or legal-answer authority. | `refines` existing retrieval quality gates such as `GATE-G011` and `GATE-G008` where present; `bounded_by` `REQ-R034` and non-authoritative answer boundaries; `evidenced_by` `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`. | Retrieval + architecture owners; verify with integration tests/runtime smoke only after implemented retrieval path exists. |
| `GATE-1000-DOC-PILOT` | `item` / `proof_gate` | `observability-operability` | `proposed` / `source-anchor` | `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`, section `Gap F — No 1000-document pilot requirement`, line 409 | Future readiness gate for a 1,000-document pilot-scale parser/ontology/retrieval validation run. | Does not invalidate existing bounded proofs, prove production scale, or claim that 1,000 representative documents have been processed. | `bounded_by` future runtime/real-document evidence; `evidenced_by` `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`; may `depends_on` parser/retrieval gates once those are implemented. | Architecture + operability owners; verify with repeatable manifest, metrics, failures, and real-document proof artifacts. |

### Candidate edge mappings

Generate these only after every endpoint item exists in the registry. Use `hypothesis` or `bounded-evidence` status unless stronger evidence is present at generation time.

| Candidate edge | Type | Status | Source anchor | Rationale | Non-claims / constraints |
|---|---|---|---|---|---|
| `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO` to each proposed data/gate item above | `evidenced_by` from target item to evidence item | `bounded-evidence` | Gap analysis sections listed per candidate | The research/gap analysis is the bounded evidence source for planning candidate generation. | Evidence edge does not upgrade target proof level beyond `source-anchor`. |
| `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` to `GATE-AKOMA-FRBR-NORMALIZATION` | `bounded_by` | `hypothesis` | Lines 362, 446, 458 | FRBR-like identity should remain bounded by parser/normalization proof. | Does not assert canonical Akoma/FRBR implementation. |
| `GATE-AKOMA-FRBR-NORMALIZATION` to `EVID-PARSER-RECORD-CONTRACT` | `refines` | `hypothesis` | Lines 446, 458 | The gate refines current parser record contract evidence into a possible canonical/projection layer. | Generate only if `EVID-PARSER-RECORD-CONTRACT` remains a current endpoint. |
| `DATA-LKIF-DEONTIC-MAPPING` to `GATE-DEONTIC-MAPPING-PROOF` | `bounded_by` | `hypothesis` | Lines 372, 392 | Deontic mapping must be proof-gated before use as semantic/legal evidence. | Does not validate extraction or legal correctness. |
| `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY` to `GATE-RUSLEGALCORE-SCOPE` | `bounded_by` | `hypothesis` | Line 372 | RusLegalCore must be scoped before it can become an active domain-ontology contract. | Does not define full ontology scope. |
| `GATE-LEGAL-COLLISION-POLICY` to `DATA-LEGAL-SOURCE-HIERARCHY` | `depends_on` | `hypothesis` | Line 382 | Collision policy needs explicit hierarchy/supersession inputs. | Does not decide priority outcomes. |
| `GATE-LEGAL-COLLISION-POLICY` to `GATE-G005` | `refines` | `hypothesis` | Line 382 | Full legal collision policy broadens the existing temporal same-date/multi-edition gate. | Generate only if `GATE-G005` remains a current endpoint. |
| `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` to retrieval boundaries such as `REQ-R034`, `GATE-G011`, and `GATE-G008` | `refines` or `bounded_by` according to endpoint semantics | `hypothesis` | Line 446 | Ontology GraphRAG should inherit citation/non-authority and retrieval-proof boundaries. | Do not generate edges to missing endpoints; do not claim retrieval quality. |
| `GATE-1000-DOC-PILOT` to future parser/retrieval runtime evidence | `bounded_by` or `validated_by` | `hypothesis` until evidence exists | Line 409 | Pilot readiness must be proven by repeatable runtime/real-document evidence rather than planning text. | Do not emit until the evidence item exists. |

### Extractor integration notes

- Prefer adding these as curated mappings in `scripts/extract-prd-architecture-items.py` from the gap-analysis source anchors above, not as manual JSONL patches.
- If an existing endpoint named in planned edges is absent or superseded when the extractor is updated, either update the edge target to the current equivalent item or omit the edge rather than producing an unresolved endpoint.
- Keep all candidate statuses at `proposed`, `hypothesis`, or `bounded-evidence`; keep proof level at `source-anchor` unless tests, runtime smoke, real-document proof, or production observation are added as separate anchored evidence.
- Run `uv run python scripts/extract-prd-architecture-items.py`, `uv run python scripts/build-architecture-graph.py`, and `uv run python scripts/verify-architecture-graph.py` after implementation, but this T02 plan intentionally does not regenerate registry artifacts.

## Chosen registry integration path

**Decision:** defer registry emission to a follow-up extractor implementation milestone/task. T03 does not edit `architecture_items.jsonl`, `architecture_edges.jsonl`, or the generator scripts.

### Why not implement in this task

The current extractor is an explicit curated mapping surface. `scripts/extract-prd-architecture-items.py` does not yet include `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`, `prd/research/ontology_architecture_requirements/05-registry-integration-plan.md`, or candidate IDs such as `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`. Adding M017 records safely therefore requires a code/test/regeneration change set, not a hand edit to derived JSONL and not a planning-only one-file task.

### Follow-up implementation scope

Owner: architecture registry owner with architecture/legal-evidence/parser/retrieval owners for domain review of candidate semantics.

Resolution path:

1. Update source mappings in `scripts/extract-prd-architecture-items.py` by adding a dedicated M017 ontology mapping section or helper functions that emit the candidate item and edge records from the source anchors listed above.
2. Add the M017 source files to the extractor's required source checks when records depend on them:
   - `prd/research/ontology_architecture_requirements/05-architecture-gap-analysis-against-current-registry.md`
   - `prd/research/ontology_architecture_requirements/05-registry-integration-plan.md`
3. Generate candidate items only with `proposed`, `hypothesis`, or `bounded-evidence` status and `source-anchor` proof level unless separate runtime/test/real-document evidence is added.
4. Generate candidate edges only when both endpoints are present in the current registry. Omit or retarget edges to absent/superseded endpoints rather than producing unresolved endpoint diagnostics.
5. Regenerate derived artifacts through the normal workflow; never hand-edit `prd/architecture/architecture_items.jsonl`, `prd/architecture/architecture_edges.jsonl`, `prd/architecture/architecture_graph_report.json`, or `prd/architecture/architecture_report.md`.

Target scripts/tests for implementation:

- `scripts/extract-prd-architecture-items.py` — add curated M017 ontology item/edge mappings and source requirements.
- `scripts/build-architecture-graph.py` — no expected code change; run after regeneration to rebuild reports and catch missing endpoints.
- `scripts/verify-architecture-graph.py` — no expected code change unless verifier policy needs a new ontology-specific guardrail; default expectation is to reuse existing source-anchor, endpoint, proof-level, and overclaim checks.
- `tests/test_architecture_registry_extractor.py` or the closest existing extractor/architecture-registry test file — add assertions for M017 candidate IDs, source anchors, proof ceilings, and edge endpoint resolution if such a tracked test surface exists.
- `tests/fixtures/architecture/valid_items.jsonl` and `tests/fixtures/architecture/valid_edges.jsonl` — update only if the test suite uses these fixtures to cover the new valid record shapes.

Expected verification commands for the follow-up:

```bash
uv run python scripts/extract-prd-architecture-items.py
uv run python scripts/extract-prd-architecture-items.py --check
uv run python scripts/build-architecture-graph.py
uv run python scripts/build-architecture-graph.py --check
uv run python scripts/verify-architecture-graph.py
uv run pytest tests/test_architecture_registry_extractor.py
```

If `tests/test_architecture_registry_extractor.py` does not exist at implementation time, create or update the nearest tracked architecture-registry test module instead and record the exact replacement command in the follow-up summary.

### Deferral criteria and verification to unblock

The deferral is resolved only when the follow-up implementation produces regenerated JSONL/report artifacts through the extractor/build workflow and `uv run python scripts/verify-architecture-graph.py` exits successfully with zero unresolved endpoints, zero forbidden ontology/runtime/legal overclaims, and preserved source-anchor proof ceilings for M017 ontology candidates.
