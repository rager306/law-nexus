# Architecture Graph Report

This report is derived, non-authoritative, and generated from the S02 architecture JSONL registry.
These graph/report outputs do not validate product/runtime/legal claims; PRD, GSD, ADR, source, and runtime evidence remain the source of truth.
Current orphans, unresolved proof gates, contradictions, and risk rows are findings for S04 or later verifier work, not automatic S03 build failures.

## Summary

| Field | Value |
| --- | --- |
| Nodes | 58 |
| Edges | 91 |
| Non-authoritative | true |
| Missing layers | 0 |
| Unresolved proof gates | 7 |
| Orphan findings | 0 |
| Contradiction edges | 0 |
| High/critical-risk nodes | 42 |

## Layer Coverage

| Layer | Node Count |
| --- | ---: |
| api-product | 1 |
| architecture-governance | 9 |
| generated-cypher | 2 |
| graph-runtime | 2 |
| legal-evidence | 7 |
| observability-operability | 2 |
| parser-ingestion | 11 |
| retrieval-embedding | 12 |
| security-safety | 5 |
| temporal-model | 4 |
| workflow-governance | 3 |

### Missing Layers

No missing schema layers.

## Findings for S04

### Unresolved Proof Gates

| ID | Layer | Owner | Risk | Verification |
| --- | --- | --- | --- | --- |
| GATE-EMBEDDING-SUPPLY-CHAIN | security-safety | future-embedding-supply-chain-proof | high | Future embedding proof records model source, checksum or revision, local runtime envelope, vector dimension, and no-secret/no-raw-vector leakage checks. |
| GATE-G005 | temporal-model | future-temporal-proof | high | A future proof slice defines and verifies same-date/multi-edition conflict policy. |
| GATE-G008 | parser-ingestion | future-product-parser-retrieval-proof | high | Future product proof demonstrates parser completeness boundaries, citation-safe retrieval behavior, and retrieval quality over real legal source fixtures. |
| GATE-G011 | retrieval-embedding | future-retrieval-quality-proof | high | Retrieval quality benchmark passes under local/open-weight embedding constraints. |
| GATE-G015 | graph-runtime | future-runtime-migration-proof | medium | Migration runbook is executed against bounded fixtures and runtime diagnostics. |
| GATE-GENERATED-CYPHER-SAFETY | generated-cypher | future-generated-cypher-safety-proof | critical | A future product proof demonstrates validator acceptance/rejection behavior across representative Legal KnowQL tasks and live graph schemas. |
| GATE-LEGAL-NEXUS-ACCESS-CONTROL | security-safety | future-api-security-proof | high | Future security proof defines caller boundaries, authorization policy, audit logging, and denial diagnostics for Legal Nexus operations. |

### Orphan Findings

| ID | Rule |
| --- | --- |
| _None_ |  |

### Contradictions

| Edge ID | From | To | Status | Rationale |
| --- | --- | --- | --- | --- |
| _None_ |  |  |  |  |

### Traceability Edges

These edge summaries expose bounded proof, requirement, gate, and data-boundary relationships without asserting product readiness.

