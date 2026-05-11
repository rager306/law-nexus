# Architecture Health Dashboard

**Status:** ⚠️  Needs Attention
**Non-Authoritative:** This dashboard is derived from graph artifacts and does not validate product/runtime/legal claims. PRD, GSD, ADR, source anchors, and runtime evidence remain the authoritative source of truth.

---

## Quick Stats

| Metric | Count |
| --- | ---: |
| Total Nodes | 23 |
| Total Edges | 17 |
| Schema Layers | 11 |
| Missing Layers | 3 |
| Invalid Layer Records | 0 |
| Unresolved Proof Gates | 4 |
| Orphan Findings | 3 |
| Contradiction Edges | 0 |
| High/Critical Risk Nodes | 15 (4 critical, 11 high) |
| Nodes with Non-Claims | 23 |
| Total Non-Claims | 64 |

---

## Layer Coverage

| Layer | Node Count |
| --- | ---: |
| api-product ⚠️ | 0 |
| architecture-governance  | 7 |
| generated-cypher  | 1 |
| graph-runtime  | 2 |
| legal-evidence ⚠️ | 0 |
| observability-operability ⚠️ | 0 |
| parser-ingestion  | 3 |
| retrieval-embedding  | 3 |
| security-safety  | 3 |
| temporal-model  | 1 |
| workflow-governance  | 3 |

### ⚠️  Missing Layers

The following schema layers have no architecture records:

- api-product
- legal-evidence
- observability-operability

---

## Open Proof Gates

| ID | Layer | Owner | Risk | Verification |
| --- | --- | --- | --- | --- |
| GATE-G005 | temporal-model | future-temporal-proof | high | A future proof slice defines and verifies same-date/multi-ed... |
| GATE-G008 | parser-ingestion | future-parser-retrieval-proof | high | Golden tests pass on real legal source fixtures and retrieva... |
| GATE-G011 | retrieval-embedding | future-retrieval-quality-proof | high | Retrieval quality benchmark passes under local/open-weight e... |
| GATE-G015 | graph-runtime | future-runtime-migration-proof | medium | Migration runbook is executed against bounded fixtures and r... |

---

## High-Risk Nodes

| ID | Risk | Type | Layer | Status | Proof Level |
| --- | --- | --- | --- | --- | --- |
| ASSUMP-PRD-SOURCE-TRUTH | high | assumption | architecture-governance | active | source-anchor |
| CHECK-ARCHITECTURE-EXTRACTOR | high | workflow_check | workflow-governance | active | static-check |
| DEC-D031 | high | decision | architecture-governance | active | source-anchor |
| GATE-G005 | high | proof_gate | temporal-model | active | none |
| GATE-G008 | high | proof_gate | parser-ingestion | active | none |
| GATE-G011 | high | proof_gate | retrieval-embedding | active | none |
| M001-ARCHITECTURE-ONLY-GUARDRAIL | critical | workflow_check | architecture-governance | out-of-scope | source-anchor |
| REQ-R009 | high | requirement | workflow-governance | active | source-anchor |
| REQ-R017 | high | requirement | generated-cypher | active | source-anchor |
| REQ-R022 | critical | requirement | security-safety | active | source-anchor |
| REQ-R028 | critical | requirement | security-safety | out-of-scope | source-anchor |
| REQ-R029 | high | requirement | architecture-governance | active | source-anchor |
| RISK-OVERCLAIM-RUNTIME | critical | risk | security-safety | active | source-anchor |
| S05-OLD-PROJECT-PRIOR-ART | high | evidence | parser-ingestion | bounded-evidence | source-anchor |
| S05-PARSER-ODT-BOUNDARY | high | evidence | parser-ingestion | bounded-evidence | real-document-proof |

---

## Non-Authoritative Boundary

This architecture graph and derived reports **do not** establish or validate:

| Non-Claim |
| --- |
| Does not itself prove product runtime behavior. |
| Does not make generated artifacts authoritative. |
| Does not prove product behavior. |
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

| ID | Rule |
| --- | --- |
| ASSUMP-PRD-SOURCE-TRUTH | isolated-node |
| S05-OLD-PROJECT-PRIOR-ART | isolated-node |
| S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED | isolated-node |

---

## Weakly Connected Components

| Size | Node Count |
| --- | ---: |
| 14 | 14 |
| 4 | 4 |
| 2 | 2 |
| 1 | 1 |
| 1 | 1 |
| 1 | 1 |

---

*Dashboard generated from `prd/architecture/architecture_graph_report.json`. This is a derived, non-authoritative view. Source-of-truth remains with PRD, GSD, ADR, and source anchor evidence.*
