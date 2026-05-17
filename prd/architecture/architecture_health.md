# Architecture Health Dashboard

**Status:** ⚠️  Needs Attention
**Non-Authoritative:** This dashboard is derived from graph artifacts and does not validate product/runtime/legal claims. PRD, GSD, ADR, source anchors, and runtime evidence remain the authoritative source of truth.

---

## Quick Stats

| Metric | Count |
| --- | ---: |
| Total Nodes | 58 |
| Total Edges | 91 |
| Schema Layers | 11 |
| Missing Layers | 0 |
| Invalid Layer Records | 0 |
| Unresolved Proof Gates | 7 |
| Orphan Findings | 0 |
| Contradiction Edges | 0 |
| High/Critical Risk Nodes | 42 (5 critical, 37 high) |
| Nodes with Non-Claims | 58 |
| Total Non-Claims | 294 |

---

## GSD Validation Snapshot

Priority and gate rows below are compact triage metadata only. They do not promote claims, prove product readiness, or replace source anchors.

| Bucket | Diagnostic Class | Count |
| --- | --- | ---: |
| P0 | critical-gate | 8 |
| P1 | high-priority-blocker | 36 |
| P2 | medium-diagnostic | 13 |
| P3 | backlog-only-signal | 1 |

### Critical Blockers

| ID | Status | Proof Level | Remediation Class |
| --- | --- | --- | --- |
| `GATE-GENERATED-CYPHER-SAFETY` | active | none | add-proof-gate |

### High-Priority Validator Failures

| ID | Status | Proof Level | Remediation Class |
| --- | --- | --- | --- |
| `GATE-AKOMA-FRBR-NORMALIZATION` | proposed | source-anchor | add-evidence-class |
| `GATE-EMBEDDING-SUPPLY-CHAIN` | active | none | add-proof-gate |
| `GATE-G005` | active | none | add-proof-gate |
| `GATE-G008` | active | none | add-proof-gate |
| `GATE-G011` | active | none | add-proof-gate |
| `GATE-LEGAL-COLLISION-POLICY` | proposed | source-anchor | add-evidence-class |
| `GATE-LEGAL-NEXUS-ACCESS-CONTROL` | active | none | add-proof-gate |
| `GATE-LKIF-DEONTIC-BENCHMARK` | proposed | source-anchor | add-evidence-class |
| `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` | proposed | source-anchor | add-evidence-class |
| `GATE-PILOT-SCALE-READINESS` | proposed | source-anchor | add-evidence-class |

### Deferred Candidates

| ID | Priority | Status | Safe Handling |
| --- | --- | --- | --- |
| `GATE-AKOMA-FRBR-NORMALIZATION` | P1 / high-priority-blocker | proposed | defer-to-backlog |
| `GATE-BFO-GOST-ALIGNMENT` | P2 / medium-diagnostic | proposed | defer-to-backlog |
| `GATE-LEGAL-COLLISION-POLICY` | P1 / high-priority-blocker | proposed | defer-to-backlog |
| `GATE-LKIF-DEONTIC-BENCHMARK` | P1 / high-priority-blocker | proposed | defer-to-backlog |
| `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` | P1 / high-priority-blocker | proposed | defer-to-backlog |
| `GATE-PILOT-SCALE-READINESS` | P1 / high-priority-blocker | proposed | defer-to-backlog |
| `GATE-RUSLEGALCORE-SCOPE` | P1 / high-priority-blocker | proposed | defer-to-backlog |

### Non-Authoritative Warnings

- Non-claim statements visible in registry: 294.
- Reports must not include raw legal text, secrets, provider payloads, vectors, prompts, or local-only execution artifact paths.
- A passing generated view check is not product/runtime/legal validation.

---

## Layer Coverage

| Layer | Node Count |
| --- | ---: |
| api-product  | 1 |
| architecture-governance  | 9 |
| generated-cypher  | 2 |
| graph-runtime  | 2 |
| legal-evidence  | 7 |
| observability-operability  | 2 |
| parser-ingestion  | 11 |
| retrieval-embedding  | 12 |
| security-safety  | 5 |
| temporal-model  | 4 |
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

---

## Non-Authoritative Boundary

This architecture graph and derived reports **do not** establish or validate:

| Non-Claim |
| --- |
| Does not allow managed embedding API fallback. |
| Does not assert BFO conformance. |
| Does not assert Common Logic necessity or OWL reasoning support. |
| Does not assert GOST requirements. |
| Does not assert current product is insecure. |
| Does not assert final legal graph schema completeness. |
| Does not authorize GigaChat or GigaEmbeddings runtime use. |
| Does not authorize automated legal conclusions. |
| Does not authorize executing raw generated Cypher. |
| Does not authorize generated Cypher execution. |
| Does not claim that 1,000 representative documents have been processed. |
| Does not close GATE-G008. |
| Does not close GATE-G011. |
| Does not decide legal priority. |
| Does not define a production API surface. |
| Does not define final ontology scope. |
| Does not implement Legal Nexus runtime behavior. |
| Does not invalidate existing bounded proofs. |
| Does not itself prove product runtime behavior. |
| Does not make Akoma Ntoso canonical. |
| Does not make LLM output legal authority. |
| Does not make ML/NER outputs authoritative assertions. |
| Does not make fixture IDs production IDs. |
| Does not make generated artifacts authoritative. |
| Does not make proof-local IDs production IDs. |
| Does not make proof-local fixture metrics production metrics. |
| Does not persist raw legal text, raw query text, raw prompts, vectors, provider payloads, managed-API evidence, raw FalkorDB rows, secrets, or generated legal advice. |
| Does not produce legally binding answers. |
| Does not promote D045 research into validated product behavior. |
| Does not promote GigaEmbeddings. |
| Does not promote any embedding model to product default. |
| Does not prove Consultant relation correctness. |
| Does not prove FalkorDB graph-vector/runtime capability. |
| Does not prove FalkorDB loading/runtime behavior. |
| Does not prove FalkorDB production-scale behavior. |
| Does not prove FalkorDB runtime/vector/full-text/rerank behavior. |
| Does not prove GOST/BFO source correctness. |
| Does not prove Garant ODT parser regression. |
| Does not prove GraphRAG-SDK compatibility. |
| Does not prove HNSW behavior or single-transaction graph+vector semantics. |
| Does not prove LKIF/deontic extraction correctness. |
| Does not prove ML model fitness. |
| Does not prove RusLawOD corpus priority. |
| Does not prove Russian-law completeness. |
| Does not prove access-control enforcement. |
| Does not prove amendment aggregation or inactive-version filtering. |
| Does not prove automated legal collision resolution. |
| Does not prove citation-safe retrieval readiness. |
| Does not prove compatibility with Consultant, Garant, RusLawOD, or Akoma Ntoso sources. |
| Does not prove correct FRBR implementation. |
| Does not prove court interpretation correctness. |
| Does not prove export compatibility. |
| Does not prove extraction precision or recall. |
| Does not prove implementation readiness. |
| Does not prove import runtime behavior. |
| Does not prove legal correctness. |
| Does not prove legal-answer correctness. |
| Does not prove local embedding quality. |
| Does not prove multi-document Consultant expansion. |
| Does not prove negation handling or modal-verb interpretation. |
| Does not prove ontology GraphRAG retrieval quality. |
| Does not prove ontology benchmark quality. |
| Does not prove ontology completeness. |
| Does not prove parser completeness. |
| Does not prove pilot-scale readiness. |
| Does not prove product ETL readiness. |
| Does not prove product Legal KnowQL behavior. |
| Does not prove product behavior. |
| Does not prove product retrieval quality. |
| Does not prove production FalkorDB runtime behavior. |
| Does not prove production Legal KnowQL behavior. |
| Does not prove production graph schema readiness. |
| Does not prove production observability. |
| Does not prove production ranker quality. |
| Does not prove production scale. |
| Does not prove production-scale FalkorDB claim. |
| Does not prove provider generation quality. |
| Does not prove raw legal text evidence quality. |
| Does not prove runtime SLOs. |
| Does not prove semantic extraction. |
| Does not prove vector/full-text/FalkorDB runtime capability. |
| Does not replace project-local LegalGraph core contracts. |
| Does not require replacing current parser record contracts. |
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
| Planning alias GATE-1000-DOC-PILOT is not emitted as an authoritative gate. |
| Planning alias GATE-DEONTIC-MAPPING-PROOF is not emitted as an authoritative gate. |
| Risk item does not assert current product failure. |
| The skill is guidance, not a source of truth. |

---

## Orphan Findings

No orphan findings.


---

## Weakly Connected Components

| Size | Node Count |
| --- | ---: |
| 54 | 54 |
| 4 | 4 |

---

*Dashboard generated from `prd/architecture/architecture_graph_report.json`. This is a derived, non-authoritative view. Source-of-truth remains with PRD, GSD, ADR, and source anchor evidence.*