| Edge ID | From | Type | To | Status | Rationale |
| --- | --- | --- | --- | --- | --- |
| EDGE-COMP-LEGAL-NEXUS-DEPENDS-ON-DATA-LEGAL-EVIDENCE-CORE | COMP-LEGAL-NEXUS-ORCHESTRATOR | depends_on | DATA-LEGAL-EVIDENCE-CORE | active | Legal Nexus orchestration depends on source-backed legal-evidence entities before answer or query behavior can be validated. |
| EDGE-DATA-LEGAL-DOCUMENT-IDENTITY-FRBR-BOUNDED-BY-GATE-AKOMA-FRBR-NORMALIZATION | DATA-LEGAL-DOCUMENT-IDENTITY-FRBR | bounded_by | GATE-AKOMA-FRBR-NORMALIZATION | hypothesis | FRBR-like identity remains bounded by parser/normalization proof before canonical legal-unit projection claims. |
| EDGE-DATA-LEGAL-DOCUMENT-IDENTITY-FRBR-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | DATA-LEGAL-DOCUMENT-IDENTITY-FRBR | evidenced_by | EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | bounded-evidence | The M017 ontology research and gap-analysis plan is bounded source-anchor evidence for this conservative ontology candidate; it does not upgrade proof beyond source-anchor. |
| EDGE-DATA-LEGAL-DOCUMENT-IDENTITY-FRBR-REFINES-DATA-TEMPORAL-PROPERTY-BUNDLE | DATA-LEGAL-DOCUMENT-IDENTITY-FRBR | refines | DATA-TEMPORAL-PROPERTY-BUNDLE | hypothesis | The FRBR-like candidate refines existing temporal property bundle concepts without replacing current parser records. |
| EDGE-DATA-LEGAL-DOCUMENT-IDENTITY-FRBR-REFINES-REQ-TEMPORAL-STATUS-SEMANTICS | DATA-LEGAL-DOCUMENT-IDENTITY-FRBR | refines | REQ-TEMPORAL-STATUS-SEMANTICS | hypothesis | The identity candidate refines existing temporal status semantics and remains source-anchor-only until examples and proof exist. |
| EDGE-DATA-LEGAL-EVIDENCE-EVIDENCED-BY-PARSER-RECORD-CONTRACT | DATA-LEGAL-EVIDENCE-CORE | evidenced_by | EVID-PARSER-RECORD-CONTRACT | active | Parser record contracts provide bounded evidence for SourceDocument/SourceBlock-related legal-evidence record shapes. |
| EDGE-DATA-LEGAL-SOURCE-HIERARCHY-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | DATA-LEGAL-SOURCE-HIERARCHY | evidenced_by | EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | bounded-evidence | The M017 ontology research and gap-analysis plan is bounded source-anchor evidence for this conservative ontology candidate; it does not upgrade proof beyond source-anchor. |
| EDGE-DATA-LKIF-DEONTIC-MAPPING-BOUNDED-BY-GATE-LKIF-DEONTIC-BENCHMARK | DATA-LKIF-DEONTIC-MAPPING | bounded_by | GATE-LKIF-DEONTIC-BENCHMARK | hypothesis | LKIF/deontic mapping must remain proof-gated by the canonical verifier-policy benchmark gate before use as semantic/legal evidence. |
| EDGE-DATA-LKIF-DEONTIC-MAPPING-DEPENDS-ON-DATA-LEGAL-EVIDENCE-CORE | DATA-LKIF-DEONTIC-MAPPING | depends_on | DATA-LEGAL-EVIDENCE-CORE | hypothesis | Deontic extraction candidates depend on source-backed legal evidence and evidence-span concepts. |
| EDGE-DATA-LKIF-DEONTIC-MAPPING-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | DATA-LKIF-DEONTIC-MAPPING | evidenced_by | EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | bounded-evidence | The M017 ontology research and gap-analysis plan is bounded source-anchor evidence for this conservative ontology candidate; it does not upgrade proof beyond source-anchor. |
| EDGE-DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY-BOUNDED-BY-GATE-RUSLEGALCORE-SCOPE | DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY | bounded_by | GATE-RUSLEGALCORE-SCOPE | hypothesis | RusLegalCore must be scoped before it can become an active domain-ontology contract. |
| EDGE-DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY-DEPENDS-ON-DATA-LEGAL-SOURCE-HIERARCHY | DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY | depends_on | DATA-LEGAL-SOURCE-HIERARCHY | hypothesis | The Russian legal domain ontology candidate depends on explicit legal-force and source hierarchy concepts before collision-policy use. |
| EDGE-DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY | evidenced_by | EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | bounded-evidence | The M017 ontology research and gap-analysis plan is bounded source-anchor evidence for this conservative ontology candidate; it does not upgrade proof beyond source-anchor. |
| EDGE-DEC-D031-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR | DEC-D031 | checked_by | CHECK-ARCHITECTURE-EXTRACTOR | active | The high-risk architecture registry decision is checked by the deterministic extractor drift check in S02. |
| EDGE-DEC-D031-HAS-ASSUMPTION-ASSUMP-PRD-SOURCE-TRUTH | DEC-D031 | has_assumption | ASSUMP-PRD-SOURCE-TRUTH | active | The architecture registry decision assumes PRD/GSD/ADR/source/runtime evidence remains authoritative and generated registry artifacts remain derived projections. |
| EDGE-DEC-D031-SATISFIES-REQ-R029 | DEC-D031 | satisfies | REQ-R029 | active | The docs-as-code architecture registry decision is the chosen approach for executable architecture verification. |
| EDGE-DEC-D032-DEPENDS-ON-DEC-D031 | DEC-D032 | depends_on | DEC-D031 | active | The architecture verification skill should be created only after the registry contract and verifier workflow exist. |
| EDGE-EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF-BOUNDED-BY-GATE-G011 | EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF | bounded_by | GATE-G011 | active | The M015 proof validates deterministic seed-fixture retrieval quality metrics under local/open-weight USER-bge-m3 boundary metadata, but remains bounded by the broader local embedding quality gate. |
| EDGE-EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR | EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF | checked_by | CHECK-ARCHITECTURE-EXTRACTOR | active | The deterministic architecture extractor keeps the M015 benchmark proof anchors, status, proof level, and non-claims visible in generated registry outputs. |
| EDGE-EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF-DEPENDS-ON-EVID-OFFLINE-CITATION-RETRIEVAL-PROOF | EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF | depends_on | EVID-OFFLINE-CITATION-RETRIEVAL-PROOF | active | The M015 seed benchmark reuses M014 offline citation retrieval fixture provenance while adding fixture-level quality metrics and S10 model boundary metadata. |
| EDGE-EVID-OFFLINE-CITATION-RETRIEVAL-PROOF-BOUNDED-BY-GATE-G008 | EVID-OFFLINE-CITATION-RETRIEVAL-PROOF | bounded_by | GATE-G008 | active | The M014 proof validates deterministic offline citation-safe retrieval behavior over a bounded tracked corpus, but remains bounded by the broader product parser/retrieval readiness gate. |
| EDGE-EVID-OFFLINE-CITATION-RETRIEVAL-PROOF-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR | EVID-OFFLINE-CITATION-RETRIEVAL-PROOF | checked_by | CHECK-ARCHITECTURE-EXTRACTOR | active | The deterministic architecture extractor keeps the M014 offline citation proof anchors, status, proof level, and non-claims visible in generated registry outputs. |
| EDGE-EVID-OFFLINE-CITATION-RETRIEVAL-PROOF-DEPENDS-ON-DATA-LEGAL-EVIDENCE-CORE | EVID-OFFLINE-CITATION-RETRIEVAL-PROOF | depends_on | DATA-LEGAL-EVIDENCE-CORE | active | The offline citation proof depends on source/evidence/legal-unit/edition ID path concepts from the legal evidence core while remaining a proof-local fixture, not production graph data. |
| EDGE-EVID-PARSER-CONSULTANT-HIERARCHY-PROOF-BOUNDED-BY-GATE-G008 | EVID-PARSER-CONSULTANT-HIERARCHY-PROOF | bounded_by | GATE-G008 | active | M009 proves a bounded single-document Consultant hierarchy path but remains bounded by the product parser/retrieval readiness gate. |
| EDGE-EVID-PARSER-GOLDEN-TEST-PROOF-BOUNDED-BY-GATE-G008 | EVID-PARSER-GOLDEN-TEST-PROOF | bounded_by | GATE-G008 | active | M008 proves a bounded golden-test harness but remains bounded by the product parser/retrieval readiness gate. |
| EDGE-EVID-REAL-ARTIFACT-RETRIEVAL-PROOF-BOUNDED-BY-GATE-G008 | EVID-REAL-ARTIFACT-RETRIEVAL-PROOF | bounded_by | GATE-G008 | active | The M013 proof validates real-artifact output IDs and diagnostics but remains bounded by the product parser/retrieval readiness gate. |
| EDGE-EVID-REAL-ARTIFACT-RETRIEVAL-PROOF-BOUNDED-BY-GATE-G011 | EVID-REAL-ARTIFACT-RETRIEVAL-PROOF | bounded_by | GATE-G011 | active | The M013 proof validates fail-closed output IDs but does not measure local embedding or product retrieval quality. |
| EDGE-EVID-REAL-ARTIFACT-RETRIEVAL-PROOF-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR | EVID-REAL-ARTIFACT-RETRIEVAL-PROOF | checked_by | CHECK-ARCHITECTURE-EXTRACTOR | active | The deterministic architecture extractor keeps the M013 real-artifact proof anchors, status, proof level, and non-claims visible in generated registry outputs. |
| EDGE-EVID-REAL-ARTIFACT-RETRIEVAL-PROOF-SATISFIES-REQ-R034 | EVID-REAL-ARTIFACT-RETRIEVAL-PROOF | satisfies | REQ-R034 | active | The M013 real-artifact proof provides executable evidence that retrieval output IDs derived from tracked parser artifacts can fail closed through source, legal-unit, and edition paths without promoting product retrieval quality or legal-answer claims. |
| EDGE-EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF-BOUNDED-BY-GATE-G011 | EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF | bounded_by | GATE-G011 | active | The M016 representative runtime benchmark confirms proof-local metrics and local/open-weight runtime boundary, but remains bounded by the broader GATE-G011 product retrieval quality disposition. |
| EDGE-EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR | EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF | checked_by | CHECK-ARCHITECTURE-EXTRACTOR | validated | The deterministic architecture extractor and regression tests keep the M016 representative runtime benchmark anchors, bounded status, proof level, redaction boundary, and open GATE-G011 disposition visible in generated registry outputs. |
| EDGE-EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF-DEPENDS-ON-EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF | EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF | depends_on | EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF | active | The M016 representative runtime benchmark extends the M015 local retrieval benchmark pattern from seed fixtures to the representative manifest while preserving bounded, local/open-weight evidence scope. |
| EDGE-EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF-DEPENDS-ON-S10-USER-BGE-M3-BASELINE | EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF | depends_on | S10-USER-BGE-M3-BASELINE | active | The M016 representative runtime benchmark depends on the bounded USER-bge-m3 local/open-weight runtime baseline and repeats the no-managed-API boundary in its proof output. |
| EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-G005 | EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS | bounded_by | GATE-G005 | active | Research ideas about temporal legal graph reasoning remain bounded by the unresolved temporal same-date conflict policy gate. |
| EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-G008 | EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS | bounded_by | GATE-G008 | active | Research ideas about graph pre-filtering and GraphRAG retrieval remain bounded by product parser/retrieval readiness proof. |
| EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-G011 | EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS | bounded_by | GATE-G011 | active | Research ideas about ranking, embeddings, and hybrid retrieval remain bounded by local embedding quality proof. |
| EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-G015 | EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS | bounded_by | GATE-G015 | active | Research performance and FalkorDB runtime claims remain bounded by runtime migration/load proof. |
| EDGE-EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS-BOUNDED-BY-GATE-GENERATED-CYPHER-SAFETY | EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS | bounded_by | GATE-GENERATED-CYPHER-SAFETY | active | Research ideas about LLM agent orchestration and generated queries remain bounded by generated-Cypher product safety proof. |
| EDGE-EVID-RESEARCH-HABR-LEGAL-RAG-BOUNDED-BY-GATE-EMBEDDING-SUPPLY-CHAIN | EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING | bounded_by | GATE-EMBEDDING-SUPPLY-CHAIN | active | Habr Legal RAG local retrieval and reranker model ideas remain bounded by embedding model provenance, integrity, local runtime, and leakage checks. |
| EDGE-EVID-RESEARCH-HABR-LEGAL-RAG-BOUNDED-BY-GATE-G005 | EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING | bounded_by | GATE-G005 | active | Habr Legal RAG scale/disambiguation lessons reinforce temporal routing but remain bounded by unresolved same-date and multi-edition conflict policy. |
| EDGE-EVID-RESEARCH-HABR-LEGAL-RAG-BOUNDED-BY-GATE-G008 | EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING | bounded_by | GATE-G008 | active | Habr Legal RAG ideas about format-first validation, citation precision, and scoped no-answer behavior remain bounded by product parser/retrieval readiness proof. |
| EDGE-EVID-RESEARCH-HABR-LEGAL-RAG-BOUNDED-BY-GATE-G011 | EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING | bounded_by | GATE-G011 | active | Habr Legal RAG ideas about hybrid retrieval, evidence precision, reranking, and scale/noise evaluation remain bounded by local embedding quality proof. |
| EDGE-EVID-RESEARCH-HABR-LEGAL-RAG-BOUNDED-BY-GATE-G015 | EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING | bounded_by | GATE-G015 | active | Habr Legal RAG scale/noise degradation lessons remain bounded by future FalkorDBLite-to-Docker runtime migration and load proof. |
| EDGE-EVID-RESEARCH-HABR-LEGAL-RAG-BOUNDED-BY-GATE-GENERATED-CYPHER-SAFETY | EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING | bounded_by | GATE-GENERATED-CYPHER-SAFETY | active | Habr Legal RAG post-LLM verification lessons support generated-output caution but remain bounded by generated-Cypher safety proof. |
| EDGE-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO-BOUNDED-BY-RISK-OVERCLAIM-RUNTIME | EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | bounded_by | RISK-OVERCLAIM-RUNTIME | bounded-evidence | Ontology intake evidence remains bounded by the project-wide runtime/legal overclaim risk until specific gates earn stronger proof. |
| EDGE-EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF-BOUNDED-BY-GATE-G008 | EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF | bounded_by | GATE-G008 | active | The validator proof checks output IDs and diagnostics but remains bounded by the product parser/retrieval readiness gate. |
| EDGE-EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF-BOUNDED-BY-GATE-G011 | EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF | bounded_by | GATE-G011 | active | The validator proof can reject unresolved IDs but does not measure local embedding or product retrieval quality. |
| EDGE-EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR | EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF | checked_by | CHECK-ARCHITECTURE-EXTRACTOR | active | The deterministic architecture extractor keeps the M012 validator proof anchors, status, proof level, and non-claims visible in generated registry outputs. |
| EDGE-EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF-DEPENDS-ON-DATA-LEGAL-EVIDENCE-CORE | EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF | depends_on | DATA-LEGAL-EVIDENCE-CORE | active | The validator proof resolves citation and evidence IDs through bounded SourceBlock, SourceDocument, LegalUnit, and ActEdition fixture paths derived from the legal-evidence core concept. |
| EDGE-EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF-SATISFIES-REQ-R034 | EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF | satisfies | REQ-R034 | active | The M012 validator proof provides bounded executable evidence for R034 fail-closed output identifier checks without promoting product retrieval or legal-answer claims. |
| EDGE-GATE-AKOMA-FRBR-NORMALIZATION-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | GATE-AKOMA-FRBR-NORMALIZATION | evidenced_by | EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | bounded-evidence | The M017 ontology research and gap-analysis plan is bounded source-anchor evidence for this conservative ontology candidate; it does not upgrade proof beyond source-anchor. |
| EDGE-GATE-AKOMA-FRBR-NORMALIZATION-REFINES-EVID-PARSER-RECORD-CONTRACT | GATE-AKOMA-FRBR-NORMALIZATION | refines | EVID-PARSER-RECORD-CONTRACT | hypothesis | The normalization gate refines current parser record contract evidence into a possible canonical/projection layer only if proof is later added. |
| EDGE-GATE-BFO-GOST-ALIGNMENT-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | GATE-BFO-GOST-ALIGNMENT | evidenced_by | EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | bounded-evidence | The M017 ontology research and gap-analysis plan is bounded source-anchor evidence for this conservative ontology candidate; it does not upgrade proof beyond source-anchor. |
| EDGE-GATE-EMBEDDING-SUPPLY-CHAIN-BOUNDS-S10-USER-BGE-M3 | GATE-EMBEDDING-SUPPLY-CHAIN | bounded_by | S10-USER-BGE-M3-BASELINE | active | USER-bge-m3 remains a bounded local/open-weight baseline until model provenance and supply-chain gates are formalized for product use. |
| EDGE-GATE-G005-BLOCKS-TEMPORAL-VALIDATION | GATE-G005 | blocks | REQ-R029 | active | Unresolved temporal conflict policy must remain visible in architecture verification outputs. |
| EDGE-GATE-G005-DEPENDS-ON-DATA-TEMPORAL-PROPERTY-BUNDLE | GATE-G005 | depends_on | DATA-TEMPORAL-PROPERTY-BUNDLE | active | Same-date conflict policy depends on explicit temporal fields and status semantics being modeled before validation. |
| EDGE-GATE-G008-BLOCKS-PARSER-RETRIEVAL-PROOF | GATE-G008 | blocks | REQ-R029 | active | Product parser/retrieval readiness gaps must remain explicit even after M008 bounded golden-test harness proof. |
| EDGE-GATE-G011-BLOCKS-RETRIEVAL-QUALITY-CLAIMS | GATE-G011 | blocks | REQ-R029 | active | Local embedding evidence remains bounded and cannot validate product retrieval quality without benchmarks. |
| EDGE-GATE-G015-BLOCKS-RUNTIME-MIGRATION-CLAIMS | GATE-G015 | blocks | REQ-R029 | active | FalkorDBLite to Docker migration remains an explicit deployment proof gate. |
| EDGE-GATE-GENERATED-CYPHER-SAFETY-BLOCKS-REQ-R017 | GATE-GENERATED-CYPHER-SAFETY | blocks | REQ-R017 | active | R017 cannot be validated for product Legal KnowQL until generated-Cypher safety is proven beyond M003 route/proof-harness evidence. |
| EDGE-GATE-LEGAL-COLLISION-POLICY-DEPENDS-ON-DATA-LEGAL-SOURCE-HIERARCHY | GATE-LEGAL-COLLISION-POLICY | depends_on | DATA-LEGAL-SOURCE-HIERARCHY | hypothesis | Collision policy needs explicit hierarchy and supersession inputs before priority behavior can be tested. |
| EDGE-GATE-LEGAL-COLLISION-POLICY-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | GATE-LEGAL-COLLISION-POLICY | evidenced_by | EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | bounded-evidence | The M017 ontology research and gap-analysis plan is bounded source-anchor evidence for this conservative ontology candidate; it does not upgrade proof beyond source-anchor. |
| EDGE-GATE-LEGAL-COLLISION-POLICY-REFINES-GATE-G005 | GATE-LEGAL-COLLISION-POLICY | refines | GATE-G005 | hypothesis | Full legal collision policy broadens the existing temporal same-date/multi-edition conflict gate without closing it. |
| EDGE-GATE-LEGAL-NEXUS-ACCESS-CONTROL-BLOCKS-COMP-LEGAL-NEXUS | GATE-LEGAL-NEXUS-ACCESS-CONTROL | blocks | COMP-LEGAL-NEXUS-ORCHESTRATOR | active | Legal Nexus component claims remain bounded until access-control behavior is specified and verified. |
| EDGE-GATE-LKIF-DEONTIC-BENCHMARK-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | GATE-LKIF-DEONTIC-BENCHMARK | evidenced_by | EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | bounded-evidence | The M017 ontology research and gap-analysis plan is bounded source-anchor evidence for this conservative ontology candidate; it does not upgrade proof beyond source-anchor. |
| EDGE-GATE-ONTOLOGY-GRAPHRAG-INTEGRATION-BOUNDED-BY-REQ-R034 | GATE-ONTOLOGY-GRAPHRAG-INTEGRATION | bounded_by | REQ-R034 | hypothesis | Ontology GraphRAG integration inherits citation/evidence identifier fail-closed boundaries from R034. |
| EDGE-GATE-ONTOLOGY-GRAPHRAG-INTEGRATION-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | GATE-ONTOLOGY-GRAPHRAG-INTEGRATION | evidenced_by | EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | bounded-evidence | The M017 ontology research and gap-analysis plan is bounded source-anchor evidence for this conservative ontology candidate; it does not upgrade proof beyond source-anchor. |
| EDGE-GATE-ONTOLOGY-GRAPHRAG-INTEGRATION-REFINES-GATE-G008 | GATE-ONTOLOGY-GRAPHRAG-INTEGRATION | refines | GATE-G008 | hypothesis | Ontology GraphRAG retrieval ideas refine product parser/retrieval readiness proof needs without closing parser completeness gates. |
| EDGE-GATE-ONTOLOGY-GRAPHRAG-INTEGRATION-REFINES-GATE-G011 | GATE-ONTOLOGY-GRAPHRAG-INTEGRATION | refines | GATE-G011 | hypothesis | Ontology GraphRAG retrieval ideas refine local retrieval quality proof needs without claiming retrieval quality. |
| EDGE-GATE-PILOT-SCALE-READINESS-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | GATE-PILOT-SCALE-READINESS | evidenced_by | EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | bounded-evidence | The M017 ontology research and gap-analysis plan is bounded source-anchor evidence for this conservative ontology candidate; it does not upgrade proof beyond source-anchor. |
| EDGE-GATE-RUSLEGALCORE-SCOPE-EVIDENCED-BY-EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | GATE-RUSLEGALCORE-SCOPE | evidenced_by | EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | bounded-evidence | The M017 ontology research and gap-analysis plan is bounded source-anchor evidence for this conservative ontology candidate; it does not upgrade proof beyond source-anchor. |
| EDGE-M001-ARCHITECTURE-ONLY-GUARDRAIL-BOUNDS-REQ-R029 | M001-ARCHITECTURE-ONLY-GUARDRAIL | bounded_by | REQ-R029 | active | Architecture registry verification must preserve architecture-only/product non-claim guardrails. |
| EDGE-QS-OBSERVABILITY-BASELINE-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR | QS-OBSERVABILITY-OPERABILITY-BASELINE | checked_by | CHECK-ARCHITECTURE-EXTRACTOR | active | The deterministic architecture extractor/check workflow keeps observability and auditability boundary records visible in derived planning views. |
| EDGE-REQ-R001-EVIDENCED-BY-S07-FIXED-PRD-CONSISTENCY | REQ-R001 | evidenced_by | S07-FIXED-PRD-CONSISTENCY | active | S07/S08 final report evidence supports architecture finding classification within M001 scope. |
| EDGE-REQ-R009-EVIDENCED-BY-S08-FINDINGS | REQ-R009 | evidenced_by | S07-FIXED-PRD-CONSISTENCY | active | S08 findings rows preserve owner, resolution path, verification criteria, and roadmap effect for architecture issues. |
| EDGE-REQ-R010-EVIDENCED-BY-S08-FINDINGS | REQ-R010 | evidenced_by | S07-FIXED-PRD-CONSISTENCY | active | S08 produced a machine-readable findings path and schema proposal consumed by this extractor. |
| EDGE-REQ-R017-BOUNDED-BY-R028 | REQ-R017 | bounded_by | REQ-R028 | active | Generated Cypher proof work remains bounded by the non-authoritative LLM/legal authority guardrail. |
| EDGE-REQ-R022-BOUNDS-S04-FALKORDB-RUNTIME-BOUNDED | REQ-R022 | bounded_by | S04-FALKORDB-RUNTIME-BOUNDED | active | Runtime proof artifacts must remain categorical and avoid raw sensitive/provider/legal payloads. |
| EDGE-REQ-TEMPORAL-STATUS-SEMANTICS-DEPENDS-ON-DATA-TEMPORAL-PROPERTY-BUNDLE | REQ-TEMPORAL-STATUS-SEMANTICS | depends_on | DATA-TEMPORAL-PROPERTY-BUNDLE | active | Temporal status semantics depend on a stable temporal property bundle contract. |
| EDGE-RISK-OVERCLAIM-CHECKED-BY-CHECK-ARCHITECTURE-EXTRACTOR | RISK-OVERCLAIM-RUNTIME | checked_by | CHECK-ARCHITECTURE-EXTRACTOR | active | The extractor check fails closed for unsafe status/proof mappings and stale generated outputs. |
| EDGE-RISK-OVERCLAIM-RISKS-DATA-LEGAL-EVIDENCE-CORE | RISK-OVERCLAIM-RUNTIME | risks | DATA-LEGAL-EVIDENCE-CORE | active | Legal-evidence entity records can be overclaimed as implemented schema or legal correctness if non-claims are ignored. |
| EDGE-RISK-OVERCLAIM-RISKS-GATE-GENERATED-CYPHER-SAFETY | RISK-OVERCLAIM-RUNTIME | risks | GATE-GENERATED-CYPHER-SAFETY | active | Generated-Cypher proof gates are threatened by overclaiming draft LLM output as executable or legally authoritative behavior. |
| EDGE-S04-FALKORDB-RUNTIME-BOUNDED-BOUNDED-BY-RISK-OVERCLAIM-RUNTIME | S04-FALKORDB-RUNTIME-BOUNDED | bounded_by | RISK-OVERCLAIM-RUNTIME | active | S04 smoke evidence must not be upgraded to product suitability, production scale, or legal-quality proof. |
| EDGE-S05-OLD-PROJECT-PRIOR-ART-BOUNDED-BY-GATE-G008 | S05-OLD-PROJECT-PRIOR-ART | bounded_by | GATE-G008 | active | Old_project prior art remains bounded by executable parser/retrieval golden-test proof before any legacy assumption is promoted. |
| EDGE-S05-PARSER-ODT-BOUNDARY-BOUNDED-BY-GATE-G008 | S05-PARSER-ODT-BOUNDARY | bounded_by | GATE-G008 | active | S05 parser smoke guides investigation but product parser/retrieval readiness remains behind GATE-G008. |
| EDGE-S05-PARSER-ODT-BOUNDARY-EVIDENCED-BY-PARSER-CONSULTANT-CANDIDATES | S05-PARSER-ODT-BOUNDARY | evidenced_by | EVID-PARSER-CONSULTANT-CANDIDATES | active | Consultant relation candidates are tracked prior-art relation evidence but remain non-authoritative candidate records. |
| EDGE-S05-PARSER-ODT-BOUNDARY-EVIDENCED-BY-PARSER-ODT-SMOKE | S05-PARSER-ODT-BOUNDARY | evidenced_by | EVID-PARSER-ODT-SMOKE | active | Bounded ODT smoke records are tracked real-document parser evidence for current parser staging scope. |
| EDGE-S05-PARSER-ODT-BOUNDARY-EVIDENCED-BY-PARSER-SOURCE-FIXTURE-INVENTORY | S05-PARSER-ODT-BOUNDARY | evidenced_by | EVID-PARSER-SOURCE-FIXTURE-INVENTORY | active | M006 fixture inventory is tracked parser evidence that supersedes ad hoc source-path assumptions for downstream parser planning. |
| EDGE-S05-PARSER-ODT-BOUNDARY-EVIDENCED-BY-PARSER-STAGING-GRAPH | S05-PARSER-ODT-BOUNDARY | evidenced_by | EVID-PARSER-STAGING-GRAPH | active | NetworkX staging graph evidence preserves parser JSONL and relation-candidate invariants without claiming FalkorDB runtime loading. |
| EDGE-S10-GIGAEMBEDDINGS-CHALLENGER-BOUNDED-BY-GATE-G011 | S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED | bounded_by | GATE-G011 | active | Blocked GigaEmbeddings challenger evidence remains behind local embedding quality proof and cannot become managed fallback or default retrieval model. |
| EDGE-S10-USER-BGE-M3-BASELINE-BOUNDED-BY-GATE-G011 | S10-USER-BGE-M3-BASELINE | bounded_by | GATE-G011 | active | USER-bge-m3 runtime proof is a local baseline, not product retrieval quality proof. |

