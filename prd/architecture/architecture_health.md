# Architecture Health Dashboard

**Status:** ⚠️  Needs Attention
**Non-Authoritative:** This dashboard is derived from graph artifacts and does not validate product/runtime/legal claims. PRD, GSD, ADR, source anchors, and runtime evidence remain the authoritative source of truth.

---

## Quick Stats

| Metric | Count |
| --- | ---: |
| Total Nodes | 44 |
| Total Edges | 59 |
| Schema Layers | 11 |
| Missing Layers | 0 |
| Invalid Layer Records | 0 |
| Unresolved Proof Gates | 7 |
| Orphan Findings | 0 |
| Contradiction Edges | 0 |
| High/Critical Risk Nodes | 29 (5 critical, 24 high) |
| Nodes with Non-Claims | 44 |
| Total Non-Claims | 150 |

---

## Layer Coverage

| Layer | Node Count |
| --- | ---: |
| api-product  | 1 |
| architecture-governance  | 7 |
| generated-cypher  | 2 |
| graph-runtime  | 2 |
| legal-evidence  | 1 |
| observability-operability  | 1 |
| parser-ingestion  | 10 |
| retrieval-embedding  | 9 |
| security-safety  | 5 |
| temporal-model  | 3 |
| workflow-governance  | 3 |

### ✅  All Schema Layers Covered

Every defined schema layer has at least one architecture record.

---

## Open Proof Gates

| ID | Layer | Owner | Risk | Verification |
| --- | --- | --- | --- | --- |
| GATE-EMBEDDING-SUPPLY-CHAIN | security-safety | future-embedding-supply-chain-proof | high | Future embedding proof records model source, checksum or rev... |
| GATE-G005 | temporal-model | future-temporal-proof | high | A future proof slice defines and verifies same-date/multi-ed... |
| GATE-G008 | parser-ingestion | future-product-parser-retrieval-proof | high | Future product proof demonstrates parser completeness bounda... |
| GATE-G011 | retrieval-embedding | future-retrieval-quality-proof | high | Retrieval quality benchmark passes under local/open-weight e... |
| GATE-G015 | graph-runtime | future-runtime-migration-proof | medium | Migration runbook is executed against bounded fixtures and r... |
| GATE-GENERATED-CYPHER-SAFETY | generated-cypher | future-generated-cypher-safety-proof | critical | A future product proof demonstrates validator acceptance/rej... |
| GATE-LEGAL-NEXUS-ACCESS-CONTROL | security-safety | future-api-security-proof | high | Future security proof defines caller boundaries, authorizati... |

---

## High-Risk Nodes

| ID | Risk | Type | Layer | Status | Proof Level |
| --- | --- | --- | --- | --- | --- |
| ASSUMP-PRD-SOURCE-TRUTH | high | assumption | architecture-governance | active | source-anchor |
| CHECK-ARCHITECTURE-EXTRACTOR | high | workflow_check | workflow-governance | active | static-check |
| COMP-LEGAL-NEXUS-ORCHESTRATOR | high | component | api-product | active | source-anchor |
| DATA-LEGAL-EVIDENCE-CORE | high | data_entity | legal-evidence | active | source-anchor |
| DATA-TEMPORAL-PROPERTY-BUNDLE | high | data_entity | temporal-model | active | source-anchor |
| DEC-D031 | high | decision | architecture-governance | active | source-anchor |
| EVID-OFFLINE-CITATION-RETRIEVAL-PROOF | high | evidence | retrieval-embedding | bounded-evidence | unit-test |
| EVID-PARSER-ODT-SMOKE | high | evidence | parser-ingestion | bounded-evidence | real-document-proof |
| EVID-REAL-ARTIFACT-RETRIEVAL-PROOF | high | evidence | retrieval-embedding | bounded-evidence | unit-test |
| EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS | high | evidence | retrieval-embedding | bounded-evidence | source-anchor |
| EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING | high | evidence | retrieval-embedding | bounded-evidence | source-anchor |
| EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF | high | evidence | retrieval-embedding | bounded-evidence | unit-test |
| GATE-EMBEDDING-SUPPLY-CHAIN | high | proof_gate | security-safety | active | none |
| GATE-G005 | high | proof_gate | temporal-model | active | none |
| GATE-G008 | high | proof_gate | parser-ingestion | active | none |
| GATE-G011 | high | proof_gate | retrieval-embedding | active | none |
| GATE-GENERATED-CYPHER-SAFETY | critical | proof_gate | generated-cypher | active | none |
| GATE-LEGAL-NEXUS-ACCESS-CONTROL | high | proof_gate | security-safety | active | none |
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

