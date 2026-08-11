# Product Readiness Blockers Report

> **D7 QUARANTINE — DERIVED VIEW.** Disposition baseline `bfe2ee6`, as-of 2026-08-11. Legacy GATE-G005/G008/G011/G015 and ACP/FalkorDB/PyO3 rows are not the current readiness map; use `prd/temporal-legal-model.md` §10–10.1.
> This view cannot satisfy requirements, promote lifecycle, or prove product/legal/runtime/parser/retrieval claims. Canonical truth: `prd/ARCHITECTURE.md`, `doc/adr/**`, `prd/PRODUCT.md`.

> **Scope:** This report maps active proof gates, blocked evidence, and non-claims to the six capability areas required for LegalGraph Nexus product readiness. It is a derived, non-authoritative planning artifact only — it does **not** assert product readiness and does not validate runtime behavior, retrieval quality, parser completeness, generated-Cypher safety, FalkorDB production scale, or legal-answer correctness.

---

## Summary Table

| Capability Area | Gate Count | Blocked / Bounded Count |
| --- | ---: | ---: |
| ETL / Parser | 1 | 3 |
| Graph Runtime | 1 | 0 |
| Legal Answering | 2 | 0 |
| Legal KnowQL / Generated Cypher | 1 | 0 |
| Retrieval / Embedding | 1 | 7 |
| Temporal Model | 1 | 0 |
| architecture-governance | 0 | 2 |

## Priority Snapshot

This snapshot is a triage view only; priority does not prove readiness or promote claims.

| Priority | Count | Representative Blockers |
| --- | ---: | --- |
| P0 | 1 | `GATE-GENERATED-CYPHER-SAFETY` |
| P1 | 17 | `ACP-AHF-0001`, `EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF`, `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF`, `EVID-PARSER-ODT-SMOKE`, `EVID-REAL-ARTIFACT-RETRIEVAL-PROOF` |
| P2 | 1 | `GATE-G015` |
| P3 | 0 | — |

## ETL / Parser

### Proof Gates

| ID | Title | Priority | Status | Risk | Verification | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| `GATE-G008` | Quarantined missing-anchor: Product parser and retrieval readiness gate | P1 / high-priority-blocker | blocked | high | Future product proof demonstrates parser completeness boundaries, citation-safe retrieval behavior, and retrieval quality over real legal source fixtures. | future-product-parser-retrieval-proof |
|  | No parser completeness claim. | — | — | — | — | — |
|  | No product retrieval quality claim. | — | — | — | — | — |

### Blocked / Bounded Evidence

| ID | Title | Priority | Status | Risk | Proof Level | Verification | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `EVID-PARSER-ODT-SMOKE` | Bounded ODT smoke-record evidence | P1 / high-priority-blocker | bounded-evidence | high | real-document-proof | `uv run python scripts/build-odt-smoke-records.py --check` verifies ODT smoke artifact freshness. | M006/S03 |
|  | No final legal hierarchy extraction claim. | — | — | — | — | — | — |
|  | No parser completeness claim. | — | — | — | — | — | — |
| `S05-OLD-PROJECT-PRIOR-ART` | Quarantined missing-anchor: Old_project artifacts remain prior art | P1 / high-priority-blocker | blocked | high | source-anchor | Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence. | S08 final architecture review / future parser owners |
|  | No Old_project artifact accepted unchanged. | — | — | — | — | — | — |
|  | No parser completeness claim. | — | — | — | — | — | — |
| `S05-PARSER-ODT-BOUNDARY` | Quarantined missing-anchor: Real ODT parser evidence boundary | P1 / high-priority-blocker | blocked | high | real-document-proof | Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence. | S05/S08 parser evidence consolidation |
|  | No final legal hierarchy extraction claim. | — | — | — | — | — | — |
|  | No parser completeness claim. | — | — | — | — | — | — |
|  | No production SourceBlock/EvidenceSpan creation claim. | — | — | — | — | — | — |

### What This Area Does Not Prove

_Below non-claims are drawn directly from architecture registry records. They are not exhaustive._

| Non-Claim |
| --- |
| No parser completeness claim. |
| No product retrieval quality claim. |
| No final legal hierarchy extraction claim. |
| No Old_project artifact accepted unchanged. |
| No production SourceBlock/EvidenceSpan creation claim. |

### Next Proof Work

Proof work for this area should:

- Address [`GATE-G008`](#proof-gates): Future product proof demonstrates parser completeness boundaries, citation-safe retrieval behavior, and retrieval quality over real legal source fixtures.
- Resolve [`EVID-PARSER-ODT-SMOKE`](#blocked--bounded-evidence): `uv run python scripts/build-odt-smoke-records.py --check` verifies ODT smoke artifact freshness.
- Resolve [`S05-OLD-PROJECT-PRIOR-ART`](#blocked--bounded-evidence): Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence.
- Resolve [`S05-PARSER-ODT-BOUNDARY`](#blocked--bounded-evidence): Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence.

## Graph Runtime

### Proof Gates

| ID | Title | Priority | Status | Risk | Verification | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| `GATE-G015` | Historical/superseded: FalkorDBLite to Docker migration runbook | P2 / medium-diagnostic | superseded | medium | Migration runbook is executed against bounded fixtures and runtime diagnostics. | future-runtime-migration-proof |
|  | No production-scale FalkorDB claim. | — | — | — | — | — |

### What This Area Does Not Prove

_Below non-claims are drawn directly from architecture registry records. They are not exhaustive._

| Non-Claim |
| --- |
| No production-scale FalkorDB claim. |

### Next Proof Work

Proof work for this area should:

- Address [`GATE-G015`](#proof-gates): Migration runbook is executed against bounded fixtures and runtime diagnostics.

## Legal Answering

### Proof Gates

| ID | Title | Priority | Status | Risk | Verification | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| `GATE-EMBEDDING-SUPPLY-CHAIN` | Quarantined missing-anchor: Embedding model supply-chain integrity gate | P1 / high-priority-blocker | blocked | high | Future embedding proof records model source, checksum or revision, local runtime envelope, vector dimension, and no-secret/no-raw-vector leakage checks. | future-embedding-supply-chain-proof |
|  | Does not allow managed embedding API fallback. | — | — | — | — | — |
|  | Does not promote any embedding model to product default. | — | — | — | — | — |
|  | Does not prove product retrieval quality. | — | — | — | — | — |
| `GATE-LEGAL-NEXUS-ACCESS-CONTROL` | Quarantined missing-anchor: Legal Nexus access-control proof gate | P1 / high-priority-blocker | blocked | high | Future security proof defines caller boundaries, authorization policy, audit logging, and denial diagnostics for Legal Nexus operations. | future-api-security-proof |
|  | Does not assert current product is insecure. | — | — | — | — | — |
|  | Does not define a production API surface. | — | — | — | — | — |
|  | Does not prove access-control enforcement. | — | — | — | — | — |

### What This Area Does Not Prove

_Below non-claims are drawn directly from architecture registry records. They are not exhaustive._

| Non-Claim |
| --- |
| Does not allow managed embedding API fallback. |
| Does not promote any embedding model to product default. |
| Does not prove product retrieval quality. |
| Does not assert current product is insecure. |
| Does not define a production API surface. |
| Does not prove access-control enforcement. |

### Next Proof Work

Proof work for this area should:

- Address [`GATE-EMBEDDING-SUPPLY-CHAIN`](#proof-gates): Future embedding proof records model source, checksum or revision, local runtime envelope, vector dimension, and no-secret/no-raw-vector leakage checks.
- Address [`GATE-LEGAL-NEXUS-ACCESS-CONTROL`](#proof-gates): Future security proof defines caller boundaries, authorization policy, audit logging, and denial diagnostics for Legal Nexus operations.

## Legal KnowQL / Generated Cypher

### Proof Gates

| ID | Title | Priority | Status | Risk | Verification | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| `GATE-GENERATED-CYPHER-SAFETY` | Quarantined missing-anchor: Generated-Cypher safety and validation gate | P0 / critical-gate | blocked | critical | A future product proof demonstrates validator acceptance/rejection behavior across representative Legal KnowQL tasks and live graph schemas. | future-generated-cypher-safety-proof |
|  | Does not authorize executing raw generated Cypher. | — | — | — | — | — |
|  | Does not prove production Legal KnowQL behavior. | — | — | — | — | — |
|  | Does not prove provider generation quality. | — | — | — | — | — |

### What This Area Does Not Prove

_Below non-claims are drawn directly from architecture registry records. They are not exhaustive._

| Non-Claim |
| --- |
| Does not authorize executing raw generated Cypher. |
| Does not prove production Legal KnowQL behavior. |
| Does not prove provider generation quality. |

### Next Proof Work

Proof work for this area should:

- Address [`GATE-GENERATED-CYPHER-SAFETY`](#proof-gates): A future product proof demonstrates validator acceptance/rejection behavior across representative Legal KnowQL tasks and live graph schemas.

## Retrieval / Embedding

### Proof Gates

| ID | Title | Priority | Status | Risk | Verification | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| `GATE-G011` | Quarantined missing-anchor: Local embedding quality proof | P1 / high-priority-blocker | blocked | high | Retrieval quality benchmark passes under local/open-weight embedding constraints. | future-retrieval-quality-proof |
|  | No managed embedding API fallback claim. | — | — | — | — | — |
|  | No product retrieval quality claim. | — | — | — | — | — |

### Blocked / Bounded Evidence

| ID | Title | Priority | Status | Risk | Proof Level | Verification | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF` | Quarantined missing-anchor: Local retrieval quality benchmark proof | P1 / high-priority-blocker | blocked | high | unit-test | Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence. | M015/S02 |
|  | Does not allow managed embedding API fallback. | — | — | — | — | — | — |
|  | Does not close GATE-G008. | — | — | — | — | — | — |
|  | Does not close GATE-G011. | — | — | — | — | — | — |
|  | Does not make LLM output legal authority. | — | — | — | — | — | — |
|  | Does not make proof-local fixture metrics production metrics. | — | — | — | — | — | — |
|  | Does not promote GigaEmbeddings. | — | — | — | — | — | — |
|  | Does not prove legal-answer correctness. | — | — | — | — | — | — |
|  | Does not prove parser completeness. | — | — | — | — | — | — |
|  | Does not prove product retrieval quality. | — | — | — | — | — | — |
|  | Does not prove production FalkorDB runtime behavior. | — | — | — | — | — | — |
|  | Does not prove production graph schema readiness. | — | — | — | — | — | — |
| `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF` | Quarantined missing-anchor: Offline citation-safe retrieval proof | P1 / high-priority-blocker | blocked | high | unit-test | Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence. | M014/S02 |
|  | Does not close GATE-G008. | — | — | — | — | — | — |
|  | Does not close GATE-G011. | — | — | — | — | — | — |
|  | Does not make LLM output legal authority. | — | — | — | — | — | — |
|  | Does not make proof-local IDs production IDs. | — | — | — | — | — | — |
|  | Does not prove legal-answer correctness. | — | — | — | — | — | — |
|  | Does not prove local embedding quality. | — | — | — | — | — | — |
|  | Does not prove parser completeness. | — | — | — | — | — | — |
|  | Does not prove product retrieval quality. | — | — | — | — | — | — |
|  | Does not prove production FalkorDB runtime behavior. | — | — | — | — | — | — |
|  | Does not prove production graph schema readiness. | — | — | — | — | — | — |
| `EVID-REAL-ARTIFACT-RETRIEVAL-PROOF` | Quarantined missing-anchor: Real-artifact retrieval output ID proof | P1 / high-priority-blocker | blocked | high | unit-test | Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence. | M013/S02 |
|  | Does not close GATE-G008. | — | — | — | — | — | — |
|  | Does not close GATE-G011. | — | — | — | — | — | — |
|  | Does not make LLM output legal authority. | — | — | — | — | — | — |
|  | Does not make proof-local IDs production IDs. | — | — | — | — | — | — |
|  | Does not prove legal-answer correctness. | — | — | — | — | — | — |
|  | Does not prove local embedding quality. | — | — | — | — | — | — |
|  | Does not prove parser completeness. | — | — | — | — | — | — |
|  | Does not prove product retrieval quality. | — | — | — | — | — | — |
|  | Does not prove production FalkorDB runtime behavior. | — | — | — | — | — | — |
|  | Does not prove production graph schema readiness. | — | — | — | — | — | — |
| `EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF` | Quarantined missing-anchor: Representative retrieval runtime benchmark proof | P1 / high-priority-blocker | blocked | high | runtime-smoke | Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence. | M016/S03 |
|  | Does not allow managed embedding API fallback. | — | — | — | — | — | — |
|  | Does not authorize GigaChat or GigaEmbeddings runtime use. | — | — | — | — | — | — |
|  | Does not close GATE-G011. | — | — | — | — | — | — |
|  | Does not make proof-local IDs production IDs. | — | — | — | — | — | — |
|  | Does not persist raw legal text, raw query text, raw prompts, vectors, provider payloads, managed-API evidence, raw FalkorDB rows, secrets, or generated legal advice. | — | — | — | — | — | — |
|  | Does not prove legal-answer correctness. | — | — | — | — | — | — |
|  | Does not prove parser completeness. | — | — | — | — | — | — |
|  | Does not prove product retrieval quality. | — | — | — | — | — | — |
|  | Does not prove production FalkorDB runtime behavior. | — | — | — | — | — | — |
|  | Does not prove production graph schema readiness. | — | — | — | — | — | — |
|  | Does not prove production ranker quality. | — | — | — | — | — | — |
| `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS` | Historical/superseded: GraphRAG/FalkorDB mathematical analysis research input | P1 / high-priority-blocker | superseded | high | source-anchor | D7 quarantine classification only; record cannot satisfy requirements or promote lifecycle. | M011/S01 |
|  | Does not prove FalkorDB production-scale behavior. | — | — | — | — | — | — |
|  | Does not prove GraphRAG-SDK compatibility. | — | — | — | — | — | — |
|  | Does not prove legal-answer correctness. | — | — | — | — | — | — |
|  | Does not prove product retrieval quality. | — | — | — | — | — | — |
|  | Does not validate benchmark, cost, or latency claims. | — | — | — | — | — | — |
| `EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING` | Historical/superseded: Habr Legal RAG iteration and scaling research input | P1 / high-priority-blocker | superseded | high | source-anchor | D7 quarantine classification only; record cannot satisfy requirements or promote lifecycle. | D045 / future-retrieval-quality-proof |
|  | Does not authorize generated Cypher execution. | — | — | — | — | — | — |
|  | Does not prove FalkorDB runtime/vector/full-text/rerank behavior. | — | — | — | — | — | — |
|  | Does not prove legal-answer correctness. | — | — | — | — | — | — |
|  | Does not prove parser completeness. | — | — | — | — | — | — |
|  | Does not prove product retrieval quality. | — | — | — | — | — | — |
| `EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF` | Quarantined missing-anchor: Retrieval output ID validator bounded proof | P1 / high-priority-blocker | blocked | high | unit-test | Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence. | M012/S02 |
|  | Does not make LLM output legal authority. | — | — | — | — | — | — |
|  | Does not make fixture IDs production IDs. | — | — | — | — | — | — |
|  | Does not promote D045 research into validated product behavior. | — | — | — | — | — | — |
|  | Does not prove legal-answer correctness. | — | — | — | — | — | — |
|  | Does not prove parser completeness. | — | — | — | — | — | — |
|  | Does not prove product retrieval quality. | — | — | — | — | — | — |
|  | Does not prove production FalkorDB runtime behavior. | — | — | — | — | — | — |
|  | Does not prove raw legal text evidence quality. | — | — | — | — | — | — |

### What This Area Does Not Prove

_Below non-claims are drawn directly from architecture registry records. They are not exhaustive._

| Non-Claim |
| --- |
| No managed embedding API fallback claim. |
| No product retrieval quality claim. |
| Does not allow managed embedding API fallback. |
| Does not close GATE-G008. |
| Does not close GATE-G011. |
| Does not make LLM output legal authority. |
| Does not make proof-local fixture metrics production metrics. |
| Does not promote GigaEmbeddings. |
| Does not prove legal-answer correctness. |
| Does not prove parser completeness. |
| Does not prove product retrieval quality. |
| Does not prove production FalkorDB runtime behavior. |
| Does not prove production graph schema readiness. |
| Does not make proof-local IDs production IDs. |
| Does not prove local embedding quality. |
| Does not authorize GigaChat or GigaEmbeddings runtime use. |
| Does not persist raw legal text, raw query text, raw prompts, vectors, provider payloads, managed-API evidence, raw FalkorDB rows, secrets, or generated legal advice. |
| Does not prove production ranker quality. |
| Does not prove FalkorDB production-scale behavior. |
| Does not prove GraphRAG-SDK compatibility. |
| Does not validate benchmark, cost, or latency claims. |
| Does not authorize generated Cypher execution. |
| Does not prove FalkorDB runtime/vector/full-text/rerank behavior. |
| Does not make fixture IDs production IDs. |
| Does not promote D045 research into validated product behavior. |
| Does not prove raw legal text evidence quality. |

### Next Proof Work

Proof work for this area should:

- Address [`GATE-G011`](#proof-gates): Retrieval quality benchmark passes under local/open-weight embedding constraints.
- Resolve [`EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF`](#blocked--bounded-evidence): Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence.
- Resolve [`EVID-OFFLINE-CITATION-RETRIEVAL-PROOF`](#blocked--bounded-evidence): Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence.
- Resolve [`EVID-REAL-ARTIFACT-RETRIEVAL-PROOF`](#blocked--bounded-evidence): Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence.
- Resolve [`EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF`](#blocked--bounded-evidence): Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence.
- Resolve [`EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS`](#blocked--bounded-evidence): D7 quarantine classification only; record cannot satisfy requirements or promote lifecycle.
- Resolve [`EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING`](#blocked--bounded-evidence): D7 quarantine classification only; record cannot satisfy requirements or promote lifecycle.
- Resolve [`EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF`](#blocked--bounded-evidence): Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence.

## Temporal Model

### Proof Gates

| ID | Title | Priority | Status | Risk | Verification | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| `GATE-G005` | Quarantined missing-anchor: Temporal same-date multi-edition conflict policy | P1 / high-priority-blocker | blocked | high | A future proof slice defines and verifies same-date/multi-edition conflict policy. | future-temporal-proof |
|  | Does not validate temporal conflict resolution. | — | — | — | — | — |

### What This Area Does Not Prove

_Below non-claims are drawn directly from architecture registry records. They are not exhaustive._

| Non-Claim |
| --- |
| Does not validate temporal conflict resolution. |

### Next Proof Work

Proof work for this area should:

- Address [`GATE-G005`](#proof-gates): A future proof slice defines and verifies same-date/multi-edition conflict policy.

## architecture-governance

### Proof Gates

| ID | Title | Priority | Status | Risk | Verification | Owner |
| --- | --- | --- | --- | --- | --- | --- |

### Blocked / Bounded Evidence

| ID | Title | Priority | Status | Risk | Proof Level | Verification | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ACP-AHF-0001` | Historical/superseded: ACP runtime adoption is blocked until fixture validation exists | P1 / high-priority-blocker | superseded | high | static-check | D7 quarantine classification only; record cannot satisfy requirements or promote lifecycle. | architecture-control-plane |
|  | Does not prove FalkorDB ingestion or runtime loading. | — | — | — | — | — | — |
|  | Does not prove graph-vector retrieval quality. | — | — | — | — | — | — |
|  | Does not prove independent external review. | — | — | — | — | — | — |
|  | Does not prove legal correctness. | — | — | — | — | — | — |
|  | Does not prove parser completeness. | — | — | — | — | — | — |
|  | Does not prove production readiness. | — | — | — | — | — | — |
|  | Does not validate R035. | — | — | — | — | — | — |
|  | Does not validate R037. | — | — | — | — | — | — |
|  | Does not validate R038. | — | — | — | — | — | — |
|  | Health finding is a governance blocker, not product readiness evidence. | — | — | — | — | — | — |
| `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO` | Quarantined missing-anchor: Ontology architecture intake research evidence | P1 / high-priority-blocker | blocked | high | source-anchor | Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence. | architecture registry owner / M017 ontology intake |
|  | Does not make LLM output legal authority. | — | — | — | — | — | — |
|  | Does not prove FalkorDB graph-vector/runtime capability. | — | — | — | — | — | — |
|  | Does not prove GOST/BFO source correctness. | — | — | — | — | — | — |
|  | Does not prove LKIF/deontic extraction correctness. | — | — | — | — | — | — |
|  | Does not prove RusLawOD corpus priority. | — | — | — | — | — | — |
|  | Does not prove legal-answer correctness. | — | — | — | — | — | — |
|  | Does not prove ontology GraphRAG retrieval quality. | — | — | — | — | — | — |
|  | Does not prove ontology benchmark quality. | — | — | — | — | — | — |
|  | Does not prove parser completeness. | — | — | — | — | — | — |
|  | Does not prove pilot-scale readiness. | — | — | — | — | — | — |
|  | Does not prove product Legal KnowQL behavior. | — | — | — | — | — | — |

### What This Area Does Not Prove

_Below non-claims are drawn directly from architecture registry records. They are not exhaustive._

| Non-Claim |
| --- |
| Does not prove FalkorDB ingestion or runtime loading. |
| Does not prove graph-vector retrieval quality. |
| Does not prove independent external review. |
| Does not prove legal correctness. |
| Does not prove parser completeness. |
| Does not prove production readiness. |
| Does not validate R035. |
| Does not validate R037. |
| Does not validate R038. |
| Health finding is a governance blocker, not product readiness evidence. |
| Does not make LLM output legal authority. |
| Does not prove FalkorDB graph-vector/runtime capability. |
| Does not prove GOST/BFO source correctness. |
| Does not prove LKIF/deontic extraction correctness. |
| Does not prove RusLawOD corpus priority. |
| Does not prove legal-answer correctness. |
| Does not prove ontology GraphRAG retrieval quality. |
| Does not prove ontology benchmark quality. |
| Does not prove pilot-scale readiness. |
| Does not prove product Legal KnowQL behavior. |

### Next Proof Work

Proof work for this area should:

- Resolve [`ACP-AHF-0001`](#blocked--bounded-evidence): D7 quarantine classification only; record cannot satisfy requirements or promote lifecycle.
- Resolve [`EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO`](#blocked--bounded-evidence): Blocked diagnostic until every claimed anchor is retargeted to tracked canonical/current evidence or explicitly historical evidence.

---

## Global Non-Claims Summary

_The following statements appear across one or more architecture records and collectively define what this architecture does NOT validate:_

| Non-Claim | Appears In |
| --- | --- |
| Does not prove FalkorDB ingestion or runtime loading. | `ACP-AHF-0001` |
| Does not prove graph-vector retrieval quality. | `ACP-AHF-0001` |
| Does not prove independent external review. | `ACP-AHF-0001` |
| Does not prove legal correctness. | `ACP-AHF-0001` |
| Does not prove parser completeness. | `ACP-AHF-0001` |
| Does not prove production readiness. | `ACP-AHF-0001` |
| Does not validate R035. | `ACP-AHF-0001` |
| Does not validate R037. | `ACP-AHF-0001` |
| Does not validate R038. | `ACP-AHF-0001` |
| Health finding is a governance blocker, not product readiness evidence. | `ACP-AHF-0001` |
| Proposal is not an accepted architecture decision. | `ACP-AP-0001` |
| Prompt provenance is not implementation proof. | `ACP-APR-0001` |
| Decision candidate is not accepted architecture doctrine. | `ACP-DC-0001` |
| Proof gate fixture does not satisfy the gated product claim. | `ACP-PG-0001` |
| Does not make generated artifacts authoritative. | `ASSUMP-PRD-SOURCE-TRUTH` |
| Extractor check is not product runtime proof. | `CHECK-ARCHITECTURE-EXTRACTOR` |
| Does not implement Legal Nexus runtime behavior. | `COMP-LEGAL-NEXUS-ORCHESTRATOR` |
| Does not prove access-control enforcement. | `COMP-LEGAL-NEXUS-ORCHESTRATOR` |
| Does not prove product Legal KnowQL behavior. | `COMP-LEGAL-NEXUS-ORCHESTRATOR` |
| Does not make LLM output legal authority. | `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` |
| Does not prove FalkorDB graph-vector/runtime capability. | `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` |
| Does not prove amendment aggregation or inactive-version filtering. | `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` |
| Does not prove compatibility with Consultant, Garant, RusLawOD, or Akoma Ntoso sources. | `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` |
| Does not prove correct FRBR implementation. | `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` |
| Does not prove legal-answer correctness. | `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` |
| Does not prove ontology benchmark quality. | `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` |
| Does not prove pilot-scale readiness. | `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` |
| Does not assert final legal graph schema completeness. | `DATA-LEGAL-EVIDENCE-CORE` |
| Does not authorize automated legal conclusions. | `DATA-LEGAL-SOURCE-HIERARCHY` |
| Does not decide legal priority. | `DATA-LEGAL-SOURCE-HIERARCHY` |
| Does not prove automated legal collision resolution. | `DATA-LEGAL-SOURCE-HIERARCHY` |
| Does not make ML/NER outputs authoritative assertions. | `DATA-LKIF-DEONTIC-MAPPING` |
| Does not prove extraction precision or recall. | `DATA-LKIF-DEONTIC-MAPPING` |
| Does not prove negation handling or modal-verb interpretation. | `DATA-LKIF-DEONTIC-MAPPING` |
| Does not define final ontology scope. | `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY` |
| Does not prove Russian-law completeness. | `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY` |
| Does not replace project-local LegalGraph core contracts. | `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY` |
| Does not specify temporal storage implementation. | `DATA-TEMPORAL-PROPERTY-BUNDLE` |
| Does not validate temporal conflict resolution. | `DATA-TEMPORAL-PROPERTY-BUNDLE` |
| JSONL and GraphML are not source-of-truth replacements. | `DEC-D031` |
| The skill is guidance, not a source of truth. | `DEC-D032` |
| Does not allow managed embedding API fallback. | `EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF` |
| Does not close GATE-G008. | `EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF` |
| Does not close GATE-G011. | `EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF` |
| Does not make proof-local fixture metrics production metrics. | `EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF` |
| Does not promote GigaEmbeddings. | `EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF` |
| Does not prove product retrieval quality. | `EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF` |
| Does not prove production FalkorDB runtime behavior. | `EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF` |
| Does not prove production graph schema readiness. | `EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF` |
| Does not make proof-local IDs production IDs. | `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF` |
| Does not prove local embedding quality. | `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF` |
| Does not prove Consultant relation correctness. | `EVID-PARSER-CONSULTANT-CANDIDATES` |
| Does not prove FalkorDB loading/runtime behavior. | `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF` |
| Does not prove Garant ODT parser regression. | `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF` |
| Does not prove multi-document Consultant expansion. | `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF` |
| Does not prove product ETL readiness. | `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF` |
| Does not prove citation-safe retrieval readiness. | `EVID-PARSER-GOLDEN-TEST-PROOF` |
| No final legal hierarchy extraction claim. | `EVID-PARSER-ODT-SMOKE` |
| No parser completeness claim. | `EVID-PARSER-ODT-SMOKE` |
| Does not authorize GigaChat or GigaEmbeddings runtime use. | `EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF` |
| Does not persist raw legal text, raw query text, raw prompts, vectors, provider payloads, managed-API evidence, raw FalkorDB rows, secrets, or generated legal advice. | `EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF` |
| Does not prove production ranker quality. | `EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF` |
| Does not prove FalkorDB production-scale behavior. | `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS` |
| Does not prove GraphRAG-SDK compatibility. | `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS` |
| Does not validate benchmark, cost, or latency claims. | `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS` |
| Does not authorize generated Cypher execution. | `EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING` |
| Does not prove FalkorDB runtime/vector/full-text/rerank behavior. | `EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING` |
| Does not prove GOST/BFO source correctness. | `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO` |
| Does not prove LKIF/deontic extraction correctness. | `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO` |
| Does not prove RusLawOD corpus priority. | `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO` |
| Does not prove ontology GraphRAG retrieval quality. | `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO` |
| Does not make fixture IDs production IDs. | `EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF` |
| Does not promote D045 research into validated product behavior. | `EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF` |
| Does not prove raw legal text evidence quality. | `EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF` |
| Does not make Akoma Ntoso canonical. | `GATE-AKOMA-FRBR-NORMALIZATION` |
| Does not prove export compatibility. | `GATE-AKOMA-FRBR-NORMALIZATION` |
| Does not require replacing current parser record contracts. | `GATE-AKOMA-FRBR-NORMALIZATION` |
| Does not assert BFO conformance. | `GATE-BFO-GOST-ALIGNMENT` |
| Does not assert Common Logic necessity or OWL reasoning support. | `GATE-BFO-GOST-ALIGNMENT` |
| Does not assert GOST requirements. | `GATE-BFO-GOST-ALIGNMENT` |
| Does not promote any embedding model to product default. | `GATE-EMBEDDING-SUPPLY-CHAIN` |
| No product retrieval quality claim. | `GATE-G008` |
| No managed embedding API fallback claim. | `GATE-G011` |
| No production-scale FalkorDB claim. | `GATE-G015` |
| Does not authorize executing raw generated Cypher. | `GATE-GENERATED-CYPHER-SAFETY` |
| Does not prove production Legal KnowQL behavior. | `GATE-GENERATED-CYPHER-SAFETY` |
| Does not prove provider generation quality. | `GATE-GENERATED-CYPHER-SAFETY` |
| Does not produce legally binding answers. | `GATE-LEGAL-COLLISION-POLICY` |
| Does not prove court interpretation correctness. | `GATE-LEGAL-COLLISION-POLICY` |
| Does not assert current product is insecure. | `GATE-LEGAL-NEXUS-ACCESS-CONTROL` |
| Does not define a production API surface. | `GATE-LEGAL-NEXUS-ACCESS-CONTROL` |
| Does not prove ML model fitness. | `GATE-LKIF-DEONTIC-BENCHMARK` |
| Does not prove semantic extraction. | `GATE-LKIF-DEONTIC-BENCHMARK` |
| Planning alias GATE-DEONTIC-MAPPING-PROOF is not emitted as an authoritative gate. | `GATE-LKIF-DEONTIC-BENCHMARK` |
| Does not prove HNSW behavior or single-transaction graph+vector semantics. | `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` |
| Does not prove vector/full-text/FalkorDB runtime capability. | `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` |
| Does not claim that 1,000 representative documents have been processed. | `GATE-PILOT-SCALE-READINESS` |
| Does not invalidate existing bounded proofs. | `GATE-PILOT-SCALE-READINESS` |
| Does not prove production scale. | `GATE-PILOT-SCALE-READINESS` |
| Does not prove production-scale FalkorDB claim. | `GATE-PILOT-SCALE-READINESS` |
| Planning alias GATE-1000-DOC-PILOT is not emitted as an authoritative gate. | `GATE-PILOT-SCALE-READINESS` |
| Does not prove implementation readiness. | `GATE-RUSLEGALCORE-SCOPE` |
| Does not prove ontology completeness. | `GATE-RUSLEGALCORE-SCOPE` |
| No KnowQL parser. | `M001-ARCHITECTURE-ONLY-GUARDRAIL` |
| No LegalNexus API. | `M001-ARCHITECTURE-ONLY-GUARDRAIL` |
| No hybrid retrieval. | `M001-ARCHITECTURE-ONLY-GUARDRAIL` |
| No legal-answering runtime. | `M001-ARCHITECTURE-ONLY-GUARDRAIL` |
| No product ETL. | `M001-ARCHITECTURE-ONLY-GUARDRAIL` |
| No production graph schema. | `M001-ARCHITECTURE-ONLY-GUARDRAIL` |
| Does not prove production observability. | `QS-OBSERVABILITY-OPERABILITY-BASELINE` |
| Does not prove runtime SLOs. | `QS-OBSERVABILITY-OPERABILITY-BASELINE` |
| No LLM legal authority claim. | `REQ-R001` |
| No legal-answer correctness claim. | `REQ-R001` |
| No product Legal KnowQL behavior claim. | `REQ-R001` |
| No live legal graph execution claim. | `REQ-R017` |
| No credential, prompt, raw legal text, or raw row emission claim. | `REQ-R022` |
| No raw provider body persistence claim. | `REQ-R022` |
| No generated Cypher authority claim. | `REQ-R028` |
| Does not itself prove product runtime behavior. | `REQ-R029` |
| Does not prove import runtime behavior. | `REQ-TEMPORAL-STATUS-SEMANTICS` |
| Does not validate same-date conflict policy. | `REQ-TEMPORAL-STATUS-SEMANTICS` |
| Risk item does not assert current product failure. | `RISK-OVERCLAIM-RUNTIME` |
| No direct LegalGraph GraphBLAS API/control surface claim. | `S04-FALKORDB-RUNTIME-BOUNDED` |
| No legal retrieval quality claim. | `S04-FALKORDB-RUNTIME-BOUNDED` |
| No Old_project artifact accepted unchanged. | `S05-OLD-PROJECT-PRIOR-ART` |
| No production SourceBlock/EvidenceSpan creation claim. | `S05-PARSER-ODT-BOUNDARY` |
| Does not prove product behavior. | `S07-FIXED-PRD-CONSISTENCY` |
| No default promotion while blocked-environment. | `S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED` |
| No raw embedding leakage claim beyond verifier scope. | `S10-USER-BGE-M3-BASELINE` |

---

*Blockers report generated from `prd/architecture/architecture_graph_report.json`. This is a derived, non-authoritative planning artifact — it makes next proof work visible without asserting product readiness. Source-of-truth remains with PRD, GSD, ADR, and source anchor evidence.*