### High and Critical Risk Nodes

| ID | Risk | Type | Layer | Status | Proof Level |
| --- | --- | --- | --- | --- | --- |
| ASSUMP-PRD-SOURCE-TRUTH | high | assumption | architecture-governance | active | source-anchor |
| CHECK-ARCHITECTURE-EXTRACTOR | high | workflow_check | workflow-governance | active | static-check |
| COMP-LEGAL-NEXUS-ORCHESTRATOR | high | component | api-product | active | source-anchor |
| DATA-LEGAL-DOCUMENT-IDENTITY-FRBR | high | data_entity | temporal-model | hypothesis | source-anchor |
| DATA-LEGAL-EVIDENCE-CORE | high | data_entity | legal-evidence | active | source-anchor |
| DATA-LEGAL-SOURCE-HIERARCHY | high | data_entity | legal-evidence | hypothesis | source-anchor |
| DATA-LKIF-DEONTIC-MAPPING | high | data_entity | legal-evidence | hypothesis | source-anchor |
| DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY | high | data_entity | legal-evidence | hypothesis | source-anchor |
| DATA-TEMPORAL-PROPERTY-BUNDLE | high | data_entity | temporal-model | active | source-anchor |
| DEC-D031 | high | decision | architecture-governance | active | source-anchor |
| EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF | high | evidence | retrieval-embedding | bounded-evidence | unit-test |
| EVID-OFFLINE-CITATION-RETRIEVAL-PROOF | high | evidence | retrieval-embedding | bounded-evidence | unit-test |
| EVID-PARSER-ODT-SMOKE | high | evidence | parser-ingestion | bounded-evidence | real-document-proof |
| EVID-REAL-ARTIFACT-RETRIEVAL-PROOF | high | evidence | retrieval-embedding | bounded-evidence | unit-test |
| EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF | high | evidence | retrieval-embedding | bounded-evidence | runtime-smoke |
| EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS | high | evidence | retrieval-embedding | bounded-evidence | source-anchor |
| EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING | high | evidence | retrieval-embedding | bounded-evidence | source-anchor |
| EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | high | evidence | architecture-governance | bounded-evidence | source-anchor |
| EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF | high | evidence | retrieval-embedding | bounded-evidence | unit-test |
| GATE-AKOMA-FRBR-NORMALIZATION | high | proof_gate | parser-ingestion | proposed | source-anchor |
| GATE-EMBEDDING-SUPPLY-CHAIN | high | proof_gate | security-safety | active | none |
| GATE-G005 | high | proof_gate | temporal-model | active | none |
| GATE-G008 | high | proof_gate | parser-ingestion | active | none |
| GATE-G011 | high | proof_gate | retrieval-embedding | active | none |
| GATE-GENERATED-CYPHER-SAFETY | critical | proof_gate | generated-cypher | active | none |
| GATE-LEGAL-COLLISION-POLICY | high | proof_gate | legal-evidence | proposed | source-anchor |
| GATE-LEGAL-NEXUS-ACCESS-CONTROL | high | proof_gate | security-safety | active | none |
| GATE-LKIF-DEONTIC-BENCHMARK | high | proof_gate | legal-evidence | proposed | source-anchor |
| GATE-ONTOLOGY-GRAPHRAG-INTEGRATION | high | proof_gate | retrieval-embedding | proposed | source-anchor |
| GATE-PILOT-SCALE-READINESS | high | proof_gate | observability-operability | proposed | source-anchor |
| GATE-RUSLEGALCORE-SCOPE | high | proof_gate | legal-evidence | proposed | source-anchor |
| M001-ARCHITECTURE-ONLY-GUARDRAIL | critical | workflow_check | architecture-governance | out-of-scope | source-anchor |
| REQ-R009 | high | requirement | workflow-governance | active | source-anchor |
| REQ-R017 | high | requirement | generated-cypher | active | source-anchor |
| REQ-R022 | critical | requirement | security-safety | active | source-anchor |
| REQ-R028 | critical | requirement | security-safety | out-of-scope | source-anchor |
| REQ-R029 | high | requirement | architecture-governance | active | source-anchor |
| REQ-R034 | high | requirement | retrieval-embedding | active | source-anchor |
| REQ-TEMPORAL-STATUS-SEMANTICS | high | requirement | temporal-model | active | source-anchor |
| RISK-OVERCLAIM-RUNTIME | critical | risk | security-safety | active | source-anchor |
| S05-OLD-PROJECT-PRIOR-ART | high | evidence | parser-ingestion | bounded-evidence | source-anchor |
| S05-PARSER-ODT-BOUNDARY | high | evidence | parser-ingestion | bounded-evidence | real-document-proof |