---

## Non-Authoritative Boundary

This architecture graph and derived reports **do not** establish or validate:

| Non-Claim |
| --- |
| Does not allow managed embedding API fallback. |
| Does not assert current product is insecure. |
| Does not assert final legal graph schema completeness. |
| Does not authorize executing raw generated Cypher. |
| Does not authorize generated Cypher execution. |
| Does not close GATE-G008. |
| Does not close GATE-G011. |
| Does not define a production API surface. |
| Does not implement Legal Nexus runtime behavior. |
| Does not itself prove product runtime behavior. |
| Does not make LLM output legal authority. |
| Does not make fixture IDs production IDs. |
| Does not make generated artifacts authoritative. |
| Does not make proof-local IDs production IDs. |
| Does not promote D045 research into validated product behavior. |
| Does not promote any embedding model to product default. |
| Does not prove Consultant relation correctness. |
| Does not prove FalkorDB loading/runtime behavior. |
| Does not prove FalkorDB production-scale behavior. |
| Does not prove FalkorDB runtime/vector/full-text/rerank behavior. |
| Does not prove Garant ODT parser regression. |
| Does not prove GraphRAG-SDK compatibility. |
| Does not prove access-control enforcement. |
| Does not prove citation-safe retrieval readiness. |
| Does not prove import runtime behavior. |
| Does not prove legal correctness. |
| Does not prove legal-answer correctness. |
| Does not prove local embedding quality. |
| Does not prove multi-document Consultant expansion. |
| Does not prove parser completeness. |
| Does not prove product ETL readiness. |
| Does not prove product Legal KnowQL behavior. |
| Does not prove product behavior. |
| Does not prove product retrieval quality. |
| Does not prove production FalkorDB runtime behavior. |
| Does not prove production Legal KnowQL behavior. |
| Does not prove production graph schema readiness. |
| Does not prove production observability. |
| Does not prove provider generation quality. |
| Does not prove raw legal text evidence quality. |
| Does not prove runtime SLOs. |
| Does not specify temporal storage implementation. |
| Does not validate benchmark, cost, or latency claims. |
| Does not validate same-date conflict policy. |
| Does not validate temporal conflict resolution. |
| Extractor check is not product runtime proof. |
| JSONL and GraphML are not source-of-truth replacements. |
| No KnowQL parser. |
| No LLM legal authority claim. |
| No LegalNexus API. |
| No Old_project artifact accepted unchanged. |
| No credential, prompt, raw legal text, or raw row emission claim. |
| No default promotion while blocked-environment. |
| No direct LegalGraph GraphBLAS API/control surface claim. |
| No final legal hierarchy extraction claim. |
| No generated Cypher authority claim. |
| No hybrid retrieval. |
| No legal retrieval quality claim. |
| No legal-answer correctness claim. |
| No legal-answering runtime. |
| No live legal graph execution claim. |
| No managed embedding API fallback claim. |
| No parser completeness claim. |
| No product ETL. |
| No product Legal KnowQL behavior claim. |
| No product retrieval quality claim. |
| No production SourceBlock/EvidenceSpan creation claim. |
| No production graph schema. |
| No production-scale FalkorDB claim. |
| No raw embedding leakage claim beyond verifier scope. |
| No raw provider body persistence claim. |
| Risk item does not assert current product failure. |
| The skill is guidance, not a source of truth. |

---

## Orphan Findings

No orphan findings.


---

## Weakly Connected Components

| Size | Node Count |
| --- | ---: |
| 40 | 40 |
| 4 | 4 |

---

*Dashboard generated from `prd/architecture/architecture_graph_report.json`. This is a derived, non-authoritative view. Source-of-truth remains with PRD, GSD, ADR, and source anchor evidence.*
