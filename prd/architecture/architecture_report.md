# Architecture Graph Report

This report is derived, non-authoritative, and generated from the S02 architecture JSONL registry.
These graph/report outputs do not validate product/runtime/legal claims; PRD, GSD, ADR, source, and runtime evidence remain the source of truth.
Current orphans, unresolved proof gates, contradictions, and risk rows are findings for S04 or later verifier work, not automatic S03 build failures.

## Summary

| Field | Value |
| --- | --- |
| Nodes | 42 |
| Edges | 52 |
| Non-authoritative | true |
| Missing layers | 0 |
| Unresolved proof gates | 7 |
| Orphan findings | 0 |
| Contradiction edges | 0 |
| High/critical-risk nodes | 27 |

## Layer Coverage

| Layer | Node Count |
| --- | ---: |
| api-product | 1 |
| architecture-governance | 7 |
| generated-cypher | 2 |
| graph-runtime | 2 |
| legal-evidence | 1 |
| observability-operability | 1 |
| parser-ingestion | 10 |
| retrieval-embedding | 7 |
| security-safety | 5 |
| temporal-model | 3 |
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

### High and Critical Risk Nodes

| ID | Risk | Type | Layer | Status | Proof Level |
| --- | --- | --- | --- | --- | --- |
| ASSUMP-PRD-SOURCE-TRUTH | high | assumption | architecture-governance | active | source-anchor |
| CHECK-ARCHITECTURE-EXTRACTOR | high | workflow_check | workflow-governance | active | static-check |
| COMP-LEGAL-NEXUS-ORCHESTRATOR | high | component | api-product | active | source-anchor |
| DATA-LEGAL-EVIDENCE-CORE | high | data_entity | legal-evidence | active | source-anchor |
| DATA-TEMPORAL-PROPERTY-BUNDLE | high | data_entity | temporal-model | active | source-anchor |
| DEC-D031 | high | decision | architecture-governance | active | source-anchor |
| EVID-PARSER-ODT-SMOKE | high | evidence | parser-ingestion | bounded-evidence | real-document-proof |
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

## Invalid Records

| ID | Rule | Value |
| --- | --- | --- |
| _None_ |  |  |

## Non-Claims Boundary

| Field | Value |
| --- | ---: |
| Nodes with non-claims | 42 |
| Total non-claims | 130 |

### Nodes with Non-Claims

| ID | Count |
| --- | ---: |
| ASSUMP-PRD-SOURCE-TRUTH | 1 |
| CHECK-ARCHITECTURE-EXTRACTOR | 1 |
| COMP-LEGAL-NEXUS-ORCHESTRATOR | 3 |
| DATA-LEGAL-EVIDENCE-CORE | 3 |
| DATA-TEMPORAL-PROPERTY-BUNDLE | 2 |
| DEC-D031 | 1 |
| DEC-D032 | 1 |
| EVID-PARSER-CONSULTANT-CANDIDATES | 2 |
| EVID-PARSER-CONSULTANT-HIERARCHY-PROOF | 5 |
| EVID-PARSER-GOLDEN-TEST-PROOF | 5 |
| EVID-PARSER-ODT-SMOKE | 2 |
| EVID-PARSER-RECORD-CONTRACT | 2 |
| EVID-PARSER-SOURCE-FIXTURE-INVENTORY | 2 |
| EVID-PARSER-STAGING-GRAPH | 2 |
| EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS | 5 |
| EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING | 5 |
| EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF | 8 |
| GATE-EMBEDDING-SUPPLY-CHAIN | 3 |
| GATE-G005 | 1 |
| GATE-G008 | 2 |
| GATE-G011 | 2 |
| GATE-G015 | 1 |
| GATE-GENERATED-CYPHER-SAFETY | 3 |
| GATE-LEGAL-NEXUS-ACCESS-CONTROL | 3 |
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