## Invalid Records

| ID | Rule | Value |
| --- | --- | --- |
| _None_ |  |  |

## Non-Claims Boundary

| Field | Value |
| --- | ---: |
| Nodes with non-claims | 58 |
| Total non-claims | 294 |

### Nodes with Non-Claims

| ID | Count |
| --- | ---: |
| ASSUMP-PRD-SOURCE-TRUTH | 1 |
| CHECK-ARCHITECTURE-EXTRACTOR | 1 |
| COMP-LEGAL-NEXUS-ORCHESTRATOR | 3 |
| DATA-LEGAL-DOCUMENT-IDENTITY-FRBR | 10 |
| DATA-LEGAL-EVIDENCE-CORE | 3 |
| DATA-LEGAL-SOURCE-HIERARCHY | 10 |
| DATA-LKIF-DEONTIC-MAPPING | 10 |
| DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY | 10 |
| DATA-TEMPORAL-PROPERTY-BUNDLE | 2 |
| DEC-D031 | 1 |
| DEC-D032 | 1 |
| EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF | 11 |
| EVID-OFFLINE-CITATION-RETRIEVAL-PROOF | 10 |
| EVID-PARSER-CONSULTANT-CANDIDATES | 2 |
| EVID-PARSER-CONSULTANT-HIERARCHY-PROOF | 5 |
| EVID-PARSER-GOLDEN-TEST-PROOF | 5 |
| EVID-PARSER-ODT-SMOKE | 2 |
| EVID-PARSER-RECORD-CONTRACT | 2 |
| EVID-PARSER-SOURCE-FIXTURE-INVENTORY | 2 |
| EVID-PARSER-STAGING-GRAPH | 2 |
| EVID-REAL-ARTIFACT-RETRIEVAL-PROOF | 10 |
| EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF | 11 |
| EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS | 5 |
| EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING | 5 |
| EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO | 11 |
| EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF | 8 |
| GATE-AKOMA-FRBR-NORMALIZATION | 10 |
| GATE-BFO-GOST-ALIGNMENT | 10 |
| GATE-EMBEDDING-SUPPLY-CHAIN | 3 |
| GATE-G005 | 1 |
| GATE-G008 | 2 |
| GATE-G011 | 2 |
| GATE-G015 | 1 |
| GATE-GENERATED-CYPHER-SAFETY | 3 |
| GATE-LEGAL-COLLISION-POLICY | 10 |
| GATE-LEGAL-NEXUS-ACCESS-CONTROL | 3 |
| GATE-LKIF-DEONTIC-BENCHMARK | 10 |
| GATE-ONTOLOGY-GRAPHRAG-INTEGRATION | 10 |
| GATE-PILOT-SCALE-READINESS | 12 |
| GATE-RUSLEGALCORE-SCOPE | 9 |
| M001-ARCHITECTURE-ONLY-GUARDRAIL | 6 |
| QS-OBSERVABILITY-OPERABILITY-BASELINE | 3 |
| REQ-R001 | 7 |
| REQ-R009 | 7 |
| REQ-R010 | 7 |
| REQ-R017 | 4 |
| REQ-R022 | 3 |
| REQ-R028 | 3 |
| REQ-R029 | 1 |
| REQ-R034 | 6 |
| REQ-TEMPORAL-STATUS-SEMANTICS | 2 |
| RISK-OVERCLAIM-RUNTIME | 1 |
| S04-FALKORDB-RUNTIME-BOUNDED | 3 |
| S05-OLD-PROJECT-PRIOR-ART | 2 |
| S05-PARSER-ODT-BOUNDARY | 3 |
| S07-FIXED-PRD-CONSISTENCY | 1 |
| S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED | 3 |
| S10-USER-BGE-M3-BASELINE | 3 |
