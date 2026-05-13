# Product Readiness Blockers Report

> **Scope:** This report maps active proof gates, blocked evidence, and non-claims to the six capability areas required for LegalGraph Nexus product readiness. It is a planning artifact only — it does **not** assert product readiness and does not validate runtime behavior, retrieval quality, parser completeness, generated-Cypher safety, FalkorDB production scale, or legal-answer correctness.

---

## Summary Table

| Capability Area | Gate Count | Blocked / Bounded Count |
| --- | ---: | ---: |
| ETL / Parser | 1 | 3 |
| Graph Runtime | 1 | 0 |
| Legal Answering | 2 | 0 |
| Legal KnowQL / Generated Cypher | 1 | 0 |
| Retrieval / Embedding | 1 | 5 |
| Temporal Model | 1 | 0 |

## ETL / Parser

### Proof Gates

| ID | Title | Risk | Verification | Owner |
| --- | --- | --- | --- | --- |
| `GATE-G008` | Product parser and retrieval readiness gate | high | Future product proof demonstrates parser completeness boundaries, citation-safe retrieval behavior, and retrieval quality over real legal source fixtures. | future-product-parser-retrieval-proof |
|  | No parser completeness claim. | — | — | — |
|  | No product retrieval quality claim. | — | — | — |

### Blocked / Bounded Evidence

| ID | Title | Risk | Verification | Owner |
| --- | --- | --- | --- | --- |
| `EVID-PARSER-ODT-SMOKE` | Bounded ODT smoke-record evidence | high | `uv run python scripts/build-odt-smoke-records.py --check` verifies ODT smoke artifact freshness. | M006/S03 |
|  | No final legal hierarchy extraction claim. | — | — | — |
|  | No parser completeness claim. | — | — | — |
| `S05-OLD-PROJECT-PRIOR-ART` | Old_project artifacts remain prior art | high | Downstream designs classify legacy reuse as prior art and avoid blessing ConsultantPlus behavior for Garant ODT. | S08 final architecture review / future parser owners |
|  | No Old_project artifact accepted unchanged. | — | — | — |
|  | No parser completeness claim. | — | — | — |
| `S05-PARSER-ODT-BOUNDARY` | Real ODT parser evidence boundary | high | S05 verifier passes; future parser tests prove final extraction behavior before promotion. | S05/S08 parser evidence consolidation |
|  | No final legal hierarchy extraction claim. | — | — | — |
|  | No parser completeness claim. | — | — | — |
|  | No production SourceBlock/EvidenceSpan creation claim. | — | — | — |

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
- Resolve [`S05-OLD-PROJECT-PRIOR-ART`](#blocked--bounded-evidence): Downstream designs classify legacy reuse as prior art and avoid blessing ConsultantPlus behavior for Garant ODT.
- Resolve [`S05-PARSER-ODT-BOUNDARY`](#blocked--bounded-evidence): S05 verifier passes; future parser tests prove final extraction behavior before promotion.

## Graph Runtime

### Proof Gates

| ID | Title | Risk | Verification | Owner |
| --- | --- | --- | --- | --- |
| `GATE-G015` | FalkorDBLite to Docker migration runbook | medium | Migration runbook is executed against bounded fixtures and runtime diagnostics. | future-runtime-migration-proof |
|  | No production-scale FalkorDB claim. | — | — | — |

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

| ID | Title | Risk | Verification | Owner |
| --- | --- | --- | --- | --- |
| `GATE-EMBEDDING-SUPPLY-CHAIN` | Embedding model supply-chain integrity gate | high | Future embedding proof records model source, checksum or revision, local runtime envelope, vector dimension, and no-secret/no-raw-vector leakage checks. | future-embedding-supply-chain-proof |
|  | Does not allow managed embedding API fallback. | — | — | — |
|  | Does not promote any embedding model to product default. | — | — | — |
|  | Does not prove product retrieval quality. | — | — | — |
| `GATE-LEGAL-NEXUS-ACCESS-CONTROL` | Legal Nexus access-control proof gate | high | Future security proof defines caller boundaries, authorization policy, audit logging, and denial diagnostics for Legal Nexus operations. | future-api-security-proof |
|  | Does not assert current product is insecure. | — | — | — |
|  | Does not define a production API surface. | — | — | — |
|  | Does not prove access-control enforcement. | — | — | — |

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

| ID | Title | Risk | Verification | Owner |
| --- | --- | --- | --- | --- |
| `GATE-GENERATED-CYPHER-SAFETY` | Generated-Cypher safety and validation gate | critical | A future product proof demonstrates validator acceptance/rejection behavior across representative Legal KnowQL tasks and live graph schemas. | future-generated-cypher-safety-proof |
|  | Does not authorize executing raw generated Cypher. | — | — | — |
|  | Does not prove production Legal KnowQL behavior. | — | — | — |
|  | Does not prove provider generation quality. | — | — | — |

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

| ID | Title | Risk | Verification | Owner |
| --- | --- | --- | --- | --- |
| `GATE-G011` | Local embedding quality proof | high | Retrieval quality benchmark passes under local/open-weight embedding constraints. | future-retrieval-quality-proof |
|  | No managed embedding API fallback claim. | — | — | — |
|  | No product retrieval quality claim. | — | — | — |

### Blocked / Bounded Evidence

| ID | Title | Risk | Verification | Owner |
| --- | --- | --- | --- | --- |
| `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF` | Offline citation-safe retrieval proof | high | `uv run python scripts/verify-offline-citation-retrieval-proof.py` proves 6 offline citation retrieval cases with selected_count=2, scoped_no_answer_count=1, rejected_count=3, validator_accepted_count=3, validator_rejected_count=1, and mismatch_count=0. | M014/S02 |
|  | Does not close GATE-G008. | — | — | — |
|  | Does not close GATE-G011. | — | — | — |
|  | Does not make LLM output legal authority. | — | — | — |
|  | Does not make proof-local IDs production IDs. | — | — | — |
|  | Does not prove legal-answer correctness. | — | — | — |
|  | Does not prove local embedding quality. | — | — | — |
|  | Does not prove parser completeness. | — | — | — |
|  | Does not prove product retrieval quality. | — | — | — |
|  | Does not prove production FalkorDB runtime behavior. | — | — | — |
|  | Does not prove production graph schema readiness. | — | — | — |
| `EVID-REAL-ARTIFACT-RETRIEVAL-PROOF` | Real-artifact retrieval output ID proof | high | `uv run python scripts/verify-real-artifact-retrieval-proof.py` proves 7 real-artifact-derived cases with 2 accepted, 5 rejected, and mismatch_count=0; M012 validator regression remains green. | M013/S02 |
|  | Does not close GATE-G008. | — | — | — |
|  | Does not close GATE-G011. | — | — | — |
|  | Does not make LLM output legal authority. | — | — | — |
|  | Does not make proof-local IDs production IDs. | — | — | — |
|  | Does not prove legal-answer correctness. | — | — | — |
|  | Does not prove local embedding quality. | — | — | — |
|  | Does not prove parser completeness. | — | — | — |
|  | Does not prove product retrieval quality. | — | — | — |
|  | Does not prove production FalkorDB runtime behavior. | — | — | — |
|  | Does not prove production graph schema readiness. | — | — | — |
| `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS` | GraphRAG/FalkorDB mathematical analysis research input | high | Assessment classifies ideas into applicable-now principles, proof-gated candidates, and deferred/not-adopted claims; future proof must validate any runtime, SDK, benchmark, or retrieval-quality claim. | M011/S01 |
|  | Does not prove FalkorDB production-scale behavior. | — | — | — |
|  | Does not prove GraphRAG-SDK compatibility. | — | — | — |
|  | Does not prove legal-answer correctness. | — | — | — |
|  | Does not prove product retrieval quality. | — | — | — |
|  | Does not validate benchmark, cost, or latency claims. | — | — | — |
| `EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING` | Habr Legal RAG iteration and scaling research input | high | Human-reviewed JSON comparison classifies all transferable ideas as requiring project-specific verification before adoption; future proof must validate retrieval IDs, evidence precision, no-answer behavior, scale/noise degradation, and any runtime or model claim. | D045 / future-retrieval-quality-proof |
|  | Does not authorize generated Cypher execution. | — | — | — |
|  | Does not prove FalkorDB runtime/vector/full-text/rerank behavior. | — | — | — |
|  | Does not prove legal-answer correctness. | — | — | — |
|  | Does not prove parser completeness. | — | — | — |
|  | Does not prove product retrieval quality. | — | — | — |
| `EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF` | Retrieval output ID validator bounded proof | high | `uv run python scripts/verify-retrieval-output-validator.py` and `uv run pytest tests/test_retrieval_output_validator.py -q` prove fixture/unit/CLI behavior for required M012 diagnostic cases only. | M012/S02 |
|  | Does not make LLM output legal authority. | — | — | — |
|  | Does not make fixture IDs production IDs. | — | — | — |
|  | Does not promote D045 research into validated product behavior. | — | — | — |
|  | Does not prove legal-answer correctness. | — | — | — |
|  | Does not prove parser completeness. | — | — | — |
|  | Does not prove product retrieval quality. | — | — | — |
|  | Does not prove production FalkorDB runtime behavior. | — | — | — |
|  | Does not prove raw legal text evidence quality. | — | — | — |

### What This Area Does Not Prove

_Below non-claims are drawn directly from architecture registry records. They are not exhaustive._

| Non-Claim |
| --- |
| No managed embedding API fallback claim. |
| No product retrieval quality claim. |
| Does not close GATE-G008. |
| Does not close GATE-G011. |
| Does not make LLM output legal authority. |
| Does not make proof-local IDs production IDs. |
| Does not prove legal-answer correctness. |
| Does not prove local embedding quality. |
| Does not prove parser completeness. |
| Does not prove product retrieval quality. |
| Does not prove production FalkorDB runtime behavior. |
| Does not prove production graph schema readiness. |
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
- Resolve [`EVID-OFFLINE-CITATION-RETRIEVAL-PROOF`](#blocked--bounded-evidence): `uv run python scripts/verify-offline-citation-retrieval-proof.py` proves 6 offline citation retrieval cases with selected_count=2, scoped_no_answer_count=1, rejected_count=3, validator_accepted_count=3, validator_rejected_count=1, and mismatch_count=0.
- Resolve [`EVID-REAL-ARTIFACT-RETRIEVAL-PROOF`](#blocked--bounded-evidence): `uv run python scripts/verify-real-artifact-retrieval-proof.py` proves 7 real-artifact-derived cases with 2 accepted, 5 rejected, and mismatch_count=0; M012 validator regression remains green.
- Resolve [`EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS`](#blocked--bounded-evidence): Assessment classifies ideas into applicable-now principles, proof-gated candidates, and deferred/not-adopted claims; future proof must validate any runtime, SDK, benchmark, or retrieval-quality claim.
- Resolve [`EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING`](#blocked--bounded-evidence): Human-reviewed JSON comparison classifies all transferable ideas as requiring project-specific verification before adoption; future proof must validate retrieval IDs, evidence precision, no-answer behavior, scale/noise degradation, and any runtime or model claim.
- Resolve [`EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF`](#blocked--bounded-evidence): `uv run python scripts/verify-retrieval-output-validator.py` and `uv run pytest tests/test_retrieval_output_validator.py -q` prove fixture/unit/CLI behavior for required M012 diagnostic cases only.

## Temporal Model

### Proof Gates

| ID | Title | Risk | Verification | Owner |
| --- | --- | --- | --- | --- |
| `GATE-G005` | Temporal same-date multi-edition conflict policy | high | A future proof slice defines and verifies same-date/multi-edition conflict policy. | future-temporal-proof |
|  | Does not validate temporal conflict resolution. | — | — | — |

### What This Area Does Not Prove

_Below non-claims are drawn directly from architecture registry records. They are not exhaustive._

| Non-Claim |
| --- |
| Does not validate temporal conflict resolution. |

### Next Proof Work

Proof work for this area should:

- Address [`GATE-G005`](#proof-gates): A future proof slice defines and verifies same-date/multi-edition conflict policy.

---

## Global Non-Claims Summary

_The following statements appear across one or more architecture records and collectively define what this architecture does NOT validate:_

| Non-Claim | Appears In |
| --- | --- |
| Does not make generated artifacts authoritative. | `ASSUMP-PRD-SOURCE-TRUTH` |
| Extractor check is not product runtime proof. | `CHECK-ARCHITECTURE-EXTRACTOR` |
| Does not implement Legal Nexus runtime behavior. | `COMP-LEGAL-NEXUS-ORCHESTRATOR` |
| Does not prove access-control enforcement. | `COMP-LEGAL-NEXUS-ORCHESTRATOR` |
| Does not prove product Legal KnowQL behavior. | `COMP-LEGAL-NEXUS-ORCHESTRATOR` |
| Does not assert final legal graph schema completeness. | `DATA-LEGAL-EVIDENCE-CORE` |
| Does not prove legal-answer correctness. | `DATA-LEGAL-EVIDENCE-CORE` |
| Does not prove parser completeness. | `DATA-LEGAL-EVIDENCE-CORE` |
| Does not specify temporal storage implementation. | `DATA-TEMPORAL-PROPERTY-BUNDLE` |
| Does not validate temporal conflict resolution. | `DATA-TEMPORAL-PROPERTY-BUNDLE` |
| JSONL and GraphML are not source-of-truth replacements. | `DEC-D031` |
| The skill is guidance, not a source of truth. | `DEC-D032` |
| Does not close GATE-G008. | `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF` |
| Does not close GATE-G011. | `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF` |
| Does not make LLM output legal authority. | `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF` |
| Does not make proof-local IDs production IDs. | `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF` |
| Does not prove local embedding quality. | `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF` |
| Does not prove product retrieval quality. | `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF` |
| Does not prove production FalkorDB runtime behavior. | `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF` |
| Does not prove production graph schema readiness. | `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF` |
| Does not prove Consultant relation correctness. | `EVID-PARSER-CONSULTANT-CANDIDATES` |
| Does not prove FalkorDB loading/runtime behavior. | `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF` |
| Does not prove Garant ODT parser regression. | `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF` |
| Does not prove multi-document Consultant expansion. | `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF` |
| Does not prove product ETL readiness. | `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF` |
| Does not prove citation-safe retrieval readiness. | `EVID-PARSER-GOLDEN-TEST-PROOF` |
| No final legal hierarchy extraction claim. | `EVID-PARSER-ODT-SMOKE` |
| No parser completeness claim. | `EVID-PARSER-ODT-SMOKE` |
| Does not prove legal correctness. | `EVID-PARSER-SOURCE-FIXTURE-INVENTORY` |
| Does not prove FalkorDB production-scale behavior. | `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS` |
| Does not prove GraphRAG-SDK compatibility. | `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS` |
| Does not validate benchmark, cost, or latency claims. | `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS` |
| Does not authorize generated Cypher execution. | `EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING` |
| Does not prove FalkorDB runtime/vector/full-text/rerank behavior. | `EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING` |
| Does not make fixture IDs production IDs. | `EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF` |
| Does not promote D045 research into validated product behavior. | `EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF` |
| Does not prove raw legal text evidence quality. | `EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF` |
| Does not allow managed embedding API fallback. | `GATE-EMBEDDING-SUPPLY-CHAIN` |
| Does not promote any embedding model to product default. | `GATE-EMBEDDING-SUPPLY-CHAIN` |
| No product retrieval quality claim. | `GATE-G008` |
| No managed embedding API fallback claim. | `GATE-G011` |
| No production-scale FalkorDB claim. | `GATE-G015` |
| Does not authorize executing raw generated Cypher. | `GATE-GENERATED-CYPHER-SAFETY` |
| Does not prove production Legal KnowQL behavior. | `GATE-GENERATED-CYPHER-SAFETY` |
| Does not prove provider generation quality. | `GATE-GENERATED-CYPHER-SAFETY` |
| Does not assert current product is insecure. | `GATE-LEGAL-NEXUS-ACCESS-CONTROL` |
| Does not define a production API surface. | `GATE-LEGAL-NEXUS-ACCESS-CONTROL` |
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

*Blockers report generated from `prd/architecture/architecture_graph_report.json`. This is a planning artifact — it makes next proof work visible without asserting product readiness. Source-of-truth remains with PRD, GSD, ADR, and source anchor evidence.*
